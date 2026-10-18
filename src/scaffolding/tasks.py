from dataclasses import dataclass, replace

from scaffolding.records import ChoiceQuestion, ItemAnswer, OpenQuestion, SelectionMode, TrueFalseQuestion

Question = ChoiceQuestion | TrueFalseQuestion | OpenQuestion


class Rejected(Exception):
    pass


@dataclass(frozen=True)
class Task:
    task_id: str
    questions: tuple[Question, ...]
    published: bool = False
    started: bool = False
    submitted: bool = False


@dataclass(frozen=True)
class ListedQuestion:
    prompt: str
    choices: tuple[str, ...] = ()
    requirements: str = ""
    selection: str = ""


@dataclass(frozen=True)
class ListedTask:
    task_id: str
    status: str
    questions: tuple[ListedQuestion, ...]


def display_status(task: Task) -> str | None:
    if not task.published:
        return None
    if task.submitted:
        return "已完成"
    return "待办"


def apply_answer(question, current: ItemAnswer, *, text: str | None = None, selected: tuple[str, ...] | None = None) -> ItemAnswer:
    if isinstance(question, OpenQuestion):
        if selected not in (None, ()):
            raise Rejected("open questions have no choices")
        new_text = current.text if text is None else text
        revisions = current.text_revisions + ((current.text,) if new_text != current.text else ())
        return ItemAnswer(text=new_text, text_revisions=revisions)
    if text not in (None, ""):
        raise Rejected("this question stores selected options")
    new_selected = current.selected if selected is None else selected
    if isinstance(question, TrueFalseQuestion) and new_selected not in ((), ("正确",), ("错误",)):
        raise Rejected("true/false answers are 正确 or 错误")
    if isinstance(question, ChoiceQuestion):
        if any(item not in question.choices for item in new_selected) or len(set(new_selected)) != len(new_selected):
            raise Rejected("selection must be one of the choices")
        if question.selection == SelectionMode.SINGLE and len(new_selected) > 1:
            raise Rejected("single choice takes one option")
    revisions = current.selected_revisions + ((current.selected,) if new_selected != current.selected else ())
    return ItemAnswer(selected=new_selected, selected_revisions=revisions)


class StudentWork:
    def __init__(self, task_id: str, questions: tuple) -> None:
        self.task_id = task_id
        self.questions = questions
        self.answers = tuple(ItemAnswer() for _ in questions)
        self.submitted = False

    def edit(self, index: int, *, text: str | None = None, selected: tuple[str, ...] | None = None) -> None:
        if self.submitted:
            raise Rejected("submitted answers are read only")
        updated = apply_answer(self.questions[index], self.answers[index], text=text, selected=selected)
        answers = list(self.answers)
        answers[index] = updated
        self.answers = tuple(answers)


def _public(question: Question) -> ListedQuestion:
    if isinstance(question, ChoiceQuestion):
        return ListedQuestion(question.prompt, question.choices, selection=question.selection.value)
    if isinstance(question, TrueFalseQuestion):
        return ListedQuestion(question.prompt, ("正确", "错误"))
    return ListedQuestion(question.prompt, requirements=question.requirements)


class TaskCatalog:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._works: dict[str, StudentWork] = {}
        self._next_id = 1

    def create(self, questions: tuple[Question, ...]) -> Task:
        task = Task(f"task-{self._next_id}", questions)
        self._next_id += 1
        self._tasks[task.task_id] = task
        return task

    def get(self, task_id: str) -> Task:
        return self._tasks[task_id]

    def update(self, task_id: str, questions: tuple[Question, ...]) -> Task:
        task = self.get(task_id)
        if task.started:
            raise Rejected("started tasks can only be deleted")
        updated = replace(task, questions=questions)
        self._tasks[task_id] = updated
        return updated

    def publish(self, task_id: str) -> Task:
        task = self.get(task_id)
        if task.questions == ():
            raise Rejected("a task needs a question before publish")
        updated = replace(task, published=True)
        self._tasks[task_id] = updated
        return updated

    def delete(self, task_id: str) -> None:
        del self._tasks[task_id]
        self._works.pop(task_id, None)

    def student_tasks(self) -> tuple[ListedTask, ...]:
        listed = []
        for task in self._tasks.values():
            status = display_status(task)
            if status is None:
                continue
            listed.append(ListedTask(task.task_id, status, tuple(_public(question) for question in task.questions)))
        return tuple(listed)

    def start(self, task_id: str) -> StudentWork:
        task = self.get(task_id)
        if not task.published or task.started or task.questions == ():
            raise Rejected("student cannot start")
        self._tasks[task_id] = replace(task, started=True)
        work = StudentWork(task_id, task.questions)
        self._works[task_id] = work
        return work

    def work(self, task_id: str) -> StudentWork:
        return self._works[task_id]
