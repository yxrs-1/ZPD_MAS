from dataclasses import dataclass, replace

from scaffolding.records import ChoiceQuestion, OpenQuestion, TrueFalseQuestion

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


def _public(question: Question) -> ListedQuestion:
    if isinstance(question, ChoiceQuestion):
        return ListedQuestion(question.prompt, question.choices, selection=question.selection.value)
    if isinstance(question, TrueFalseQuestion):
        return ListedQuestion(question.prompt, ("正确", "错误"))
    return ListedQuestion(question.prompt, requirements=question.requirements)


class TaskCatalog:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
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

    def student_tasks(self) -> tuple[ListedTask, ...]:
        listed = []
        for task in self._tasks.values():
            status = display_status(task)
            if status is None:
                continue
            listed.append(ListedTask(task.task_id, status, tuple(_public(question) for question in task.questions)))
        return tuple(listed)

    def start(self, task_id: str) -> Task:
        task = self.get(task_id)
        if not task.published or task.started or task.questions == ():
            raise Rejected("student cannot start")
        updated = replace(task, started=True)
        self._tasks[task_id] = updated
        return updated
