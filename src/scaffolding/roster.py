from dataclasses import dataclass


class RosterError(Exception):
    pass


@dataclass(frozen=True)
class ClassRecord:
    class_id: str
    name: str


@dataclass(frozen=True)
class StudentRecord:
    account: str
    password: str
    name: str
    class_id: str


@dataclass(frozen=True)
class ImportFailure:
    row: int
    reason: str


@dataclass(frozen=True)
class ImportResult:
    added: tuple[StudentRecord, ...]
    failures: tuple[ImportFailure, ...]


def _clean(value: str) -> str:
    return value.strip()


class Roster:
    def __init__(self) -> None:
        self.teacher_account = "643590872"
        self.teacher_password = "643590872"
        self._classes: dict[str, ClassRecord] = {}
        self._order: list[str] = []
        self._students: dict[str, StudentRecord] = {}
        self._members: dict[str, list[str]] = {}
        self._next_class = 1

    def authenticate_teacher(self, account: str, password: str) -> bool:
        return account == self.teacher_account and password == self.teacher_password

    def authenticate_student(self, account: str, password: str) -> StudentRecord | None:
        student = self._students.get(account)
        if student is None or student.password != password:
            return None
        return student

    def change_teacher_password(self, old: str, new: str) -> None:
        if old != self.teacher_password:
            raise RosterError("原密码不正确")
        cleaned = _clean(new)
        if cleaned == "":
            raise RosterError("密码不能为空")
        self.teacher_password = cleaned

    def create_class(self, name: str) -> ClassRecord:
        cleaned = _clean(name)
        if cleaned == "":
            raise RosterError("先填写班级名称")
        if any(item.name == cleaned for item in self._classes.values()):
            raise RosterError("已有同名班级")
        class_id = "class-" + str(self._next_class)
        self._next_class += 1
        record = ClassRecord(class_id, cleaned)
        self._classes[class_id] = record
        self._order.append(class_id)
        self._members[class_id] = []
        return record

    def classes(self) -> tuple[ClassRecord, ...]:
        return tuple(self._classes[class_id] for class_id in self._order)

    def students(self, class_id: str) -> tuple[StudentRecord, ...]:
        self._require_class(class_id)
        return tuple(self._students[account] for account in self._members[class_id])

    def student(self, class_id: str, account: str) -> StudentRecord:
        self._require_class(class_id)
        student = self._students.get(account)
        if student is None or student.class_id != class_id:
            raise RosterError("学生不存在")
        return student

    def import_rows(
        self,
        class_id: str,
        rows: tuple[tuple[int, str | None, str | None, str | None], ...],
    ) -> ImportResult:
        self._require_class(class_id)
        added: list[StudentRecord] = []
        failures: list[ImportFailure] = []
        seen: set[str] = set()
        for row, account, password, name in rows:
            raw = (account, password, name)
            if all(item is None or _clean(item) == "" for item in raw):
                continue
            if any(item is None for item in raw):
                failures.append(ImportFailure(row, "缺账号、密码或姓名"))
                continue
            account = _clean(account)
            password = _clean(password)
            name = _clean(name)
            if account in seen:
                failures.append(ImportFailure(row, "账号在这份表里重复"))
                continue
            seen.add(account)
            if account == "" or password == "":
                failures.append(ImportFailure(row, "账号或密码为空"))
                continue
            if name == "":
                failures.append(ImportFailure(row, "姓名为空"))
                continue
            if account in self._students:
                failures.append(ImportFailure(row, "账号已经存在"))
                continue
            student = StudentRecord(account, password, name, class_id)
            self._students[account] = student
            self._members[class_id].append(account)
            added.append(student)
        return ImportResult(tuple(added), tuple(failures))

    def register_student(self, class_id: str, account: str, password: str, name: str) -> StudentRecord:
        if not self._classes:
            raise RosterError("先由教师创建班级")
        class_id = _clean(class_id)
        if class_id == "":
            raise RosterError("先选择班级")
        if class_id not in self._classes:
            raise RosterError("班级不存在")
        account = _clean(account)
        password = _clean(password)
        name = _clean(name)
        if account == "" or password == "":
            raise RosterError("账号或密码为空")
        if name == "":
            raise RosterError("姓名为空")
        if account in self._students:
            raise RosterError("账号已经存在")
        student = StudentRecord(account, password, name, class_id)
        self._students[account] = student
        self._members[class_id].append(account)
        return student

    def rename_student(self, class_id: str, account: str, name: str) -> None:
        student = self.student(class_id, account)
        cleaned = _clean(name)
        if cleaned == "":
            raise RosterError("姓名不能为空")
        self._students[account] = StudentRecord(
            student.account, student.password, cleaned, student.class_id
        )

    def reset_password(self, class_id: str, account: str, password: str) -> None:
        student = self.student(class_id, account)
        cleaned = _clean(password)
        if cleaned == "":
            raise RosterError("密码不能为空")
        self._students[account] = StudentRecord(
            student.account, cleaned, student.name, student.class_id
        )

    def move_student(self, account: str, class_id: str) -> StudentRecord:
        account = _clean(account)
        student = self._students.get(account)
        if account == "" or student is None:
            raise RosterError("学生不存在")
        class_id = _clean(class_id)
        if class_id == "":
            raise RosterError("先选择班级")
        if class_id not in self._classes:
            raise RosterError("班级不存在")
        if student.class_id == class_id:
            return student
        self._members[student.class_id].remove(account)
        updated = StudentRecord(student.account, student.password, student.name, class_id)
        self._students[account] = updated
        self._members[class_id].append(account)
        return updated

    def remove_student(self, class_id: str, account: str) -> str:
        self.student(class_id, account)
        del self._students[account]
        self._members[class_id].remove(account)
        return account

    def delete_class(self, class_id: str) -> tuple[str, ...]:
        self._require_class(class_id)
        removed = tuple(self._members[class_id])
        for account in removed:
            del self._students[account]
        del self._members[class_id]
        del self._classes[class_id]
        self._order.remove(class_id)
        return removed

    def _require_class(self, class_id: str) -> None:
        if class_id not in self._classes:
            raise RosterError("班级不存在")
