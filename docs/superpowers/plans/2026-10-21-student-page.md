# 学生页面 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用一个本地页面服务让学生打开已发布的任务，作答、求助、按件查看并保存支架素材，然后提交。

**Architecture:** 新增 `student_page.py`。它持有一份任务目录、一个决策智能体和一个支架智能体，并为已经成功建立的会话保留 `Session`。页面由标准库拼出 HTML。测试调用 `StudentPage` 和 `response_for`，不监听端口，不打开浏览器。正式运行的 `production_page` 使用已有的 DeepSeek 决策智能体和支架智能体；`serve` 只给本机浏览器使用，测试不调用它。

**Tech Stack:** Python 3.14，pytest 9，标准库。实现从 `origin/main` 建工作区。规格在本地 `master` 的 `ce36e3d`，文件是 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-21-student-page-design.md`。工作区里若没有这份规格，从该文件原样复制，不要改写。测试命令是 `.\.venv\Scripts\python.exe -m pytest`。PowerShell 下不要使用 `&&` 或 bash heredoc；提交用 `git commit -m "message"`。不要改 git config，不要 push。

## Global Constraints

- 本计划只做学生页面。教师页面、教材和课标的预置内容不在这里。
- 任务仍由现有库函数事先发布到这次服务使用的任务目录。目录是空的，待办就是空的。这次不预置样例任务。
- 服务和任务目录只活在这次进程里。进程结束后，任务、作答和会话都不保留。
- 这一服务只有一名本地学生，没有登录。页面有两处：待办，以及一份任务。
- 待办只显示已发布任务的标识和执行状态。出现在待办里不开始任务，不建立会话，不累计停留时间，不显示参考答案、解析和支架。
- 打开已发布任务时，若还没开始就先开始，再建立会话。成功建立的会话保留到进程结束。再次打开、改答案、求助和提交都用这份会话。
- 提交前不显示参考答案和解析。题干、选项、作答要求、作答、预设提问、求助原话、支架文字和文件名都按文字写进页面。
- 求助成功后显示支架文字，并按件显示图片素材、思维导图、结构图和微格动画。每件显示类型和文件名，并用该件自己的地址显示内容。模型返回的 HTML 不整页嵌进页面。
- 导出一次一件，返回该件的文件名和内容。同一文件名有多件时，返回当前支架里的第一件。其他文件名不返回内容。没有素材时不提供导出。
- 画出任务页时记下时刻。下一次改答案、求助、提交或再次打开该页时，把大于零的经过秒数加到已保存的停留时间上。不大于零则不加。还没有会话时不记停留时间。空白提问不调用两个智能体，但已有会话时仍记停留时间。
- 建立会话失败时不保存会话。页面显示题目和已有作答，没有预设提问和支架。再次打开重新建立。仍然失败时，改答案、求助和提交都不发生。
- 改答案先保存，再更新预设提问。更新失败时，新作答留下，预设提问仍是上一次的。不合格作答被拒绝，页面仍是原来的作答。
- 类型不在六类之中、调用失败，或支架没有文字也没有四类素材时，不显示新支架。已有支架和预设提问保留。这次提问记在对话里，这一条下面没有支架。
- 提交后作答只读，求助入口关闭，预设提问清空，已有对话还在，并显示提交当时的题目、作答、参考答案和解析。综合题没填的参考答案或解析就是空的。之后再改或再求助会被拒绝。
- 正式运行使用已有的 `ModelDecisionAgent` 和 `ModelScaffoldAgent`，完成函数是已有的 `deepseek_complete`。测试注入脚本智能体，不发出网络请求。
- 不修改 `session.py`、`tasks.py`、`html_assets.py`、`agents.py`、`scripted.py`、`records.py`、`model_decision.py`、`model_scaffold.py`、`model_generator.py`、`model_extractor.py`、`objectives.py`、`knowledge.py`、`generation.py`。

## File Map

- Create: `src/scaffolding/student_page.py` — 待办、任务页、作答、求助、提交、素材和停留时间。
- Create: `tests/student_page_helpers.py` — 测试用的目录和响应正文。
- Create: `tests/test_student_page_todo.py`
- Create: `tests/test_student_page_open.py`
- Create: `tests/test_student_page_failure.py`
- Create: `tests/test_student_page_edit.py`
- Create: `tests/test_student_page_ask.py`
- Create: `tests/test_student_page_assets.py`
- Create: `tests/test_student_page_submit.py`
- Create: `tests/test_student_page_dwell.py`
- Create: `tests/test_student_page_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-21-student-page-design.md`
- Do not modify: 上面 Global Constraints 列出的已有模块。

---

### Task 1: 待办

**Files:**
- Create: `src/scaffolding/student_page.py`
- Create: `tests/student_page_helpers.py`
- Test: `tests/test_student_page_todo.py`

**Interfaces:**
- Consumes: `TaskCatalog.student_tasks()`、`display_status` 已由任务目录提供。`ScriptedDecisionAgent`、`ScriptedScaffoldAgent`。
- Produces: `PageResponse(status: int, content_type: str, body: bytes, filename: str = "")`。`StudentPage(catalog, decision, scaffold_agent)`，属性 `catalog`、`decision`、`scaffold_agent`、`sessions`、`shown_at`。`StudentPage.todo() -> str`。`response_for(page, method: str, path: str, body: str, now: float) -> PageResponse`。

- [ ] **Step 1: Write the failing test**

Create `tests/student_page_helpers.py`:

```python
from scaffolding.records import TrueFalseQuestion
from scaffolding.tasks import TaskCatalog


def true_false_catalog(prompt="判断说法"):
    catalog = TaskCatalog()
    task = catalog.create((TrueFalseQuestion(prompt, "正确", "题目里有依据"),))
    catalog.publish(task.task_id)
    return catalog, task.task_id


def body_text(response) -> str:
    return response.body.decode()
```

Create `tests/test_student_page_todo.py`:

```python
from scaffolding.records import TrueFalseQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage, response_for
from scaffolding.tasks import TaskCatalog
from tests.student_page_helpers import body_text, true_false_catalog


def _page(catalog):
    return StudentPage(catalog, ScriptedDecisionAgent(), ScriptedScaffoldAgent())


def test_empty_catalog_has_an_empty_todo():
    page = _page(TaskCatalog())

    assert "<h1>待办</h1><ul></ul>" in page.todo()
    assert page.sessions == {}


def test_todo_lists_only_published_tasks_and_does_not_start_them():
    catalog, task_id = true_false_catalog()
    hidden = catalog.create((TrueFalseQuestion("未发布题目", "错误", "未发布解析"),))
    page = _page(catalog)

    html = page.todo()

    assert task_id in html
    assert "待办" in html
    assert "未发布题目" not in html
    assert "题目里有依据" not in html
    assert "未发布解析" not in html
    assert catalog.get(task_id).started is False
    assert page.sessions == {}
    response = response_for(page, "GET", "/", "", 0)
    assert response.status == 200
    assert body_text(response) == html


def test_submitted_task_is_listed_as_finished_without_a_session():
    catalog, task_id = true_false_catalog()
    catalog.start(task_id)
    catalog.mark_submitted(task_id)
    page = _page(catalog)

    assert task_id in page.todo()
    assert "已完成" in page.todo()
    assert page.sessions == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_todo.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'scaffolding.student_page'`

- [ ] **Step 3: Write minimal implementation**

Create `src/scaffolding/student_page.py`:

```python
from dataclasses import dataclass
from html import escape
from urllib.parse import quote, unquote, urlsplit


@dataclass(frozen=True)
class PageResponse:
    status: int
    content_type: str
    body: bytes
    filename: str = ""


class StudentPage:
    def __init__(self, catalog, decision, scaffold_agent) -> None:
        self.catalog = catalog
        self.decision = decision
        self.scaffold_agent = scaffold_agent
        self.sessions = {}
        self.shown_at = {}

    def todo(self) -> str:
        items = []
        for listed in self.catalog.student_tasks():
            href = "/tasks/" + quote(listed.task_id, safe="")
            items.append(
                "<li><a href=\"" + href + "\">" + escape(listed.task_id)
                + "</a> " + escape(listed.status) + "</li>"
            )
        return _document("<h1>待办</h1><ul>" + "".join(items) + "</ul>")


def _document(body: str) -> str:
    return "<!DOCTYPE html><html lang=\"zh\"><body>" + body + "</body></html>"


def _missing() -> str:
    return _document("<h1>任务不存在</h1>")


def _html_response(text: str, status: int = 200) -> PageResponse:
    return PageResponse(status, "text/html; charset=utf-8", text.encode())


def response_for(page: StudentPage, method: str, path: str, body: str, now: float) -> PageResponse:
    parts = [unquote(part) for part in urlsplit(path).path.split("/") if part]
    if method == "GET" and parts == []:
        return _html_response(page.todo())
    return _html_response(_missing(), 404)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_todo.py -v`

Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add src/scaffolding/student_page.py tests/student_page_helpers.py tests/test_student_page_todo.py
git commit -m "feat: list published tasks on the student todo page"
```

---

### Task 2: 打开任务

**Files:**
- Modify: `src/scaffolding/student_page.py`
- Test: `tests/test_student_page_open.py`

**Interfaces:**
- Consumes: Task 1 的 `StudentPage`、`response_for`、`_document`、`_html_response`、`_missing`。`Session`、`ChoiceQuestion`、`TrueFalseQuestion`、`OpenQuestion`、`SelectionMode`。
- Produces: `StudentPage.open_task(task_id: str, now: float) -> str`。`GET /tasks/<task_id>` 调用它并返回 200。成功时 `sessions[task_id]` 是那份 `Session`，`shown_at[task_id]` 记下 `now`。

- [ ] **Step 1: Write the failing test**

Create `tests/test_student_page_open.py`:

```python
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage, response_for
from scaffolding.tasks import TaskCatalog
from tests.student_page_helpers import body_text


def _catalog():
    catalog = TaskCatalog()
    task = catalog.create((
        ChoiceQuestion("选出<人员>", SelectionMode.SINGLE, ("人员", "<硬件>"), ("人员",), "选择依据"),
        ChoiceQuestion("选出组成", SelectionMode.MULTIPLE, ("人员", "硬件", "软件"), ("人员", "硬件"), "多选依据"),
        TrueFalseQuestion("判断说法", "正确", "题目里有依据"),
        OpenQuestion("完成作品", "写明人员", "标准作品", "作品解析"),
    ))
    catalog.publish(task.task_id)
    return catalog, task.task_id


def test_opening_a_published_task_starts_it_and_shows_questions_without_keys():
    catalog, task_id = _catalog()
    decision = ScriptedDecisionAgent(presets=("先看题目",))
    page = StudentPage(catalog, decision, ScriptedScaffoldAgent())

    html = page.open_task(task_id, 0)

    assert catalog.get(task_id).started is True
    assert task_id in page.sessions
    assert page.shown_at[task_id] == 0
    assert "单选" in html
    assert "多选" in html
    assert 'type="checkbox"' in html
    assert "选出&lt;人员&gt;" in html
    assert "&lt;硬件&gt;" in html
    assert "<硬件>" not in html
    assert "判断" in html
    assert "判断说法" in html
    assert "综合" in html
    assert "完成作品" in html
    assert "写明人员" in html
    assert "先看题目" in html
    assert "选择依据" not in html
    assert "多选依据" not in html
    assert "题目里有依据" not in html
    assert "标准作品" not in html
    assert "作品解析" not in html
    assert "参考答案" not in html
    assert "解析" not in html
    assert "<h2>支架</h2>" not in html
    response = response_for(page, "GET", "/tasks/" + task_id, "", 1)
    assert response.status == 200
    assert task_id in body_text(response)


def test_opening_again_uses_the_same_session():
    catalog, task_id = _catalog()
    decision = ScriptedDecisionAgent(presets=("先看题目",))
    page = StudentPage(catalog, decision, ScriptedScaffoldAgent())
    page.open_task(task_id, 0)
    decision.presets = ("新的预设",)

    html = page.open_task(task_id, 1)

    assert "先看题目" in html
    assert "新的预设" not in html
    assert len(page.sessions) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_open.py -v`

Expected: FAIL with `AttributeError: 'StudentPage' object has no attribute 'open_task'`

- [ ] **Step 3: Write minimal implementation**

Add these imports to `src/scaffolding/student_page.py`:

```python
from scaffolding.records import ChoiceQuestion, HelpSource, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.session import Session
```

Add these methods to `StudentPage`, and add the functions below the class. Replace `response_for` with the version here.

```python
def open_task(self, task_id: str, now: float) -> str:
    if not _published(self, task_id):
        return _missing()
    session = self._ensure_session(task_id)
    self._note_shown(session, task_id, now)
    return _render_session(session)


def _ensure_session(self, task_id: str):
    if task_id in self.sessions:
        return self.sessions[task_id]
    task = self.catalog.get(task_id)
    if not task.started:
        self.catalog.start(task_id)
    session = Session(self.catalog, self.catalog.work(task_id), self.decision, self.scaffold_agent)
    self.sessions[task_id] = session
    return session


def _note_shown(self, session, task_id: str, now: float) -> None:
    if task_id not in self.shown_at:
        self.shown_at[task_id] = now
```

```python
def _published(page: StudentPage, task_id: str) -> bool:
    try:
        task = page.catalog.get(task_id)
    except KeyError:
        return False
    return task.published


def _render_session(session: Session) -> str:
    view = session.view()
    return _page(
        session.work.task_id,
        view.status,
        session.work.questions,
        session.work.answers,
        view.presets,
    )


def _page(task_id, status, questions, answers, presets) -> str:
    parts = ["<h1>" + escape(task_id) + "</h1><p>" + escape(status) + "</p>"]
    action = "/tasks/" + quote(task_id, safe="") + "/answers"
    parts.append("<form method=\"post\" action=\"" + action + "\">")
    for index, question in enumerate(questions):
        parts.append(_question(index, question, answers[index], locked=False))
    parts.append("<button type=\"submit\">保存作答</button></form>")
    if presets:
        parts.append("<h2>预设提问</h2><ul>")
        for preset in presets:
            parts.append("<li>" + _ask_form(task_id, preset, HelpSource.PRESET.value) + "</li>")
        parts.append("</ul>")
    parts.append(_ask_form(task_id, "", HelpSource.OWN.value, own=True))
    submit_action = "/tasks/" + quote(task_id, safe="") + "/submit"
    parts.append(
        "<form method=\"post\" action=\"" + submit_action + "\">"
        + "<button type=\"submit\">提交</button></form>"
    )
    return _document("".join(parts))


def _question(index: int, question, answer, locked: bool) -> str:
    if isinstance(question, ChoiceQuestion):
        kind = question.selection.value
        choices = question.choices
        requirements = ""
        input_type = "radio" if question.selection == SelectionMode.SINGLE else "checkbox"
    elif isinstance(question, TrueFalseQuestion):
        kind = "判断"
        choices = ("正确", "错误")
        requirements = ""
        input_type = "radio"
    elif isinstance(question, OpenQuestion):
        kind = "综合"
        choices = ()
        requirements = question.requirements
        input_type = ""
    else:
        raise TypeError("unknown question")
    disabled = " disabled" if locked else ""
    body = (
        "<section><h2>题目" + str(index + 1) + "</h2><p>" + escape(kind)
        + "</p><p>" + escape(question.prompt) + "</p>"
    )
    if requirements:
        body += "<p>" + escape(requirements) + "</p>"
    if choices:
        for choice in choices:
            checked = " checked" if choice in answer.selected else ""
            body += (
                "<label><input type=\"" + input_type + "\" name=\"selected-" + str(index)
                + "\" value=\"" + escape(choice) + "\"" + checked + disabled + ">"
                + escape(choice) + "</label>"
            )
    else:
        body += (
            "<textarea name=\"text-" + str(index) + "\"" + disabled + ">"
            + escape(answer.text) + "</textarea>"
        )
    return body + "</section>"


def _ask_form(task_id: str, question: str, source: str, own: bool = False) -> str:
    action = "/tasks/" + quote(task_id, safe="") + "/ask"
    if own:
        control = "<input type=\"text\" name=\"question\" value=\"\">"
        label = "<button type=\"submit\">提问</button>"
    else:
        control = "<input type=\"hidden\" name=\"question\" value=\"" + escape(question) + "\">"
        label = "<button type=\"submit\">" + escape(question) + "</button>"
    return (
        "<form method=\"post\" action=\"" + action + "\">" + control
        + "<input type=\"hidden\" name=\"source\" value=\"" + escape(source) + "\">"
        + label + "</form>"
    )


def response_for(page: StudentPage, method: str, path: str, body: str, now: float) -> PageResponse:
    parts = [unquote(part) for part in urlsplit(path).path.split("/") if part]
    if method == "GET" and parts == []:
        return _html_response(page.todo())
    if method == "GET" and len(parts) == 2 and parts[0] == "tasks":
        if not _published(page, parts[1]):
            return _html_response(_missing(), 404)
        return _html_response(page.open_task(parts[1], now))
    return _html_response(_missing(), 404)
```

未知题型抛出 `TypeError("unknown question")`。

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_open.py tests/test_student_page_todo.py -v`

Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add src/scaffolding/student_page.py tests/test_student_page_open.py
git commit -m "feat: open a published task on the student page"
```

---

### Task 3: 打不开和会话建立失败

**Files:**
- Modify: `src/scaffolding/student_page.py`
- Test: `tests/test_student_page_failure.py`

**Interfaces:**
- Consumes: Task 2 的 `open_task`、`_ensure_session`、`_page`、`_missing`。
- Produces: `_ensure_session` 在 `Session(...)` 抛出异常时返回 `None`，不写入 `sessions`，不写入 `shown_at`。`_render_work(page, task_id) -> str` 用已开始任务的题目和作答画出页面，没有预设提问和支架。再次打开会重新建立会话。

- [ ] **Step 1: Write the failing test**

Create `tests/test_student_page_failure.py`:

```python
from scaffolding.records import TrueFalseQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage, response_for
from scaffolding.tasks import TaskCatalog
from tests.student_page_helpers import body_text, true_false_catalog


class FailOnce:
    def __init__(self) -> None:
        self.calls = 0

    def suggest(self, record):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("down")
        return ("先看题目",)

    def choose_type(self, record, question):
        return "提示"


class AlwaysFail:
    def suggest(self, record):
        raise RuntimeError("down")

    def choose_type(self, record, question):
        return "提示"


def test_missing_and_unpublished_tasks_show_nothing():
    catalog, task_id = true_false_catalog("判断说法")
    hidden = catalog.create((TrueFalseQuestion("未发布题目", "错误", "未发布解析"),))
    page = StudentPage(catalog, ScriptedDecisionAgent(), ScriptedScaffoldAgent())

    missing = page.open_task("task-missing", 0)
    unpublished = page.open_task(hidden.task_id, 0)
    response = response_for(page, "GET", "/tasks/" + hidden.task_id, "", 0)

    assert "判断说法" not in missing
    assert "未发布题目" not in unpublished
    assert "未发布解析" not in unpublished
    assert "参考答案" not in unpublished
    assert response.status == 404
    assert "未发布题目" not in body_text(response)
    assert task_id not in page.sessions


def test_failed_session_shows_questions_and_the_next_open_retries():
    catalog, task_id = true_false_catalog()
    decision = FailOnce()
    page = StudentPage(catalog, decision, ScriptedScaffoldAgent())

    first = page.open_task(task_id, 0)

    assert "判断说法" in first
    assert "先看题目" not in first
    assert "<h2>支架</h2>" not in first
    assert task_id not in page.sessions
    assert task_id not in page.shown_at
    assert catalog.get(task_id).started is True

    second = page.open_task(task_id, 5)

    assert "先看题目" in second
    assert task_id in page.sessions


def test_actions_do_nothing_while_the_session_cannot_be_created():
    catalog, task_id = true_false_catalog()
    page = StudentPage(catalog, AlwaysFail(), ScriptedScaffoldAgent())
    page.open_task(task_id, 0)

    edited = page.edit_answer(task_id, 0, selected=("错误",), now=1)
    asked = page.ask(task_id, "旧求助原文", "自己写的", 2)
    submitted = page.submit(task_id, 3)

    assert catalog.work(task_id).answers[0].selected == ()
    assert catalog.work(task_id).dialogue == ()
    assert catalog.get(task_id).submitted is False
    assert "旧求助原文" not in asked
    assert "参考答案" not in submitted
    assert task_id not in page.sessions
    assert "判断说法" in edited
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_failure.py -v`

Expected: FAIL with `RuntimeError: down`

- [ ] **Step 3: Write minimal implementation**

Replace `_ensure_session` and `open_task` with these versions. Add `_render_work`, `edit_answer`, `ask`, and `submit`.

```python
def open_task(self, task_id: str, now: float) -> str:
    if not _published(self, task_id):
        return _missing()
    session = self._ensure_session(task_id)
    if session is None:
        return _render_work(self, task_id)
    self._note_shown(session, task_id, now)
    return _render_session(session)


def edit_answer(self, task_id: str, index: int, *, text: str | None = None, selected: tuple[str, ...] | None = None, now: float) -> str:
    if not _published(self, task_id):
        return _missing()
    session = self._ensure_session(task_id)
    if session is None:
        return _render_work(self, task_id)
    self._note_shown(session, task_id, now)
    try:
        session.edit_answer(index, text=text, selected=selected)
    except Exception:
        pass
    return _render_session(session)


def ask(self, task_id: str, question: str, source: str, now: float) -> str:
    if not _published(self, task_id):
        return _missing()
    session = self._ensure_session(task_id)
    if session is None:
        return _render_work(self, task_id)
    self._note_shown(session, task_id, now)
    if source in (HelpSource.PRESET.value, HelpSource.OWN.value):
        try:
            session.ask(question, HelpSource(source))
        except Exception:
            pass
    return _render_session(session)


def submit(self, task_id: str, now: float) -> str:
    if not _published(self, task_id):
        return _missing()
    session = self._ensure_session(task_id)
    if session is None:
        return _render_work(self, task_id)
    self._note_shown(session, task_id, now)
    try:
        session.submit()
    except Exception:
        pass
    return _render_session(session)


def _ensure_session(self, task_id: str):
    if task_id in self.sessions:
        return self.sessions[task_id]
    task = self.catalog.get(task_id)
    if not task.started:
        self.catalog.start(task_id)
    try:
        session = Session(self.catalog, self.catalog.work(task_id), self.decision, self.scaffold_agent)
    except Exception:
        return None
    self.sessions[task_id] = session
    return session
```

```python
from scaffolding.tasks import display_status


def _render_work(page: StudentPage, task_id: str) -> str:
    task = page.catalog.get(task_id)
    work = page.catalog.work(task_id)
    return _page(task_id, display_status(task), work.questions, work.answers, ())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_failure.py tests/test_student_page_open.py -v`

Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add src/scaffolding/student_page.py tests/test_student_page_failure.py
git commit -m "feat: show the task when the first preset call fails"
```

---

### Task 4: 修改作答

**Files:**
- Modify: `src/scaffolding/student_page.py`
- Test: `tests/test_student_page_edit.py`

**Interfaces:**
- Consumes: Task 3 的 `edit_answer(task_id, index, *, text=None, selected=None, now) -> str`。
- Produces: `POST /tasks/<task_id>/answers` 读取 `selected-<index>` 和 `text-<index>`，逐题调用 `edit_answer`。同一请求里后面的调用经过的秒数为零，因此停留锚点只在第一次向前移动。

- [ ] **Step 1: Write the failing test**

Create `tests/test_student_page_edit.py`:

```python
from scaffolding.records import ChoiceQuestion, SelectionMode
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage, response_for
from scaffolding.tasks import TaskCatalog
from tests.student_page_helpers import body_text


class FailSecondSuggest:
    def __init__(self) -> None:
        self.calls = 0

    def suggest(self, record):
        self.calls += 1
        if self.calls >= 2:
            raise RuntimeError("down")
        return ("先看题目",)

    def choose_type(self, record, question):
        return "提示"


def _catalog():
    catalog = TaskCatalog()
    task = catalog.create((
        ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "硬件"), ("人员",), "选择依据"),
    ))
    catalog.publish(task.task_id)
    return catalog, task.task_id


def test_an_accepted_edit_refreshes_presets_and_a_rejected_edit_keeps_the_answer():
    catalog, task_id = _catalog()
    decision = ScriptedDecisionAgent(presets=("先看题目",))
    page = StudentPage(catalog, decision, ScriptedScaffoldAgent())
    page.open_task(task_id, 0)
    decision.presets = ("改后预设",)

    accepted = page.edit_answer(task_id, 0, selected=("人员",), now=1)

    assert 'value="人员" checked' in accepted
    assert "改后预设" in accepted
    assert catalog.work(task_id).answers[0].selected == ("人员",)
    decision.presets = ("不应出现",)

    rejected = page.edit_answer(task_id, 0, selected=("人员", "硬件"), now=2)

    assert 'value="人员" checked' in rejected
    assert "改后预设" in rejected
    assert "不应出现" not in rejected
    assert catalog.work(task_id).answers[0].selected == ("人员",)


def test_a_failed_preset_refresh_keeps_the_new_answer_and_the_old_presets():
    catalog, task_id = _catalog()
    page = StudentPage(catalog, FailSecondSuggest(), ScriptedScaffoldAgent())
    page.open_task(task_id, 0)

    html = page.edit_answer(task_id, 0, selected=("硬件",), now=1)

    assert 'value="硬件" checked' in html
    assert "先看题目" in html
    assert catalog.work(task_id).answers[0].selected == ("硬件",)


def test_posting_the_answer_form_updates_the_page():
    catalog, task_id = _catalog()
    decision = ScriptedDecisionAgent(presets=("先看题目",))
    page = StudentPage(catalog, decision, ScriptedScaffoldAgent())
    page.open_task(task_id, 0)
    decision.presets = ("改后预设",)

    response = response_for(page, "POST", "/tasks/" + task_id + "/answers", "selected-0=人员", 3)

    assert response.status == 200
    assert "改后预设" in body_text(response)
    assert catalog.work(task_id).answers[0].selected == ("人员",)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_edit.py::test_posting_the_answer_form_updates_the_page -v`

Expected: FAIL because the response is the missing-task page and the selection stays empty

- [ ] **Step 3: Write minimal implementation**

Add `from urllib.parse import parse_qs` to the existing urllib import. Replace `response_for` with:

```python
def response_for(page: StudentPage, method: str, path: str, body: str, now: float) -> PageResponse:
    parts = [unquote(part) for part in urlsplit(path).path.split("/") if part]
    fields = parse_qs(body, keep_blank_values=True)
    if method == "GET" and parts == []:
        return _html_response(page.todo())
    if len(parts) >= 2 and parts[0] == "tasks":
        task_id = parts[1]
        if method == "GET" and len(parts) == 2:
            if not _published(page, task_id):
                return _html_response(_missing(), 404)
            return _html_response(page.open_task(task_id, now))
        if method == "POST" and parts[2:] == ["answers"]:
            if not _published(page, task_id):
                return _html_response(_missing(), 404)
            return _html_response(_post_answers(page, task_id, fields, now))
    return _html_response(_missing(), 404)


def _post_answers(page: StudentPage, task_id: str, fields: dict, now: float) -> str:
    indexes = []
    for key in fields:
        if key.startswith("selected-") or key.startswith("text-"):
            suffix = key.split("-", 1)[1]
            if suffix.isdigit():
                indexes.append(int(suffix))
    html = None
    for index in sorted(set(indexes)):
        text_key = "text-" + str(index)
        selected_key = "selected-" + str(index)
        if text_key in fields:
            html = page.edit_answer(task_id, index, text=fields[text_key][-1], now=now)
        if selected_key in fields:
            html = page.edit_answer(task_id, index, selected=tuple(fields[selected_key]), now=now)
    if html is None:
        return page.open_task(task_id, now)
    return html
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_edit.py -v`

Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add src/scaffolding/student_page.py tests/test_student_page_edit.py
git commit -m "feat: edit an answer from the student page"
```

---

### Task 5: 求助和支架

**Files:**
- Modify: `src/scaffolding/student_page.py`
- Test: `tests/test_student_page_ask.py`

**Interfaces:**
- Consumes: Task 3 的 `ask(task_id, question, source, now) -> str`。`HelpSource.PRESET` 的值是 `预设提问`，`HelpSource.OWN` 的值是 `自己写的`。`ScaffoldDraft(text, html, assets=())`。会话会从 HTML 抽出素材。
- Produces: 任务页在有当前支架时输出 `<h2>支架</h2>`、文字、每件素材的类型、文件名、`<img src>` 和 `保存` 链接。对话里每个 `<article>` 含求助原话；没有新支架的一条不含 `class="turn-scaffold"`。`POST /tasks/<task_id>/ask` 读取 `question` 和 `source`。

- [ ] **Step 1: Write the failing test**

Create `tests/test_student_page_ask.py`:

```python
from urllib.parse import quote

from scaffolding.agents import ScaffoldDraft
from scaffolding.records import TrueFalseQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage, response_for
from scaffolding.tasks import TaskCatalog
from tests.student_page_helpers import body_text


def _page(draft=None, scaffold_type="提示", error=None):
    catalog = TaskCatalog()
    task = catalog.create((TrueFalseQuestion("判断说法", "正确", "题目里有依据"),))
    catalog.publish(task.task_id)
    decision = ScriptedDecisionAgent(presets=("先看题目",), scaffold_type=scaffold_type)
    scaffold = ScriptedScaffoldAgent(draft=draft, error=error)
    page = StudentPage(catalog, decision, scaffold)
    return catalog, task.task_id, decision, scaffold, page


_HTML = (
    '<asset kind="图片素材" name="图.png">PNGDATA</asset>'
    '<asset kind="思维导图" name="导图.svg">导图内容</asset>'
    '<asset kind="结构图" name="结构.svg">结构内容</asset>'
    '<asset kind="微格动画" name="动画.html"><anim></asset>'
)


def test_preset_and_own_questions_show_text_and_four_assets():
    draft = ScaffoldDraft(text="先看人员和硬件是否都写到了。", html=_HTML)
    catalog, task_id, decision, scaffold, page = _page(draft)
    page.open_task(task_id, 0)

    clicked = page.ask(task_id, "先看题目", "预设提问", 1)

    assert scaffold.calls[0]["scaffold_type"] == "提示"
    assert scaffold.calls[0]["question"] == "先看题目"
    assert "先看人员和硬件是否都写到了。" in clicked
    assert "图片素材" in clicked and "图.png" in clicked
    assert "思维导图" in clicked and "导图.svg" in clicked
    assert "结构图" in clicked and "结构.svg" in clicked
    assert "微格动画" in clicked and "动画.html" in clicked
    assert quote("图.png", safe="") in clicked
    assert "<asset" not in clicked
    assert "<anim>" not in clicked
    assert "PNGDATA" not in clicked
    decision.presets = ("改后预设",)
    edited = page.edit_answer(task_id, 0, selected=("错误",), now=2)
    assert "先看人员和硬件是否都写到了。" in edited
    assert "改后预设" in edited

    own = response_for(page, "POST", "/tasks/" + task_id + "/ask", "question=还缺什么？&source=自己写的", 3)
    assert scaffold.calls[1]["question"] == "还缺什么？"
    assert "还缺什么？" in body_text(own)


def test_blank_question_does_not_call_the_agents():
    catalog, task_id, decision, scaffold, page = _page(ScaffoldDraft(text="有支架", html=_HTML))
    page.open_task(task_id, 0)

    html = page.ask(task_id, "   ", "自己写的", 1)

    assert decision.choose_calls == []
    assert scaffold.calls == []
    assert "<h2>支架</h2>" not in html


def test_failed_help_keeps_the_existing_scaffold_and_records_the_question():
    draft = ScaffoldDraft(text="先看人员和硬件是否都写到了。", html=_HTML)
    catalog, task_id, decision, scaffold, page = _page(draft)
    page.open_task(task_id, 0)
    page.ask(task_id, "先看题目", "预设提问", 1)
    decision.scaffold_type = "课外"

    illegal = page.ask(task_id, "课外提问", "自己写的", 2)
    article = illegal.split("<article>")[-1]
    assert "课外提问" in article
    assert "turn-scaffold" not in article
    assert "先看人员和硬件是否都写到了。" in illegal
    assert "先看题目" in illegal

    decision.scaffold_type = "提示"
    scaffold.error = RuntimeError("down")
    failed = page.ask(task_id, "调用失败", "自己写的", 3)
    assert "调用失败" in failed.split("<article>")[-1]
    assert "turn-scaffold" not in failed.split("<article>")[-1]
    assert "先看人员和硬件是否都写到了。" in failed

    scaffold.error = None
    scaffold.draft = ScaffoldDraft()
    empty = page.ask(task_id, "空支架", "自己写的", 4)
    assert "空支架" in empty.split("<article>")[-1]
    assert "turn-scaffold" not in empty.split("<article>")[-1]
    assert "先看人员和硬件是否都写到了。" in empty
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_ask.py::test_preset_and_own_questions_show_text_and_four_assets -v`

Expected: FAIL because `图片素材` is absent

- [ ] **Step 3: Write minimal implementation**

Replace `_render_session` and `_page` with these versions. Add `_render_work` argument alignment, `_scaffold_body`, and `_turn`. Extend `response_for` with the ask branch shown here.

```python
def _render_session(session: Session) -> str:
    view = session.view()
    return _page(
        session.work.task_id,
        view.status,
        session.work.questions,
        session.work.answers,
        view.presets,
        scaffold=view.scaffold,
        dialogue=view.dialogue,
    )


def _render_work(page: StudentPage, task_id: str) -> str:
    task = page.catalog.get(task_id)
    work = page.catalog.work(task_id)
    return _page(
        task_id,
        display_status(task),
        work.questions,
        work.answers,
        (),
        dialogue=work.dialogue,
    )


def _page(task_id, status, questions, answers, presets, scaffold=None, dialogue=()) -> str:
    parts = ["<h1>" + escape(task_id) + "</h1><p>" + escape(status) + "</p>"]
    action = "/tasks/" + quote(task_id, safe="") + "/answers"
    parts.append("<form method=\"post\" action=\"" + action + "\">")
    for index, question in enumerate(questions):
        parts.append(_question(index, question, answers[index], locked=False))
    parts.append("<button type=\"submit\">保存作答</button></form>")
    if presets:
        parts.append("<h2>预设提问</h2><ul>")
        for preset in presets:
            parts.append("<li>" + _ask_form(task_id, preset, HelpSource.PRESET.value) + "</li>")
        parts.append("</ul>")
    parts.append(_ask_form(task_id, "", HelpSource.OWN.value, own=True))
    submit_action = "/tasks/" + quote(task_id, safe="") + "/submit"
    parts.append(
        "<form method=\"post\" action=\"" + submit_action + "\">"
        + "<button type=\"submit\">提交</button></form>"
    )
    if scaffold is not None:
        parts.append("<h2>支架</h2>" + _scaffold_body(task_id, scaffold))
    if dialogue:
        parts.append("<h2>对话</h2>")
        for turn in dialogue:
            parts.append(_turn(task_id, turn))
    return _document("".join(parts))


def _scaffold_body(task_id: str, scaffold) -> str:
    parts = ["<p>" + escape(scaffold.text) + "</p>"]
    for asset in scaffold.assets:
        address = "/tasks/" + quote(task_id, safe="") + "/assets/" + quote(asset.filename, safe="")
        parts.append(
            "<figure><figcaption>" + escape(asset.kind.value) + " " + escape(asset.filename)
            + "</figcaption><img src=\"" + escape(address) + "\" alt=\"" + escape(asset.filename)
            + "\"><a href=\"" + escape(address) + "\" download=\"" + escape(asset.filename)
            + "\">保存</a></figure>"
        )
    return "".join(parts)


def _turn(task_id: str, turn) -> str:
    body = "<h3>" + escape(turn.question) + "</h3>"
    if turn.scaffold is not None:
        body += "<div class=\"turn-scaffold\">" + _scaffold_body(task_id, turn.scaffold) + "</div>"
    return "<article>" + body + "</article>"
```

Inside `response_for`, after the answers branch and before the final missing return, add:

```python
if method == "POST" and parts[2:] == ["ask"]:
    if not _published(page, task_id):
        return _html_response(_missing(), 404)
    question = fields.get("question", [""])[-1]
    source = fields.get("source", [""])[-1]
    return _html_response(page.ask(task_id, question, source, now))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_ask.py tests/test_student_page_open.py tests/test_student_page_failure.py -v`

Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add src/scaffolding/student_page.py tests/test_student_page_ask.py
git commit -m "feat: show a scaffold after the student asks"
```

---

### Task 6: 按件保存素材

**Files:**
- Modify: `src/scaffolding/student_page.py`
- Test: `tests/test_student_page_assets.py`

**Interfaces:**
- Consumes: Task 5 的页面地址 `/tasks/<task_id>/assets/<filename>`。当前支架来自 `sessions[task_id].view().scaffold`。
- Produces: `StudentPage.asset(task_id: str, filename: str) -> tuple[str, bytes] | None`。找到时 `response_for` 返回 200、`application/octet-stream`、该件内容和文件名。找不到时返回 404 和空正文。同一文件名返回当前支架里的第一件。

- [ ] **Step 1: Write the failing test**

Create `tests/test_student_page_assets.py`:

```python
from urllib.parse import quote

from scaffolding.agents import ScaffoldDraft
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage, response_for
from tests.student_page_helpers import true_false_catalog


def test_one_asset_is_returned_and_unknown_names_are_empty():
    catalog, task_id = true_false_catalog()
    draft = ScaffoldDraft(
        text="先看。",
        html=(
            '<asset kind="思维导图" name="组成.svg">第一</asset>'
            '<asset kind="结构图" name="组成.svg">第二</asset>'
        ),
    )
    page = StudentPage(catalog, ScriptedDecisionAgent(presets=("先看题目",)), ScriptedScaffoldAgent(draft))
    page.open_task(task_id, 0)
    page.ask(task_id, "先看题目", "预设提问", 1)
    path = "/tasks/" + task_id + "/assets/" + quote("组成.svg", safe="")

    found = response_for(page, "GET", path, "", 2)
    missing = response_for(page, "GET", "/tasks/" + task_id + "/assets/没有.svg", "", 2)

    assert found.status == 200
    assert found.filename == "组成.svg"
    assert found.body == "第一".encode()
    assert found.content_type == "application/octet-stream"
    assert missing.status == 404
    assert missing.body == b""


def test_a_page_without_assets_does_not_offer_export():
    catalog, task_id = true_false_catalog()
    page = StudentPage(catalog, ScriptedDecisionAgent(presets=("先看题目",)), ScriptedScaffoldAgent())
    html = page.open_task(task_id, 0)

    assert ">保存</a>" not in html
    assert page.asset(task_id, "组成.svg") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_assets.py -v`

Expected: FAIL with `AttributeError: 'StudentPage' object has no attribute 'asset'`

- [ ] **Step 3: Write minimal implementation**

Add this method to `StudentPage`:

```python
def asset(self, task_id: str, filename: str) -> tuple[str, bytes] | None:
    session = self.sessions.get(task_id)
    if session is None:
        return None
    scaffold = session.view().scaffold
    if scaffold is None:
        return None
    for asset in scaffold.assets:
        if asset.filename == filename:
            return asset.filename, asset.content
    return None
```

Inside `response_for`, after the task id is known and before the final missing return, add:

```python
if method == "GET" and len(parts) == 4 and parts[2] == "assets":
    found = page.asset(task_id, parts[3])
    if found is None:
        return PageResponse(404, "application/octet-stream", b"")
    filename, content = found
    return PageResponse(200, "application/octet-stream", content, filename)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_assets.py -v`

Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add src/scaffolding/student_page.py tests/test_student_page_assets.py
git commit -m "feat: save one scaffold asset from the student page"
```

---

### Task 7: 提交

**Files:**
- Modify: `src/scaffolding/student_page.py`
- Test: `tests/test_student_page_submit.py`

**Interfaces:**
- Consumes: Task 3 的 `submit(task_id, now) -> str`。`view.answers_locked`、`view.send_closed`、`view.revealed`、`view.status`。
- Produces: `POST /tasks/<task_id>/submit` 调用 `submit`。提交后的页面给输入加上 `disabled`，不再输出保存、提问和提交按钮，并写出每题的参考答案和解析。

- [ ] **Step 1: Write the failing test**

Create `tests/test_student_page_submit.py`:

```python
from scaffolding.agents import ScaffoldDraft
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage, response_for
from scaffolding.tasks import TaskCatalog
from tests.student_page_helpers import body_text


def test_submit_locks_the_page_and_reveals_keys():
    catalog = TaskCatalog()
    task = catalog.create((
        ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "硬件"), ("人员",), "选择依据"),
        TrueFalseQuestion("判断说法", "正确", "题目里有依据"),
        OpenQuestion("完成作品", "写明人员"),
    ))
    catalog.publish(task.task_id)
    decision = ScriptedDecisionAgent(presets=("先看题目",))
    draft = ScaffoldDraft(text="先看人员和硬件是否都写到了。", html="")
    page = StudentPage(catalog, decision, ScriptedScaffoldAgent(draft))
    page.open_task(task.task_id, 0)
    page.edit_answer(task.task_id, 0, selected=("人员",), now=1)
    page.ask(task.task_id, "旧求助原文", "自己写的", 2)

    response = response_for(page, "POST", "/tasks/" + task.task_id + "/submit", "", 3)
    html = body_text(response)

    assert response.status == 200
    assert "已完成" in html
    assert "disabled" in html
    assert "<button type=\"submit\">保存作答</button>" not in html
    assert "<button type=\"submit\">提问</button>" not in html
    assert "<button type=\"submit\">提交</button>" not in html
    assert "先看题目" not in html
    assert "旧求助原文" in html
    assert "先看人员和硬件是否都写到了。" in html
    assert "参考答案：人员" in html
    assert "解析：选择依据" in html
    assert "参考答案：正确" in html
    assert "解析：题目里有依据" in html
    sections = html.split("<section>")
    assert "<p>参考答案：</p><p>解析：</p>" in sections[3]
    assert "已完成" in page.todo()

    again = page.edit_answer(task.task_id, 0, selected=("硬件",), now=4)
    asked = page.ask(task.task_id, "再问一次", "自己写的", 5)

    assert catalog.work(task.task_id).answers[0].selected == ("人员",)
    assert 'value="硬件" checked' not in again
    assert "再问一次" not in asked
    assert len(catalog.work(task.task_id).dialogue) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_submit.py -v`

Expected: FAIL because the response is the missing-task page

- [ ] **Step 3: Write minimal implementation**

Replace `_question` so it accepts `revealed` and appends the two paragraphs. Replace `_page` so locked questions omit the save button, `send_closed` omits preset, own-question, and submit forms, and revealed answers are passed through. Replace `_render_session` so it passes the view flags.

```python
def _render_session(session: Session) -> str:
    view = session.view()
    return _page(
        session.work.task_id,
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


def _page(
    task_id,
    status,
    questions,
    answers,
    presets,
    locked=False,
    revealed=(),
    scaffold=None,
    dialogue=(),
    send_closed=False,
) -> str:
    parts = ["<h1>" + escape(task_id) + "</h1><p>" + escape(status) + "</p>"]
    action = "/tasks/" + quote(task_id, safe="") + "/answers"
    parts.append("<form method=\"post\" action=\"" + action + "\">")
    for index, question in enumerate(questions):
        item = revealed[index] if revealed else None
        parts.append(_question(index, question, answers[index], locked, item))
    if not locked:
        parts.append("<button type=\"submit\">保存作答</button>")
    parts.append("</form>")
    if not send_closed:
        if presets:
            parts.append("<h2>预设提问</h2><ul>")
            for preset in presets:
                parts.append("<li>" + _ask_form(task_id, preset, HelpSource.PRESET.value) + "</li>")
            parts.append("</ul>")
        parts.append(_ask_form(task_id, "", HelpSource.OWN.value, own=True))
        submit_action = "/tasks/" + quote(task_id, safe="") + "/submit"
        parts.append(
            "<form method=\"post\" action=\"" + submit_action + "\">"
            + "<button type=\"submit\">提交</button></form>"
        )
    if scaffold is not None:
        parts.append("<h2>支架</h2>" + _scaffold_body(task_id, scaffold))
    if dialogue:
        parts.append("<h2>对话</h2>")
        for turn in dialogue:
            parts.append(_turn(task_id, turn))
    return _document("".join(parts))


def _question(index: int, question, answer, locked: bool, revealed=None) -> str:
    if isinstance(question, ChoiceQuestion):
        kind = question.selection.value
        choices = question.choices
        requirements = ""
        input_type = "radio" if question.selection == SelectionMode.SINGLE else "checkbox"
    elif isinstance(question, TrueFalseQuestion):
        kind = "判断"
        choices = ("正确", "错误")
        requirements = ""
        input_type = "radio"
    elif isinstance(question, OpenQuestion):
        kind = "综合"
        choices = ()
        requirements = question.requirements
        input_type = ""
    else:
        raise TypeError("unknown question")
    disabled = " disabled" if locked else ""
    body = (
        "<section><h2>题目" + str(index + 1) + "</h2><p>" + escape(kind)
        + "</p><p>" + escape(question.prompt) + "</p>"
    )
    if requirements:
        body += "<p>" + escape(requirements) + "</p>"
    if choices:
        for choice in choices:
            checked = " checked" if choice in answer.selected else ""
            body += (
                "<label><input type=\"" + input_type + "\" name=\"selected-" + str(index)
                + "\" value=\"" + escape(choice) + "\"" + checked + disabled + ">"
                + escape(choice) + "</label>"
            )
    else:
        body += (
            "<textarea name=\"text-" + str(index) + "\"" + disabled + ">"
            + escape(answer.text) + "</textarea>"
        )
    if revealed is not None:
        shown = revealed.answer if isinstance(revealed.answer, str) else "、".join(revealed.answer)
        body += "<p>参考答案：" + escape(shown) + "</p><p>解析：" + escape(revealed.explanation) + "</p>"
    return body + "</section>"
```

Update `_render_work` to call `_page` with the new defaults by keeping its existing positional call. The new parameters have defaults, so that call still works.

Inside `response_for`, after the ask branch, add:

```python
if method == "POST" and parts[2:] == ["submit"]:
    if not _published(page, task_id):
        return _html_response(_missing(), 404)
    return _html_response(page.submit(task_id, now))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_submit.py tests/test_student_page_open.py tests/test_student_page_ask.py -v`

Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add src/scaffolding/student_page.py tests/test_student_page_submit.py
git commit -m "feat: lock the student page after submit"
```

---

### Task 8: 停留时间

**Files:**
- Modify: `src/scaffolding/student_page.py`
- Test: `tests/test_student_page_dwell.py`

**Interfaces:**
- Consumes: `Session.note_dwell(seconds)`。Task 2 的 `_note_shown(session, task_id, now)` 目前只在第一次写下 `shown_at`。
- Produces: `_note_shown` 在已有锚点且 `now - shown > 0` 时，把这个差加到 `behavior.dwell_seconds` 并改写锚点。差不大于零时不改锚点，也不改停留时间。

- [ ] **Step 1: Write the failing test**

Create `tests/test_student_page_dwell.py`:

```python
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage
from tests.student_page_helpers import true_false_catalog
from tests.test_student_page_failure import AlwaysFail


def _page():
    catalog, task_id = true_false_catalog()
    page = StudentPage(catalog, ScriptedDecisionAgent(presets=("先看题目",)), ScriptedScaffoldAgent())
    return catalog, task_id, page


def test_later_actions_add_positive_elapsed_seconds():
    catalog, task_id, page = _page()
    page.open_task(task_id, 10)
    assert catalog.work(task_id).behavior.dwell_seconds == 0

    page.open_task(task_id, 10)
    page.open_task(task_id, 9)
    assert catalog.work(task_id).behavior.dwell_seconds == 0

    page.open_task(task_id, 12)
    assert catalog.work(task_id).behavior.dwell_seconds == 2

    page.todo()
    assert catalog.work(task_id).behavior.dwell_seconds == 2

    page.edit_answer(task_id, 0, selected=("人员", "硬件"), now=15)
    assert catalog.work(task_id).behavior.dwell_seconds == 5
    assert catalog.work(task_id).answers[0].selected == ()

    page.ask(task_id, "   ", "自己写的", 16)
    assert catalog.work(task_id).behavior.dwell_seconds == 6

    page.submit(task_id, 20)
    assert catalog.work(task_id).behavior.dwell_seconds == 10

    page.asset(task_id, "组成.svg")
    assert catalog.work(task_id).behavior.dwell_seconds == 10


def test_a_missing_session_does_not_record_dwell():
    catalog, task_id = true_false_catalog()
    page = StudentPage(catalog, AlwaysFail(), ScriptedScaffoldAgent())
    page.open_task(task_id, 0)
    page.open_task(task_id, 5)
    page.edit_answer(task_id, 0, selected=("错误",), now=6)

    assert task_id not in page.shown_at
    assert catalog.work(task_id).behavior.dwell_seconds == 0
```

The rejected edit uses a true/false question, so `("人员", "硬件")` is an illegal selection and the previous empty answer remains.

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_dwell.py::test_later_actions_add_positive_elapsed_seconds -v`

Expected: FAIL because `dwell_seconds` stays `0` after the open at time 12

- [ ] **Step 3: Write minimal implementation**

Replace `_note_shown` with:

```python
def _note_shown(self, session, task_id: str, now: float) -> None:
    shown = self.shown_at.get(task_id)
    if shown is None:
        self.shown_at[task_id] = now
        return
    elapsed = now - shown
    if elapsed > 0:
        session.note_dwell(session.work.behavior.dwell_seconds + elapsed)
        self.shown_at[task_id] = now
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_dwell.py -v`

Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add src/scaffolding/student_page.py tests/test_student_page_dwell.py
git commit -m "feat: record dwell time on the student task page"
```

---

### Task 9: 正式运行和规格验收

**Files:**
- Modify: `src/scaffolding/student_page.py`
- Create: `tests/test_student_page_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-21-student-page-design.md`

**Interfaces:**
- Consumes: Task 1 到 Task 8 的 `StudentPage` 和 `response_for`。`ModelDecisionAgent`、`ModelScaffoldAgent`、`deepseek_complete`。
- Produces: `production_page(catalog, *, post, api_key=None) -> StudentPage`。`serve(page, port: int) -> None` 绑定 `127.0.0.1`。测试不调用 `serve`。

- [ ] **Step 1: Write the failing test**

Create `tests/test_student_page_acceptance.py`:

```python
from pathlib import Path

from scaffolding.agents import ScaffoldDraft
from scaffolding.model_decision import ModelDecisionAgent
from scaffolding.model_scaffold import ModelScaffoldAgent
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage, production_page, response_for
from scaffolding.tasks import TaskCatalog
from tests.student_page_helpers import body_text, true_false_catalog


def test_student_page_spec_is_in_the_workspace():
    spec = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "specs" / "2026-10-21-student-page-design.md"
    assert spec.is_file()


def test_a_student_can_open_ask_save_one_asset_and_submit():
    catalog, task_id = true_false_catalog()
    draft = ScaffoldDraft(
        text="先看人员和硬件是否都写到了。",
        html='<asset kind="思维导图" name="组成.svg">人员—硬件</asset>',
    )
    page = StudentPage(
        catalog,
        ScriptedDecisionAgent(presets=("先看题目",), scaffold_type="提示"),
        ScriptedScaffoldAgent(draft),
    )

    todo = response_for(page, "GET", "/", "", 0)
    assert task_id in body_text(todo)
    assert catalog.get(task_id).started is False

    opened = response_for(page, "GET", "/tasks/" + task_id, "", 0)
    assert "判断说法" in body_text(opened)
    assert "先看题目" in body_text(opened)
    assert "题目里有依据" not in body_text(opened)

    asked = response_for(page, "POST", "/tasks/" + task_id + "/ask", "question=先看题目&source=预设提问", 1)
    assert "先看人员和硬件是否都写到了。" in body_text(asked)
    assert "<asset" not in body_text(asked)
    asset = response_for(page, "GET", "/tasks/" + task_id + "/assets/组成.svg", "", 1)
    assert asset.body == "人员—硬件".encode()

    submitted = response_for(page, "POST", "/tasks/" + task_id + "/submit", "", 2)
    assert "已完成" in body_text(submitted)
    assert "参考答案：正确" in body_text(submitted)
    assert "解析：题目里有依据" in body_text(submitted)

    fresh = StudentPage(TaskCatalog(), ScriptedDecisionAgent(), ScriptedScaffoldAgent())
    assert task_id not in fresh.todo()
    assert fresh.sessions == {}


def test_production_page_uses_the_model_agents_without_a_network_call():
    def post(url, headers, payload):
        raise AssertionError("network")

    page = production_page(TaskCatalog(), post=post, api_key="secret")

    assert isinstance(page.decision, ModelDecisionAgent)
    assert isinstance(page.scaffold_agent, ModelScaffoldAgent)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_student_page_acceptance.py -v`

Expected: FAIL because the spec file is missing and `production_page` is undefined. If the spec is already present and another assertion fails, stop and report it. Do not change the earlier production modules.

- [ ] **Step 3: Copy the spec and add the production entry**

Copy `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-21-student-page-design.md` to `docs/superpowers/specs/2026-10-21-student-page-design.md`. Do not edit the spec.

Add these imports:

```python
import time

from scaffolding.model_decision import ModelDecisionAgent
from scaffolding.model_generator import deepseek_complete
from scaffolding.model_scaffold import ModelScaffoldAgent
```

Add these functions:

```python
def production_page(catalog, *, post, api_key=None) -> StudentPage:
    def complete(messages):
        return deepseek_complete(messages, post=post, api_key=api_key)
    return StudentPage(catalog, ModelDecisionAgent(complete), ModelScaffoldAgent(complete))


def serve(page: StudentPage, port: int) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._respond()

        def do_POST(self) -> None:
            self._respond()

        def _respond(self) -> None:
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length).decode("utf-8")
            response = response_for(page, self.command, self.path, raw, time.monotonic())
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            if response.filename:
                encoded = quote(response.filename, safe="")
                self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + encoded)
            self.send_header("Content-Length", str(len(response.body)))
            self.end_headers()
            self.wfile.write(response.body)

        def log_message(self, *args) -> None:
            return

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
```

Do not call `serve` from tests. `quote` is already imported in this module.

- [ ] **Step 4: Run the full suite**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/student_page.py tests/test_student_page_acceptance.py docs/superpowers/specs/2026-10-21-student-page-design.md
git commit -m "test: accept the local student page for a published task"
```
