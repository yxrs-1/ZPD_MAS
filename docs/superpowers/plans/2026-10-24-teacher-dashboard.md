# 教师仪表盘 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 教师登录后进入左侧导航的教师页，新建任务分成手动添加和智能体生成，文档放在资料库，账号管理可以重置密码和换班。

**Architecture:** `Roster.move_student` 只改所属班级，不碰作答。资料库从目标页拆到 `/documents`。`/objectives` 只保留需求和确认。`/tasks/new` 提供两种新建。`/accounts` 列出全部学生并重置密码、换班。已登录教师页共用导航；修改密码和退出放在导航底部的账号面板里，仍提交到任务列表。

**Tech Stack:** Python 3.14，pytest，现有 FastAPI 应用和 `/static/classroom.css`。在 `F:\work\zpd_MAS` 里改，不新建 worktree。规格是 `docs/superpowers/specs/2026-10-24-teacher-dashboard-design.md`。测试命令用 `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest`。PowerShell 不要使用 `&&`。不要改 git config，不要 push。用户没要求时跳过每一步的 Commit。

## Global Constraints

- 导航文字只有「任务」「班级」「资料库」「账号管理」。任务列表不再有「目标」，也不链接 `/generation`。
- 「新建」指向 `/tasks/new`，不创建任务。`/tasks/new` 不是任务标识。任务标识仍按现在的方式分配。
- 「手动添加」走现有创建，得到没有题目、尚未发布的任务。「智能体生成」指向 `/objectives`。
- `/objectives` 的 GET 只有 `text` 和「生成目标」。没有上传、删除、文件名和指向 `/generation` 的链接。确认后仍进入未发布任务页，不写目标库，不预先写支架。
- 在 `/objectives` 提交「上传」或「删除」不改文档库，不另报失败。`/generation` 仍按文字生成，且不读取文档库。
- 资料库是 `/documents`。字段仍是 `file`、`doc_id`，动作仍是「上传」「删除」。失败句仍是「只接受 docx 或 pdf」「不能读取这份文件」「这份文件没有可用的正文」「文档不存在」。
- 账号管理是 `/accounts`。每名学生显示姓名、账号和当前班级名称。重置密码字段是 `account`、`password`，动作是「重置密码」。换班字段是 `account`、`class_id`，动作是「换班」。
- 重置密码先查账号：空账号或没有这名学生是「学生不存在」；密码去掉空白后为空是「密码不能为空」；成功是「密码已重置」。
- 换班顺序：学生不存在，先选择班级，班级不存在。选中当前班级不改数据、不写文件。换班留着作答、求助、支架和停留。学生改看新班级被布置的任务。
- 移除学生仍清掉作答。班级页仍可重置密码、修改姓名、导入和删除班级。完成情况仍用「还没作答」「待办」「已完成」，列表不做人数汇总。
- 修改密码字段仍是 `old_password`、`password`，按钮「修改密码」，提交到教师任务列表。失败句仍是「原密码不正确」「密码不能为空」，成功是「密码已修改」。退出动作仍是「退出」，之后是预选「教师」的登录页。
- 课堂地址带 `/teacher`，单独调用教师页时不带前缀。末尾斜杠和查询字符串不影响。学生打开这些新地址仍是「任务不存在」，状态 404。
- `classroom.json` 不增加字段。不引入 React，不请求其他网站。测试不调用监听，不打开浏览器，不访问网络，不在仓库里创建 `classroom.json`，也不测量颜色和动画时长。

---

### Task 1: 名册换班

**Files:**
- Modify: `src/scaffolding/roster.py`
- Test: `tests/test_roster.py`

**Interfaces:**
- Consumes: `Roster.create_class`、`Roster.import_rows`、`RosterError`、`_clean`
- Produces: `Roster.move_student(self, account: str, class_id: str) -> StudentRecord`。失败抛 `RosterError`。当前班级原样返回，不替换记录。换班后学生在新班名单末尾，原班名单里没有。

- [ ] **Step 1: Write the failing test**

在 `tests/test_roster.py` 末尾追加：

```python
def test_move_student_changes_class_or_rejects_in_order():
    roster = Roster()
    first = roster.create_class("一班")
    second = roster.create_class("二班")
    roster.import_rows(first.class_id, ((2, "s1", "secret", "甲"),))
    kept = roster.student(first.class_id, "s1")

    same = roster.move_student("s1", first.class_id)
    assert same is kept
    assert roster.students(first.class_id) == (kept,)

    with pytest.raises(RosterError, match="学生不存在"):
        roster.move_student("  ", second.class_id)
    with pytest.raises(RosterError, match="学生不存在"):
        roster.move_student("missing", second.class_id)
    with pytest.raises(RosterError, match="先选择班级"):
        roster.move_student("s1", "  ")
    with pytest.raises(RosterError, match="班级不存在"):
        roster.move_student("s1", "class-9")
    assert roster.student(first.class_id, "s1").class_id == first.class_id

    moved = roster.move_student(" s1 ", second.class_id)
    assert moved.account == "s1"
    assert moved.password == "secret"
    assert moved.name == "甲"
    assert moved.class_id == second.class_id
    assert roster.students(first.class_id) == ()
    assert roster.students(second.class_id) == (moved,)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest tests/test_roster.py::test_move_student_changes_class_or_rejects_in_order -v`

Expected: FAIL，`Roster` 没有 `move_student`。

- [ ] **Step 3: Write minimal implementation**

在 `src/scaffolding/roster.py` 的 `reset_password` 后面追加：

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest tests/test_roster.py::test_move_student_changes_class_or_rejects_in_order -v`

Expected: PASS

- [ ] **Step 5: Commit**

用户没要求时跳过。

```bash
git add src/scaffolding/roster.py tests/test_roster.py
git commit -m "Let a teacher move a student to another class"
```

---

### Task 2: 资料库与目标页分开

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Modify: `tests/test_document_page.py`
- Modify: `tests/test_document_acceptance.py`
- Test: `tests/test_teacher_documents.py`

**Interfaces:**
- Consumes: `TeacherPage.library`、`TeacherPage.open_objectives`、`_upload_document`、`_delete_document`、`response_for`
- Produces: `TeacherPage.open_documents(self, message: str = "") -> str`。`response_for` 认识 GET/POST `/documents`。POST `/objectives` 的「上传」「删除」不再改文档库。

- [ ] **Step 1: Write the failing test**

新建 `tests/test_teacher_documents.py`：

```python
from scaffolding.teacher_page import TeacherPage, response_for
from tests.teacher_objectives_helpers import form, text
from tests.test_documents import _docx


def test_documents_list_upload_and_delete_without_objectives():
    page = TeacherPage(complete=lambda _messages: "")
    content = _docx((("第一章 数据", ""), ("片段", "")))

    opened = text(response_for(page, "GET", "/documents", ""))
    assert "<h1>资料库</h1>" in opened
    assert 'name="file"' in opened
    assert "上传" in opened
    assert 'name="text"' not in opened
    assert "生成目标" not in opened

    uploaded = text(response_for(
        page, "POST", "/documents", form(action="上传"),
        {"file": content}, {"file": "a<b.docx"},
    ))
    assert page.library.documents()[0].doc_id == "doc-1"
    assert "a&lt;b.docx" in uploaded
    rejected = text(response_for(
        page, "POST", "/documents", form(action="上传"),
        {"file": b"notes"}, {"file": "笔记.txt"},
    ))
    assert "只接受 docx 或 pdf" in rejected
    missing = text(response_for(page, "POST", "/documents", form(action="删除", doc_id="doc-9")))
    assert "文档不存在" in missing
    removed = text(response_for(page, "POST", "/documents", form(action="删除", doc_id="doc-1")))
    assert page.library.documents() == ()
    assert "a&lt;b.docx" not in removed


def test_objectives_upload_does_not_change_the_library():
    page = TeacherPage(complete=lambda _messages: "")
    content = _docx((("第一章 数据", ""), ("片段", "")))
    response_for(page, "POST", "/documents", form(action="上传"), {"file": content}, {"file": "教材.docx"})

    ignored = text(response_for(
        page, "POST", "/objectives", form(action="上传"),
        {"file": content}, {"file": "另一份.docx"},
    ))
    assert len(page.library.documents()) == 1
    assert 'name="file"' not in ignored
    assert 'name="text"' in ignored
    assert "生成目标" in ignored
    assert 'href="/generation"' not in ignored
```

把 `tests/test_document_page.py` 里上传和删除的路径从 `"/objectives"` 改成 `"/documents"`。`test_get_lists_upload_and_does_not_call_the_model` 改为：

```python
def test_get_lists_upload_and_does_not_call_the_model():
    calls = []
    page, _catalog = _page(calls)

    opened = text(response_for(page, "GET", "/objectives/?ready=1", ""))
    library = text(response_for(page, "GET", "/documents", ""))

    assert 'name="text"' in opened
    assert "生成目标" in opened
    assert 'name="file"' not in opened
    assert 'href="/generation"' not in opened
    assert 'name="objectives"' not in opened
    assert 'name="file"' in library
    assert calls == []
```

`tests/test_document_acceptance.py` 里上传地址从 `"/teacher/objectives"` 改成 `"/teacher/documents"`。生成目标和确认仍提交到 `/objectives`。

- [ ] **Step 2: Run test to verify it fails**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest tests/test_teacher_documents.py tests/test_document_page.py::test_get_lists_upload_and_does_not_call_the_model -v`

Expected: FAIL，`/documents` 是「任务不存在」，目标页仍有上传。

- [ ] **Step 3: Write minimal implementation**

在 `TeacherPage` 增加：

```python
def open_documents(self, message: str = "") -> str:
    return _render_documents(self, message)
```

`apply_objectives` 去掉「上传」和「删除」两个分支，不认识的动作仍 `return self.open_objectives()`。

新增：

```python
def _render_documents(page, message: str) -> str:
    action = _with_prefix(page.prefix, "/documents")
    parts = ["<h1>资料库</h1>"]
    if message:
        parts.append("<p>" + escape(message) + "</p>")
    for item in page.library.documents():
        parts.append(
            "<li>" + escape(item.name)
            + "<form method=\"post\" action=\"" + action + "\">"
            + "<input type=\"hidden\" name=\"action\" value=\"删除\">"
            + "<input type=\"hidden\" name=\"doc_id\" value=\"" + escape(item.doc_id) + "\">"
            + "<button type=\"submit\">删除</button></form></li>"
        )
    parts.append(
        "<form method=\"post\" action=\"" + action + "\" enctype=\"multipart/form-data\">"
        + "<input type=\"hidden\" name=\"action\" value=\"上传\">"
        + "<input type=\"file\" name=\"file\">"
        + "<button type=\"submit\">上传</button></form>"
    )
    return _document("".join(parts))
```

`_upload_document` 和 `_delete_document` 失败、成功都改成 `page.open_documents(...)`。

`_render_library` 删掉文件列表、上传表单和 `<a href=".../generation">生成</a>`。留下标题「目标」、可选失败句、`text` 和「生成目标」。有目标文字时仍留下「确认」。

`response_for` 在 objectives 分支前增加：

```python
if parts == ["documents"] and method == "GET":
    return _html(page.open_documents())
if parts == ["documents"] and method == "POST":
    fields = parse_qs(body, keep_blank_values=True)
    action = fields.get("action", [""])[-1]
    if action == "上传":
        return _html(_upload_document(page, uploads or {}, filenames or {}))
    if action == "删除":
        return _html(_delete_document(page, fields.get("doc_id", [""])[-1]))
    return _html(page.open_documents())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest tests/test_teacher_documents.py tests/test_document_page.py tests/test_document_acceptance.py tests/test_document_confirm.py tests/test_teacher_text_generation_success.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

用户没要求时跳过。

```bash
git add src/scaffolding/teacher_page.py tests/test_teacher_documents.py tests/test_document_page.py tests/test_document_acceptance.py
git commit -m "Move teacher documents off the objectives page"
```

---

### Task 3: 账号管理

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Test: `tests/test_teacher_accounts.py`

**Interfaces:**
- Consumes: `Roster.move_student`、`Roster.reset_password`、`Roster.classes`、`Roster.students`
- Produces: `TeacherPage.open_accounts(self, message: str = "") -> str`。`response_for` 认识 GET/POST `/accounts`。

- [ ] **Step 1: Write the failing test**

新建 `tests/test_teacher_accounts.py`：

```python
from scaffolding.records import TrueFalseQuestion
from scaffolding.tasks import StudentWork
from scaffolding.teacher_page import response_for
from tests.classroom_helpers import form, room, student_cookie, text


def test_accounts_lists_students_and_resets_a_password():
    page = room()
    first = page.roster.create_class("一班")
    page.roster.import_rows(first.class_id, ((2, "s1", "secret", "甲"),))

    opened = text(response_for(page.teacher, "GET", "/accounts", ""))
    assert "<h1>账号管理</h1>" in opened
    assert "甲" in opened and "s1" in opened and "一班" in opened

    empty = text(response_for(page.teacher, "POST", "/accounts", form(action="重置密码", account="s1", password="  ")))
    assert "密码不能为空" in empty
    assert page.roster.student(first.class_id, "s1").password == "secret"
    missing = text(response_for(page.teacher, "POST", "/accounts", form(action="重置密码", account="none", password="next")))
    assert "学生不存在" in missing
    changed = text(response_for(page.teacher, "POST", "/accounts", form(action="重置密码", account="s1", password="next")))
    assert "密码已重置" in changed
    assert page.roster.student(first.class_id, "s1").password == "next"


def test_moving_class_keeps_the_answer_and_follows_the_new_class():
    page = room()
    first = page.roster.create_class("一班")
    second = page.roster.create_class("二班")
    page.roster.import_rows(first.class_id, ((2, "s1", "secret", "甲"),))
    task = page.catalog.create((TrueFalseQuestion("判断说法", "正确", "依据"),))
    page.catalog.publish(task.task_id)
    page.classwork.assign(page.catalog, task.task_id, (first.class_id,))
    work = StudentWork(task.task_id, task.questions)
    work.edit(0, selected=("正确",))
    page.classwork._works[( "s1", task.task_id )] = work

    same = text(response_for(page.teacher, "POST", "/accounts", form(action="换班", account="s1", class_id=first.class_id)))
    assert "学生不存在" not in same
    assert page.roster.student(first.class_id, "s1").class_id == first.class_id
    blank = text(response_for(page.teacher, "POST", "/accounts", form(action="换班", account="s1", class_id="  ")))
    assert "先选择班级" in blank
    unknown = text(response_for(page.teacher, "POST", "/accounts", form(action="换班", account="s1", class_id="class-9")))
    assert "班级不存在" in unknown
    moved = text(response_for(page.teacher, "POST", "/accounts", form(action="换班", account="s1", class_id=second.class_id)))
    assert "甲" in moved and "二班" in moved
    assert page.roster.students(first.class_id) == ()
    assert page.roster.students(second.class_id)[0].account == "s1"
    assert page.classwork._works[("s1", task.task_id)].answers[0].selected == ("正确",)
    todo = text(response_for(page, "GET", "/student", "", 0, student_cookie(page)))
    assert task.task_id not in todo
```

`student_cookie` 在学生已存在时不会重复导入。这里学生已经导入，直接用它登录。

- [ ] **Step 2: Run test to verify it fails**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest tests/test_teacher_accounts.py -v`

Expected: FAIL，`/accounts` 是「任务不存在」。

- [ ] **Step 3: Write minimal implementation**

```python
def open_accounts(self, message: str = "") -> str:
    return _render_accounts(self, message)


def _render_accounts(page, message: str) -> str:
    action = _with_prefix(page.prefix, "/accounts")
    parts = ["<h1>账号管理</h1>"]
    if message:
        parts.append("<p>" + escape(message) + "</p>")
    if page.roster is None:
        return _document("".join(parts))
    for item in page.roster.classes():
        for student in page.roster.students(item.class_id):
            options = []
            for choice in page.roster.classes():
                selected = " selected" if choice.class_id == student.class_id else ""
                options.append(
                    "<option value=\"" + escape(choice.class_id) + "\"" + selected + ">"
                    + escape(choice.name) + "</option>"
                )
            parts.append(
                "<li>" + escape(student.name) + " " + escape(student.account) + " " + escape(item.name)
                + "<form method=\"post\" action=\"" + action + "\">"
                + "<input type=\"hidden\" name=\"account\" value=\"" + escape(student.account) + "\">"
                + "<input name=\"password\">"
                + "<button type=\"submit\" name=\"action\" value=\"重置密码\">重置密码</button></form>"
                + "<form method=\"post\" action=\"" + action + "\">"
                + "<input type=\"hidden\" name=\"account\" value=\"" + escape(student.account) + "\">"
                + "<select name=\"class_id\">" + "".join(options) + "</select>"
                + "<button type=\"submit\" name=\"action\" value=\"换班\">换班</button></form></li>"
            )
    return _document("".join(parts))


def _apply_accounts(page, fields) -> str:
    action = fields.get("action", [""])[-1]
    account = fields.get("account", [""])[-1].strip()
    student = None if page.roster is None else page.roster._students.get(account)
    if action == "重置密码":
        if student is None:
            return page.open_accounts("学生不存在")
        try:
            page.roster.reset_password(student.class_id, account, fields.get("password", [""])[-1])
        except RosterError as error:
            return page.open_accounts(str(error))
        return page.open_accounts("密码已重置")
    if action == "换班":
        if page.roster is None or student is None:
            return page.open_accounts("学生不存在")
        try:
            page.roster.move_student(account, fields.get("class_id", [""])[-1])
        except RosterError as error:
            return page.open_accounts(str(error))
        return page.open_accounts()
    return page.open_accounts()
```

`response_for` 增加：

```python
if parts == ["accounts"] and method == "GET":
    return _html(page.open_accounts())
if parts == ["accounts"] and method == "POST":
    return _html(_apply_accounts(page, parse_qs(body, keep_blank_values=True)))
```

不要在页面上调用私有 `_students` 以外的新存储。查找可以用 `_students`，因为名册没有按账号查找的公开方法；如果实现时愿意，先加 `Roster.find_student(self, account: str) -> StudentRecord | None`，两个任务都用它。上面的代码直接读 `_students`。

- [ ] **Step 4: Run test to verify it passes**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest tests/test_teacher_accounts.py tests/test_roster.py::test_move_student_changes_class_or_rejects_in_order -q`

Expected: PASS

- [ ] **Step 5: Commit**

用户没要求时跳过。

```bash
git add src/scaffolding/teacher_page.py tests/test_teacher_accounts.py
git commit -m "Reset passwords and move students from one account list"
```

---

### Task 4: 新建的两个入口

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Modify: `tests/test_teacher_objective_generation_acceptance.py`
- Test: `tests/test_teacher_new_task.py`

**Interfaces:**
- Consumes: `TeacherPage.create_task`、`TeacherPage.open_objectives`
- Produces: GET `/tasks/new` 返回选择页。任务列表的「新建」改为指向它的链接。列表不再包含「目标」。

- [ ] **Step 1: Write the failing test**

新建 `tests/test_teacher_new_task.py`：

```python
from scaffolding.teacher_page import TeacherPage, response_for
from tests.teacher_objectives_helpers import text


def test_new_task_offers_manual_and_agent_choices():
    page = TeacherPage()
    listed = text(response_for(page, "GET", "/", ""))
    choice = text(response_for(page, "GET", "/tasks/new", ""))

    assert 'href="/tasks/new"' in listed
    assert ">目标<" not in listed
    assert "<h1>新建任务</h1>" in choice
    assert "手动添加" in choice
    assert 'href="/objectives"' in choice
    assert "智能体生成" in choice
    assert page.catalog._tasks == {}

    created = text(response_for(page, "POST", "/tasks", ""))
    assert "task-1" in created
    assert "未发布" in created
```

把 `tests/test_teacher_objective_generation_acceptance.py` 里这两行：

```python
assert 'href="/teacher/objectives"' in listed
assert 'href="/teacher/generation">生成</a>' in objectives
```

换成：

```python
assert 'href="/teacher/tasks/new"' in listed
assert ">目标<" not in listed
assert 'href="/teacher/generation"' not in objectives
assert "生成目标" in objectives
```

- [ ] **Step 2: Run test to verify it fails**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest tests/test_teacher_new_task.py tests/test_teacher_objective_generation_acceptance.py::test_the_classroom_hides_objective_generation_until_objectives_exist -v`

Expected: FAIL，列表仍指向「目标」，`/tasks/new` 被当成任务标识。

- [ ] **Step 3: Write minimal implementation**

`_render_list` 里的新建表单和「目标」链接改成：

```python
"<a href=\"" + _with_prefix(page.prefix, "/tasks/new") + "\">新建</a>"
```

不要再输出 `href=".../objectives">目标`。班级、修改密码和退出这一步先留在列表里，下一步再挪进导航。

`response_for` 在 `parts == ["tasks"]` 的创建分支之后、按任务标识打开之前增加：

```python
if parts == ["tasks", "new"] and method == "GET":
    body = (
        "<h1>新建任务</h1>"
        + "<form method=\"post\" action=\"" + _with_prefix(page.prefix, "/tasks") + "\">"
        + "<button type=\"submit\">手动添加</button></form>"
        + "<a href=\"" + _with_prefix(page.prefix, "/objectives") + "\">智能体生成</a>"
    )
    return _html(_document(body))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest tests/test_teacher_new_task.py tests/test_teacher_objective_generation_acceptance.py tests/test_teacher_page_started.py -q`

Expected: PASS。若 `test_teacher_page_started.py` 只断言删除后的页面含「新建」，链接文字仍能通过。

- [ ] **Step 5: Commit**

用户没要求时跳过。

```bash
git add src/scaffolding/teacher_page.py tests/test_teacher_new_task.py tests/test_teacher_objective_generation_acceptance.py
git commit -m "Offer manual and generated task creation from one page"
```

---

### Task 5: 教师导航和账号面板

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Modify: `src/scaffolding/class_page.py`
- Modify: `src/scaffolding/classroom.py`
- Modify: `src/scaffolding/static/classroom.css`
- Modify: `src/scaffolding/static/teacher.js`（新建）
- Test: `tests/test_teacher_nav.py`

**Interfaces:**
- Consumes: 前四步的页面正文、`Roster.teacher_account`、现有 `/static/logo.png`
- Produces: `teacher_shell(body: str, prefix: str, current: str, account: str) -> str`。已登录教师页的 HTML 都包这一层。修改密码和退出只出现在这层里。

- [ ] **Step 1: Write the failing test**

新建 `tests/test_teacher_nav.py`：

```python
from scaffolding.classroom import response_for
from tests.classroom_helpers import form, room, student_cookie, teacher_cookie, text


def test_logged_in_teacher_pages_share_the_nav():
    page = room()
    cookie = teacher_cookie(page)
    listed = text(response_for(page, "GET", "/teacher", "", 0, cookie))
    library = text(response_for(page, "GET", "/teacher/documents", "", 0, cookie))
    accounts = text(response_for(page, "GET", "/teacher/accounts", "", 0, cookie))

    for html, current in ((listed, "任务"), (library, "资料库"), (accounts, "账号管理")):
        assert 'href="/teacher/"' in html or 'href="/teacher"' in html
        assert 'href="/teacher/classes"' in html
        assert 'href="/teacher/documents"' in html
        assert 'href="/teacher/accounts"' in html
        assert 'src="/static/logo.png"' in html
        assert 'name="old_password"' in html and 'name="password"' in html
        assert "修改密码" in html and "退出" in html
        assert ">目标<" not in html
    assert 'class="current"' in listed
    assert "old_password" not in listed.split("<nav", 1)[-1].split("</nav>", 1)[-1]

    guest = text(response_for(page, "GET", "/teacher", "", 0))
    assert "<nav" not in guest
    assert "<h1>登录</h1>" in guest
    for path in ("/student/documents", "/student/accounts", "/student/tasks/new"):
        missing = response_for(page, "GET", path, "", 0, student_cookie(page))
        assert missing.status == 404
        assert "任务不存在" in text(missing)
```

课堂任务列表的链接如果写成 `href="/teacher"` 而不是 `href="/teacher/"`，断言用 `'href="/teacher"'` 即可，但不要误匹配 `/teacher/classes`。实现里任务链接用 `prefix + "/"`，课堂前缀是 `/teacher`，所以是 `href="/teacher/"`。

- [ ] **Step 2: Run test to verify it fails**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest tests/test_teacher_nav.py -v`

Expected: FAIL，页面没有 `<nav`，修改密码仍在列表正文里。

- [ ] **Step 3: Write minimal implementation**

在 `teacher_page.py` 增加：

```python
def teacher_shell(body: str, prefix: str, current: str, account: str) -> str:
    root = prefix if prefix else "/"
    def item(label: str, path: str) -> str:
        href = prefix + path
        mark = " class=\"current\"" if label == current else ""
        return "<a" + mark + " href=\"" + href + "\">" + label + "</a>"
    nav = (
        "<nav class=\"teacher-nav\">"
        + "<img class=\"logo\" src=\"/static/logo.png\" alt=\"zpd_MAS\">"
        + item("任务", "/")
        + item("班级", "/classes")
        + item("资料库", "/documents")
        + item("账号管理", "/accounts")
        + "<button type=\"button\" class=\"account\">" + escape(account) + "</button>"
        + "<div class=\"account-card\">"
        + "<form method=\"post\" action=\"" + root + "\">"
        + "<input name=\"old_password\"><input name=\"password\">"
        + "<button type=\"submit\" name=\"action\" value=\"修改密码\">修改密码</button></form>"
        + "<form method=\"post\" action=\"" + root + "\">"
        + "<button type=\"submit\" name=\"action\" value=\"退出\">退出</button></form>"
        + "</div></nav>"
    )
    return nav + "<div class=\"teacher-main\">" + body + "</div>"
```

`_document` 改成接收 `prefix`、`current`、`account`，正文先经过 `teacher_shell`。教师页各渲染函数把当前项传进去：任务列表、新建、目标、任务详情和「任务不存在」用「任务」；资料库用「资料库」；账号管理用「账号管理」。有 `page.roster` 时账号文字用 `page.roster.teacher_account`，否则用「账号」。

`_render_list` 删掉原来的修改密码表单和退出表单，保留「班级」链接也可以，因为导航里已经有。不要留下第二套 `old_password`。

`class_page._document` 改为调用 `teacher_shell(body, "/teacher", "班级", "账号")`。默认当前项就是「班级」，现有调用可以不改参数。

`classroom.py` 里已登录教师的「班级不存在」「学生不存在」改用带导航的文档，当前项是「班级」。未登录仍只用 `entrance_page`。

新建 `src/scaffolding/static/teacher.js`：

```javascript
var account = document.querySelector(".teacher-nav .account");
var card = document.querySelector(".teacher-nav .account-card");
if (account && card) {
  account.addEventListener("click", function () {
    card.classList.toggle("open");
  });
}
```

教师页 `_document` 在 `</body>` 前加上 `<script src="/static/teacher.js"></script>`。班级页同样加上。

在 `src/scaffolding/static/classroom.css` 末尾追加。这些规则只约束 `.teacher-nav`，不改登录页：

```css
body:has(.teacher-nav) { max-width: none; margin: 0; padding: 0; background: #f8fafc; }
body:has(.teacher-nav) { display: flex; min-height: 100vh; }
.teacher-nav {
  width: 220px; flex: none; display: flex; flex-direction: column; gap: 8px;
  padding: 28px 18px; background: #fff; border-right: 1px solid #e5e7eb;
}
.teacher-nav .logo { width: 54px; height: auto; margin-bottom: 18px; }
.teacher-nav a {
  display: block; padding: 10px 14px; border-radius: 999px; color: #0f172a;
}
.teacher-nav a:hover { background: #f1f5f9; }
.teacher-nav a.current { background: #eef2ff; color: #1e3a8a; font-weight: 600; }
.teacher-nav .account {
  margin-top: auto; border: 1px solid #e5e7eb; border-radius: 999px;
  background: #fff; color: #0f172a;
}
.teacher-nav .account-card { display: none; padding: 8px 0 0; }
.teacher-nav .account-card.open { display: block; }
.teacher-nav .account-card input,
.teacher-nav .account-card button {
  width: 100%; margin-top: 8px; border: 1px solid #e5e7eb; border-radius: 999px;
  background: #fff; color: #0f172a;
}
.teacher-main { flex: 1; padding: 36px 28px; }
.teacher-nav a, .teacher-nav .account-card { transition: background 0.2s ease, color 0.2s ease; }
@media (prefers-reduced-motion: reduce) {
  .teacher-nav a, .teacher-nav .account-card { transition: none; }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest tests/test_teacher_nav.py tests/test_teacher_new_task.py tests/test_teacher_accounts.py tests/test_teacher_documents.py tests/test_class_login.py tests/test_document_page.py tests/test_login_entrance.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

用户没要求时跳过。

```bash
git add src/scaffolding/teacher_page.py src/scaffolding/class_page.py src/scaffolding/classroom.py src/scaffolding/static/classroom.css src/scaffolding/static/teacher.js tests/test_teacher_nav.py
git commit -m "Add the teacher navigation and account menu"
```

---

### Task 6: 整页回归

**Files:**
- Test: 不新增文件，跑现有教师、班级、文档和登录测试。

**Interfaces:**
- Consumes: 前五步的全部页面

- [ ] **Step 1: Run the teacher and classroom suites**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest tests/test_teacher_nav.py tests/test_teacher_new_task.py tests/test_teacher_accounts.py tests/test_teacher_documents.py tests/test_document_page.py tests/test_document_acceptance.py tests/test_document_confirm.py tests/test_teacher_objective_generation_acceptance.py tests/test_teacher_text_generation_success.py tests/test_class_login.py tests/test_login_entrance.py tests/test_roster.py -q`

Expected: PASS

- [ ] **Step 2: Run the full suite**

Run: `F:\work\zpd_MAS\.worktrees\classroom-launch\.venv\Scripts\python.exe -m pytest -q`

Expected: PASS。若某条旧断言仍要求任务列表上的「目标」或目标页上的「生成」链接，按本规格改那一条断言，不把入口加回去。

- [ ] **Step 3: Commit**

用户没要求时跳过。没有新的产品改动时，不单独提交这一步。
