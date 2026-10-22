from dataclasses import replace

from scaffolding.records import ChoiceQuestion, TrueFalseQuestion
from scaffolding.roster import RosterError
from scaffolding.tasks import ListedQuestion, ListedTask, Rejected, StudentWork, display_status


class Classwork:
    def __init__(self, roster) -> None:
        self._roster = roster
        self._catalog = None
        self._assigned: dict[str, tuple[str, ...]] = {}
        self._works: dict[tuple[str, str], StudentWork] = {}

    def assign(self, catalog, task_id: str, class_ids: tuple[str, ...]) -> None:
        task = catalog.get(task_id)
        if not task.published:
            raise RosterError("先发布再布置")
        unique: list[str] = []
        for class_id in class_ids:
            self._roster.students(class_id)
            if class_id not in unique:
                unique.append(class_id)
        self._catalog = catalog
        keep: set[str] = set()
        for class_id in unique:
            for student in self._roster.students(class_id):
                keep.add(student.account)
        for account, work_task in list(self._works):
            if work_task == task_id and account not in keep:
                del self._works[(account, work_task)]
        if unique:
            self._assigned[task_id] = tuple(unique)
        else:
            self._assigned.pop(task_id, None)
        self._idle_if_quiet(task_id)

    def assigned(self, task_id: str) -> tuple[str, ...]:
        return self._assigned.get(task_id, ())

    def tasks_for_class(self, class_id: str) -> tuple[str, ...]:
        return tuple(
            task_id for task_id, class_ids in self._assigned.items() if class_id in class_ids
        )

    def drop_student(self, account: str) -> None:
        affected: list[str] = []
        for key in list(self._works):
            if key[0] == account:
                affected.append(key[1])
                del self._works[key]
        for task_id in affected:
            self._idle_if_quiet(task_id)

    def drop_class(self, class_id: str) -> None:
        try:
            accounts = tuple(student.account for student in self._roster.students(class_id))
        except RosterError:
            accounts = ()
        for task_id in list(self._assigned):
            remaining = tuple(item for item in self._assigned[task_id] if item != class_id)
            if len(remaining) == len(self._assigned[task_id]):
                continue
            if remaining:
                self._assigned[task_id] = remaining
            else:
                del self._assigned[task_id]
        for account in accounts:
            self.drop_student(account)

    def drop_task(self, task_id: str) -> None:
        self._assigned.pop(task_id, None)
        for key in list(self._works):
            if key[1] == task_id:
                del self._works[key]

    def any_started(self, task_id: str) -> bool:
        return any(work_task == task_id for _account, work_task in self._works)

    def _idle_if_quiet(self, task_id: str) -> None:
        catalog = self._catalog
        if catalog is None or self.any_started(task_id):
            return
        try:
            catalog.get(task_id)
        except KeyError:
            return
        catalog.note_idle(task_id)


def _listed_question(question) -> ListedQuestion:
    if isinstance(question, ChoiceQuestion):
        return ListedQuestion(question.prompt, question.choices, selection=question.selection.value)
    if isinstance(question, TrueFalseQuestion):
        return ListedQuestion(question.prompt, ("正确", "错误"))
    return ListedQuestion(question.prompt, requirements=question.requirements)


class StudentView:
    def __init__(self, catalog, classwork: Classwork, account: str, class_id: str) -> None:
        self._catalog = catalog
        self._classwork = classwork
        self._account = account
        self._class_id = class_id

    def student_tasks(self) -> tuple[ListedTask, ...]:
        listed = []
        for task_id in self._classwork.tasks_for_class(self._class_id):
            try:
                task = self.get(task_id)
            except KeyError:
                continue
            status = display_status(task)
            if status is None:
                continue
            listed.append(ListedTask(
                task.task_id,
                status,
                tuple(_listed_question(question) for question in task.questions),
            ))
        return tuple(listed)

    def get(self, task_id: str):
        try:
            self._classwork._roster.student(self._class_id, self._account)
        except RosterError:
            raise KeyError(task_id) from None
        task = self._catalog.get(task_id)
        if not task.published or self._class_id not in self._classwork.assigned(task_id):
            raise KeyError(task_id)
        work = self._classwork._works.get((self._account, task_id))
        return replace(task, started=work is not None, submitted=bool(work and work.submitted))

    def start(self, task_id: str) -> StudentWork:
        task = self.get(task_id)
        if task.started or task.questions == ():
            raise Rejected("student cannot start")
        self._catalog.note_started(task_id)
        work = StudentWork(task_id, task.questions)
        self._classwork._works[(self._account, task_id)] = work
        return work

    def work(self, task_id: str) -> StudentWork:
        found = self._classwork._works.get((self._account, task_id))
        if found is None:
            raise KeyError(task_id)
        return found

    def mark_submitted(self, task_id: str):
        if not self.get(task_id).started:
            raise Rejected("cannot submit before start")
        self.work(task_id).submitted = True
        return self.get(task_id)
