# 课堂 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让教师页和学生页在同一次本机进程里共用一份任务目录，学生能看到教师发布的任务。

**Architecture:** 教师页和学生页各增加一个默认空字符串的路径前缀，只在写出链接和表单时使用。新的 `classroom.py` 持有同一份 `TaskCatalog`、一个前缀为 `/teacher` 的教师页和一个前缀为 `/student` 的学生页。它按第一个路径片段分发请求，分发前去掉前缀。`/` 是入口。测试调用 `response_for`，不监听端口。

**Tech Stack:** Python 3.14，pytest 9，标准库。实现从 `origin/main` 建工作区。规格在本地 `master` 的 `ba8941d`，文件是 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-21-classroom-design.md`。工作区里若没有这份规格，在 Task 6 从该文件原样复制，不要改写。测试命令是 `.\.venv\Scripts\python.exe -m pytest`。PowerShell 下不要使用 `&&` 或 bash heredoc；提交用 `git commit -m "message"`。不要改 git config，不要 push。

## Global Constraints

- 教师和学生使用同一次进程里的同一份任务目录。教师发布之后，学生待办里出现这份任务。
- 教材和课标的预置内容、教学目标提炼和按目标出题不在这里。
- 教师页和学生页已有的编写、发布、作答、求助和提交规则保持不变。任务目录、会话和模型模块自己的规则不改。
- 不修改 `tasks.py`、`session.py`、`html_assets.py`、`agents.py`、`scripted.py`、`records.py`、`model_decision.py`、`model_scaffold.py`、`model_generator.py`、`model_extractor.py`、`objectives.py`、`knowledge.py`、`generation.py`。
- 教师页前缀是 `/teacher`，学生页前缀是 `/student`。页面单独使用时前缀是空字符串，链接仍是 `/tasks/...`。前缀只加在路径最前面一次。
- `/` 显示「课堂」，链接顺序是「教师」到 `/teacher`，「学生」到 `/student`。这里不显示任务、题目、作答或草稿。
- 分发前去掉前缀。末尾多一个斜杠不影响判断。查询字符串不参与判断。提交正文原样交给页面。
- 学生页请求带上调用方传入的当前时间。教师页不使用这个时间。正式监听用 `time.monotonic()`。第一次打开已发布任务时，这个时间只写入 `shown_at`。停留秒数仍由学生页已有的 `_note_shown` 累加。
- 课堂服务不调用 `catalog.start`。学生打开已发布任务时，仍由学生页自己的 `open_task` 开始。
- 教师删除任务后，目录中的任务、学生端作答、教师草稿、学生页的 `sessions[task_id]` 和 `shown_at[task_id]` 一起去掉。
- 正式运行的学生页使用现有的 `ModelDecisionAgent`、`ModelScaffoldAgent` 和 `deepseek_complete`。监听绑定 `127.0.0.1`。测试使用 `ScriptedDecisionAgent` 和 `ScriptedScaffoldAgent`，不调用 `serve`，不打开浏览器，不访问网络。
- 一名本地教师和一名本地学生，没有登录。进程结束后目录、草稿和会话都不保留。再新建一个课堂服务时，这些都不共享。
- HTML 用拼接，不用 `str.format`。
- 除了 `/` 以外，第一个路径片段不是 `teacher` 或 `student` 时，显示「页面不存在」，状态 404。不显示任务内容，也不显示两个入口。
- 任务不在目录里，或尚未发布时，学生侧的打开、作答、提问、提交和素材下载都显示「任务不存在」，状态 404，不抛出异常，不开始任务，不重建会话。任务已发布时，未知素材名仍返回状态 404、正文 `b""`、类型 `application/octet-stream`。
- 学生看不到教师草稿。学生提交后，教师页仍显示「已开始」，不显示学生作答。已开始后的教师保存仍显示「学生已开始，只能删除」。

## File Map

- Modify: `src/scaffolding/teacher_page.py` — 教师页链接前缀。
- Modify: `src/scaffolding/student_page.py` — 学生页链接前缀。
- Create: `src/scaffolding/classroom.py` — 共用目录、分发、删除后清会话、监听。
- Create: `tests/test_teacher_page_prefix.py`
- Create: `tests/test_student_page_prefix.py`
- Create: `tests/classroom_helpers.py`
- Create: `tests/test_classroom_routes.py`
- Create: `tests/test_classroom_publish.py`
- Create: `tests/test_classroom_delete.py`
- Create: `tests/test_classroom_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-21-classroom-design.md`

---

### Task 1: 教师页链接前缀

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Test: `tests/test_teacher_page_prefix.py`

**Interfaces:**
- Consumes: `TeacherPage(catalog)`。现有调用不传前缀。
- Produces: `TeacherPage(catalog, prefix: str = "")`。`page.prefix` 只参与写出链接。`response_for` 仍接收不带前缀的路径。`_with_prefix(prefix, path) -> str` 返回 `prefix + path`。

- [ ] **Step 1: Write the failing test**

Create `tests/test_teacher_page_prefix.py`:

```python
from scaffolding.records import TrueFalseQuestion
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage


def test_the_teacher_prefix_is_written_on_list_and_task_links():
    catalog = TaskCatalog()
    task = catalog.create((TrueFalseQuestion("判断说法", "正确", "题目里有依据"),))
    catalog.publish(task.task_id)
    catalog.start(task.task_id)
    page = TeacherPage(catalog, prefix="/teacher")

    listed = page.list_tasks()
    opened = page.open_task(task.task_id)

    assert 'href="/teacher/tasks/task-1"' in listed
    assert 'action="/teacher/tasks"' in listed
    assert 'action="/teacher/tasks/task-1"' in opened
    assert 'action="/tasks"' not in listed
    assert 'action="/tasks/task-1"' not in opened
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_page_prefix.py -v`

Expected: FAIL because `TeacherPage` does not accept `prefix`

- [ ] **Step 3: Write minimal implementation**

Change `TeacherPage.__init__` to:

```python
    def __init__(self, catalog, prefix: str = "") -> None:
        self.catalog = catalog
        self.drafts = {}
        self.prefix = prefix
```

Add this function above `_fact`:

```python
def _with_prefix(prefix: str, path: str) -> str:
    return prefix + path
```

In `list_tasks`, build the href and the form action with the prefix:

```python
            href = _with_prefix(self.prefix, "/tasks/" + quote(task.task_id, safe=""))
```

```python
            "<h1>任务列表</h1><form method=\"post\" action=\""
            + _with_prefix(self.prefix, "/tasks") + "\">"
```

In `_render`, both form actions use the page prefix. The started-task branch:

```python
        action = _with_prefix(page.prefix, "/tasks/" + quote(task_id, safe=""))
```

The editable branch uses the same assignment. Do not change `response_for`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_page_prefix.py tests/test_teacher_page_list.py tests/test_teacher_page_open.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/teacher_page.py tests/test_teacher_page_prefix.py
git commit -m "feat: prefix teacher page links"
```

---

### Task 2: 学生页链接前缀

**Files:**
- Modify: `src/scaffolding/student_page.py`
- Test: `tests/test_student_page_prefix.py`

**Interfaces:**
- Consumes: `StudentPage(catalog, decision, scaffold_agent)`。现有三参数调用保持可用。
- Produces: `StudentPage(catalog, decision, scaffold_agent, prefix: str = "")`。`page.prefix` 写入作答、提问、提交、当前素材和某一轮素材的地址。`response_for` 仍接收不带前缀的路径。

- [ ] **Step 1: Write the failing test**

Create `tests/test_student_page_prefix.py`:

```python
from scaffolding.agents import ScaffoldDraft
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage, response_for
from tests.student_page_helpers import body_text, true_false_catalog


def test_the_student_prefix_is_written_on_forms_and_assets():
    catalog, task_id = true_false_catalog()
    draft = ScaffoldDraft(
        text="先看。",
        html='<asset kind="图片素材" name="a.png">AAAA</asset>',
    )
    page = StudentPage(
        catalog,
        ScriptedDecisionAgent(presets=("先看题目",)),
        ScriptedScaffoldAgent(draft),
        prefix="/student",
    )

    opened = body_text(response_for(page, "GET", "/tasks/" + task_id, "", 0))
    asked = body_text(response_for(page, "POST", "/tasks/" + task_id + "/ask", "question=先看题目&source=预设提问", 1))
    listed = body_text(response_for(page, "GET", "/", "", 2))

    assert 'href="/student/tasks/' + task_id + '"' in listed
    assert 'action="/student/tasks/' + task_id + '/answers"' in opened
    assert 'action="/student/tasks/' + task_id + '/ask"' in opened
    assert 'action="/student/tasks/' + task_id + '/submit"' in opened
    assert 'src="/student/tasks/' + task_id + '/assets/a.png"' in asked
    assert 'src="/student/tasks/' + task_id + '/turns/0/assets/a.png"' in asked
    assert 'action="/tasks/' not in opened
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_prefix.py -v`

Expected: FAIL because `StudentPage` does not accept `prefix`

- [ ] **Step 3: Write minimal implementation**

Change `StudentPage.__init__` to:

```python
    def __init__(self, catalog, decision, scaffold_agent, prefix: str = "") -> None:
        self.catalog = catalog
        self.decision = decision
        self.scaffold_agent = scaffold_agent
        self.sessions = {}
        self.shown_at = {}
        self.prefix = prefix
```

Add:

```python
def _with_prefix(prefix: str, path: str) -> str:
    return prefix + path
```

Pass `self.prefix` into every `_render_session` call in `open_task`, `edit_answer`, `ask`, and `submit`:

```python
        return _render_session(session, self.prefix)
```

Change `_render_work` so `_page` receives `page.prefix` immediately after `task_id`. Change `_render_session` to:

```python
def _render_session(session: Session, prefix: str) -> str:
    view = session.view()
    return _page(
        session.work.task_id,
        prefix,
        view.status,
        session.work.questions,
        session.work.answers,
        view.presets,
        locked=view.answers_locked,
        revealed=view.revealed,
        scaffold=view.scaffold,
        dialogue=view.dialogue,
        send_closed=view.send_closed,
    )
```

Change `_page` so its second parameter is `prefix: str`. Replace the three address assignments inside it:

```python
    action = _with_prefix(prefix, "/tasks/" + quote(task_id, safe="") + "/answers")
```

```python
                parts.append("<li>" + _ask_form(task_id, preset, HelpSource.PRESET.value, prefix) + "</li>")
```

```python
        parts.append(_ask_form(task_id, "", HelpSource.OWN.value, prefix, own=True))
        submit_action = _with_prefix(prefix, "/tasks/" + quote(task_id, safe="") + "/submit")
```

```python
        current = _with_prefix(prefix, "/tasks/" + quote(task_id, safe="") + "/assets/")
```

```python
            parts.append(_turn(task_id, index, turn, prefix))
```

Change `_turn` and `_ask_form` to take `prefix: str` before `own`:

```python
def _turn(task_id: str, index: int, turn, prefix: str) -> str:
    body = "<h3>" + escape(turn.question) + "</h3>"
    if turn.scaffold is not None:
        address = _with_prefix(prefix, "/tasks/" + quote(task_id, safe="") + "/turns/" + str(index) + "/assets/")
        body += "<div class=\"turn-scaffold\">" + _scaffold_body(turn.scaffold, address) + "</div>"
    return "<article>" + body + "</article>"


def _ask_form(task_id: str, question: str, source: str, prefix: str, own: bool = False) -> str:
    action = _with_prefix(prefix, "/tasks/" + quote(task_id, safe="") + "/ask")
```

The rest of `_ask_form` stays as it is. Do not change `response_for`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_prefix.py tests/test_student_page_open.py tests/test_student_page_assets.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/student_page.py tests/test_student_page_prefix.py
git commit -m "feat: prefix student page links"
```

---

### Task 3: 课堂入口和路径分发

**Files:**
- Create: `src/scaffolding/classroom.py`
- Create: `tests/classroom_helpers.py`
- Test: `tests/test_classroom_routes.py`

**Interfaces:**
- Consumes: `TeacherPage(catalog, prefix)`、`StudentPage(catalog, decision, scaffold_agent, prefix)`，以及两边的 `response_for`。
- Produces: `Classroom(catalog, decision, scaffold_agent)`。属性是 `catalog`、`teacher`、`student`。`response_for(room, method, path, body, now)`。教师分支返回教师页的 `PageResponse`。学生分支返回学生页的 `PageResponse`。`tests.classroom_helpers.room` 和 `text`。

- [ ] **Step 1: Write the failing test**

Create `tests/classroom_helpers.py`:

```python
from urllib.parse import urlencode

from scaffolding.classroom import Classroom
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.tasks import TaskCatalog


def room():
    return Classroom(TaskCatalog(), ScriptedDecisionAgent(), ScriptedScaffoldAgent())


def text(response) -> str:
    return response.body.decode()


def form(**fields) -> str:
    pairs = []
    for key, value in fields.items():
        if isinstance(value, (list, tuple)):
            for item in value:
                pairs.append((key, item))
        else:
            pairs.append((key, value))
    return urlencode(pairs)
```

Create `tests/test_classroom_routes.py`:

```python
from scaffolding.classroom import response_for
from tests.classroom_helpers import room, text


def test_the_root_links_to_the_teacher_and_the_student():
    page = room()

    html = text(response_for(page, "GET", "/", "", 0))

    assert "<h1>课堂</h1>" in html
    assert html.index("教师") < html.index("学生")
    assert 'href="/teacher"' in html
    assert 'href="/student"' in html
    assert "task-" not in html


def test_prefixes_dispatch_and_a_trailing_slash_or_query_does_not_matter():
    page = room()

    teacher = text(response_for(page, "GET", "/teacher/?ready=1", "", 0))
    student = text(response_for(page, "GET", "/student", "", 0))
    missing = response_for(page, "GET", "/teachers", "", 0)

    assert "<h1>任务列表</h1>" in teacher
    assert "<h1>待办</h1>" in student
    assert missing.status == 404
    assert "页面不存在" in text(missing)
    assert "任务列表" not in text(missing)
    assert "待办" not in text(missing)
    assert 'href="/teacher"' not in text(missing)


def test_an_unknown_teacher_path_stays_a_missing_task():
    page = room()

    missing = response_for(page, "GET", "/teacher/missing", "", 0)

    assert missing.status == 404
    assert "任务不存在" in text(missing)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_classroom_routes.py -v`

Expected: FAIL with `ImportError` for `scaffolding.classroom`

- [ ] **Step 3: Write minimal implementation**

Create `src/scaffolding/classroom.py`:

```python
from urllib.parse import urlsplit

from scaffolding.student_page import StudentPage
from scaffolding.student_page import response_for as student_response_for
from scaffolding.teacher_page import PageResponse
from scaffolding.teacher_page import TeacherPage
from scaffolding.teacher_page import response_for as teacher_response_for


class Classroom:
    def __init__(self, catalog, decision, scaffold_agent) -> None:
        self.catalog = catalog
        self.teacher = TeacherPage(catalog, prefix="/teacher")
        self.student = StudentPage(catalog, decision, scaffold_agent, prefix="/student")


def response_for(room: Classroom, method: str, path: str, body: str, now: float):
    raw_path = urlsplit(path).path
    parts = [part for part in raw_path.split("/") if part]
    if parts == []:
        return _html(_document("<h1>课堂</h1><a href=\"/teacher\">教师</a><a href=\"/student\">学生</a>"))
    if parts[0] not in ("teacher", "student"):
        return _html(_document("<h1>页面不存在</h1>"), 404)
    rest = raw_path[len("/" + parts[0]):] or "/"
    if not rest.startswith("/"):
        rest = "/" + rest
    if parts[0] == "teacher":
        return teacher_response_for(room.teacher, method, rest, body)
    return student_response_for(room.student, method, rest, body, now)


def _document(body: str) -> str:
    return "<!DOCTYPE html><html lang=\"zh\"><body>" + body + "</body></html>"


def _html(text: str, status: int = 200) -> PageResponse:
    return PageResponse(status, "text/html; charset=utf-8", text.encode())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_classroom_routes.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/classroom.py tests/classroom_helpers.py tests/test_classroom_routes.py
git commit -m "feat: route the classroom to the teacher and student pages"
```

---

### Task 4: 发布后的任务出现在学生待办

**Files:**
- Modify: `src/scaffolding/classroom.py`
- Test: `tests/test_classroom_publish.py`

**Interfaces:**
- Consumes: Task 3 的 `Classroom` 和 `response_for`。学生页在任务缺失或未发布时，现有的打开、作答、提问和提交已经返回「任务不存在」；素材下载还没有这层判断。
- Produces: 学生路径带任务标识时，任务缺失或未发布先返回「任务不存在」，不调用学生页，因此不开始任务，素材也不返回空字节。已发布任务仍交给学生页。

- [ ] **Step 1: Write the failing test**

Create `tests/test_classroom_publish.py`:

```python
from scaffolding.classroom import response_for
from tests.classroom_helpers import form, room, text


def _save(page):
    response_for(page, "POST", "/teacher/tasks", "", 0)
    response_for(page, "POST", "/teacher/tasks/task-1", form(**{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "selected-0": "正确",
        "explanation-0": "题目里有依据",
        "action": "save",
    }), 0)


def test_an_unpublished_task_is_hidden_and_does_not_start():
    page = room()
    _save(page)

    student = text(response_for(page, "GET", "/student", "", 0))
    opened = response_for(page, "GET", "/student/tasks/task-1", "", 1)
    asset = response_for(page, "GET", "/student/tasks/task-1/assets/a.png", "", 1)

    assert "task-1" not in student
    assert opened.status == 404
    assert "任务不存在" in text(opened)
    assert asset.status == 404
    assert "任务不存在" in text(asset)
    assert page.catalog.get("task-1").started is False
    assert page.student.sessions == {}


def test_publishing_shows_the_task_and_opening_starts_it():
    page = room()
    _save(page)
    response_for(page, "POST", "/teacher/tasks/task-1", form(action="publish"), 0)

    student = text(response_for(page, "GET", "/student", "", 0))
    opened = text(response_for(page, "GET", "/student/tasks/task-1", "", 10))
    teacher = text(response_for(page, "GET", "/teacher", "", 11))
    missing = response_for(page, "GET", "/student/tasks/task-1/assets/没有.svg", "", 12)

    assert "task-1" in student
    assert "待办" in student
    assert 'href="/student/tasks/task-1"' in student
    assert "判断说法" in opened
    assert "参考答案" not in opened
    assert "解析" not in opened
    assert page.student.shown_at["task-1"] == 10
    assert page.catalog.work("task-1").behavior.dwell_seconds == 0
    assert "已开始" in teacher
    assert missing.status == 404
    assert missing.body == b""
    assert missing.content_type == "application/octet-stream"
    locked = text(response_for(page, "POST", "/teacher/tasks/task-1", form(**{
        "kind-0": "判断",
        "prompt-0": "不该写入",
        "selected-0": "错误",
        "explanation-0": "题目里有依据",
        "action": "save",
    }), 13))
    assert "学生已开始，只能删除" in locked
    assert page.catalog.get("task-1").questions[0].prompt == "判断说法"


def test_a_teacher_draft_is_not_visible_to_the_student():
    page = room()
    _save(page)
    response_for(page, "POST", "/teacher/tasks/task-1", form(action="publish"), 0)
    response_for(page, "POST", "/teacher/tasks/task-1", form(**{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "action": "add:单选",
    }), 0)
    response_for(page, "POST", "/teacher/tasks/task-1", form(**{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "kind-1": "单选",
        "prompt-1": "草稿里的新题干",
        "action": "add-option:1",
    }), 0)

    opened = text(response_for(page, "GET", "/student/tasks/task-1", "", 5))

    assert "判断说法" in opened
    assert "草稿里的新题干" not in opened
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_classroom_publish.py -v`

Expected: FAIL because the unpublished asset request returns an empty body instead of 「任务不存在」

- [ ] **Step 3: Write minimal implementation**

In `response_for`, keep the teacher branch. Before the student call, reject a missing or unpublished task:

```python
    if parts[0] == "teacher":
        return teacher_response_for(room.teacher, method, rest, body)
    if len(parts) >= 3 and parts[1] == "tasks" and not _student_visible(room, parts[2]):
        return _html(_document("<h1>任务不存在</h1>"), 404)
    return student_response_for(room.student, method, rest, body, now)


def _student_visible(room: Classroom, task_id: str) -> bool:
    try:
        task = room.catalog.get(task_id)
    except KeyError:
        return False
    return task.published
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_classroom_publish.py tests/test_classroom_routes.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/classroom.py tests/test_classroom_publish.py
git commit -m "feat: show a published task on the student page"
```

---

### Task 5: 删除任务时清掉学生会话

**Files:**
- Modify: `src/scaffolding/classroom.py`
- Test: `tests/test_classroom_delete.py`

**Interfaces:**
- Consumes: Task 4 的 `response_for`。教师页的 `action=delete` 已经删除目录任务、学生端作答和教师草稿。
- Produces: 这次删除成功后，`room.student.sessions` 和 `room.student.shown_at` 不再含该任务。后续学生请求不重建它们。

- [ ] **Step 1: Write the failing test**

Create `tests/test_classroom_delete.py`:

```python
import pytest

from scaffolding.classroom import response_for
from tests.classroom_helpers import form, room, text


def _started(page):
    response_for(page, "POST", "/teacher/tasks", "", 0)
    response_for(page, "POST", "/teacher/tasks/task-1", form(**{
        "kind-0": "综合",
        "prompt-0": "完成作品",
        "requirements-0": "写明人员",
        "answer-0": "",
        "explanation-0": "",
        "action": "save",
    }), 0)
    response_for(page, "POST", "/teacher/tasks/task-1", form(action="publish"), 0)
    response_for(page, "GET", "/student/tasks/task-1", "", 3)
    response_for(page, "POST", "/student/tasks/task-1/answers", form(**{"text-0": "学生写下的答案"}), 4)


def test_delete_removes_the_student_session_and_later_requests_do_not_rebuild_it():
    page = room()
    _started(page)

    response_for(page, "POST", "/teacher/tasks/task-1", form(action="delete"), 5)
    opened = response_for(page, "GET", "/student/tasks/task-1", "", 6)
    asset = response_for(page, "GET", "/student/tasks/task-1/assets/a.png", "", 6)
    teacher = text(response_for(page, "GET", "/teacher", "", 6))
    student = text(response_for(page, "GET", "/student", "", 6))

    assert "task-1" not in teacher
    assert "task-1" not in student
    assert "task-1" not in page.teacher.drafts
    assert "task-1" not in page.student.sessions
    assert "task-1" not in page.student.shown_at
    assert opened.status == 404
    assert "任务不存在" in text(opened)
    assert "任务不存在" in text(asset)
    assert page.student.sessions == {}
    assert page.student.shown_at == {}
    with pytest.raises(KeyError):
        page.catalog.get("task-1")
    with pytest.raises(KeyError):
        page.catalog.work("task-1")


def test_submit_leaves_the_teacher_page_without_the_student_answer():
    page = room()
    _started(page)

    response_for(page, "POST", "/student/tasks/task-1/submit", "", 8)
    teacher = text(response_for(page, "GET", "/teacher/tasks/task-1", "", 9))

    assert "已开始" in teacher
    assert "学生写下的答案" not in teacher
    assert "待办" not in teacher
    assert "已完成" not in teacher
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_classroom_delete.py -v`

Expected: FAIL because `shown_at` still contains `task-1` after delete

- [ ] **Step 3: Write minimal implementation**

Add `parse_qs` to the urllib import. Replace the teacher branch with:

```python
    if parts[0] == "teacher":
        response = teacher_response_for(room.teacher, method, rest, body)
        if method == "POST" and len(parts) == 3 and parts[1] == "tasks":
            action = parse_qs(body, keep_blank_values=True).get("action", [""])[-1]
            task_id = parts[2]
            if action == "delete" and task_id not in room.catalog._tasks:
                room.student.sessions.pop(task_id, None)
                room.student.shown_at.pop(task_id, None)
        return response
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_classroom_delete.py tests/test_classroom_publish.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/classroom.py tests/test_classroom_delete.py
git commit -m "feat: drop the student session when the teacher deletes a task"
```

---

### Task 6: 验收和本机监听

**Files:**
- Modify: `src/scaffolding/classroom.py`
- Create: `tests/test_classroom_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-21-classroom-design.md`

**Interfaces:**
- Consumes: Task 5 的 `Classroom` 和 `response_for`。`deepseek_complete`、`ModelDecisionAgent`、`ModelScaffoldAgent`。
- Produces: `serve(room: Classroom, port: int) -> None`。`production_classroom(*, post, api_key=None) -> Classroom`。测试不调用 `serve`。

- [ ] **Step 1: Write the failing test**

If `docs/superpowers/specs/2026-10-21-classroom-design.md` is missing in this worktree, copy `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-21-classroom-design.md` unchanged. Do not edit it.

Create `tests/test_classroom_acceptance.py`:

```python
from pathlib import Path

from scaffolding.classroom import production_classroom, response_for, serve
from tests.classroom_helpers import room, text


def test_a_new_classroom_does_not_see_another_catalog_draft_or_session():
    first = room()
    response_for(first, "POST", "/teacher/tasks", "", 0)
    first.teacher.drafts["task-1"] = ()
    first.student.shown_at["task-1"] = 1
    second = room()

    assert "task-1" not in text(response_for(second, "GET", "/teacher", "", 0))
    assert "task-1" not in text(response_for(second, "GET", "/student", "", 0))
    assert second.teacher.drafts == {}
    assert second.student.sessions == {}
    assert second.student.shown_at == {}
    assert first.catalog is not second.catalog


def test_the_spec_is_present_and_the_listener_is_not_started():
    assert Path("docs/superpowers/specs/2026-10-21-classroom-design.md").is_file()
    assert callable(serve)
    assert callable(production_classroom)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_classroom_acceptance.py -v`

Expected: FAIL with `ImportError` for `serve` or `production_classroom`, or because the spec file is missing

- [ ] **Step 3: Write minimal implementation**

Add these imports at the top of `classroom.py`:

```python
import time
from urllib.parse import parse_qs, quote, urlsplit

from scaffolding.model_decision import ModelDecisionAgent
from scaffolding.model_generator import deepseek_complete
from scaffolding.model_scaffold import ModelScaffoldAgent
from scaffolding.tasks import TaskCatalog
```

Remove the old `from urllib.parse import urlsplit` line when adding this import. `parse_qs` is already required by Task 5.

Add these two functions at the end of `classroom.py`. `Classroom.__init__` already gives the student page the prefix `/student`, so this function passes the model agents into that constructor:

```python
def production_classroom(*, post, api_key=None) -> Classroom:
    catalog = TaskCatalog()

    def complete(messages):
        return deepseek_complete(messages, post=post, api_key=api_key)

    return Classroom(catalog, ModelDecisionAgent(complete), ModelScaffoldAgent(complete))


def serve(room: Classroom, port: int) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._respond()

        def do_POST(self) -> None:
            self._respond()

        def _respond(self) -> None:
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length).decode("utf-8")
            response = response_for(room, self.command, self.path, raw, time.monotonic())
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            filename = getattr(response, "filename", "")
            if filename:
                encoded = quote(filename, safe="")
                self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + encoded)
            self.send_header("Content-Length", str(len(response.body)))
            self.end_headers()
            self.wfile.write(response.body)

        def log_message(self, *args) -> None:
            return

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
```

No test calls `serve`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS. The count is the previous suite plus the new classroom tests. No test calls `serve`.

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/classroom.py tests/test_classroom_acceptance.py docs/superpowers/specs/2026-10-21-classroom-design.md
git commit -m "test: accept the local classroom for a shared task catalog"
```

The spec file in this commit must be the unchanged copy from `ba8941d`.
