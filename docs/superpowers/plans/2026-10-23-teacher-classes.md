# 班级和学生账号 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让教师和学生登录，教师管理班级并批量导入学生，再把已发布任务布置给班级；每名学生单独作答，教师可查看详情，这些内容写入本机文件。

**Architecture:** 新增 `Roster` 保存教师密码、班级和学生。`Classwork` 保存布置，以及按「学生账号 + 任务」分开的作答。现有 `TaskCatalog` 仍保存题目；任一学生开始后，用新增的 `note_started` 把任务标成已开始。课堂在教师、学生地址上检查 Cookie。班级页和详情页是新页面。`classroom.json` 在每次修改成功后整份重写。

**Tech Stack:** Python 3.14，pytest 9，标准库。实现从 `origin/main` 的 `9433deb` 建工作区。规格在本地 `master` 的 `83dd4cf`，文件是 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-23-teacher-classes-design.md`。工作区里若没有这份规格，在 Task 8 从该文件原样复制，不要改写。测试命令是 `.\.venv\Scripts\python.exe -m pytest`。PowerShell 下不要使用 `&&` 或 bash heredoc；提交用 `git commit -m "message"`。不要改 git config，不要 push。不要提交本计划。

## Global Constraints

- 正式运行读取当前目录下的 `classroom.json`。测试传入另一份临时文件。文件不存在就新建，教师账号是 `643590872`，密码是 `643590872`。密码按原文保存。登录标记只在这次进程里有效。
- 教师 Cookie 名是 `teacher`，学生 Cookie 名是 `student`。登录字段名是 `account` 和 `password`，按钮是「登录」，提交到这一边的 `/login`。
- 班级标识按创建顺序是 `class-1`、`class-2`。名称去掉两端空白后不能为空，也不能和已有班级相同。学生账号去掉两端空白后唯一，只属于一个班级。
- 作答记在「学生账号 + 任务」上。任务本身保留题目和是否已发布。任务页「已开始」表示至少有一名学生已经开始。有学生开始后，题目不能再改，教师只能删除；仍可把任务布置给还没布置的班级。
- 布置在已发布任务的任务页完成。选择框名是 `class_id`，按钮是「布置」。未发布不能布置。提交后，选中的班级是全部布置。取消一个班的布置时，只去掉这个班的学生在这份任务上的作答。一个班级都不选，等于取消全部分配。
- 学生只能看到已发布且布置给自己班级的任务。教师详情只读。教师能看到参考答案和解析，不论学生是否提交。学生页仍是提交后才显示参考答案和解析。
- 详情状态是「还没作答」「待办」「已完成」。学生待办里，还没打开的已布置任务状态是「待办」。
- Excel 是 xlsx 文件字节。只读第一个工作表，第一行是「账号」「密码」「姓名」。只读这三列。空行跳过。合格行导入，不合格行写明规格里的原因。同一账号多次出现时，第一次按规则处理，后面几次是「账号在这份表里重复」。已有账号不覆盖。
- 修改密码的字段是 `old_password` 和 `password`。修改姓名的字段是 `name`。重置密码的字段是 `password`。创建班级的字段是 `name`。导入文件字段是 `file`。
- 失败句和状态以规格为准：登录失败是「账号或密码不正确」，状态 200。不存在的班级、学生、任务在打开时是 404。布置里带有不存在的班级时状态 200，布置不生效。写入失败显示「没有写入文件」，内存和文件保持修改前的内容。
- 页面文字按文字写入。HTML 用拼接，不用 `str.format`。课堂地址带 `/teacher` 或 `/student`，单独调用页面时不带前缀。
- 发布、草稿、提炼、生成、作答、求助和支架的原有规则保持不变。教材和课标不在这里上传或预置。测试不调用 `serve`，不打开浏览器，不访问网络。
- 不修改 `model_decision.py`、`model_scaffold.py`、`model_generator.py`、`model_extractor.py`、`model_text.py`、`text_generation.py`、`html_assets.py`、`agents.py`、`scripted.py`。

## File Map

- Create: `src/scaffolding/roster.py` — 教师密码、班级、学生、导入结果。
- Create: `src/scaffolding/sheet.py` — 从 xlsx 字节读出学生行。
- Create: `src/scaffolding/classwork.py` — 布置、按学生分开的作答、学生目录视图。
- Create: `src/scaffolding/class_page.py` — 班级页、学生详情、教师只读任务详情。
- Create: `src/scaffolding/store.py` — 读写 `classroom.json`。
- Modify: `src/scaffolding/tasks.py` — `note_started`、`note_idle`。
- Modify: `src/scaffolding/session.py` — `Session.restore`，重启后不调用决策智能体。
- Modify: `src/scaffolding/teacher_page.py` — 登录后的班级链接、修改密码、退出、布置选择框。`PageResponse` 增加 `set_cookie`。
- Modify: `src/scaffolding/student_page.py` — `PageResponse` 增加 `set_cookie`。学生页增加退出。
- Modify: `src/scaffolding/classroom.py` — Cookie、上传字节、班级路由、保存文件。
- Modify: `tests/classroom_helpers.py` — 登录和导入辅助。
- Create: `tests/test_roster.py`
- Create: `tests/test_sheet.py`
- Create: `tests/test_class_login.py`
- Create: `tests/test_class_page.py`
- Create: `tests/test_classwork.py`
- Create: `tests/test_class_detail.py`
- Create: `tests/test_classroom_store.py`
- Create: `tests/test_class_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-23-teacher-classes-design.md`

Task 3 先要求登录，已登录学生暂时仍看到全部已发布任务，这样现有课堂测试只需补上登录。Task 5 再改成只看已布置的任务，并更新这些测试。

---

### Task 1: 记录班级和学生账号

**Files:**
- Create: `src/scaffolding/roster.py`
- Test: `tests/test_roster.py`

**Interfaces:**
- Consumes: 无。
- Produces: `RosterError(message: str)`。`ClassRecord(class_id, name)`。`StudentRecord(account, password, name, class_id)`。`ImportFailure(row: int, reason: str)`。`ImportResult(added, failures)`。`Roster.authenticate_teacher(account, password) -> bool`。`authenticate_student(account, password) -> StudentRecord | None`。`change_teacher_password(old, new) -> None`。`create_class(name) -> ClassRecord`。`classes() -> tuple[ClassRecord, ...]`。`students(class_id) -> tuple[StudentRecord, ...]`。`student(class_id, account) -> StudentRecord`。`import_rows(class_id, rows: tuple[tuple[int, str | None, str | None, str | None], ...]) -> ImportResult`。某一项是 `None` 表示这一列缺失。`rename_student(class_id, account, name) -> None`。`reset_password(class_id, account, password) -> None`。`remove_student(class_id, account) -> str`。`delete_class(class_id) -> tuple[str, ...]`。

- [ ] **Step 1: Write the failing test**

Create `tests/test_roster.py`:

```python
import pytest

from scaffolding.roster import ImportFailure, Roster, RosterError


def test_the_teacher_starts_as_the_preset_account():
    roster = Roster()

    assert roster.authenticate_teacher("643590872", "643590872") is True
    assert roster.authenticate_teacher("643590872", "nope") is False
    assert roster.authenticate_student("643590872", "643590872") is None


def test_the_teacher_can_change_only_a_filled_new_password():
    roster = Roster()

    with pytest.raises(RosterError, match="原密码不正确"):
        roster.change_teacher_password("nope", "next")
    with pytest.raises(RosterError, match="密码不能为空"):
        roster.change_teacher_password("643590872", "  ")
    roster.change_teacher_password("643590872", " next ")

    assert roster.authenticate_teacher("643590872", "next") is True
    assert roster.teacher_account == "643590872"


def test_class_names_are_stripped_and_unique():
    roster = Roster()

    with pytest.raises(RosterError, match="先填写班级名称"):
        roster.create_class("  ")
    created = roster.create_class(" 一班 ")
    with pytest.raises(RosterError, match="已有同名班级"):
        roster.create_class("一班")

    assert created.class_id == "class-1"
    assert created.name == "一班"
    assert roster.classes() == (created,)


def test_import_keeps_valid_rows_and_reports_the_rest():
    roster = Roster()
    first = roster.create_class("一班")
    second = roster.create_class("二班")
    roster.import_rows(first.class_id, ((2, "s1", "secret", "甲"),))

    result = roster.import_rows(second.class_id, (
        (2, "s2", "secret", "乙"),
        (3, "", "secret", "丙"),
        (4, "s3", "  ", "丁"),
        (5, "s4", "secret", "  "),
        (6, "s2", "other", "戊"),
        (7, "s1", "other", "己"),
        (8, "  ", " ", " "),
    ))

    assert [item.account for item in result.added] == ["s2"]
    assert [item.reason for item in result.failures] == [
        "账号或密码为空",
        "账号或密码为空",
        "姓名为空",
        "账号在这份表里重复",
        "账号已经存在",
    ]
    assert roster.authenticate_student("s1", "secret").class_id == first.class_id
    assert roster.authenticate_student("s1", "other") is None
    assert [item.name for item in roster.students(second.class_id)] == ["乙"]


def test_a_missing_field_on_the_first_copy_blocks_later_copies():
    roster = Roster()
    created = roster.create_class("一班")

    result = roster.import_rows(created.class_id, (
        (2, "s1", "", "甲"),
        (3, "s1", "secret", "乙"),
    ))

    assert result.added == ()
    assert [item.reason for item in result.failures] == ["账号或密码为空", "账号在这份表里重复"]


def test_a_missing_cell_is_reported_separately_from_a_blank_cell():
    roster = Roster()
    created = roster.create_class("一班")

    result = roster.import_rows(created.class_id, ((2, "s1", None, "甲"),))

    assert result.added == ()
    assert result.failures == (ImportFailure(2, "缺账号、密码或姓名"),)


def test_rename_reset_and_remove_keep_other_students():
    roster = Roster()
    created = roster.create_class("一班")
    roster.import_rows(created.class_id, ((2, "s1", "secret", "甲"), (3, "s2", "secret", "乙")))

    with pytest.raises(RosterError, match="姓名不能为空"):
        roster.rename_student(created.class_id, "s1", " ")
    roster.rename_student(created.class_id, "s1", " 甲一 ")
    with pytest.raises(RosterError, match="密码不能为空"):
        roster.reset_password(created.class_id, "s1", " ")
    roster.reset_password(created.class_id, "s1", " next ")
    removed = roster.remove_student(created.class_id, "s1")

    assert removed == "s1"
    assert roster.authenticate_student("s1", "next") is None
    assert roster.student(created.class_id, "s2").name == "乙"
    with pytest.raises(RosterError, match="学生不存在"):
        roster.student(created.class_id, "s1")


def test_deleting_a_class_removes_its_accounts_only():
    roster = Roster()
    first = roster.create_class("一班")
    second = roster.create_class("二班")
    roster.import_rows(first.class_id, ((2, "s1", "secret", "甲"),))
    roster.import_rows(second.class_id, ((2, "s2", "secret", "乙"),))

    removed = roster.delete_class(first.class_id)

    assert removed == ("s1",)
    assert roster.classes() == (second,)
    assert roster.authenticate_student("s2", "secret").name == "乙"
    with pytest.raises(RosterError, match="班级不存在"):
        roster.students(first.class_id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_roster.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'scaffolding.roster'`

- [ ] **Step 3: Write minimal implementation**

Create `src/scaffolding/roster.py`:

```python
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

    def import_rows(self, class_id: str, rows: tuple[tuple[int, str, str, str], ...]) -> ImportResult:
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

    def rename_student(self, class_id: str, account: str, name: str) -> None:
        student = self.student(class_id, account)
        cleaned = _clean(name)
        if cleaned == "":
            raise RosterError("姓名不能为空")
        self._students[account] = StudentRecord(student.account, student.password, cleaned, student.class_id)

    def reset_password(self, class_id: str, account: str, password: str) -> None:
        student = self.student(class_id, account)
        cleaned = _clean(password)
        if cleaned == "":
            raise RosterError("密码不能为空")
        self._students[account] = StudentRecord(student.account, cleaned, student.name, student.class_id)

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
```

`缺账号、密码或姓名` 由 Task 2 在单元格缺失时产生。Task 1 收到的每行都有三项字符串。

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_roster.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/roster.py tests/test_roster.py
git commit -m "feat: record classes and student accounts"
```

---

### Task 2: 从 xlsx 读出学生行

**Files:**
- Create: `src/scaffolding/sheet.py`
- Test: `tests/test_sheet.py`

**Interfaces:**
- Consumes: 无。行再交给 `Roster.import_rows`。
- Produces: `SheetError(message: str)`。`read_student_rows(data: bytes) -> tuple[tuple[int, str, str, str], ...]`。成功时每项是 `(工作表行号, 账号, 密码, 姓名)`。表头不对抛出 `SheetError("表头必须是账号、密码、姓名")`。读不出来抛出 `SheetError("不能读取这份表格")`。缺某一列的数据行用空字符串占位，交给 Task 1 报「账号或密码为空」或「姓名为空」。三个单元格都空的行不返回。

- [ ] **Step 1: Write the failing test**

Create `tests/test_sheet.py`。测试里用标准库 `zipfile` 写一份最小 xlsx，单元格使用 `inlineStr`。再写一份第一行不是表头的表，以及一段不是 zip 的字节。

```python
import io
import zipfile

import pytest

from scaffolding.sheet import SheetError, read_student_rows


def _xlsx(rows: tuple[tuple[str, ...], ...]) -> bytes:
    sheet_rows = []
    for index, values in enumerate(rows, start=1):
        cells = []
        for column, value in enumerate(values):
            ref = chr(ord("A") + column) + str(index)
            cells.append(
                '<c r="' + ref + '" t="inlineStr"><is><t>' + value + "</t></is></c>"
            )
        sheet_rows.append('<row r="' + str(index) + '">' + "".join(cells) + "</row>")
    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>" + "".join(sheet_rows) + "</sheetData></worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="学生" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as book:
        book.writestr("xl/workbook.xml", workbook)
        book.writestr("xl/_rels/workbook.xml.rels", rels)
        book.writestr("xl/worksheets/sheet1.xml", sheet)
    return buffer.getvalue()


def test_the_first_sheet_returns_data_rows_after_the_header():
    data = _xlsx((
        ("账号", "密码", "姓名", "备注"),
        ("s1", "secret", "甲", "忽略"),
        ("", "", ""),
        ("s2", "secret", ""),
        ("s3", "secret"),
    ))

    assert read_student_rows(data) == (
        (2, "s1", "secret", "甲"),
        (4, "s2", "secret", ""),
        (5, "s3", "secret", None),
    )


def test_a_bad_header_or_unreadable_bytes_raise_the_spec_sentences():
    with pytest.raises(SheetError, match="表头必须是账号、密码、姓名"):
        read_student_rows(_xlsx((("姓名", "账号", "密码"),)))
    with pytest.raises(SheetError, match="不能读取这份表格"):
        read_student_rows(b"not a spreadsheet")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_sheet.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'scaffolding.sheet'`

- [ ] **Step 3: Write minimal implementation**

Create `src/scaffolding/sheet.py`。用 `zipfile` 和 `xml.etree.ElementTree` 读取 `xl/workbook.xml` 的第一个 `sheet`，再从 `xl/_rels/workbook.xml.rels` 找到对应工作表。单元格支持 `inlineStr`。列只取 A、B、C。找不到 zip、工作表或 XML 时抛出「不能读取这份表格」。第一行前三个文本不是「账号」「密码」「姓名」时抛出「表头必须是账号、密码、姓名」。

```python
import zipfile
from xml.etree import ElementTree

_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_OFFICE = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


class SheetError(Exception):
    pass


def read_student_rows(data: bytes) -> tuple[tuple[int, str, str, str], ...]:
    try:
        with zipfile.ZipFile(__import__("io").BytesIO(data)) as book:
            workbook = ElementTree.fromstring(book.read("xl/workbook.xml"))
            rels = ElementTree.fromstring(book.read("xl/_rels/workbook.xml.rels"))
            sheet = workbook.find(_MAIN + "sheets").find(_MAIN + "sheet")
            relation_id = sheet.attrib[_OFFICE + "id"]
            target = ""
            for item in rels:
                if item.attrib.get("Id") == relation_id:
                    target = "xl/" + item.attrib["Target"].lstrip("/")
            worksheet = ElementTree.fromstring(book.read(target))
    except Exception as error:
        raise SheetError("不能读取这份表格") from error
    rows = _rows(worksheet)
    if not rows or rows[0][1:4] != ("账号", "密码", "姓名"):
        raise SheetError("表头必须是账号、密码、姓名")
    kept = []
    for number, account, password, name in rows[1:]:
        if all(item in ("", None) for item in (account, password, name)):
            continue
        kept.append((number, account, password, name))
    return tuple(kept)


def _rows(worksheet) -> list[tuple[int, str, str, str]]:
    found = []
    for row in worksheet.find(_MAIN + "sheetData"):
        number = int(row.attrib.get("r", "0"))
        values = {0: None, 1: None, 2: None}
        for cell in row:
            ref = cell.attrib.get("r", "A")
            column = ord(ref[0]) - ord("A")
            if column in values:
                values[column] = _text(cell)
        found.append((number, values[0], values[1], values[2]))
    return found


def _text(cell) -> str:
    inline = cell.find(_MAIN + "is")
    if inline is None:
        return ""
    node = inline.find(_MAIN + "t")
    if node is None or node.text is None:
        return ""
    return node.text
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_sheet.py tests/test_roster.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/sheet.py tests/test_sheet.py
git commit -m "feat: read student rows from an xlsx sheet"
```

---

### Task 3: 教师和学生登录

**Files:**
- Modify: `src/scaffolding/teacher_page.py` — `PageResponse` 增加 `set_cookie: str = ""`。`TeacherPage.__init__` 增加可选 `roster=None`。`_render_list` 在 `roster` 不是 `None` 时，在「目标」链接后拼接 `<a href=".../classes">班级</a>`，并拼接修改密码表单和退出表单。修改密码字段 `old_password`、`password`，按钮 `action` 值「修改密码」。退出按钮 `action` 值「退出」。两个表单都提交到教师列表地址。
- Modify: `src/scaffolding/student_page.py` — `PageResponse` 增加同样的 `set_cookie`。`todo` 在页面有 `show_logout=True` 时拼接退出表单，提交到学生待办，按钮「退出」。默认 `False`，现有直接调用不变。
- Modify: `src/scaffolding/classroom.py` — `Classroom` 持有 `Roster()`。`response_for` 增加 `headers: str = ""`。
- Modify: `tests/classroom_helpers.py`
- Test: `tests/test_class_login.py`
- Modify: 现有调用 `response_for(room, ...)` 且路径在 `/teacher` 或 `/student` 下的测试，补上教师或学生 Cookie。

**Interfaces:**
- Consumes: `Roster`。
- Produces: `response_for(room, method, path, body, now, headers="") -> PageResponse`。登录成功的 `set_cookie` 以 `teacher=<标记>; HttpOnly; Path=/teacher` 或 `student=<标记>; HttpOnly; Path=/student` 开头。退出时 `set_cookie` 是 `teacher=; Max-Age=0; Path=/teacher` 或学生对应的那条。`Classroom.roster`。

- [ ] **Step 1: Write the failing test**

Create `tests/test_class_login.py`。用 `tests.classroom_helpers.room`。

```python
from scaffolding.classroom import response_for
from tests.classroom_helpers import form, room, text


def test_teacher_and_student_pages_require_login():
    page = room()

    teacher = response_for(page, "GET", "/teacher", "", 0)
    student = response_for(page, "GET", "/student", "", 0)
    home = text(response_for(page, "GET", "/", "", 0))

    assert teacher.status == 200
    assert "<h1>登录</h1>" in text(teacher)
    assert "任务列表" not in text(teacher)
    assert "<h1>登录</h1>" in text(student)
    assert "待办" not in text(student)
    assert 'href="/teacher"' in home and 'href="/student"' in home


def test_the_preset_teacher_logs_in_changes_password_and_logs_out():
    page = room()

    wrong = response_for(page, "POST", "/teacher/login", form(account="s1", password="secret"), 0)
    opened = response_for(page, "POST", "/teacher/login", form(account="643590872", password="643590872"), 0)
    listed = response_for(page, "GET", "/teacher", "", 0, opened.set_cookie.split(";", 1)[0])
    changed = response_for(
        page, "POST", "/teacher", form(action="修改密码", old_password="643590872", password="next"), 0,
        opened.set_cookie.split(";", 1)[0],
    )
    again = response_for(page, "POST", "/teacher/login", form(account="643590872", password="next"), 0)
    left = response_for(page, "POST", "/teacher", form(action="退出"), 0, again.set_cookie.split(";", 1)[0])

    assert wrong.status == 200
    assert "账号或密码不正确" in text(wrong)
    assert wrong.set_cookie == ""
    assert opened.set_cookie.startswith("teacher=")
    assert "Path=/teacher" in opened.set_cookie
    assert "<h1>任务列表</h1>" in text(opened)
    assert 'href="/teacher/classes"' in text(listed)
    assert "密码已修改" in text(changed)
    assert again.set_cookie.startswith("teacher=")
    assert left.set_cookie.startswith("teacher=;")
    assert "<h1>登录</h1>" in text(left)


def test_a_student_cookie_does_not_open_the_teacher_page():
    page = room()
    created = page.roster.create_class("一班")
    page.roster.import_rows(created.class_id, ((2, "s1", "secret", "甲"),))

    opened = response_for(page, "POST", "/student/login", form(account="s1", password="secret"), 0)
    teacher = response_for(page, "GET", "/teacher", "", 0, opened.set_cookie.split(";", 1)[0])

    assert opened.set_cookie.startswith("student=")
    assert "<h1>待办</h1>" in text(opened)
    assert "<h1>登录</h1>" in text(teacher)
```

然后把 `tests/test_classroom_routes.py` 改成：未登录的 `/teacher` 和 `/student` 显示登录；登录后再检查前缀。`tests/classroom_helpers.py` 增加：

```python
from scaffolding.classroom import response_for


def teacher_cookie(page) -> str:
    response = response_for(
        page, "POST", "/teacher/login", form(account="643590872", password="643590872"), 0
    )
    return response.set_cookie.split(";", 1)[0]


def student_cookie(page, account="s1", password="secret", name="甲") -> str:
    if page.roster.authenticate_student(account, password) is None:
        created = page.roster.create_class("一班")
        page.roster.import_rows(created.class_id, ((2, account, password, name),))
    response = response_for(
        page, "POST", "/student/login", form(account=account, password=password), 0
    )
    return response.set_cookie.split(";", 1)[0]
```

现有这些文件里，访问 `/teacher` 的调用补 `headers=teacher_cookie(room)`，访问 `/student` 的调用补 `headers=student_cookie(room)`：

- `tests/test_classroom_acceptance.py`
- `tests/test_classroom_delete.py`
- `tests/test_classroom_publish.py`
- `tests/test_classroom_routes.py`
- `tests/test_teacher_objectives_acceptance.py`
- `tests/test_teacher_objective_generation_acceptance.py`
- `tests/test_teacher_text_generation_acceptance.py`

这一步还不要按班级过滤学生任务。已登录学生仍看到全部已发布任务。

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_class_login.py -v`

Expected: FAIL，因为 `response_for` 还不接受 `headers`，或登录页不存在。

- [ ] **Step 3: Write minimal implementation**

`classroom.response_for` 解析 `headers` 里的 Cookie。`teacher` 标记对得上时才调用现有教师页；`student` 标记对得上时才调用现有学生页。标记用 `secrets.token_hex(16)`，存在 `room.teacher_tokens` 和 `room.student_tokens`。学生登录成功后，为该账号准备一份 `StudentPage(room.catalog, room.student.decision, room.student.scaffold_agent, prefix="/student")`，并设 `show_logout=True`，存在 `room.student_pages`。

登录失败返回状态 200 的「登录」页，`set_cookie` 为空。教师修改密码调用 `roster.change_teacher_password`，失败时把 `RosterError` 的文字显示在任务列表，成功时显示「密码已修改」。退出删除对应标记。

`serve` 在 `response.set_cookie` 非空时增加响应头 `Set-Cookie`。测试不调用 `serve`。

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/classroom.py src/scaffolding/teacher_page.py src/scaffolding/student_page.py tests/classroom_helpers.py tests/test_class_login.py tests/test_classroom_acceptance.py tests/test_classroom_delete.py tests/test_classroom_publish.py tests/test_classroom_routes.py tests/test_teacher_objectives_acceptance.py tests/test_teacher_objective_generation_acceptance.py tests/test_teacher_text_generation_acceptance.py
git commit -m "feat: require the teacher and the student to log in"
```

---

### Task 4: 班级页管理学生

**Files:**
- Create: `src/scaffolding/class_page.py`
- Modify: `src/scaffolding/classroom.py` — 已登录教师访问 `/classes` 时交给班级页。
- Test: `tests/test_class_page.py`

**Interfaces:**
- Consumes: `Roster`、`read_student_rows`、`RosterError`、`SheetError`。
- Produces: `class_response(page, method, path, fields, uploads) -> str`。`uploads` 是 `dict[str, bytes]`。课堂 `response_for` 增加可选 `uploads=None`。班级页显示失败句，课堂把它包成状态 200；打开不存在的班级或学生时，班级页返回空字符串，课堂改成状态 404 和对应标题。

- [ ] **Step 1: Write the failing test**

Create `tests/test_class_page.py`:

```python
from scaffolding.classroom import files_from_body, response_for
from tests.classroom_helpers import form, room, teacher_cookie, text
from tests.test_sheet import _xlsx


def _headers(page):
    return teacher_cookie(page)


def test_the_teacher_creates_a_class_and_imports_a_sheet():
    page = room()
    headers = _headers(page)
    data = _xlsx((
        ("账号", "密码", "姓名"),
        ("s1", "secret", "<甲"),
        ("s1", "other", "乙"),
    ))

    created = response_for(page, "POST", "/teacher/classes", form(action="创建", name="一班"), 0, headers)
    imported = response_for(
        page, "POST", "/teacher/classes/class-1", form(action="导入"), 0, headers, uploads={"file": data}
    )
    missing = response_for(page, "GET", "/teacher/classes/missing", "", 0, headers)

    assert 'enctype="multipart/form-data"' in text(created)
    assert 'name="file"' in text(created)
    assert "一班" in text(created)
    assert "&lt;甲" in text(imported)
    assert "账号在这份表里重复" in text(imported)
    assert "<甲" not in text(imported).replace("&lt;甲", "")
    assert missing.status == 404
    assert "班级不存在" in text(missing)


def test_rename_reset_remove_and_delete_class():
    page = room()
    headers = _headers(page)
    response_for(page, "POST", "/teacher/classes", form(action="创建", name="一班"), 0, headers)
    response_for(
        page, "POST", "/teacher/classes/class-1", form(action="导入"), 0, headers,
        uploads={"file": _xlsx((("账号", "密码", "姓名"), ("s1", "secret", "甲")))},
    )

    renamed = response_for(
        page, "POST", "/teacher/classes/class-1/students/s1",
        form(action="修改姓名", name="甲一"), 0, headers,
    )
    reset = response_for(
        page, "POST", "/teacher/classes/class-1/students/s1",
        form(action="重置密码", password="next"), 0, headers,
    )
    removed = response_for(
        page, "POST", "/teacher/classes/class-1/students/s1",
        form(action="移除"), 0, headers,
    )
    response_for(page, "POST", "/teacher/classes", form(action="创建", name="二班"), 0, headers)
    deleted = response_for(page, "POST", "/teacher/classes/class-2", form(action="删除班级"), 0, headers)

    assert "甲一" in text(renamed)
    assert "密码已重置" in text(reset)
    assert "value=\"next\"" not in text(reset)
    assert "s1" not in text(removed)
    assert page.roster.authenticate_student("s1", "next") is None
    assert "二班" not in text(deleted)


def test_files_from_body_reads_the_uploaded_bytes():
    body = (
        b"--line\r\n"
        b"Content-Disposition: form-data; name=\"file\"; filename=\"students.xlsx\"\r\n"
        b"\r\n"
        b"PK\x03\x04sheet\r\n"
        b"--line--\r\n"
    )

    assert files_from_body("multipart/form-data; boundary=line", body)["file"] == b"PK\x03\x04sheet"
```

`response_for` 的签名是 `(room, method, path, body, now, headers="", uploads=None)`。

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_class_page.py -v`

Expected: FAIL，因为还没有 `/classes`。

- [ ] **Step 3: Write minimal implementation**

`class_page.py` 用拼接写 HTML。创建、导入、删除提交到当前班级页或 `/classes`。导入调用 `read_student_rows`，再调用 `roster.import_rows`。`SheetError` 和整份拒绝时不改已有学生。失败行显示 `第N行：` 加上原因。移除后回到班级页。删除班级后回到列表。

课堂把 `/teacher/classes` 去掉前缀后交给 `class_response`。`uploads` 由调用方传入。增加 `files_from_body(content_type: str, body: bytes) -> dict[str, bytes]`，用 `email.message_from_bytes` 解析 multipart，供 `serve` 使用。测试直接传 `uploads`，不调用 `serve`。另测一次 `files_from_body` 能从自己拼出的 multipart 正文取出 `file` 字节。

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_class_page.py tests/test_sheet.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/class_page.py src/scaffolding/classroom.py tests/test_class_page.py
git commit -m "feat: manage students from the class page"
```

---

### Task 5: 布置任务并按学生作答

**Files:**
- Create: `src/scaffolding/classwork.py`
- Modify: `src/scaffolding/tasks.py` — 增加 `note_started(task_id)` 和 `note_idle(task_id)`。不改变现有 `start`、`work`、`mark_submitted`。
- Modify: `src/scaffolding/teacher_page.py` — 已发布且 `page.classwork` 不是 `None` 时显示班级选择框。
- Modify: `src/scaffolding/classroom.py` — 已登录学生使用 `StudentView`。
- Modify: Task 3 里改过的课堂测试。学生要看到任务前，先把任务布置给该学生的班级。
- Test: `tests/test_classwork.py`

**Interfaces:**
- Consumes: `Roster.students`、`TaskCatalog.get`、`Task.published`、`StudentWork`。
- Produces: `Classwork(roster)`。`assign(catalog, task_id, class_ids: tuple[str, ...]) -> None`。`assigned(task_id) -> tuple[str, ...]`。`tasks_for_class(class_id) -> tuple[str, ...]`。`drop_student(account) -> None`。`drop_class(class_id) -> None`。`drop_task(task_id) -> None`。`any_started(task_id) -> bool`。`StudentView(catalog, classwork, account, class_id)`，实现 `student_tasks`、`get`、`start`、`work`、`mark_submitted`。`get` 在任务未布置或未发布时抛出 `KeyError`。`start` 调用 `catalog.note_started`。没有任何学生仍开始时，`assign` 调用 `catalog.note_idle`。

- [ ] **Step 1: Write the failing test**

Create `tests/test_classwork.py`。两班各一名学生。发布含一题的任务后布置给两班。未发布任务布置抛出 `RosterError("先发布再布置")`。不存在的班级抛出 `RosterError("班级不存在")`，原布置不变。两名学生通过各自的 `StudentView` 和 `StudentPage` 作答、提交，互不影响。未布置任务打开时状态 404，且 `note_started` 不被调用。第一名学生开始后 `catalog.get(task_id).started` 为真。取消一班布置后，一班学生再打开是 404，二班作答还在。一个班级都不选时任务回到未开始，前提是作答都已删除。`drop_student` 后该生作答不在。

教师页测试：登录后的任务页对已发布任务显示两班选择框；提交 `class_id` 后 `classwork.assigned` 与选择一致。

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_classwork.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'scaffolding.classwork'`

- [ ] **Step 3: Write minimal implementation**

`StudentView.student_tasks` 只列出已发布且布置给该班的任务。没有 `StudentWork` 时状态是「待办」；`submitted` 时是「已完成」；否则是「待办」。`get` 返回 `replace(task, started=work is not None, submitted=bool(work and work.submitted))`。

课堂里每个已登录学生的 `StudentPage.catalog` 换成该生的 `StudentView`。教师移除学生或删除班级时调用 `drop_student` 或 `drop_class`。教师删除任务时调用 `drop_task`。

现有课堂测试在学生打开任务前，用 `room.classwork.assign(room.catalog, task_id, (class_id,))`。`student_cookie` 返回班级标识，或测试从 `room.roster.students` 取 `class_id`。

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/classwork.py src/scaffolding/tasks.py src/scaffolding/teacher_page.py src/scaffolding/classroom.py tests/test_classwork.py tests/classroom_helpers.py tests/test_classroom_acceptance.py tests/test_classroom_delete.py tests/test_classroom_publish.py tests/test_classroom_routes.py tests/test_teacher_objectives_acceptance.py tests/test_teacher_objective_generation_acceptance.py tests/test_teacher_text_generation_acceptance.py
git commit -m "feat: assign published tasks and separate student answers"
```

---

### Task 6: 教师查看一名学生的作答详情

**Files:**
- Modify: `src/scaffolding/class_page.py`
- Test: `tests/test_class_detail.py`

**Interfaces:**
- Consumes: `Classwork`、`StudentWork.answers`、`StudentWork.behavior`、`StudentWork.dialogue`、`StudentWork.submitted`、题目的 `answer` 和 `explanation`。
- Produces: 地址 `/classes/<班级标识>/students/<账号>` 和 `/classes/<班级标识>/students/<账号>/tasks/<任务标识>`。详情只读。

- [ ] **Step 1: Write the failing test**

Create `tests/test_class_detail.py`。学生未打开时，详情含「还没作答」，同时含参考答案和解析。学生打开后含「待办」。学生提交后含「已完成」、作答、求助原话、支架文字和停留秒数。详情 HTML 不含 `/answers`、`/ask`、`/submit`。未布置的任务地址状态 404，正文「任务不存在」，不含参考答案。不属于该班的账号状态 404，正文「学生不存在」。学生自己的任务页在提交前不含「参考答案」。

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_class_detail.py -v`

Expected: FAIL，详情地址还没有这三态。

- [ ] **Step 3: Write minimal implementation**

学生列表链接到详情。任务列表链接到只读任务页。还没有 `StudentWork` 时写「还没作答」，仍写出每题参考答案和解析。有作答且未提交时写「待办」。已提交时写「已完成」。停留时间写成 `str(int(dwell_seconds))` 前加「停留」。求助和支架从 `behavior.helps` 与 `dialogue` 读出。素材沿用学生页的类型和文件名，地址使用教师前缀下的只读路径 `/classes/.../tasks/<任务>/assets/<文件名>`，从该生当前支架或对应对话轮取出字节。不要调用决策或支架智能体。

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_class_detail.py tests/test_class_page.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/class_page.py tests/test_class_detail.py
git commit -m "feat: show a student's task detail to the teacher"
```

---

### Task 7: 把课堂写入本机文件

**Files:**
- Create: `src/scaffolding/store.py`
- Modify: `src/scaffolding/session.py` — `Session.restore(catalog, work, decision, scaffold_agent, presets, scaffold)`，不调用 `decision.suggest`。
- Modify: `src/scaffolding/classroom.py` — 构造时从路径加载；每次成功修改后保存；保存失败时从文件重新加载。
- Test: `tests/test_classroom_store.py`

**Interfaces:**
- Consumes: `Classroom` 上的 `roster`、`catalog`、`classwork`、`teacher.drafts`、`knowledge`、`objectives`、`generation._origins`、每名学生的 `StudentPage.sessions`。
- Produces: `save_classroom(path, room) -> None`。`load_classroom(path, room) -> None`。`Classroom(path=...)`。路径缺失时创建文件并写入预设教师。`production_classroom` 使用当前目录的 `classroom.json`。

- [ ] **Step 1: Write the failing test**

Create `tests/test_classroom_store.py`。使用 `tmp_path`。第一份课堂创建班级、导入学生、发布并布置任务、保存草稿、写入一条教材和一条目标、学生作答并求助。新建第二份 `Classroom(path=同一文件)` 后，这些内容都在，登录标记不在，必须重新登录。新密码在重启后有效。把 `save_classroom` 换成会抛出 `OSError` 的函数后创建班级，页面含「没有写入文件」，内存和文件都没有这个新班级。

保存的 JSON 至少包含：`teacher_password`、`classes`、`students`、`tasks`、`drafts`、`assignments`、`works`、`lessons`、`standards`、`objectives`、`origins`。作答里的支架字节用 base64。

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_classroom_store.py -v`

Expected: FAIL，因为 `Classroom` 还不接受 `path`。

- [ ] **Step 3: Write minimal implementation**

`save_classroom` 先把 JSON 写到同目录临时文件，再 `os.replace`。`load_classroom` 覆盖 room 里的名册、任务、草稿、布置、作答、知识库、目标和来源。学生重新登录时，若该生这份任务保存过 `presets`，用 `Session.restore` 恢复，不调用模型。

每次创建班级、导入、修改姓名、重置密码、移除、删除班级、布置、教师保存或发布、学生作答、求助、提交、打开任务之后调用保存。保存抛出 `OSError` 时调用 `load_classroom` 恢复内存，页面显示「没有写入文件」。

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_classroom_store.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/store.py src/scaffolding/session.py src/scaffolding/classroom.py tests/test_classroom_store.py
git commit -m "feat: keep the classroom in a local file"
```

---

### Task 8: 课堂验收

**Files:**
- Create: `tests/test_class_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-23-teacher-classes-design.md`

**Interfaces:**
- Consumes: Task 1 到 Task 7 的课堂。
- Produces: 无新的生产接口。`production_classroom` 仍使用 `ModelTextGenerator`，构造时不调用补全，并带上当前目录的 `classroom.json`。测试把工作目录换到临时目录，避免写到仓库里的文件。

- [ ] **Step 1: Write the failing test**

若规格文件不在工作区，从 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-23-teacher-classes-design.md` 原样复制。不要改写。

Create `tests/test_class_acceptance.py`：

```python
from pathlib import Path

from scaffolding.classroom import production_classroom, response_for, serve
from scaffolding.model_text import ModelTextGenerator
from tests.classroom_helpers import form, text


def test_the_classroom_entry_has_no_tasks():
    room = production_classroom(post=lambda _request: (_ for _ in ()).throw(AssertionError("network")))

    home = text(response_for(room, "GET", "/", "", 0))

    assert "<h1>课堂</h1>" in home
    assert 'href="/teacher"' in home
    assert 'href="/student"' in home
    assert "task-" not in home
    assert isinstance(room.generation._text_generator, ModelTextGenerator)
    assert Path("docs/superpowers/specs/2026-10-23-teacher-classes-design.md").is_file()
    assert callable(serve)
    assert callable(production_classroom)


def test_a_logged_in_student_only_sees_an_assigned_task(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    room = production_classroom(post=lambda _request: (_ for _ in ()).throw(AssertionError("network")))
    teacher = response_for(room, "POST", "/teacher/login", form(account="643590872", password="643590872"), 0)
    headers = teacher.set_cookie.split(";", 1)[0]
    response_for(room, "POST", "/teacher/classes", form(action="创建", name="一班"), 0, headers)
    from scaffolding.records import ChoiceQuestion, SelectionMode
    from tests.test_sheet import _xlsx

    task = room.catalog.create((
        ChoiceQuestion("题干", SelectionMode.SINGLE, ("甲", "乙"), ("甲",), "因为甲"),
    ))
    room.catalog.publish(task.task_id)
    response_for(
        room, "POST", "/teacher/tasks/" + task.task_id,
        form(action="布置", class_id="class-1"), 0, headers,
    )
    response_for(
        room, "POST", "/teacher/classes/class-1", form(action="导入"), 0, headers,
        uploads={"file": _xlsx((("账号", "密码", "姓名"), ("s1", "secret", "甲")))},
    )
    student = response_for(room, "POST", "/student/login", form(account="s1", password="secret"), 0)
    todo = text(response_for(room, "GET", "/student", "", 0, student.set_cookie.split(";", 1)[0]))
    hidden = response_for(room, "GET", "/student/tasks/task-2", "", 0, student.set_cookie.split(";", 1)[0])

    assert "task-1" in todo
    assert hidden.status == 404
    assert "任务不存在" in text(hidden)
```

把注释换成真实步骤：教师新建任务、保存一题、发布、布置 `class_id=class-1`，再用 Task 2 的 xlsx 导入 `s1`。断言以规格为准。

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_class_acceptance.py -v`

Expected: FAIL，直到生产课堂使用文件并且验收步骤走通。若前面任务已经满足，此测试应直接 PASS，仍只提交测试和规格副本。

- [ ] **Step 3: Write minimal implementation**

不改 `production_classroom` 的模型接线。只确认它传入 `classroom.json`。不要调用 `serve`。

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add tests/test_class_acceptance.py docs/superpowers/specs/2026-10-23-teacher-classes-design.md
git commit -m "test: accept classes and login in the classroom"
```
