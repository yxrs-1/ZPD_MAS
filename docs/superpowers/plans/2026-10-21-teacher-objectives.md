# 教师目标 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让教师页按课时或学段查看知识库检索，并提炼、修改和删除四维教学目标。

**Architecture:** 目标页并进现有 `TeacherPage`。路径是 `/objectives`，前缀仍只加在最前面一次。课堂服务持有同一份知识库、目标库和任务生成记录，并把它们交给教师页。目标页只读取来源，不调用生成。测试调用 `response_for`，不监听端口。

**Tech Stack:** Python 3.14，pytest 9，标准库。实现从 `origin/main` 建工作区。规格在本地 `master` 的 `fef53b0`，文件是 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-21-teacher-objectives-design.md`。工作区里若没有这份规格，在 Task 7 从该文件原样复制，不要改写。测试命令是 `.\.venv\Scripts\python.exe -m pytest`。PowerShell 下不要使用 `&&` 或 bash heredoc；提交用 `git commit -m "message"`。不要改 git config，不要 push。

## Global Constraints

- 目标页并进现有教师页。课堂服务持有一份知识库、一份目标库，以及挂在这份任务目录上的任务生成记录。学生页不读取它们，也不增加路径。
- 不传入知识库、目标库和任务生成记录时，使用空知识库、空目标库和空的来源记录。编写、发布和任务页的原有规则仍然成立。列表上仍然有「目标」。
- 再新建一个课堂服务时，资料、目标和来源互不共享。进程结束后也不保留。
- 目标页不另记草稿。每次提交带上这次的选择和字段。
- 查看只调用现有检索，不调用提炼方。提炼只调用现有的课时提炼或学段提炼，提炼方最多调用一次。目标页不调用任务生成。
- 不修改 `tasks.py`、`session.py`、`html_assets.py`、`agents.py`、`scripted.py`、`records.py`、`model_decision.py`、`model_scaffold.py`、`model_generator.py`、`model_extractor.py`、`objectives.py`、`knowledge.py`、`generation.py`、`student_page.py`。
- 正式运行时，目标库使用现有的 `ModelObjectiveExtractor`。任务生成记录用现有的 `ModelQuestionGenerator` 准备好。目标页不调用生成。测试注入 `ScriptedExtractor`。资料由测试写入。任务链接由测试调用现有 `TaskGeneration` 写下来源。
- 教师列表在任务行之外有「目标」，指向 `/objectives`。课堂里带 `/teacher`。`/` 不增加「目标」。末尾多一个斜杠不影响。查询字符串不参与判断。
- GET 打开目标页时只显示查询，不检索，不提炼。
- 查询先选「课时」或「学段」。课时填写版本、册次、课时，不读取学段栏。学段只填写学段，不读取版本、册次、课时。
- 课时检索显示课时原文、教材来源、课标全文和课标来源。教材来源是版本、册次、课时、学段、页码。课标来源是名称、学段、条款号，并标明现行。学段检索只显示课标全文和课标来源。
- 原文、来源、表述和标识都按文字写进页面。HTML 用拼接，不用 `str.format`。
- 已有目标按保存顺序显示标识、维度、表述和来源。还没有记录时提供「提炼」。有记录时不提供「提炼」。
- 修改只改表述。删除最后一条后可以重新提炼。修改和删除只接受当前查询里的目标，不调用提炼方，不改知识库。
- 任务链接按 `catalog._tasks` 的插入顺序。课时查询只对 `LessonOrigin` 的版本、册次、课时。学段查询只对 `StageOrigin`。手写任务不出现。已发布或已开始且仍在目录里的对得上的任务仍然列出。页面不显示题目或学生作答。没有对得上的任务时不列出链接。
- 失败句子用这些原文：「先填完整再查询」「没有检索到资料」「已有目标，不能再次提炼」「没有留下可保存的目标」「提炼失败，没有保存目标」「目标不存在」「表述不能为空」。空白不算已填写。这些失败的状态是 200。已有记录时的提炼拒绝不再显示「没有检索到资料」。
- 不认识的动作只显示查询，不另报失败。学生地址 `/student/objectives` 仍是「任务不存在」，状态 404。
- 测试不调用 `serve`，不打开浏览器，不访问网络。

## File Map

- Modify: `src/scaffolding/teacher_page.py` — 目标页。
- Modify: `src/scaffolding/classroom.py` — 持有知识库、目标库和任务生成记录。
- Create: `tests/teacher_objectives_helpers.py`
- Create: `tests/test_teacher_objectives_open.py`
- Create: `tests/test_teacher_objectives_view.py`
- Create: `tests/test_teacher_objectives_stage.py`
- Create: `tests/test_teacher_objectives_extract.py`
- Create: `tests/test_teacher_objectives_edit.py`
- Create: `tests/test_teacher_objectives_links.py`
- Create: `tests/test_teacher_objectives_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-21-teacher-objectives-design.md`

---

### Task 1: 打开目标页

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Create: `tests/teacher_objectives_helpers.py`
- Test: `tests/test_teacher_objectives_open.py`

**Interfaces:**
- Consumes: `TeacherPage(catalog)` 和 `TeacherPage(catalog, prefix="")`。`response_for(page, method, path, body)`。
- Produces: `TeacherPage(catalog, prefix="", *, knowledge=None, objectives=None, generation=None)`。`page.knowledge`、`page.objectives`、`page.generation`。GET `/objectives` 返回查询表单。列表链接是 `prefix + "/objectives"`。

- [ ] **Step 1: Write the failing test**

Create `tests/teacher_objectives_helpers.py`:

```python
from urllib.parse import urlencode

from scaffolding.knowledge import KnowledgeBase
from scaffolding.objectives import ObjectiveCatalog
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage
from tests.objective_helpers import ScriptedExtractor


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


def make_page(base=None, extractor=None, catalog=None, generation=None, prefix=""):
    if base is None:
        base = KnowledgeBase()
    if extractor is None:
        extractor = ScriptedExtractor()
    objectives = ObjectiveCatalog(base, extractor)
    if catalog is None:
        catalog = TaskCatalog()
    page = TeacherPage(
        catalog,
        prefix=prefix,
        knowledge=base,
        objectives=objectives,
        generation=generation,
    )
    return page, objectives
```

Create `tests/test_teacher_objectives_open.py`:

```python
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage, response_for
from tests.teacher_objectives_helpers import form, text


def test_the_list_links_to_objectives_outside_the_task_rows():
    page = TeacherPage(TaskCatalog())

    listed = text(response_for(page, "GET", "/", ""))

    assert 'href="/objectives"' in listed
    assert "<li>" not in listed


def test_get_objectives_shows_the_query_and_does_not_retrieve():
    page = TeacherPage(TaskCatalog())

    opened = response_for(page, "GET", "/objectives", "")
    slashed = text(response_for(page, "GET", "/objectives/?ready=1", ""))
    unknown = response_for(page, "POST", "/objectives", form(action="发布"))

    assert opened.status == 200
    assert "课时" in text(opened)
    assert "学段" in text(opened)
    assert "查看" in text(opened)
    assert "提炼" not in text(opened)
    assert "课时原文" not in text(opened)
    assert "查看" in slashed
    assert unknown.status == 200
    assert "任务不存在" not in text(unknown)
    assert "先填完整再查询" not in text(unknown)


def test_the_teacher_prefix_is_written_on_the_objectives_link():
    page = TeacherPage(TaskCatalog(), prefix="/teacher")

    listed = text(response_for(page, "GET", "/", ""))
    opened = text(response_for(page, "GET", "/objectives", ""))

    assert 'href="/teacher/objectives"' in listed
    assert 'action="/teacher/objectives"' in opened
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_objectives_open.py -v`

Expected: FAIL because the list has no `/objectives` link and GET `/objectives` is 「任务不存在」

- [ ] **Step 3: Write minimal implementation**

Add these imports to `teacher_page.py`:

```python
from scaffolding.knowledge import KnowledgeBase
from scaffolding.objectives import ObjectiveCatalog
```

Add this class above `TeacherPage`:

```python
class _EmptyExtractor:
    def extract(self, retrieval):
        return ()
```

Change `TeacherPage.__init__` to:

```python
    def __init__(self, catalog, prefix: str = "", *, knowledge=None, objectives=None, generation=None) -> None:
        self.catalog = catalog
        self.drafts = {}
        self.prefix = prefix
        self.knowledge = knowledge if knowledge is not None else KnowledgeBase()
        self.objectives = (
            objectives if objectives is not None else ObjectiveCatalog(self.knowledge, _EmptyExtractor())
        )
        self.generation = generation
```

In `list_tasks`, put the objectives link after the create form and before `<ul>`. Do not wrap it in `<li>`.

```python
        body = (
            "<h1>任务列表</h1><form method=\"post\" action=\""
            + _with_prefix(self.prefix, "/tasks") + "\">"
            + "<button type=\"submit\">新建</button></form>"
            + "<a href=\"" + _with_prefix(self.prefix, "/objectives") + "\">目标</a><ul>"
            + "".join(items) + "</ul>"
        )
```

Add this method on `TeacherPage`:

```python
    def open_objectives(self) -> str:
        action = _with_prefix(self.prefix, "/objectives")
        body = (
            "<h1>目标</h1><form method=\"post\" action=\"" + action + "\">"
            + "<label><input type=\"radio\" name=\"mode\" value=\"课时\">课时</label>"
            + "<label><input type=\"radio\" name=\"mode\" value=\"学段\">学段</label>"
            + "<input name=\"version\">"
            + "<input name=\"volume\">"
            + "<input name=\"lesson\">"
            + "<input name=\"stage\">"
            + "<button type=\"submit\" name=\"action\" value=\"查看\">查看</button></form>"
        )
        return _document(body)
```

In `response_for`, before the final `return _html(_missing(), 404)`:

```python
    if parts == ["objectives"] and method == "GET":
        return _html(page.open_objectives())
    if parts == ["objectives"] and method == "POST":
        return _html(page.open_objectives())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_objectives_open.py tests/test_teacher_page_list.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/teacher_page.py tests/teacher_objectives_helpers.py tests/test_teacher_objectives_open.py
git commit -m "feat: open the teacher objectives page"
```

---

### Task 2: 查看课时检索

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Test: `tests/test_teacher_objectives_view.py`

**Interfaces:**
- Consumes: Task 1 的 `open_objectives` 和 `response_for`。`KnowledgeBase.retrieve_lesson`。`tests.objective_helpers.sample_base`。
- Produces: POST `/objectives` 的 `action=查看`。课时字段是 `mode`、`version`、`volume`、`lesson`。学段栏叫 `stage`，课时查询不读取它。

- [ ] **Step 1: Write the failing test**

Create `tests/test_teacher_objectives_view.py`:

```python
from scaffolding.knowledge import TextbookLesson
from scaffolding.teacher_page import response_for
from tests.objective_helpers import ScriptedExtractor, sample_base
from tests.teacher_objectives_helpers import form, make_page, text


def test_viewing_a_lesson_shows_both_texts_and_does_not_extract():
    base = sample_base()
    base.add_lesson(TextbookLesson("人教版", "必修一", "数据编码", "高中", "16", "<课时"))
    extractor = ScriptedExtractor()
    page, _objectives = make_page(base, extractor)

    opened = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        stage="初中",
        action="查看",
    ), ))
    again = text(response_for(page, "GET", "/objectives", ""))
    escaped = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="数据编码",
        action="查看",
    ), ))

    assert "课时原文" in opened
    assert "课标全文" in opened
    assert "12-15" in opened
    assert "1.1.2" in opened
    assert "现行" in opened
    assert "没有检索到资料" not in opened
    assert "提炼" in opened
    assert extractor.calls == []
    assert "课时原文" not in again
    assert "&lt;课时" in escaped
    assert "<课时" not in escaped


def test_an_incomplete_or_unknown_lesson_query_stays_on_the_page():
    base = sample_base()
    extractor = ScriptedExtractor()
    page, _objectives = make_page(base, extractor)

    blank = response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="   ",
        volume="必修一",
        lesson="信息系统的组成",
        action="查看",
    ), )
    missing = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="没有这一课",
        action="查看",
    ), ))
    unknown = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        action="发布",
    ), ))

    assert blank.status == 200
    assert "先填完整再查询" in text(blank)
    assert "课时原文" not in text(blank)
    assert "没有检索到资料" in missing
    assert "课时原文" not in missing
    assert "课标全文" not in missing
    assert "任务不存在" not in unknown
    assert "课时原文" not in unknown
    assert extractor.calls == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_objectives_view.py -v`

Expected: FAIL because POST `/objectives` still returns the empty query

- [ ] **Step 3: Write minimal implementation**

Add imports:

```python
from scaffolding.knowledge import KnowledgeBase, LessonRetrieval, LessonSource, StandardSource
from scaffolding.objectives import ObjectiveCatalog
```

`KnowledgeBase` and `ObjectiveCatalog` are already imported. Add `LessonRetrieval`, `LessonSource`, and `StandardSource` to the knowledge import.

Add these functions above `response_for`:

```python
def _filled(value: str) -> bool:
    return value.strip() != ""


def _objective_query(fields):
    mode = fields.get("mode", [""])[-1]
    if mode == "课时":
        version = fields.get("version", [""])[-1]
        volume = fields.get("volume", [""])[-1]
        lesson = fields.get("lesson", [""])[-1]
        if not all(_filled(value) for value in (version, volume, lesson)):
            return None
        return ("课时", version, volume, lesson)
    return None


def _retrieve(page, query):
    if query[0] == "课时":
        return page.knowledge.retrieve_lesson(query[1], query[2], query[3])
    return None


def _saved(page, query):
    if query[0] == "课时":
        return page.objectives.lesson_objectives(query[1], query[2], query[3])
    return ()


def _source_text(source) -> str:
    if isinstance(source, LessonSource):
        return (
            "版本：" + source.version
            + " 册次：" + source.volume
            + " 课时：" + source.lesson
            + " 学段：" + source.stage
            + " 页码：" + source.pages
        )
    return (
        "名称：" + source.name
        + " 学段：" + source.stage
        + " 条款号：" + source.clauses
        + " 现行"
    )


def _query_fields(query):
    version = volume = lesson = stage = ""
    mode = "" if query is None else query[0]
    if query is not None and query[0] == "课时":
        version, volume, lesson = query[1], query[2], query[3]
    checked_lesson = " checked" if mode == "课时" else ""
    checked_stage = " checked" if mode == "学段" else ""
    return mode, version, volume, lesson, stage, checked_lesson, checked_stage


def _query_form(page, query, offer_extract: bool) -> str:
    _mode, version, volume, lesson, stage, checked_lesson, checked_stage = _query_fields(query)
    action = _with_prefix(page.prefix, "/objectives")
    body = (
        "<form method=\"post\" action=\"" + action + "\">"
        + "<label><input type=\"radio\" name=\"mode\" value=\"课时\"" + checked_lesson + ">课时</label>"
        + "<label><input type=\"radio\" name=\"mode\" value=\"学段\"" + checked_stage + ">学段</label>"
        + "<input name=\"version\" value=\"" + escape(version) + "\">"
        + "<input name=\"volume\" value=\"" + escape(volume) + "\">"
        + "<input name=\"lesson\" value=\"" + escape(lesson) + "\">"
        + "<input name=\"stage\" value=\"" + escape(stage) + "\">"
        + "<button type=\"submit\" name=\"action\" value=\"查看\">查看</button>"
    )
    if offer_extract:
        body += "<button type=\"submit\" name=\"action\" value=\"提炼\">提炼</button>"
    return body + "</form>"


def _retrieval_html(retrieval) -> str:
    if not isinstance(retrieval, LessonRetrieval):
        return ""
    return (
        "<section><h2>课时原文</h2><p>" + escape(retrieval.lesson_text) + "</p>"
        + "<p>教材来源：" + escape(_source_text(retrieval.lesson_source)) + "</p>"
        + "<h2>课标全文</h2><p>" + escape(retrieval.standard_text) + "</p>"
        + "<p>课标来源：" + escape(_source_text(retrieval.standard_source)) + "</p></section>"
    )


def _render_objectives(page, query, message: str) -> str:
    retrieval = None if query is None else _retrieve(page, query)
    objectives = () if query is None else _saved(page, query)
    if retrieval is None and query is not None and message == "":
        message = "没有检索到资料"
    parts = ["<h1>目标</h1>"]
    if message:
        parts.append("<p>" + escape(message) + "</p>")
    parts.append(_query_form(page, query, offer_extract=query is not None and objectives == ()))
    parts.append(_retrieval_html(retrieval))
    return _document("".join(parts))
```

Replace `open_objectives` with:

```python
    def open_objectives(self, message: str = "") -> str:
        return _render_objectives(self, None, message)


    def apply_objectives(self, fields, action: str) -> str:
        if action != "查看":
            return self.open_objectives()
        query = _objective_query(fields)
        if query is None:
            return self.open_objectives("先填完整再查询")
        return _render_objectives(self, query, "")
```

Replace the POST branch in `response_for` with:

```python
    if parts == ["objectives"] and method == "POST":
        fields = parse_qs(body, keep_blank_values=True)
        action = fields.get("action", [""])[-1]
        return _html(page.apply_objectives(fields, action))
```

`LessonSource` is used by `_source_text`. `StandardSource` is imported for the later stage branch; importing it now avoids a second import edit only if this task's `_source_text` already handles it. The `isinstance(source, LessonSource)` branch covers lesson sources. A non-lesson source uses the other branch, so `StandardSource` does not have to be named. Do not leave an unused import. Import `LessonRetrieval` and `LessonSource` only.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_objectives_view.py tests/test_teacher_objectives_open.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/teacher_page.py tests/test_teacher_objectives_view.py
git commit -m "feat: show a lesson retrieval on the teacher objectives page"
```

---

### Task 3: 查看学段检索

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Test: `tests/test_teacher_objectives_stage.py`

**Interfaces:**
- Consumes: Task 2 的 `_objective_query`、`_retrieve`、`_saved`、`_query_fields`、`_retrieval_html`。
- Produces: `mode=学段` 时查询元组是 `("学段", stage)`。`retrieve_stage` 和 `stage_objectives`。

- [ ] **Step 1: Write the failing test**

Create `tests/test_teacher_objectives_stage.py`:

```python
from scaffolding.knowledge import TextbookLesson
from scaffolding.teacher_page import response_for
from tests.objective_helpers import ScriptedExtractor, sample_base
from tests.teacher_objectives_helpers import form, make_page, text


def test_viewing_a_stage_shows_only_the_standard():
    base = sample_base()
    extractor = ScriptedExtractor()
    page, _objectives = make_page(base, extractor)

    opened = text(response_for(page, "POST", "/objectives", form(
        mode="学段",
        stage="高中",
        version="没有的版本",
        volume="必修一",
        lesson="信息系统的组成",
        action="查看",
    ), ))

    assert "课标全文" in opened
    assert "1.1.2" in opened
    assert "现行" in opened
    assert "课时原文" not in opened
    assert "没有检索到资料" not in opened
    assert extractor.calls == []


def test_a_different_lesson_and_a_half_retrieval_stay_separate():
    base = sample_base()
    base.add_lesson(TextbookLesson("沪科教版", "必修一", "信息系统的组成", "高中", "8", "沪科原文"))
    base.add_lesson(TextbookLesson("人教版", "必修一", "没有课标的课", "初中", "3", "半份原文"))
    extractor = ScriptedExtractor()
    page, _objectives = make_page(base, extractor)

    other = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="沪科教版",
        volume="必修一",
        lesson="信息系统的组成",
        action="查看",
    ), ))
    half = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="没有课标的课",
        action="查看",
    ), ))
    blank_stage = text(response_for(page, "POST", "/objectives", form(
        mode="学段",
        stage="  ",
        action="查看",
    ), ))

    assert "沪科原文" in other
    assert "12-15" not in other
    assert "没有检索到资料" in half
    assert "半份原文" not in half
    assert "先填完整再查询" in blank_stage
    assert extractor.calls == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_objectives_stage.py -v`

Expected: FAIL because a stage query is treated as incomplete and shows 「先填完整再查询」

- [ ] **Step 3: Write minimal implementation**

Replace `_objective_query` with:

```python
def _objective_query(fields):
    mode = fields.get("mode", [""])[-1]
    if mode == "课时":
        version = fields.get("version", [""])[-1]
        volume = fields.get("volume", [""])[-1]
        lesson = fields.get("lesson", [""])[-1]
        if not all(_filled(value) for value in (version, volume, lesson)):
            return None
        return ("课时", version, volume, lesson)
    if mode == "学段":
        stage = fields.get("stage", [""])[-1]
        if not _filled(stage):
            return None
        return ("学段", stage)
    return None
```

Replace `_retrieve` with:

```python
def _retrieve(page, query):
    if query[0] == "课时":
        return page.knowledge.retrieve_lesson(query[1], query[2], query[3])
    return page.knowledge.retrieve_stage(query[1])
```

Replace `_saved` with:

```python
def _saved(page, query):
    if query[0] == "课时":
        return page.objectives.lesson_objectives(query[1], query[2], query[3])
    return page.objectives.stage_objectives(query[1])
```

In `_query_fields`, after the lesson assignment, add:

```python
    if query is not None and query[0] == "学段":
        stage = query[1]
```

Replace `_retrieval_html` with:

```python
def _retrieval_html(retrieval) -> str:
    if isinstance(retrieval, LessonRetrieval):
        return (
            "<section><h2>课时原文</h2><p>" + escape(retrieval.lesson_text) + "</p>"
            + "<p>教材来源：" + escape(_source_text(retrieval.lesson_source)) + "</p>"
            + "<h2>课标全文</h2><p>" + escape(retrieval.standard_text) + "</p>"
            + "<p>课标来源：" + escape(_source_text(retrieval.standard_source)) + "</p></section>"
        )
    if retrieval is None:
        return ""
    return (
        "<section><h2>课标全文</h2><p>" + escape(retrieval.standard_text) + "</p>"
        + "<p>课标来源：" + escape(_source_text(retrieval.standard_source)) + "</p></section>"
    )
```

Import `StageRetrieval` only if a branch names it. This replacement does not name it. Do not add an unused import.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_objectives_stage.py tests/test_teacher_objectives_view.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/teacher_page.py tests/test_teacher_objectives_stage.py
git commit -m "feat: show a stage retrieval on the teacher objectives page"
```

---

### Task 4: 提炼目标

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Test: `tests/test_teacher_objectives_extract.py`

**Interfaces:**
- Consumes: Task 3 的查询、`_render_objectives`、`_saved`、`_retrieve`。`ObjectiveCatalog.extract_lesson` 和 `extract_stage`。`objectives.Rejected`。
- Produces: `action=提炼`。已有记录时不调用提炼方。

- [ ] **Step 1: Write the failing test**

Create `tests/test_teacher_objectives_extract.py`:

```python
from scaffolding.objectives import ObjectiveDraft
from scaffolding.teacher_page import response_for
from tests.objective_helpers import ScriptedExtractor, sample_base
from tests.teacher_objectives_helpers import form, make_page, text


def _lesson_form(**extra):
    fields = {
        "mode": "课时",
        "version": "人教版",
        "volume": "必修一",
        "lesson": "信息系统的组成",
        "action": "提炼",
    }
    fields.update(extra)
    return form(**fields)


def test_extract_keeps_valid_objectives_and_drops_the_rest():
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (
        ObjectiveDraft("计算思维", "能描述组成", retrieval.lesson_source),
        ObjectiveDraft("超纲维度", "不算", retrieval.lesson_source),
        ObjectiveDraft("信息意识", "   ", retrieval.lesson_source),
        ObjectiveDraft("信息意识", "能识别信息", retrieval.standard_source),
        ObjectiveDraft("信息意识", "能再举一例", retrieval.lesson_source),
    )
    page, objectives = make_page(base, extractor)

    opened = text(response_for(page, "POST", "/objectives", _lesson_form(), ))

    assert opened.index("objective-1") < opened.index("objective-2")
    assert "能描述组成" in opened
    assert "能识别信息" in opened
    assert "能再举一例" in opened
    assert opened.index("能识别信息") < opened.index("能再举一例")
    assert "不算" not in opened
    assert "计算思维" in opened
    assert "页码：" in opened
    assert "提炼" not in opened
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能描述组成"
    assert extractor.calls == [retrieval]


def test_extract_reports_empty_invalid_and_failed_results():
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    page, objectives = make_page(base, extractor)

    empty = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="没有这一课",
        action="提炼",
    ), ))
    extractor.lesson_results = (ObjectiveDraft("超纲维度", "不算", retrieval.lesson_source),)
    invalid = text(response_for(page, "POST", "/objectives", _lesson_form(), ))
    extractor.lesson_error = RuntimeError("boom")
    failed = text(response_for(page, "POST", "/objectives", _lesson_form(), ))

    assert "没有检索到资料" in empty
    assert extractor.calls == []
    assert "没有留下可保存的目标" in invalid
    assert "课时原文" in invalid
    assert "提炼" in invalid
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
    assert "提炼失败，没有保存目标" in failed
    assert "课时原文" in failed
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()


def test_an_existing_record_rejects_extract_without_calling_the_extractor():
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (ObjectiveDraft("计算思维", "能描述组成", retrieval.lesson_source),)
    page, objectives = make_page(base, extractor)
    response_for(page, "POST", "/objectives", _lesson_form(), )
    calls = list(extractor.calls)
    page.knowledge = type(page.knowledge)()

    rejected = response_for(page, "POST", "/objectives", _lesson_form(), )
    rejected_text = text(rejected)

    assert rejected.status == 200
    assert "已有目标，不能再次提炼" in rejected_text
    assert "没有检索到资料" not in rejected_text
    assert "能描述组成" in rejected_text
    assert "提炼" not in rejected_text
    assert extractor.calls == calls
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能描述组成"
```

The third test replaces `page.knowledge` with an empty `KnowledgeBase` after the first extract. `type(page.knowledge)()` is that empty base. The catalog still holds the saved objective. The second extract must not call the extractor.

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_objectives_extract.py -v`

Expected: FAIL because `action=提炼` still returns the empty query

- [ ] **Step 3: Write minimal implementation**

Import `Rejected` from objectives under another name:

```python
from scaffolding.objectives import ObjectiveCatalog, Rejected as ObjectiveRejected
```

Add `_extract_objectives` above `response_for`:

```python
def _extract_objectives(page, query) -> str:
    if _saved(page, query) != ():
        return _render_objectives(page, query, "已有目标，不能再次提炼")
    if _retrieve(page, query) is None:
        return _render_objectives(page, query, "没有检索到资料")
    try:
        if query[0] == "课时":
            saved = page.objectives.extract_lesson(query[1], query[2], query[3])
        else:
            saved = page.objectives.extract_stage(query[1])
    except ObjectiveRejected:
        return _render_objectives(page, query, "已有目标，不能再次提炼")
    except Exception:
        return _render_objectives(page, query, "提炼失败，没有保存目标")
    if saved == ():
        return _render_objectives(page, query, "没有留下可保存的目标")
    return _render_objectives(page, query, "")
```

Replace `apply_objectives` with:

```python
    def apply_objectives(self, fields, action: str) -> str:
        if action not in ("查看", "提炼"):
            return self.open_objectives()
        query = _objective_query(fields)
        if query is None:
            return self.open_objectives("先填完整再查询")
        if action == "提炼":
            return _extract_objectives(self, query)
        return _render_objectives(self, query, "")
```

`_render_objectives` already sets `offer_extract` when `objectives == ()`. After a saved extract, `_saved` is non-empty, so the button is absent. Do not render the objective rows yet; Task 5 adds edit and delete. The saved statements still need to be visible. Append this inside `_render_objectives` before `return _document`:

```python
    for item in objectives:
        parts.append(
            "<article><p>" + escape(item.objective_id) + "</p><p>"
            + escape(item.dimension) + "</p><p>" + escape(item.statement) + "</p><p>"
            + escape(_source_text(item.source)) + "</p></article>"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_objectives_extract.py tests/test_teacher_objectives_view.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/teacher_page.py tests/test_teacher_objectives_extract.py
git commit -m "feat: extract objectives on the teacher page"
```

---

### Task 5: 修改和删除目标

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Test: `tests/test_teacher_objectives_edit.py`

**Interfaces:**
- Consumes: Task 4 的目标文章和 `_extract_objectives`。`edit_statement(objective_id, statement)` 和 `delete(objective_id)`。
- Produces: `action=修改` 读取 `objective` 和 `statement`。`action=删除` 读取 `objective`。两个动作都重新提交本次查询字段。

- [ ] **Step 1: Write the failing test**

Create `tests/test_teacher_objectives_edit.py`:

```python
from scaffolding.knowledge import CurriculumStandard
from scaffolding.objectives import ObjectiveDraft
from scaffolding.teacher_page import response_for
from tests.objective_helpers import ScriptedExtractor, sample_base
from tests.teacher_objectives_helpers import form, make_page, text


def _prepare():
    base = sample_base()
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    lesson = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    stage = base.retrieve_stage("初中")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (
        ObjectiveDraft("计算思维", "能描述组成", lesson.lesson_source),
        ObjectiveDraft("信息意识", "能识别信息", lesson.standard_source),
    )
    extractor.stage_results = (ObjectiveDraft("信息社会责任", "遵守规范", stage.standard_source),)
    page, objectives = make_page(base, extractor)
    response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        action="提炼",
    ), )
    response_for(page, "POST", "/objectives", form(
        mode="学段",
        stage="初中",
        action="提炼",
    ), )
    return page, objectives, base


def test_edit_changes_only_the_statement_in_the_current_query():
    page, objectives, base = _prepare()
    stored = base.get_lesson("人教版", "必修一", "信息系统的组成")

    edited = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        objective="objective-1",
        statement="能说明组成",
        action="修改",
    ), ))
    blank = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        objective="objective-1",
        statement="  ",
        action="修改",
    ), ))
    other = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        objective="objective-3",
        statement="不该改学段",
        action="修改",
    ), ))

    assert "能说明组成" in edited
    assert "计算思维" in edited
    assert "课时原文" in edited
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能说明组成"
    assert "表述不能为空" in blank
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能说明组成"
    assert "目标不存在" in other
    assert objectives.stage_objectives("初中")[0].statement == "遵守规范"
    assert base.get_lesson("人教版", "必修一", "信息系统的组成") is stored


def test_delete_keeps_the_remaining_ids_and_allows_extract_when_none_remain():
    page, objectives, _base = _prepare()

    deleted = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        objective="objective-1",
        action="删除",
    ), ))
    cleared = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        objective="objective-2",
        action="删除",
    ), ))

    assert "objective-1" not in deleted
    assert "objective-2" in deleted
    assert "能识别信息" in deleted
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].objective_id == "objective-2"
    assert "提炼" in cleared
    assert "课时原文" in cleared
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
    assert objectives.stage_objectives("初中")[0].statement == "遵守规范"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_objectives_edit.py -v`

Expected: FAIL because `action=修改` returns the empty query and the statement stays 「能描述组成」

- [ ] **Step 3: Write minimal implementation**

Add `_hidden_query`, `_edit_objective`, and `_delete_objective` above `response_for`:

```python
def _hidden_query(query) -> str:
    mode, version, volume, lesson, stage, _checked_lesson, _checked_stage = _query_fields(query)
    return (
        "<input type=\"hidden\" name=\"mode\" value=\"" + escape(mode) + "\">"
        + "<input type=\"hidden\" name=\"version\" value=\"" + escape(version) + "\">"
        + "<input type=\"hidden\" name=\"volume\" value=\"" + escape(volume) + "\">"
        + "<input type=\"hidden\" name=\"lesson\" value=\"" + escape(lesson) + "\">"
        + "<input type=\"hidden\" name=\"stage\" value=\"" + escape(stage) + "\">"
    )


def _edit_objective(page, query, fields) -> str:
    objective_id = fields.get("objective", [""])[-1]
    statement = fields.get("statement", [""])[-1]
    current = _saved(page, query)
    if objective_id not in {item.objective_id for item in current}:
        return _render_objectives(page, query, "目标不存在")
    if not _filled(statement):
        return _render_objectives(page, query, "表述不能为空")
    try:
        page.objectives.edit_statement(objective_id, statement)
    except ObjectiveRejected:
        return _render_objectives(page, query, "目标不存在")
    return _render_objectives(page, query, "")


def _delete_objective(page, query, fields) -> str:
    objective_id = fields.get("objective", [""])[-1]
    current = _saved(page, query)
    if objective_id not in {item.objective_id for item in current}:
        return _render_objectives(page, query, "目标不存在")
    try:
        page.objectives.delete(objective_id)
    except ObjectiveRejected:
        return _render_objectives(page, query, "目标不存在")
    return _render_objectives(page, query, "")
```

Replace the objective article loop in `_render_objectives` with:

```python
    action = _with_prefix(page.prefix, "/objectives")
    for item in objectives:
        hidden = "" if query is None else _hidden_query(query)
        parts.append(
            "<article><p>" + escape(item.objective_id) + "</p><p>"
            + escape(item.dimension) + "</p><p>" + escape(item.statement) + "</p><p>"
            + escape(_source_text(item.source)) + "</p>"
            + "<form method=\"post\" action=\"" + action + "\">" + hidden
            + "<input type=\"hidden\" name=\"objective\" value=\"" + escape(item.objective_id) + "\">"
            + "<input name=\"statement\" value=\"" + escape(item.statement) + "\">"
            + "<button type=\"submit\" name=\"action\" value=\"修改\">修改表述</button></form>"
            + "<form method=\"post\" action=\"" + action + "\">" + hidden
            + "<input type=\"hidden\" name=\"objective\" value=\"" + escape(item.objective_id) + "\">"
            + "<button type=\"submit\" name=\"action\" value=\"删除\">删除</button></form></article>"
        )
```

Replace `apply_objectives` with:

```python
    def apply_objectives(self, fields, action: str) -> str:
        if action not in ("查看", "提炼", "修改", "删除"):
            return self.open_objectives()
        query = _objective_query(fields)
        if query is None:
            return self.open_objectives("先填完整再查询")
        if action == "提炼":
            return _extract_objectives(self, query)
        if action == "修改":
            return _edit_objective(self, query, fields)
        if action == "删除":
            return _delete_objective(self, query, fields)
        return _render_objectives(self, query, "")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_objectives_edit.py tests/test_teacher_objectives_extract.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/teacher_page.py tests/test_teacher_objectives_edit.py
git commit -m "feat: edit and delete a teacher objective"
```

---

### Task 6: 链到对应任务

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Test: `tests/test_teacher_objectives_links.py`

**Interfaces:**
- Consumes: Task 5 的 `_render_objectives`。`TaskGeneration.origin(task_id)`。`LessonOrigin` 和 `StageOrigin`。
- Produces: 目标页上的任务链接，地址是 `prefix + "/tasks/" + task_id`。`page.generation is None` 时不列出链接。

- [ ] **Step 1: Write the failing test**

Create `tests/test_teacher_objectives_links.py`:

```python
from scaffolding.generation import TaskGeneration
from scaffolding.knowledge import CurriculumStandard
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft
from scaffolding.records import TrueFalseQuestion
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage, response_for
from tests.generation_helpers import ScriptedGenerator, single
from tests.objective_helpers import ScriptedExtractor, sample_base
from tests.teacher_objectives_helpers import form, text


def _page():
    base = sample_base()
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    lesson = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    stage = base.retrieve_stage("初中")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (ObjectiveDraft("计算思维", "能描述组成", lesson.lesson_source),)
    extractor.stage_results = (ObjectiveDraft("信息社会责任", "遵守规范", stage.standard_source),)
    objectives = ObjectiveCatalog(base, extractor)
    objectives.extract_lesson("人教版", "必修一", "信息系统的组成")
    objectives.extract_stage("初中")
    catalog = TaskCatalog()
    generator = ScriptedGenerator()
    generation = TaskGeneration(objectives, catalog, generator)
    generator.questions = (single("课时甲"),)
    first = generation.generate_lesson(
        "人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0
    )
    catalog.create((TrueFalseQuestion("手写题干", "正确", "手写解析"),))
    generator.questions = (single("课时乙"),)
    second = generation.generate_lesson(
        "人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0
    )
    generator.questions = (single("学段题"),)
    stage_task = generation.generate_stage("初中", single=1, multiple=0, true_false=0, open_ended=0)
    catalog.publish(first.task_id)
    catalog.start(first.task_id)
    page = TeacherPage(
        catalog,
        knowledge=base,
        objectives=objectives,
        generation=generation,
    )
    return page, generator, first, second, stage_task


def test_lesson_links_follow_catalog_order_and_skip_other_origins():
    page, generator, first, second, stage_task = _page()
    calls = list(generator.calls)

    opened = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        action="查看",
    ), ))
    page.catalog.delete(second.task_id)
    after_delete = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        action="查看",
    ), ))

    assert 'href="/tasks/' + first.task_id + '"' in opened
    assert 'href="/tasks/' + second.task_id + '"' in opened
    assert opened.index(first.task_id) < opened.index(second.task_id)
    assert stage_task.task_id not in opened
    assert "task-2" not in opened
    assert "课时甲" not in opened
    assert "手写题干" not in opened
    assert "学段题" not in opened
    assert generator.calls == calls
    assert second.task_id not in after_delete
    assert first.task_id in after_delete


def test_stage_links_and_the_teacher_prefix_do_not_call_generation():
    page, generator, _first, _second, stage_task = _page()
    page.prefix = "/teacher"
    calls = list(generator.calls)

    opened = text(response_for(page, "POST", "/objectives", form(
        mode="学段",
        stage="初中",
        action="查看",
    ), ))

    assert 'href="/teacher/tasks/' + stage_task.task_id + '"' in opened
    assert "task-1" not in opened
    assert "学段题" not in opened
    assert generator.calls == calls


def test_a_hand_written_task_has_no_objectives_link():
    base = sample_base()
    objectives = ObjectiveCatalog(base, ScriptedExtractor())
    catalog = TaskCatalog()
    catalog.create((TrueFalseQuestion("手写题干", "正确", "手写解析"),))
    generation = TaskGeneration(objectives, catalog, ScriptedGenerator())
    page = TeacherPage(catalog, knowledge=base, objectives=objectives, generation=generation)

    opened = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        action="查看",
    ), ))

    assert "课时原文" in opened
    assert 'href="/tasks/' not in opened
    assert "手写题干" not in opened
```

`catalog.create` after the first generated task assigns `task-2` to the hand-written task. The lesson page must not contain that id.

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_objectives_links.py -v`

Expected: FAIL because the objectives page has no task href

- [ ] **Step 3: Write minimal implementation**

Import origins:

```python
from scaffolding.generation import LessonOrigin, StageOrigin
```

Add `_task_links` above `response_for`:

```python
def _task_links(page, query) -> str:
    if page.generation is None or query is None:
        return ""
    items = []
    for task in page.catalog._tasks.values():
        origin = page.generation.origin(task.task_id)
        matched = False
        if query[0] == "课时":
            matched = origin == LessonOrigin(query[1], query[2], query[3])
        elif query[0] == "学段":
            matched = origin == StageOrigin(query[1])
        if not matched:
            continue
        href = _with_prefix(page.prefix, "/tasks/" + quote(task.task_id, safe=""))
        items.append("<li><a href=\"" + href + "\">" + escape(task.task_id) + "</a></li>")
    if items == []:
        return ""
    return "<ul>" + "".join(items) + "</ul>"
```

In `_render_objectives`, after the objective articles and before `return _document`, append:

```python
    parts.append(_task_links(page, query))
```

Do not call `generate_lesson` or `generate_stage`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_objectives_links.py tests/test_teacher_objectives_edit.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/teacher_page.py tests/test_teacher_objectives_links.py
git commit -m "feat: link a lesson to its generated tasks"
```

---

### Task 7: 课堂验收

**Files:**
- Modify: `src/scaffolding/classroom.py`
- Create: `tests/test_teacher_objectives_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-21-teacher-objectives-design.md`

**Interfaces:**
- Consumes: Task 6 的 `TeacherPage(..., knowledge=, objectives=, generation=)`。`ModelObjectiveExtractor`、`ModelQuestionGenerator`、`deepseek_complete`。
- Produces: `Classroom(..., knowledge=None, objectives=None, generation=None)`。`room.knowledge`、`room.objectives`、`room.generation` 与 `room.teacher` 上的是同一组。`production_classroom` 准备模型提炼方和模型出题方。

- [ ] **Step 1: Write the failing test**

If `docs/superpowers/specs/2026-10-21-teacher-objectives-design.md` is missing in this worktree, copy `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-21-teacher-objectives-design.md` unchanged. Do not edit it.

Create `tests/test_teacher_objectives_acceptance.py`:

```python
from pathlib import Path

from scaffolding.classroom import Classroom, production_classroom, response_for, serve
from scaffolding.knowledge import KnowledgeBase
from scaffolding.model_extractor import ModelObjectiveExtractor
from scaffolding.model_generator import ModelQuestionGenerator
from scaffolding.objectives import ObjectiveCatalog
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.tasks import TaskCatalog
from tests.classroom_helpers import text
from tests.objective_helpers import ScriptedExtractor, sample_base


def test_the_classroom_prefixes_objectives_and_hides_them_from_the_student():
    base = sample_base()
    objectives = ObjectiveCatalog(base, ScriptedExtractor())
    catalog = TaskCatalog()
    room = Classroom(
        catalog,
        ScriptedDecisionAgent(),
        ScriptedScaffoldAgent(),
        base,
        objectives,
        None,
    )

    home = text(response_for(room, "GET", "/", "", 0))
    listed = text(response_for(room, "GET", "/teacher", "", 0))
    opened = text(response_for(room, "GET", "/teacher/objectives/?ready=1", "", 0))
    student = response_for(room, "GET", "/student/objectives", "", 1)

    assert "目标" not in home
    assert 'href="/teacher/objectives"' in listed
    assert "查看" in opened
    assert student.status == 404
    assert "任务不存在" in text(student)
    assert "课时原文" not in text(student)
    assert "能描述组成" not in text(student)


def test_a_new_classroom_does_not_see_another_knowledge_base_or_objectives():
    base = sample_base()
    objectives = ObjectiveCatalog(base, ScriptedExtractor())
    first = Classroom(
        TaskCatalog(),
        ScriptedDecisionAgent(),
        ScriptedScaffoldAgent(),
        base,
        objectives,
        None,
    )
    second = Classroom(TaskCatalog(), ScriptedDecisionAgent(), ScriptedScaffoldAgent())

    assert second.knowledge.lesson_count() == 0
    assert second.objectives.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
    assert first.knowledge is not second.knowledge
    assert first.objectives is not second.objectives
    assert first.teacher.knowledge is first.knowledge
    assert second.teacher.objectives is second.objectives


def test_production_prepares_the_model_records_without_calling_them():
    def post(_request):
        raise AssertionError("network")

    room = production_classroom(post=post)

    assert isinstance(room.objectives._extractor, ModelObjectiveExtractor)
    assert isinstance(room.generation._generator, ModelQuestionGenerator)
    assert room.teacher.knowledge is room.knowledge
    assert room.teacher.objectives is room.objectives
    assert room.teacher.generation is room.generation
    assert room.generation._tasks is room.catalog
    assert room.generation._objectives is room.objectives


def test_the_spec_is_present_and_the_listener_is_not_started():
    assert Path("docs/superpowers/specs/2026-10-21-teacher-objectives-design.md").is_file()
    assert callable(serve)
    assert callable(production_classroom)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_objectives_acceptance.py -v`

Expected: FAIL because `Classroom` does not accept the knowledge base, or `production_classroom` leaves `generation` empty

- [ ] **Step 3: Write minimal implementation**

Add these imports to `classroom.py`:

```python
from scaffolding.generation import TaskGeneration
from scaffolding.knowledge import KnowledgeBase
from scaffolding.model_extractor import ModelObjectiveExtractor
from scaffolding.model_generator import ModelQuestionGenerator
from scaffolding.objectives import ObjectiveCatalog
```

Copy `_EmptyExtractor` into `classroom.py` above `Classroom`. Do not import it from `teacher_page`; it is private there.

```python
class _EmptyExtractor:
    def extract(self, retrieval):
        return ()
```

Replace `Classroom.__init__` with:

```python
    def __init__(
        self,
        catalog,
        decision,
        scaffold_agent,
        knowledge=None,
        objectives=None,
        generation=None,
    ) -> None:
        self.catalog = catalog
        self.knowledge = knowledge if knowledge is not None else KnowledgeBase()
        self.objectives = (
            objectives
            if objectives is not None
            else ObjectiveCatalog(self.knowledge, _EmptyExtractor())
        )
        self.generation = generation
        self.teacher = TeacherPage(
            catalog,
            prefix="/teacher",
            knowledge=self.knowledge,
            objectives=self.objectives,
            generation=generation,
        )
        self.student = StudentPage(catalog, decision, scaffold_agent, prefix="/student")
```

Replace `production_classroom` with:

```python
def production_classroom(*, post, api_key=None) -> Classroom:
    catalog = TaskCatalog()
    knowledge = KnowledgeBase()

    def complete(messages):
        return deepseek_complete(messages, post=post, api_key=api_key)

    objectives = ObjectiveCatalog(knowledge, ModelObjectiveExtractor(complete))
    generation = TaskGeneration(objectives, catalog, ModelQuestionGenerator(complete))
    return Classroom(
        catalog,
        ModelDecisionAgent(complete),
        ModelScaffoldAgent(complete),
        knowledge,
        objectives,
        generation,
    )
```

No test calls `serve`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS. The count is the previous suite plus the new objectives tests. No test calls `serve`.

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/classroom.py tests/test_teacher_objectives_acceptance.py docs/superpowers/specs/2026-10-21-teacher-objectives-design.md
git commit -m "test: accept teacher retrieval and objectives in the classroom"
```

The spec file in this commit must be the unchanged copy from `fef53b0`.
