# 按目标生成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让教师在目标页按已经保存的目标生成一份带有当前查询来源的未发布任务。

**Architecture:** `TaskGeneration` 增加 `generate_from_objectives`。它把保存的目标写成规定文字，调用现有文字生成方，用现有 `parse_text_task` 核对，创建未发布任务后写入课时来源或学段来源。目标页在已有目标后面放「按目标生成」。成功响应是现有任务页。失败仍停在目标页。

**Tech Stack:** Python 3.14，pytest 9，标准库。实现从 `origin/main` 的 `ff60f2a` 建工作区。规格在本地 `master` 的 `4fd1650`，文件是 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-22-teacher-objective-generation-design.md`。工作区里若没有这份规格，在 Task 4 从该文件原样复制，不要改写。测试命令是 `.\.venv\Scripts\python.exe -m pytest`。PowerShell 下不要使用 `&&` 或 bash heredoc；提交用 `git commit -m "message"`。不要改 git config，不要 push。不要提交本计划。

## Global Constraints

- 「按目标生成」只在当前查询已经有保存的目标时出现，放在这些目标后面、任务链接前面。整页只有一个，不放进某一条的修改或删除表单。按钮上的字和提交值都是这四个字，提交字段的名字是 `action`。它带上和修改、删除相同的查询字段，提交地址仍是目标页。
- 还没有查询、还没有目标，或最后一条被删掉时，不显示这个按钮。查看、提炼、修改、删除之后，只要目标还在，按钮就在。检索没有资料但目标还在时，按钮也在。
- 查询表单旁的「生成」仍打开文字生成页。教师列表和课堂入口不增加「按目标生成」。课堂里带 `/teacher`，单独调用教师页时不带前缀。末尾多一个斜杠或查询字符串不影响。
- 新入口接收已经保存的目标和这次查询的来源。课时来源是版本、册次、课时。学段来源是学段。它不读知识库，不提炼，也不走课时生成或学段生成。按文字生成仍不写来源。
- 文字按保存顺序逐条两行：`维度：` 紧接维度，`表述：` 紧接表述，用保存下来的原文。各行用换行连接，中间不插空行，末尾不另加空行。最后一行是 `没有指定题型和数量。`
- 没有文字生成方，或一条目标都没有时，不调用模型。有目标时最多调用一次，用课堂里已有的文字生成方。
- 交回仍用现有核对。交回的目标核对后丢掉，不写入目标库，也不必和已保存目标逐条相同。已保存目标保持原样。四类合计至少一道。题目顺序是单选、多选、判断、综合。
- 核对通过后创建未发布任务并写上来源。每提交一次另创建一份。它出现在任务列表和这次查询的任务链接里。成功响应是现有任务页，状态 200，标为未发布。
- 失败停在目标页，状态 200，显示「生成失败，没有创建任务」，不创建任务。原文、已保存目标和已有任务链接还在。知识库、目标库和已有任务保持原样。没有目标、没有任务生成记录、没有文字生成方时不调用模型。
- 查询没填完整时显示「先填完整再查询」，不调用模型。不认识的动作仍只显示查询。「按目标生成」是认识的动作。检索没有资料时，失败句代替「没有检索到资料」。
- 原文、表述、题目和标识按文字写进页面。HTML 用拼接，不用 `str.format`。
- 学生地址仍是「任务不存在」，状态 404。学生页没有这个按钮。
- 知识库上传和教材课标预置不在这里。测试不调用 `serve`，不打开浏览器，不访问网络。
- 不修改 `tasks.py`、`session.py`、`html_assets.py`、`agents.py`、`scripted.py`、`records.py`、`model_decision.py`、`model_scaffold.py`、`model_generator.py`、`model_extractor.py`、`model_text.py`、`text_generation.py`、`objectives.py`、`knowledge.py`、`student_page.py`、`classroom.py`。

## File Map

- Modify: `src/scaffolding/generation.py` — `generate_from_objectives`。
- Modify: `src/scaffolding/teacher_page.py` — 按钮、失败和成功响应。
- Create: `tests/test_objective_generation_record.py`
- Create: `tests/test_teacher_objective_generation_page.py`
- Create: `tests/test_teacher_objective_generation_success.py`
- Create: `tests/test_teacher_objective_generation_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-22-teacher-objective-generation-design.md`

---

### Task 1: 按已保存目标创建带来源的任务

**Files:**
- Modify: `src/scaffolding/generation.py`
- Test: `tests/test_objective_generation_record.py`

**Interfaces:**
- Consumes: `parse_text_task(reply)`。`LessonOrigin`、`StageOrigin`。`Objective`。现有 `TaskGeneration` 和 `TaskCatalog.create`。
- Produces: `generate_from_objectives(objectives: tuple[Objective, ...], origin: LessonOrigin | StageOrigin) -> Task`。创建后写入 `_origins`。文字生成方的方法仍是 `generate(text) -> str`。

- [ ] **Step 1: Write the failing test**

Create `tests/test_objective_generation_record.py`:

```python
import pytest

from scaffolding.generation import LessonOrigin, Rejected, StageOrigin, TaskGeneration
from scaffolding.objectives import Objective
from scaffolding.tasks import TaskCatalog
from tests.generation_helpers import ScriptedGenerator, prepared_objectives
from tests.test_text_generation_record import ScriptedTextGenerator


def _pair(saved):
    source = saved.source
    return (
        saved,
        Objective("objective-9", "计算思维", "  能分解步骤  ", source),
    )


def test_saved_objectives_create_an_unpublished_task_with_the_given_origin():
    base, objectives = prepared_objectives()
    catalog = TaskCatalog()
    questions = ScriptedGenerator()
    text_generator = ScriptedTextGenerator()
    generation = TaskGeneration(objectives, catalog, questions, text_generator)
    saved = objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0]

    task = generation.generate_from_objectives(
        _pair(saved),
        LessonOrigin("人教版", "必修一", "信息系统的组成"),
    )

    assert task.published is False
    assert [item.prompt for item in task.questions] == ["第一", "综合题"]
    assert generation.origin(task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")
    assert text_generator.calls == [
        "维度：信息意识\n表述：能识别信息\n维度：计算思维\n表述：  能分解步骤  \n没有指定题型和数量。"
    ]
    assert questions.calls == []
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能识别信息"
    assert base.retrieve_lesson("人教版", "必修一", "信息系统的组成").lesson_text == "课时原文"


def test_a_stage_origin_is_stored_as_given():
    _base, objectives = prepared_objectives()
    saved = objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0]
    generation = TaskGeneration(
        objectives, TaskCatalog(), ScriptedGenerator(), ScriptedTextGenerator()
    )

    task = generation.generate_from_objectives((saved,), StageOrigin("高中"))

    assert generation.origin(task.task_id) == StageOrigin("高中")


def test_no_objectives_or_no_text_generator_does_not_call_the_model():
    _base, objectives = prepared_objectives()
    text_generator = ScriptedTextGenerator()
    generation = TaskGeneration(
        objectives, TaskCatalog(), ScriptedGenerator(), text_generator
    )
    bare = TaskGeneration(objectives, TaskCatalog(), ScriptedGenerator())

    with pytest.raises(Rejected):
        generation.generate_from_objectives((), LessonOrigin("人教版", "必修一", "信息系统的组成"))
    with pytest.raises(Rejected):
        bare.generate_from_objectives(
            objectives.lesson_objectives("人教版", "必修一", "信息系统的组成"),
            LessonOrigin("人教版", "必修一", "信息系统的组成"),
        )

    assert text_generator.calls == []


def test_a_bad_reply_does_not_create_a_task_or_an_origin():
    _base, objectives = prepared_objectives()
    catalog = TaskCatalog()
    text_generator = ScriptedTextGenerator()
    text_generator.reply = "```"
    generation = TaskGeneration(objectives, catalog, ScriptedGenerator(), text_generator)
    saved = objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")

    with pytest.raises(Rejected):
        generation.generate_from_objectives(
            saved, LessonOrigin("人教版", "必修一", "信息系统的组成")
        )

    assert catalog._tasks == {}
    assert generation.origin("task-1") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_objective_generation_record.py -v`

Expected: FAIL because `TaskGeneration` has no `generate_from_objectives`

- [ ] **Step 3: Write minimal implementation**

Add this method to `TaskGeneration` after `generate_from_text`:

```python
def generate_from_objectives(self, objectives: tuple[Objective, ...], origin: LessonOrigin | StageOrigin) -> Task:
    from scaffolding.text_generation import parse_text_task

    if self._text_generator is None:
        raise Rejected("there is no text generator")
    if not objectives:
        raise Rejected("there is no objective record to generate from")
    lines = []
    for item in objectives:
        lines.append("维度：" + item.dimension)
        lines.append("表述：" + item.statement)
    lines.append("没有指定题型和数量。")
    reply = self._text_generator.generate("\n".join(lines))
    task = self._tasks.create(parse_text_task(reply))
    self._origins[task.task_id] = origin
    return task
```

The import stays inside the method. Do not change `generate_from_text`, `generate_lesson`, or `generate_stage`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_objective_generation_record.py tests/test_text_generation_record.py tests/test_task_generation.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

Run the full suite once. Then:

```powershell
git add src/scaffolding/generation.py tests/test_objective_generation_record.py
git commit -m "feat: create an unpublished task from saved objectives"
```

---

### Task 2: 显示按钮并报告失败

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Test: `tests/test_teacher_objective_generation_page.py`

**Interfaces:**
- Consumes: `generate_from_objectives(objectives, origin)`。`tests.teacher_objectives_helpers.form`、`make_page`、`text`。`tests.test_text_generation_record.ScriptedTextGenerator`。
- Produces: 已有目标时出现「按目标生成」。失败时状态 200，正文含「生成失败，没有创建任务」。成功时返回现有任务页；成功断言在 Task 3。

- [ ] **Step 1: Write the failing test**

Create `tests/test_teacher_objective_generation_page.py`:

```python
from scaffolding.generation import TaskGeneration
from scaffolding.knowledge import KnowledgeBase
from scaffolding.objectives import ObjectiveDraft
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import response_for
from tests.generation_helpers import ScriptedGenerator
from tests.objective_helpers import ScriptedExtractor, sample_base
from tests.teacher_objectives_helpers import form, make_page, text
from tests.test_text_generation_record import ScriptedTextGenerator


def _lesson(**extra):
    fields = {
        "mode": "课时",
        "version": "人教版",
        "volume": "必修一",
        "lesson": "信息系统的组成",
    }
    fields.update(extra)
    return form(**fields)


def _ready(generator=None, statements=("能识别信息", "能分解步骤")):
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    extractor.lesson_results = tuple(
        ObjectiveDraft(dimension, statement, retrieval.lesson_source)
        for dimension, statement in zip(("信息意识", "计算思维"), statements)
    )
    catalog = TaskCatalog()
    page, objectives = make_page(base, extractor, catalog)
    if generator is not None:
        page.generation = TaskGeneration(
            objectives, catalog, ScriptedGenerator(), generator
        )
    extracted = text(response_for(page, "POST", "/objectives", _lesson(action="提炼")))
    return page, generator, catalog, extracted


def test_the_button_appears_only_beside_saved_objectives():
    page, _generator, _catalog, extracted = _ready(None, statements=("<需求", "能分解步骤"))

    opened = text(response_for(page, "GET", "/objectives", ""))
    viewed = text(response_for(page, "POST", "/objectives", _lesson(action="查看")))
    edited = text(response_for(page, "POST", "/objectives", _lesson(
        objective="objective-1", statement="能认出信息", action="修改"
    )))
    listed = text(response_for(page, "GET", "/", ""))

    assert 'value="按目标生成"' in extracted
    assert extracted.index("&lt;需求") < extracted.index('value="按目标生成"')
    assert "<需求" not in extracted
    assert "按目标生成" not in opened
    assert viewed.count('value="按目标生成"') == 1
    assert viewed.index("能分解步骤") < viewed.index('value="按目标生成"')
    assert '<input type="hidden" name="mode" value="课时">' in viewed
    assert '<input type="hidden" name="lesson" value="信息系统的组成">' in viewed
    assert "</form>" in viewed.split('value="按目标生成"')[0]
    assert 'href="/generation">生成</a>' in viewed
    assert 'value="按目标生成"' in edited
    assert "能认出信息" in edited
    assert 'href="/generation">生成</a>' not in listed
    assert "按目标生成" not in listed


def test_removing_the_last_objective_removes_the_button():
    page, _generator, _catalog, _extracted = _ready(ScriptedTextGenerator())

    remaining = text(response_for(page, "POST", "/objectives", _lesson(
        objective="objective-1", action="删除"
    )))
    gone = text(response_for(page, "POST", "/objectives", _lesson(
        objective="objective-2", action="删除"
    )))

    assert 'value="按目标生成"' in remaining
    assert "能分解步骤" in remaining
    assert 'value="按目标生成"' not in gone


def test_failures_keep_the_query_and_do_not_call_the_model():
    generator = ScriptedTextGenerator()
    page, _generator, catalog, _extracted = _ready(generator)
    idle = ScriptedGenerator()
    bare_extractor = ScriptedExtractor()
    bare, _bare_objectives = make_page(sample_base(), bare_extractor)
    bare_retrieval = bare.knowledge.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    bare_extractor.lesson_results = (
        ObjectiveDraft("信息意识", "能识别信息", bare_retrieval.lesson_source),
    )
    response_for(bare, "POST", "/objectives", _lesson(action="提炼"))

    absent = text(response_for(page, "POST", "/objectives", form(
        mode="课时", version="人教版", volume="必修一", lesson="没有这一课", action="按目标生成"
    )))
    missing_record = response_for(bare, "POST", "/objectives", _lesson(action="按目标生成"))
    page.generation = TaskGeneration(page.objectives, catalog, idle)
    missing_generator = response_for(page, "POST", "/objectives", _lesson(action="按目标生成"))

    assert "生成失败，没有创建任务" in absent
    assert "没有检索到资料" not in absent
    assert 'value="按目标生成"' not in absent
    assert "课时原文" not in absent
    assert generator.calls == []
    assert missing_record.status == 200
    assert "生成失败，没有创建任务" in text(missing_record)
    assert "能识别信息" in text(missing_record)
    assert "课时原文" in text(missing_record)
    assert missing_generator.status == 200
    assert "生成失败，没有创建任务" in text(missing_generator)
    assert idle.calls == []

    page.generation = TaskGeneration(page.objectives, catalog, ScriptedGenerator(), generator)
    sent = "维度：信息意识\n表述：能识别信息\n维度：计算思维\n表述：能分解步骤\n没有指定题型和数量。"
    generator.error = RuntimeError("boom")
    failed = response_for(page, "POST", "/objectives", _lesson(action="按目标生成"))
    generator.error = None
    generator.reply = "```"
    rejected = response_for(page, "POST", "/objectives", _lesson(action="按目标生成"))
    before = len(generator.calls)
    incomplete = response_for(page, "POST", "/objectives", form(
        mode="课时", version="   ", volume="必修一", lesson="信息系统的组成", action="按目标生成"
    ))
    unknown = text(response_for(page, "POST", "/objectives", _lesson(action="发布")))
    assert len(generator.calls) == before
    page.knowledge = KnowledgeBase()
    kept = text(response_for(page, "POST", "/objectives", _lesson(action="查看")))
    empty = text(response_for(page, "POST", "/objectives", _lesson(action="按目标生成")))

    assert failed.status == 200
    assert "生成失败，没有创建任务" in text(failed)
    assert "能识别信息" in text(failed)
    assert "课时原文" in text(failed)
    assert rejected.status == 200
    assert "生成失败，没有创建任务" in text(rejected)
    assert list(catalog._tasks) == []
    assert generator.calls[0] == sent
    assert generator.calls[1] == sent
    assert incomplete.status == 200
    assert "先填完整再查询" in text(incomplete)
    assert "生成失败，没有创建任务" not in unknown
    assert "课时原文" not in unknown
    assert "没有检索到资料" in kept
    assert 'value="按目标生成"' in kept
    assert "能识别信息" in kept
    assert "生成失败，没有创建任务" in empty
    assert "没有检索到资料" not in empty
    assert "能识别信息" in empty
    assert "课时原文" not in empty
    assert generator.calls[2] == sent
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_objective_generation_page.py -v`

Expected: FAIL because the objectives page has no 「按目标生成」 and does not report 「生成失败，没有创建任务」

- [ ] **Step 3: Write minimal implementation**

In `apply_objectives`, recognize the new action before the incomplete-query return is skipped. The action tuple becomes:

```python
if action not in ("查看", "提炼", "修改", "删除", "按目标生成"):
    return self.open_objectives()
```

After `query is None` is handled, add:

```python
if action == "按目标生成":
    return _generate_from_objectives(self, query)
```

Add this function beside `_extract_objectives`:

```python
def _generate_from_objectives(page, query) -> str:
    saved = _saved(page, query)
    if saved == () or page.generation is None:
        return _render_objectives(page, query, "生成失败，没有创建任务")
    if query[0] == "课时":
        origin = LessonOrigin(query[1], query[2], query[3])
    else:
        origin = StageOrigin(query[1])
    try:
        task = page.generation.generate_from_objectives(saved, origin)
    except Exception:
        return _render_objectives(page, query, "生成失败，没有创建任务")
    return _render(page, task.task_id)
```

In `_render_objectives`, after the objective articles and before `_task_links`, add:

```python
if objectives:
    parts.append(
        "<form method=\"post\" action=\"" + action + "\">"
        + _hidden_query(query)
        + "<button type=\"submit\" name=\"action\" value=\"按目标生成\">按目标生成</button></form>"
    )
```

`LessonOrigin` and `StageOrigin` are already imported in this file.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_objective_generation_page.py tests/test_teacher_objectives_open.py tests/test_teacher_objectives_view.py tests/test_teacher_text_generation_page.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

Run the full suite once. Then:

```powershell
git add src/scaffolding/teacher_page.py tests/test_teacher_objective_generation_page.py
git commit -m "feat: offer objective generation on the teacher page"
```

---

### Task 3: 显示按目标生成的任务

**Files:**
- Test: `tests/test_teacher_objective_generation_success.py`
- Modify: `src/scaffolding/teacher_page.py`

**Interfaces:**
- Consumes: Task 2 的「按目标生成」。`generate_from_objectives`。`generate_from_text`。`dumped`。
- Produces: 成功响应是未发布任务页。任务带当前查询的来源。目标页链接列出它。按文字生成的任务不在这些链接里。

- [ ] **Step 1: Write the failing test**

Create `tests/test_teacher_objective_generation_success.py`:

```python
from scaffolding.generation import LessonOrigin, StageOrigin, TaskGeneration
from scaffolding.objectives import ObjectiveDraft
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import response_for
from tests.generation_helpers import ScriptedGenerator
from tests.objective_helpers import ScriptedExtractor, sample_base
from tests.teacher_objectives_helpers import form, make_page, text
from tests.test_text_generation_record import ScriptedTextGenerator
from tests.text_generation_helpers import choice, dumped, opened


def test_objective_generation_opens_the_new_task_and_records_the_query_origin():
    base = sample_base()
    lesson = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    stage = base.retrieve_stage("高中")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (
        ObjectiveDraft("信息意识", "能识别信息", lesson.lesson_source),
    )
    extractor.stage_results = (
        ObjectiveDraft("信息社会责任", "遵守规范", stage.standard_source),
    )
    catalog = TaskCatalog()
    questions = ScriptedGenerator()
    text_generator = ScriptedTextGenerator()
    text_generator.reply = dumped(
        reading={"单选": 2, "多选": "未指定", "判断": 0, "综合": "未指定"},
        questions={
            "单选": [choice("第一"), choice("第二")],
            "多选": [],
            "判断": [],
            "综合": [opened("综合题")],
        },
    )
    page, objectives = make_page(base, extractor, catalog)
    generation = TaskGeneration(objectives, catalog, questions, text_generator)
    page.generation = generation
    response_for(page, "POST", "/objectives", form(
        mode="课时", version="人教版", volume="必修一", lesson="信息系统的组成", action="提炼"
    ))
    response_for(page, "POST", "/objectives", form(
        mode="学段", stage="高中", action="提炼"
    ))
    loose = generation.generate_from_text("出一道题")

    opened = text(response_for(page, "POST", "/objectives", form(
        mode="课时", version="人教版", volume="必修一", lesson="信息系统的组成", action="按目标生成"
    )))
    again = text(response_for(page, "POST", "/objectives", form(
        mode="课时", version="人教版", volume="必修一", lesson="信息系统的组成", action="按目标生成"
    )))
    listed = text(response_for(page, "GET", "/", ""))
    viewed = text(response_for(page, "POST", "/objectives", form(
        mode="课时", version="人教版", volume="必修一", lesson="信息系统的组成", action="查看"
    )))
    staged = text(response_for(page, "POST", "/objectives", form(
        mode="学段", stage="高中", action="按目标生成"
    )))
    stage_view = text(response_for(page, "POST", "/objectives", form(
        mode="学段", stage="高中", action="查看"
    )))

    assert opened.index("第一") < opened.index("第二") < opened.index("综合题")
    assert "未发布" in opened
    assert "生成失败，没有创建任务" not in opened
    assert text_generator.calls[1:] == [
        "维度：信息意识\n表述：能识别信息\n没有指定题型和数量。",
        "维度：信息意识\n表述：能识别信息\n没有指定题型和数量。",
        "维度：信息社会责任\n表述：遵守规范\n没有指定题型和数量。",
    ]
    assert questions.calls == []
    assert generation.origin("task-2") == LessonOrigin("人教版", "必修一", "信息系统的组成")
    assert generation.origin("task-3") == LessonOrigin("人教版", "必修一", "信息系统的组成")
    assert generation.origin(loose.task_id) is None
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能识别信息"
    assert "task-2" in listed and "task-3" in listed
    assert "task-2" in viewed and "task-3" in viewed
    assert loose.task_id not in viewed
    assert "未发布" in again
    assert generation.origin("task-4") == StageOrigin("高中")
    assert "task-4" in staged
    assert "task-4" in stage_view
    assert "task-2" not in stage_view
```

`generate_from_text` runs before the objective posts, so its task is `task-1`. The two lesson posts are `task-2` and `task-3`. The stage post is `task-4`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_objective_generation_success.py -v`

Expected: FAIL if the success path is missing. If Task 2 already returns the task page and stores the origin, this test PASSes immediately. Keep every assertion.

- [ ] **Step 3: Write minimal implementation**

`_generate_from_objectives` must return the existing task page after a successful call:

```python
def _generate_from_objectives(page, query) -> str:
    saved = _saved(page, query)
    if saved == () or page.generation is None:
        return _render_objectives(page, query, "生成失败，没有创建任务")
    if query[0] == "课时":
        origin = LessonOrigin(query[1], query[2], query[3])
    else:
        origin = StageOrigin(query[1])
    try:
        task = page.generation.generate_from_objectives(saved, origin)
    except Exception:
        return _render_objectives(page, query, "生成失败，没有创建任务")
    return _render(page, task.task_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_objective_generation_success.py tests/test_teacher_objective_generation_page.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

Run the full suite once. If `teacher_page.py` has no new change, commit the test file alone.

```powershell
git add tests/test_teacher_objective_generation_success.py src/scaffolding/teacher_page.py
git commit -m "feat: show a task generated from saved objectives"
```

---

### Task 4: 课堂验收

**Files:**
- Create: `tests/test_teacher_objective_generation_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-22-teacher-objective-generation-design.md`

**Interfaces:**
- Consumes: `Classroom.response_for`。`production_classroom`。`ModelTextGenerator`。Task 2 的按钮和 Task 3 的成功响应。
- Produces: 课堂前缀下可以按目标生成。正式运行的文字生成方仍是 `ModelTextGenerator`，构造时不调用补全。

- [ ] **Step 1: Write the failing test**

If `docs/superpowers/specs/2026-10-22-teacher-objective-generation-design.md` is missing in this worktree, copy `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-22-teacher-objective-generation-design.md` unchanged. Do not edit it.

Create `tests/test_teacher_objective_generation_acceptance.py`:

```python
from pathlib import Path

from scaffolding.classroom import Classroom, production_classroom, response_for, serve
from scaffolding.generation import TaskGeneration
from scaffolding.model_text import ModelTextGenerator
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.tasks import TaskCatalog
from tests.classroom_helpers import text
from tests.generation_helpers import ScriptedGenerator
from tests.objective_helpers import ScriptedExtractor, sample_base
from tests.teacher_objectives_helpers import form
from tests.test_text_generation_record import ScriptedTextGenerator


def test_the_classroom_hides_objective_generation_until_objectives_exist():
    room = Classroom(TaskCatalog(), ScriptedDecisionAgent(), ScriptedScaffoldAgent())

    home = text(response_for(room, "GET", "/", "", 0))
    listed = text(response_for(room, "GET", "/teacher", "", 0))
    objectives = text(response_for(room, "GET", "/teacher/objectives/", "", 0))
    student = response_for(room, "GET", "/student/objectives", "", 1)

    assert "按目标生成" not in home
    assert "按目标生成" not in listed
    assert 'href="/teacher/objectives"' in listed
    assert 'href="/teacher/generation">生成</a>' in objectives
    assert "按目标生成" not in objectives
    assert student.status == 404
    assert "任务不存在" in text(student)


def test_the_classroom_generates_from_saved_objectives():
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (
        ObjectiveDraft("信息意识", "能识别信息", retrieval.lesson_source),
    )
    catalog = TaskCatalog()
    objectives = ObjectiveCatalog(base, extractor)
    objectives.extract_lesson("人教版", "必修一", "信息系统的组成")
    generation = TaskGeneration(
        objectives, catalog, ScriptedGenerator(), ScriptedTextGenerator()
    )
    room = Classroom(
        catalog,
        ScriptedDecisionAgent(),
        ScriptedScaffoldAgent(),
        base,
        objectives,
        generation,
    )

    opened = text(response_for(room, "POST", "/teacher/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        action="按目标生成",
    ), 0))
    viewed = text(response_for(room, "POST", "/teacher/objectives?ready=1", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        action="查看",
    ), 0))

    assert "未发布" in opened
    assert "task-1" in viewed
    assert 'action="/teacher/objectives"' in viewed
    assert 'value="按目标生成"' in viewed


def test_production_still_prepares_the_text_generator_without_calling_it():
    def post(_request):
        raise AssertionError("network")

    room = production_classroom(post=post)

    assert isinstance(room.generation._text_generator, ModelTextGenerator)
    assert room.teacher.generation is room.generation
    assert Path("docs/superpowers/specs/2026-10-22-teacher-objective-generation-design.md").is_file()
    assert callable(serve)
    assert callable(production_classroom)
```

Do not change `production_classroom`. No test calls `serve`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_objective_generation_acceptance.py -v`

Expected: FAIL because the spec file is missing, or the classroom objectives page does not yet show the button. Copy the spec before this run if it is missing, so the remaining failure is the product behavior.

- [ ] **Step 3: Write minimal implementation**

No new production wiring. The button and `generate_from_objectives` already come from Tasks 1–3. The spec file in this commit must be the unchanged copy from `4fd1650`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS. The count is the previous suite plus the new objective-generation tests. No test calls `serve`.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_teacher_objective_generation_acceptance.py docs/superpowers/specs/2026-10-22-teacher-objective-generation-design.md
git commit -m "test: accept objective generation in the classroom"
```
