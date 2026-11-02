# 教师页面 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用一个本地页面服务让教师编写题目、保存整份任务、发布，并在学生开始前修改或删除。

**Architecture:** 新增 `teacher_page.py`。它持有一份任务目录，并按任务标识把草稿留在页面服务里。草稿不是题目记录。增加、删除、移动、改选项和保存都先把本次提交的字段写入草稿，再执行动作；保存成功才整份写入目录。页面由标准库拼出 HTML。测试调用 `TeacherPage` 和 `response_for`，不监听端口，不打开浏览器。`serve` 只给本机浏览器使用，测试不调用它。

**Tech Stack:** Python 3.14，pytest 9，标准库。实现从 `origin/main` 建工作区。规格在本地 `master` 的 `5f52009`，文件是 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-21-teacher-page-design.md`。工作区里若没有这份规格，从该文件原样复制，不要改写。测试命令是 `.\.venv\Scripts\python.exe -m pytest`。PowerShell 下不要使用 `&&` 或 bash heredoc；提交用 `git commit -m "message"`。不要改 git config，不要 push。

## Global Constraints

- 本计划只做教师页面。学生页面、教材和课标的预置内容、教学目标提炼和按目标出题不在这里。
- 学生的作答、停留时间、求助和支架不在这里。发布规则保持不变。本服务不开始任务。
- 这一轮不把教师页面和学生页面放进同一次进程。
- 一名本地教师，没有登录。服务和任务目录只活在这次进程里。进程结束后，任务和草稿都不保留。
- 页面有两处：任务列表，以及一份任务。列表按创建顺序显示全部任务，包括未发布的。每条只显示任务标识，以及未发布、已发布、已开始之一。不用待办或已完成。列表不显示题目、参考答案和解析。任务页显示同一种事实。
- 新建调用现有的 `TaskCatalog.create(())`，得到没有题目、尚未发布的任务，并进入这份任务。
- 草稿含类型、题干和解析。类型是单选、多选、判断、综合之一。单选和多选另含选项和参考答案。判断的参考答案是正确、错误或空。综合另含作答要求，参考答案和解析可以空着。
- 增加、删除、上移、下移、增加选项、删除选项和保存，都先写入本次提交的字段，再执行动作。没有这些提交的键入，服务不记住。
- 保存把草稿变成现有的选择题、判断题或综合题，再整份 `update`。成功后丢掉草稿。尚未发布的任务可以保存成零题。有题不合格时目录不变、草稿留下，页面显示「题目不合格，原任务保持不变」。已发布却保存成零题时显示「已发布的任务至少留一题」。空白不算已填写。
- 没有草稿时显示目录里的题目。有草稿时显示草稿，并提供放弃草稿，不提供发布。没有草稿且目录里至少有一题才提供发布。发布只发布目录里的题目。还有草稿就发布时显示「先保存再发布」。没有草稿也没有题目就发布时显示「没有题目，不能发布」。再次发布仍是已发布，不另报失败。
- 学生开始后不读取、不修改草稿。已有草稿不显示。页面只显示目录内容和删除。修改请求显示「学生已开始，只能删除」。删除去掉任务、学生端数据和草稿，然后回到列表。
- 题干、选项、作答要求、参考答案和解析都按文字写进页面。HTML 用拼接，不用 `str.format`。
- 目录没有公开的全部任务枚举。列表读取 `catalog._tasks`，不要修改 `tasks.py`。
- 不修改 `session.py`、`tasks.py`、`html_assets.py`、`agents.py`、`scripted.py`、`records.py`、`student_page.py`、`model_decision.py`、`model_scaffold.py`、`model_generator.py`、`model_extractor.py`、`objectives.py`、`knowledge.py`、`generation.py`。

## File Map

- Create: `src/scaffolding/teacher_page.py` — 列表、草稿、保存、发布、删除和只读显示。
- Create: `tests/teacher_page_helpers.py` — 表单编码和响应正文。
- Create: `tests/test_teacher_page_list.py`
- Create: `tests/test_teacher_page_open.py`
- Create: `tests/test_teacher_page_draft.py`
- Create: `tests/test_teacher_page_save.py`
- Create: `tests/test_teacher_page_publish.py`
- Create: `tests/test_teacher_page_started.py`
- Create: `tests/test_teacher_page_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-21-teacher-page-design.md`
- Do not modify: 上面 Global Constraints 列出的已有模块。

---

### Task 1: 任务列表和新建

**Files:**
- Create: `src/scaffolding/teacher_page.py`
- Create: `tests/teacher_page_helpers.py`
- Test: `tests/test_teacher_page_list.py`

**Interfaces:**
- Consumes: `TaskCatalog.create(())`、`TaskCatalog.get`。任务存在 `catalog._tasks`，按插入顺序。
- Produces: `PageResponse(status: int, content_type: str, body: bytes)`。`TeacherPage(catalog)`，属性 `catalog`、`drafts`。`TeacherPage.list_tasks() -> str`。`TeacherPage.create_task() -> str`。`response_for(page, method: str, path: str, body: str) -> PageResponse`。

- [ ] **Step 1: Write the failing test**

Create `tests/teacher_page_helpers.py`:

```python
def body_text(response) -> str:
    return response.body.decode()
```

Create `tests/test_teacher_page_list.py`:

```python
from scaffolding.records import ChoiceQuestion, SelectionMode
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage, response_for
from tests.teacher_page_helpers import body_text


def test_an_empty_catalog_lists_no_tasks_and_create_enters_an_unpublished_task():
    page = TeacherPage(TaskCatalog())

    empty = response_for(page, "GET", "/", "", )
    created = response_for(page, "POST", "/tasks", "")
    listed = response_for(page, "GET", "/", "")

    assert "<li>" not in body_text(empty)
    assert "新建" in body_text(empty)
    assert "task-1" in body_text(created)
    assert "未发布" in body_text(created)
    assert "待办" not in body_text(created)
    assert "已完成" not in body_text(created)
    task = page.catalog.get("task-1")
    assert task.questions == ()
    assert task.published is False
    assert 'href="/tasks/task-1"' in body_text(listed)


def test_the_list_is_in_creation_order_and_hides_question_text():
    catalog = TaskCatalog()
    catalog.create((
        ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "硬件"), ("人员",), "选择依据"),
    ))
    page = TeacherPage(catalog)
    page.create_task()

    listed = body_text(response_for(page, "GET", "/", ""))

    assert listed.index("task-1") < listed.index("task-2")
    assert "未发布" in listed
    assert "选出人员" not in listed
    assert "选择依据" not in listed
    assert "参考答案" not in listed
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_page_list.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'scaffolding.teacher_page'`

- [ ] **Step 3: Write minimal implementation**

Create `src/scaffolding/teacher_page.py`:

```python
from dataclasses import dataclass
from html import escape
from urllib.parse import quote, unquote, urlsplit


@dataclass(frozen=True)
class PageResponse:
    status: int
    content_type: str
    body: bytes


class TeacherPage:
    def __init__(self, catalog) -> None:
        self.catalog = catalog
        self.drafts = {}

    def list_tasks(self) -> str:
        items = []
        for task in self.catalog._tasks.values():
            href = "/tasks/" + quote(task.task_id, safe="")
            items.append(
                "<li><a href=\"" + href + "\">" + escape(task.task_id)
                + "</a> " + escape(_fact(task)) + "</li>"
            )
        body = (
            "<h1>任务列表</h1><form method=\"post\" action=\"/tasks\">"
            + "<button type=\"submit\">新建</button></form><ul>"
            + "".join(items) + "</ul>"
        )
        return _document(body)

    def create_task(self) -> str:
        task = self.catalog.create(())
        return _document("<h1>" + escape(task.task_id) + "</h1><p>" + escape(_fact(task)) + "</p>")


def _fact(task) -> str:
    if task.started:
        return "已开始"
    if task.published:
        return "已发布"
    return "未发布"


def _document(body: str) -> str:
    return "<!DOCTYPE html><html lang=\"zh\"><body>" + body + "</body></html>"


def _missing() -> str:
    return _document("<h1>任务不存在</h1>")


def _html(text: str, status: int = 200) -> PageResponse:
    return PageResponse(status, "text/html; charset=utf-8", text.encode())


def response_for(page: TeacherPage, method: str, path: str, body: str) -> PageResponse:
    parts = [unquote(part) for part in urlsplit(path).path.split("/") if part]
    if method == "GET" and parts == []:
        return _html(page.list_tasks())
    if method == "POST" and parts == ["tasks"]:
        return _html(page.create_task())
    return _html(_missing(), 404)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_page_list.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/teacher_page.py tests/teacher_page_helpers.py tests/test_teacher_page_list.py
git commit -m "feat: list tasks on the teacher page"
```

---

### Task 2: 打开任务

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Test: `tests/test_teacher_page_open.py`

**Interfaces:**
- Consumes: Task 1 的 `TeacherPage`、`response_for`、`_fact`、`_document`、`_html`、`_missing`。`ChoiceQuestion`、`TrueFalseQuestion`、`OpenQuestion`。
- Produces: `TeacherPage.open_task(task_id: str) -> str`。`DraftQuestion(kind: str, prompt: str = "", options: tuple[str, ...] = (), requirements: str = "", selected: tuple[str, ...] = (), answer: str = "", explanation: str = "")`。`GET /tasks/<id>` 返回任务页；目录里没有的任务返回 404 和「任务不存在」。

- [ ] **Step 1: Write the failing test**

Create `tests/test_teacher_page_open.py`:

```python
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage, response_for
from tests.teacher_page_helpers import body_text


def _page():
    catalog = TaskCatalog()
    task = catalog.create((
        ChoiceQuestion("选出<人员>", SelectionMode.SINGLE, ("人员", "<硬件>"), ("人员",), "选择依据"),
        ChoiceQuestion("选出组成", SelectionMode.MULTIPLE, ("人员", "硬件"), ("人员", "硬件"), "多选依据"),
        TrueFalseQuestion("判断说法", "正确", "题目里有依据"),
        OpenQuestion("完成作品", "写明人员", "", ""),
    ))
    catalog.publish(task.task_id)
    return TeacherPage(catalog), task.task_id


def test_opening_a_task_shows_its_fact_and_only_each_questions_fields():
    page, task_id = _page()

    html = body_text(response_for(page, "GET", "/tasks/" + task_id, ""))

    assert "已发布" in html
    assert "待办" not in html
    assert "选出&lt;人员&gt;" in html
    assert "<人员>" not in html
    assert "&lt;硬件&gt;" in html
    assert "<硬件>" not in html
    assert 'type="radio"' in html
    assert 'type="checkbox"' in html
    assert "判断说法" in html
    assert "正确" in html
    assert "错误" in html
    assert "完成作品" in html
    assert 'name="requirements-3"' in html
    assert 'name="answer-3" value=""' in html
    assert 'value="publish"' in html
    assert 'value="save"' in html
    assert 'value="delete"' in html
    assert 'value="abandon"' not in html
    assert 'value="add:单选"' in html
    assert 'value="add:多选"' in html
    assert 'value="add:判断"' in html
    assert 'value="add:综合"' in html
    assert page.drafts == {}


def test_a_missing_task_shows_no_questions():
    page = TeacherPage(TaskCatalog())

    opened = response_for(page, "GET", "/tasks/missing", "")
    posted = response_for(page, "POST", "/tasks/missing", "action=save")

    assert opened.status == 404
    assert "任务不存在" in body_text(opened)
    assert "选出" not in body_text(opened)
    assert "参考答案" not in body_text(opened)
    assert posted.status == 404
    assert "任务不存在" in body_text(posted)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_page_open.py -v`

Expected: FAIL because `GET /tasks/<id>` still returns 「任务不存在」

- [ ] **Step 3: Write minimal implementation**

Replace `create_task` and add the renderer. Keep `list_tasks`, `_fact`, `_document`, `_missing`, and `_html`. Replace `response_for` with the complete function below.

```python
from dataclasses import dataclass, replace
from html import escape
from urllib.parse import quote, unquote, urlsplit

from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion


KINDS = ("单选", "多选", "判断", "综合")


@dataclass(frozen=True)
class DraftQuestion:
    kind: str
    prompt: str = ""
    options: tuple[str, ...] = ()
    requirements: str = ""
    selected: tuple[str, ...] = ()
    answer: str = ""
    explanation: str = ""
```

`PageResponse` and `TeacherPage.__init__` stay as in Task 1. Replace `create_task`:

```python
    def create_task(self) -> str:
        task = self.catalog.create(())
        return _render(self, task.task_id)

    def open_task(self, task_id: str) -> str:
        if task_id not in self.catalog._tasks:
            return _missing()
        return _render(self, task_id)
```

Add these functions before `response_for`:

```python
def _render(page: TeacherPage, task_id: str, message: str = "") -> str:
    task = page.catalog.get(task_id)
    parts = ["<h1>" + escape(task_id) + "</h1><p>" + escape(_fact(task)) + "</p>"]
    if message:
        parts.append("<p>" + escape(message) + "</p>")
    if task.started:
        for question in task.questions:
            parts.append(_read_only(question))
        action = "/tasks/" + quote(task_id, safe="")
        parts.append(
            "<form method=\"post\" action=\"" + action + "\">"
            + "<button type=\"submit\" name=\"action\" value=\"delete\">删除</button></form>"
        )
        return _document("".join(parts))
    questions, has_draft = _shown(page, task_id)
    action = "/tasks/" + quote(task_id, safe="")
    parts.append("<form method=\"post\" action=\"" + action + "\">")
    for index, item in enumerate(questions):
        parts.append(_editor(index, item, len(questions)))
    for kind in KINDS:
        parts.append(
            "<button type=\"submit\" name=\"action\" value=\"add:" + kind
            + "\">增加" + kind + "</button>"
        )
    parts.append("<button type=\"submit\" name=\"action\" value=\"save\">保存</button>")
    if has_draft:
        parts.append("<button type=\"submit\" name=\"action\" value=\"abandon\">放弃草稿</button>")
    elif task.questions != ():
        parts.append("<button type=\"submit\" name=\"action\" value=\"publish\">发布</button>")
    parts.append("<button type=\"submit\" name=\"action\" value=\"delete\">删除</button></form>")
    return _document("".join(parts))


def _shown(page: TeacherPage, task_id: str):
    if task_id in page.drafts:
        return page.drafts[task_id], True
    task = page.catalog.get(task_id)
    return tuple(_from_question(question) for question in task.questions), False


def _from_question(question) -> DraftQuestion:
    if isinstance(question, ChoiceQuestion):
        kind = "单选" if question.selection == SelectionMode.SINGLE else "多选"
        return DraftQuestion(kind, question.prompt, question.choices, "", question.answer, "", question.explanation)
    if isinstance(question, TrueFalseQuestion):
        return DraftQuestion("判断", question.prompt, (), "", (question.answer,), "", question.explanation)
    if isinstance(question, OpenQuestion):
        return DraftQuestion("综合", question.prompt, (), question.requirements, (), question.answer, question.explanation)
    raise TypeError("unknown question")


def _editor(index: int, item: DraftQuestion, count: int) -> str:
    name = str(index)
    body = "<section><p>" + escape(item.kind) + "</p>"
    body += "<input type=\"hidden\" name=\"kind-" + name + "\" value=\"" + escape(item.kind) + "\">"
    body += "<input type=\"text\" name=\"prompt-" + name + "\" value=\"" + escape(item.prompt) + "\">"
    if item.kind in ("单选", "多选"):
        input_type = "radio" if item.kind == "单选" else "checkbox"
        for option_index, option in enumerate(item.options):
            checked = " checked" if option in item.selected else ""
            option_name = name + ":" + str(option_index)
            body += (
                "<input type=\"text\" name=\"option-" + name + "-" + str(option_index)
                + "\" value=\"" + escape(option) + "\">"
            )
            body += (
                "<input type=\"" + input_type + "\" name=\"selected-" + name
                + "\" value=\"" + escape(option) + "\"" + checked + ">"
            )
            if option_index > 0:
                body += (
                    "<button type=\"submit\" name=\"action\" value=\"up-option:"
                    + option_name + "\">上移选项</button>"
                )
            if option_index < len(item.options) - 1:
                body += (
                    "<button type=\"submit\" name=\"action\" value=\"down-option:"
                    + option_name + "\">下移选项</button>"
                )
            body += (
                "<button type=\"submit\" name=\"action\" value=\"delete-option:"
                + option_name + "\">删除选项</button>"
            )
        body += "<button type=\"submit\" name=\"action\" value=\"add-option:" + name + "\">增加选项</button>"
    elif item.kind == "判断":
        for choice in ("正确", "错误"):
            checked = " checked" if choice in item.selected else ""
            body += (
                "<input type=\"radio\" name=\"selected-" + name + "\" value=\""
                + choice + "\"" + checked + ">" + choice
            )
    else:
        body += (
            "<input type=\"text\" name=\"requirements-" + name + "\" value=\""
            + escape(item.requirements) + "\">"
        )
        body += "<input type=\"text\" name=\"answer-" + name + "\" value=\"" + escape(item.answer) + "\">"
    body += "<input type=\"text\" name=\"explanation-" + name + "\" value=\"" + escape(item.explanation) + "\">"
    body += "<button type=\"submit\" name=\"action\" value=\"delete:" + name + "\">删除题目</button>"
    if index > 0:
        body += "<button type=\"submit\" name=\"action\" value=\"up:" + name + "\">上移</button>"
    if index < count - 1:
        body += "<button type=\"submit\" name=\"action\" value=\"down:" + name + "\">下移</button>"
    return body + "</section>"


def _read_only(question) -> str:
    if isinstance(question, ChoiceQuestion):
        kind = question.selection.value
        prompt = question.prompt
        options = question.choices
        requirements = ""
        answer = "、".join(question.answer)
        explanation = question.explanation
    elif isinstance(question, TrueFalseQuestion):
        kind = "判断"
        prompt = question.prompt
        options = ("正确", "错误")
        requirements = ""
        answer = question.answer
        explanation = question.explanation
    elif isinstance(question, OpenQuestion):
        kind = "综合"
        prompt = question.prompt
        options = ()
        requirements = question.requirements
        answer = question.answer
        explanation = question.explanation
    else:
        raise TypeError("unknown question")
    body = "<section><p>" + escape(kind) + "</p><p>" + escape(prompt) + "</p>"
    if kind == "综合":
        body += "<p>" + escape(requirements) + "</p>"
    for option in options:
        body += "<p>" + escape(option) + "</p>"
    return body + "<p>参考答案：" + escape(answer) + "</p><p>解析：" + escape(explanation) + "</p></section>"
```

`replace` is imported for later tasks. Replace `response_for`:

```python
def response_for(page: TeacherPage, method: str, path: str, body: str) -> PageResponse:
    parts = [unquote(part) for part in urlsplit(path).path.split("/") if part]
    if method == "GET" and parts == []:
        return _html(page.list_tasks())
    if method == "POST" and parts == ["tasks"]:
        return _html(page.create_task())
    if len(parts) == 2 and parts[0] == "tasks":
        task_id = parts[1]
        if task_id not in page.catalog._tasks:
            return _html(_missing(), 404)
        if method == "GET":
            return _html(page.open_task(task_id))
    return _html(_missing(), 404)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_page_list.py tests/test_teacher_page_open.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/teacher_page.py tests/test_teacher_page_open.py
git commit -m "feat: open a task on the teacher page"
```

---

### Task 3: 草稿里的题目和选项

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Modify: `tests/teacher_page_helpers.py`
- Test: `tests/test_teacher_page_draft.py`

**Interfaces:**
- Consumes: `DraftQuestion`、`KINDS`、`_render`、`_editor`。
- Produces: `TeacherPage.apply(task_id: str, fields: dict, action: str) -> str`。`POST /tasks/<id>` 读取 `action` 和题目字段。动作值是 `add:单选`、`add:多选`、`add:判断`、`add:综合`、`delete:<index>`、`up:<index>`、`down:<index>`、`add-option:<index>`、`delete-option:<index>:<option>`、`up-option:<index>:<option>`、`down-option:<index>:<option>`。

- [ ] **Step 1: Write the failing test**

Add to `tests/teacher_page_helpers.py`:

```python
from urllib.parse import urlencode


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

Create `tests/test_teacher_page_draft.py`:

```python
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage, response_for
from tests.teacher_page_helpers import body_text, form


def _post(page, task_id, **fields):
    return response_for(page, "POST", "/tasks/" + task_id, form(**fields))


def test_adding_a_question_keeps_a_draft_and_shows_only_that_kinds_fields():
    page = TeacherPage(TaskCatalog())
    page.create_task()

    single = _post(page, "task-1", action="add:单选")
    assert 'value="单选"' in body_text(single)
    assert 'value="add-option:0"' in body_text(single)
    assert 'name="requirements-0"' not in body_text(single)
    assert 'value="up:0"' not in body_text(single)
    assert 'value="down:0"' not in body_text(single)
    assert page.catalog.get("task-1").questions == ()

    multiple = _post(page, "task-1", **{"kind-0": "单选", "prompt-0": "第一", "action": "add:多选"})
    assert 'type="checkbox"' in body_text(multiple)
    assert 'value="第一"' in body_text(multiple)

    judgement = _post(page, "task-1", **{
        "kind-0": "单选", "prompt-0": "第一", "kind-1": "多选", "action": "add:判断",
    })
    assert "正确" in body_text(judgement)
    assert "错误" in body_text(judgement)
    assert 'value="add-option:2"' not in body_text(judgement)

    opened = _post(page, "task-1", **{
        "kind-0": "单选", "prompt-0": "第一",
        "kind-1": "多选",
        "kind-2": "判断",
        "action": "add:综合",
    })
    html = body_text(opened)
    assert 'name="requirements-3"' in html
    assert 'name="answer-3"' in html
    assert 'value="add-option:3"' not in html
    again = body_text(response_for(page, "GET", "/tasks/task-1", ""))
    assert 'value="第一"' in again
    assert page.catalog.get("task-1").questions == ()


def test_an_unknown_kind_does_not_add_a_question():
    page = TeacherPage(TaskCatalog())
    page.create_task()

    html = body_text(_post(page, "task-1", action="add:课外"))

    assert "课外" not in html
    assert page.catalog.get("task-1").questions == ()


def test_options_and_questions_move_only_inside_their_ends():
    page = TeacherPage(TaskCatalog())
    page.create_task()
    _post(page, "task-1", action="add:单选")
    added = _post(page, "task-1", **{
        "kind-0": "单选",
        "prompt-0": "选出<人员>",
        "action": "add-option:0",
    })
    assert "选出&lt;人员&gt;" in body_text(added)
    assert "<人员>" not in body_text(added)
    assert 'name="option-0-0"' in body_text(added)
    _post(page, "task-1", **{
        "kind-0": "单选",
        "prompt-0": "选出<人员>",
        "option-0-0": "人员",
        "action": "add-option:0",
    })
    moved = _post(page, "task-1", **{
        "kind-0": "单选",
        "prompt-0": "选出<人员>",
        "option-0-0": "人员",
        "option-0-1": "硬件",
        "action": "up-option:0:1",
    })
    text = body_text(moved)
    assert text.index('value="硬件"') < text.index('value="人员"')
    assert 'value="up-option:0:0"' not in text
    assert 'value="down-option:0:1"' not in text
    stayed = _post(page, "task-1", **{
        "kind-0": "单选",
        "prompt-0": "选出<人员>",
        "option-0-0": "硬件",
        "option-0-1": "人员",
        "action": "up-option:0:0",
    })
    stayed_text = body_text(stayed)
    assert stayed_text.index('value="硬件"') < stayed_text.index('value="人员"')

    _post(page, "task-1", **{
        "kind-0": "单选", "prompt-0": "第一", "action": "add:判断",
    })
    swapped = _post(page, "task-1", **{
        "kind-0": "单选", "prompt-0": "第一",
        "kind-1": "判断", "prompt-1": "第二",
        "action": "down:0",
    })
    order = body_text(swapped)
    assert order.index('value="第二"') < order.index('value="第一"')
    untouched = _post(page, "task-1", **{
        "kind-0": "判断", "prompt-0": "第二",
        "kind-1": "单选", "prompt-1": "第一",
        "action": "up:0",
    })
    assert body_text(untouched).index('value="第二"') < body_text(untouched).index('value="第一"')
    assert page.catalog.get("task-1").questions == ()


def test_option_actions_on_a_true_false_question_do_not_add_options():
    page = TeacherPage(TaskCatalog())
    page.create_task()
    _post(page, "task-1", action="add:判断")

    html = body_text(_post(page, "task-1", **{"kind-0": "判断", "prompt-0": "判断说法", "action": "add-option:0"}))

    assert 'name="option-0-0"' not in html
    assert page.catalog.get("task-1").questions == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_page_draft.py -v`

Expected: FAIL because `POST /tasks/task-1` still returns 「任务不存在」 or does not show the new question

- [ ] **Step 3: Write minimal implementation**

Add `TeacherPage.apply` and keep the Task 2 renderer. The POST route calls `apply`.

```python
    def apply(self, task_id: str, fields: dict, action: str) -> str:
        if task_id not in self.catalog._tasks:
            return _missing()
        self.drafts[task_id] = _apply_action(_draft_from_fields(fields), action)
        return _render(self, task_id)
```

Add the parsers before `response_for`:

```python
def _draft_from_fields(fields: dict) -> tuple:
    indexes = []
    for key in fields:
        if key.startswith("kind-") and key[5:].isdigit():
            indexes.append(int(key[5:]))
    items = []
    for index in sorted(set(indexes)):
        kind = fields["kind-" + str(index)][-1]
        if kind not in KINDS:
            continue
        prefix = "option-" + str(index) + "-"
        option_ids = []
        for key in fields:
            if key.startswith(prefix) and key[len(prefix):].isdigit():
                option_ids.append(int(key[len(prefix):]))
        options = tuple(
            fields["option-" + str(index) + "-" + str(option_id)][-1]
            for option_id in sorted(set(option_ids))
        )
        items.append(DraftQuestion(
            kind,
            fields.get("prompt-" + str(index), [""])[-1],
            options,
            fields.get("requirements-" + str(index), [""])[-1],
            tuple(fields.get("selected-" + str(index), ())),
            fields.get("answer-" + str(index), [""])[-1],
            fields.get("explanation-" + str(index), [""])[-1],
        ))
    return tuple(items)


def _apply_action(draft: tuple, action: str) -> tuple:
    parts = action.split(":")
    head = parts[0]
    if head == "add" and len(parts) == 2 and parts[1] in KINDS:
        return draft + (DraftQuestion(parts[1]),)
    if head == "delete" and len(parts) == 2 and parts[1].isdigit():
        index = int(parts[1])
        if 0 <= index < len(draft):
            return draft[:index] + draft[index + 1:]
        return draft
    if head == "up" and len(parts) == 2 and parts[1].isdigit():
        index = int(parts[1])
        if 1 <= index < len(draft):
            items = list(draft)
            items[index - 1], items[index] = items[index], items[index - 1]
            return tuple(items)
        return draft
    if head == "down" and len(parts) == 2 and parts[1].isdigit():
        index = int(parts[1])
        if 0 <= index < len(draft) - 1:
            items = list(draft)
            items[index + 1], items[index] = items[index], items[index + 1]
            return tuple(items)
        return draft
    if head == "add-option" and len(parts) == 2 and parts[1].isdigit():
        return _map_choice(draft, int(parts[1]), lambda question: replace(question, options=question.options + ("",)))
    if head == "delete-option" and len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
        option_index = int(parts[2])

        def remove(question):
            if not 0 <= option_index < len(question.options):
                return question
            return replace(
                question,
                options=question.options[:option_index] + question.options[option_index + 1:],
            )

        return _map_choice(draft, int(parts[1]), remove)
    if head == "up-option" and len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
        option_index = int(parts[2])

        def move_up(question):
            if not 1 <= option_index < len(question.options):
                return question
            items = list(question.options)
            items[option_index - 1], items[option_index] = items[option_index], items[option_index - 1]
            return replace(question, options=tuple(items))

        return _map_choice(draft, int(parts[1]), move_up)
    if head == "down-option" and len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
        option_index = int(parts[2])

        def move_down(question):
            if not 0 <= option_index < len(question.options) - 1:
                return question
            items = list(question.options)
            items[option_index + 1], items[option_index] = items[option_index], items[option_index + 1]
            return replace(question, options=tuple(items))

        return _map_choice(draft, int(parts[1]), move_down)
    return draft


def _map_choice(draft: tuple, index: int, change) -> tuple:
    if not 0 <= index < len(draft) or draft[index].kind not in ("单选", "多选"):
        return draft
    items = list(draft)
    items[index] = change(draft[index])
    return tuple(items)
```

In `response_for`, add `parse_qs` to the urllib import: `from urllib.parse import parse_qs, quote, unquote, urlsplit`. Inside the `len(parts) == 2` branch, after the missing-task check, add:

```python
        if method == "POST":
            fields = parse_qs(body, keep_blank_values=True)
            action = fields.get("action", [""])[-1]
            return _html(page.apply(task_id, fields, action))
```

`parse_qs` must run for that POST. A GET must not require fields. The existing GET branch stays.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_page_list.py tests/test_teacher_page_open.py tests/test_teacher_page_draft.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/teacher_page.py tests/teacher_page_helpers.py tests/test_teacher_page_draft.py
git commit -m "feat: keep a question draft on the teacher page"
```

---

### Task 4: 保存整份题目

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Test: `tests/test_teacher_page_save.py`

**Interfaces:**
- Consumes: `TeacherPage.apply`。动作 `save` 在写入草稿后调用现有的 `ChoiceQuestion`、`TrueFalseQuestion`、`OpenQuestion` 和 `TaskCatalog.update`。
- Produces: 保存成功后 `drafts` 不再含该任务。失败时草稿还在，目录不变。

- [ ] **Step 1: Write the failing test**

Create `tests/test_teacher_page_save.py`:

```python
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage, response_for
from tests.teacher_page_helpers import body_text, form


def _post(page, task_id, **fields):
    return response_for(page, "POST", "/tasks/" + task_id, form(**fields))


def _valid_fields():
    return {
        "kind-0": "单选",
        "prompt-0": "选出<人员>",
        "option-0-0": "人员",
        "option-0-1": "<硬件>",
        "selected-0": "人员",
        "explanation-0": "选择依据",
        "kind-1": "多选",
        "prompt-1": "选出组成",
        "option-1-0": "人员",
        "option-1-1": "硬件",
        "selected-1": ["人员", "硬件"],
        "explanation-1": "多选依据",
        "kind-2": "判断",
        "prompt-2": "判断说法",
        "selected-2": "正确",
        "explanation-2": "题目里有依据",
        "kind-3": "综合",
        "prompt-3": "完成作品",
        "requirements-3": "写明人员",
        "answer-3": "",
        "explanation-3": "",
        "action": "save",
    }


def test_saving_a_valid_draft_updates_the_catalog_and_clears_the_draft():
    page = TeacherPage(TaskCatalog())
    page.create_task()

    html = body_text(_post(page, "task-1", **_valid_fields()))
    questions = page.catalog.get("task-1").questions

    assert "task-1" not in page.drafts
    assert 'value="publish"' in html
    assert 'value="abandon"' not in html
    assert "选出&lt;人员&gt;" in html
    assert "<人员>" not in html
    assert isinstance(questions[0], ChoiceQuestion)
    assert questions[0].selection == SelectionMode.SINGLE
    assert questions[0].choices == ("人员", "<硬件>")
    assert isinstance(questions[1], ChoiceQuestion)
    assert questions[1].selection == SelectionMode.MULTIPLE
    assert questions[1].answer == ("人员", "硬件")
    assert isinstance(questions[2], TrueFalseQuestion)
    assert questions[2].answer == "正确"
    assert isinstance(questions[3], OpenQuestion)
    assert questions[3].answer == ""
    assert questions[3].explanation == ""


def test_an_invalid_question_keeps_the_catalog_and_the_draft():
    page = TeacherPage(TaskCatalog())
    page.create_task()

    html = body_text(_post(page, "task-1", **{
        "kind-0": "单选",
        "prompt-0": "   ",
        "option-0-0": "人员",
        "option-0-1": "硬件",
        "selected-0": "人员",
        "explanation-0": "选择依据",
        "action": "save",
    }))

    assert page.catalog.get("task-1").questions == ()
    assert "task-1" in page.drafts
    assert "题目不合格，原任务保持不变" in html
    assert 'value="publish"' not in html


def test_a_removed_option_that_is_still_selected_is_rejected():
    page = TeacherPage(TaskCatalog())
    page.create_task()

    html = body_text(_post(page, "task-1", **{
        "kind-0": "单选",
        "prompt-0": "选出人员",
        "option-0-0": "硬件",
        "selected-0": "人员",
        "explanation-0": "选择依据",
        "action": "save",
    }))

    assert page.catalog.get("task-1").questions == ()
    assert "题目不合格，原任务保持不变" in html


def test_an_unpublished_task_can_be_saved_with_no_questions():
    page = TeacherPage(TaskCatalog())
    page.create_task()
    _post(page, "task-1", action="add:单选")

    html = body_text(_post(page, "task-1", action="save"))

    assert page.catalog.get("task-1").questions == ()
    assert "task-1" not in page.drafts
    assert "题目不合格" not in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_page_save.py -v`

Expected: FAIL because `action=save` does not update the catalog

- [ ] **Step 3: Write minimal implementation**

In `TeacherPage.apply`, after `self.drafts[task_id] = _apply_action(...)`, save before the ordinary render:

```python
        self.drafts[task_id] = _apply_action(_draft_from_fields(fields), action)
        if action == "save":
            return _save(self, task_id)
        return _render(self, task_id)
```

Add `_save` and `_to_question`:

```python
def _save(page: TeacherPage, task_id: str) -> str:
    draft = page.drafts[task_id]
    task = page.catalog.get(task_id)
    if task.published and draft == ():
        return _render(page, task_id, "已发布的任务至少留一题")
    try:
        questions = tuple(_to_question(item) for item in draft)
    except ValueError:
        return _render(page, task_id, "题目不合格，原任务保持不变")
    page.catalog.update(task_id, questions)
    del page.drafts[task_id]
    return _render(page, task_id)


def _to_question(item: DraftQuestion):
    if item.kind == "单选":
        return ChoiceQuestion(item.prompt, SelectionMode.SINGLE, item.options, item.selected, item.explanation)
    if item.kind == "多选":
        return ChoiceQuestion(item.prompt, SelectionMode.MULTIPLE, item.options, item.selected, item.explanation)
    if item.kind == "判断":
        if len(item.selected) != 1:
            raise ValueError("true/false answer")
        return TrueFalseQuestion(item.prompt, item.selected[0], item.explanation)
    if item.kind == "综合":
        return OpenQuestion(item.prompt, item.requirements, item.answer, item.explanation)
    raise ValueError("unknown kind")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_page_save.py tests/test_teacher_page_draft.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/teacher_page.py tests/test_teacher_page_save.py
git commit -m "feat: save a teacher draft into the task catalog"
```

---

### Task 5: 发布和放弃草稿

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Test: `tests/test_teacher_page_publish.py`

**Interfaces:**
- Consumes: Task 4 的 `TeacherPage.apply` 和 `_save`。`TaskCatalog.publish`。
- Produces: `apply` 在写入草稿之前处理 `abandon` 和 `publish`。发布成功后任务页和列表都显示已发布。

- [ ] **Step 1: Write the failing test**

Create `tests/test_teacher_page_publish.py`:

```python
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage, response_for
from tests.teacher_page_helpers import body_text, form


def _post(page, task_id, **fields):
    return response_for(page, "POST", "/tasks/" + task_id, form(**fields))


def test_an_empty_task_cannot_be_published_and_a_draft_must_be_saved_first():
    page = TeacherPage(TaskCatalog())
    page.create_task()

    empty = body_text(_post(page, "task-1", action="publish"))

    assert "没有题目，不能发布" in empty
    assert page.catalog.get("task-1").published is False
    _post(page, "task-1", action="add:判断")
    _post(page, "task-1", **{"kind-0": "判断", "prompt-0": "判断说法", "action": "add-option:0"})
    drafted = body_text(_post(page, "task-1", action="publish"))
    assert "先保存再发布" in drafted
    assert page.catalog.get("task-1").published is False
    assert page.drafts["task-1"][0].prompt == "判断说法"
    assert page.drafts["task-1"][0].options == ()


def test_publish_then_edit_then_publish_again():
    page = TeacherPage(TaskCatalog())
    page.create_task()
    _post(page, "task-1", **{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "selected-0": "正确",
        "explanation-0": "题目里有依据",
        "action": "save",
    })

    published = body_text(_post(page, "task-1", action="publish"))
    listed = body_text(response_for(page, "GET", "/", ""))

    assert "已发布" in published
    assert "没有题目，不能发布" not in published
    assert "已发布" in listed
    assert page.catalog.get("task-1").published is True
    edited = body_text(_post(page, "task-1", **{
        "kind-0": "判断",
        "prompt-0": "改后的说法",
        "selected-0": "错误",
        "explanation-0": "题目里有依据",
        "action": "save",
    }))
    assert "改后的说法" in edited
    assert page.catalog.get("task-1").published is True
    assert page.catalog.get("task-1").questions[0].prompt == "改后的说法"
    assert page.catalog.get("task-1").questions[0].answer == "错误"
    assert "task-1" not in page.drafts
    again = body_text(_post(page, "task-1", action="publish"))
    assert "已发布" in again
    assert "没有题目，不能发布" not in again
    assert "先保存再发布" not in again


def test_abandoning_a_draft_returns_the_saved_questions():
    page = TeacherPage(TaskCatalog())
    page.create_task()
    _post(page, "task-1", **{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "selected-0": "正确",
        "explanation-0": "题目里有依据",
        "action": "save",
    })
    _post(page, "task-1", **{"kind-0": "判断", "prompt-0": "判断说法", "action": "add:单选"})

    html = body_text(_post(page, "task-1", action="abandon"))

    assert "task-1" not in page.drafts
    assert 'value="判断说法"' in html
    assert 'value="publish"' in html
    assert 'value="abandon"' not in html
    assert page.catalog.get("task-1").questions[0].prompt == "判断说法"


def test_clearing_a_published_task_is_rejected_and_publish_still_sees_the_draft():
    page = TeacherPage(TaskCatalog())
    page.create_task()
    _post(page, "task-1", **{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "selected-0": "正确",
        "explanation-0": "题目里有依据",
        "action": "save",
    })
    _post(page, "task-1", action="publish")
    _post(page, "task-1", **{"kind-0": "判断", "prompt-0": "判断说法", "action": "delete:0"})

    saved = body_text(_post(page, "task-1", action="save"))
    published = body_text(_post(page, "task-1", action="publish"))

    assert page.catalog.get("task-1").questions[0].prompt == "判断说法"
    assert "已发布的任务至少留一题" in saved
    assert "task-1" in page.drafts
    assert "先保存再发布" in published
    assert page.catalog.get("task-1").published is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_page_publish.py -v`

Expected: FAIL because `action=publish` does not show 「没有题目，不能发布」 and does not set `published`

- [ ] **Step 3: Write minimal implementation**

Replace `TeacherPage.apply` with this complete method. Keep `_save` from Task 4, including the published-zero message.

```python
    def apply(self, task_id: str, fields: dict, action: str) -> str:
        if task_id not in self.catalog._tasks:
            return _missing()
        task = self.catalog.get(task_id)
        if action == "abandon":
            self.drafts.pop(task_id, None)
            return _render(self, task_id)
        if action == "publish":
            if task_id in self.drafts:
                return _render(self, task_id, "先保存再发布")
            if task.questions == ():
                return _render(self, task_id, "没有题目，不能发布")
            self.catalog.publish(task_id)
            return _render(self, task_id)
        self.drafts[task_id] = _apply_action(_draft_from_fields(fields), action)
        if action == "save":
            return _save(self, task_id)
        return _render(self, task_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_page_publish.py tests/test_teacher_page_save.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add tests/test_teacher_page_publish.py src/scaffolding/teacher_page.py
git commit -m "feat: publish a saved task from the teacher page"
```

---

### Task 6: 学生开始后只能删除

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Test: `tests/test_teacher_page_started.py`

**Interfaces:**
- Consumes: Task 5 的 `TeacherPage.apply`。`TaskCatalog.publish`、`TaskCatalog.start`。Task 2 的 `_render` 在 `task.started` 时只画只读题目和删除按钮。
- Produces: `apply` 先处理 `delete`，再拒绝已开始任务上的修改。删除成功后响应是任务列表。

- [ ] **Step 1: Write the failing test**

Create `tests/test_teacher_page_started.py`:

```python
import pytest

from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import DraftQuestion, TeacherPage, response_for
from tests.teacher_page_helpers import body_text, form


def _started_page():
    page = TeacherPage(TaskCatalog())
    page.create_task()
    response_for(page, "POST", "/tasks/task-1", form(**{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "selected-0": "正确",
        "explanation-0": "题目里有依据",
        "action": "save",
    }))
    page.catalog.publish("task-1")
    page.catalog.start("task-1")
    page.drafts["task-1"] = (DraftQuestion("单选", prompt="隐藏草稿"),)
    return page


def test_a_started_task_is_read_only_and_a_mutation_does_not_touch_the_draft():
    page = _started_page()

    opened = body_text(response_for(page, "GET", "/tasks/task-1", ""))
    listed = body_text(response_for(page, "GET", "/", ""))
    posted = body_text(response_for(page, "POST", "/tasks/task-1", form(**{
        "kind-0": "判断",
        "prompt-0": "不该写入",
        "action": "save",
    })))

    assert "已开始" in opened
    assert "已开始" in listed
    assert "<input" not in opened
    assert 'value="save"' not in opened
    assert 'value="publish"' not in opened
    assert 'value="delete"' in opened
    assert "判断说法" in opened
    assert "参考答案：正确" in opened
    assert "解析：题目里有依据" in opened
    assert "隐藏草稿" not in opened
    assert "不该写入" not in posted
    assert "学生已开始，只能删除" in posted
    assert page.drafts["task-1"] == (DraftQuestion("单选", prompt="隐藏草稿"),)
    assert page.catalog.get("task-1").questions[0].prompt == "判断说法"


def test_delete_removes_the_task_its_work_and_its_draft():
    page = _started_page()

    deleted = body_text(response_for(page, "POST", "/tasks/task-1", form(action="delete")))
    missing = response_for(page, "GET", "/tasks/task-1", "")

    assert "task-1" not in deleted
    assert "新建" in deleted
    assert "task-1" not in page.drafts
    with pytest.raises(KeyError):
        page.catalog.get("task-1")
    with pytest.raises(KeyError):
        page.catalog.work("task-1")
    assert missing.status == 404
    assert "任务不存在" in body_text(missing)
    posted = response_for(page, "POST", "/tasks/task-1", form(action="delete"))
    assert posted.status == 404
    assert "任务不存在" in body_text(posted)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_page_started.py -v`

Expected: FAIL because the save writes 「不该写入」 and does not show 「学生已开始，只能删除」

- [ ] **Step 3: Write minimal implementation**

Replace `TeacherPage.apply` with this complete method. The started branch in `_render` from Task 2 stays: it calls `_read_only` and its only button is `value="delete"`.

```python
    def apply(self, task_id: str, fields: dict, action: str) -> str:
        if task_id not in self.catalog._tasks:
            return _missing()
        task = self.catalog.get(task_id)
        if action == "delete":
            self.drafts.pop(task_id, None)
            self.catalog.delete(task_id)
            return self.list_tasks()
        if task.started:
            return _render(self, task_id, "学生已开始，只能删除")
        if action == "abandon":
            self.drafts.pop(task_id, None)
            return _render(self, task_id)
        if action == "publish":
            if task_id in self.drafts:
                return _render(self, task_id, "先保存再发布")
            if task.questions == ():
                return _render(self, task_id, "没有题目，不能发布")
            self.catalog.publish(task_id)
            return _render(self, task_id)
        self.drafts[task_id] = _apply_action(_draft_from_fields(fields), action)
        if action == "save":
            return _save(self, task_id)
        return _render(self, task_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_page_started.py tests/test_teacher_page_publish.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/teacher_page.py tests/test_teacher_page_started.py
git commit -m "feat: lock teacher edits after the student starts"
```

---

### Task 7: 验收和本机监听

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Create: `tests/test_teacher_page_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-21-teacher-page-design.md`

**Interfaces:**
- Consumes: `TeacherPage`、`response_for`、`serve`。
- Produces: `serve(page: TeacherPage, port: int) -> None`。测试不调用它。

- [ ] **Step 1: Write the failing test**

If the spec file is missing in this worktree, copy `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-21-teacher-page-design.md` unchanged. Do not edit it.

Create `tests/test_teacher_page_acceptance.py`:

```python
from pathlib import Path

from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage, serve


def test_a_new_service_does_not_see_another_catalog_or_draft():
    first = TeacherPage(TaskCatalog())
    first.create_task()
    first.drafts["task-1"] = ()
    second = TeacherPage(TaskCatalog())

    assert "task-1" not in second.list_tasks()
    assert second.drafts == {}
    assert first.catalog is not second.catalog


def test_the_spec_is_present_and_the_listener_is_not_started():
    assert Path("docs/superpowers/specs/2026-10-21-teacher-page-design.md").is_file()
    assert callable(serve)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_page_acceptance.py -v`

Expected: FAIL with `ImportError` for `serve`, or because the spec file is missing

- [ ] **Step 3: Write minimal implementation**

Add `serve` at the end of `teacher_page.py`. Do not call it from tests.

```python
def serve(page: TeacherPage, port: int) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._respond()

        def do_POST(self) -> None:
            self._respond()

        def _respond(self) -> None:
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length).decode("utf-8")
            response = response_for(page, self.command, self.path, raw)
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            self.send_header("Content-Length", str(len(response.body)))
            self.end_headers()
            self.wfile.write(response.body)

        def log_message(self, *args) -> None:
            return

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS, including the existing suite and the teacher-page tests. The count is the previous suite plus the new tests. No test calls `serve`.

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/teacher_page.py tests/test_teacher_page_acceptance.py docs/superpowers/specs/2026-10-21-teacher-page-design.md
git commit -m "test: accept the local teacher page for writing a task"
```

The spec file in this commit must be the unchanged copy from `5f52009`.
