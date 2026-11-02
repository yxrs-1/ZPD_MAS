# 模型提炼目标 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 DeepSeek 按一次知识库检索交回目标草稿，并仍由现有目标库丢掉不合格项后保存。

**Architecture:** 新的 `model_extractor.py` 提供解析、提示词和模型提炼方。`ObjectiveCatalog` 不改，只把模型提炼方当作原来的提炼方传入。DeepSeek 请求复用 `deepseek_complete`。测试注入事先写好的正文，不打开套接字。

**Tech Stack:** Python 3.14，pytest 9，标准库。实现从 `origin/main` 建工作区。规格在本地 `master` 的 `77fc49d`，文件是 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-19-model-objective-extractor-design.md`。工作区里若没有这份规格，从该提交原样复制，不要改写。测试命令是 `.\.venv\Scripts\python.exe -m pytest`。PowerShell 下不要使用 `&&` 或 bash heredoc；提交用 `git commit -m "message"`。不要改 git config，不要 push。

## Global Constraints

- 本计划只把提炼方换成 DeepSeek。任务生成方、决策智能体和支架智能体不在这里。
- 已有记录、空检索、不合格目标的丢弃、标识分配和保存仍按四维教学目标规格执行。
- 测试不访问网络。
- 模型提炼方实现 `extract(retrieval)`。它不保存目标，不分配标识，不改知识库，也不读取密钥。
- 完成函数是已有的 `deepseek_complete`。测试换上返回事先写好正文的函数。不修改 `model_generator.py`。
- 已经有记录时不调用完成函数。这时即使检索没有资料，也仍然是拒绝。还没有记录且检索没有资料时，结果为空，不调用完成函数，也不保存。
- 系统消息写明 JSON 形状、四个维度和来源规则。指定课时时来源可以是「教材」或「课标」。只给学段时来源只能是「课标」。
- 用户消息只写这次检索的原文和来源。指定课时时包含课时原文、教材来源、课标全文和课标来源。只给学段时只有课标全文和课标来源。
- 正文去掉前后空白后必须直接是约定的 JSON。顶层只有「目标」。每条的键正好是维度、表述、来源，三个值都是字符串。不是字符串也算解析失败。
- 「教材」对上这次的教材来源，「课标」对上这次的课标来源。草稿里的来源就是这次检索交回的来源对象。数组先后交给现有筛选。
- 解析失败抛出目标库的 `Rejected`。完成函数抛出的异常原样传出。不保存，已有记录保持不变。完成函数只调用一次，不重试。
- 维度不在四维之中、表述为空白、来源不是「教材」或「课标」、这次没有这种来源，或「目标」是空数组时，不是调用失败。不合格的丢掉，合格的按先后保存。一条合格的都没有时不保存，不分配标识，之后可以再提炼。
- 空白不算已填写。
- 不修改 `objectives.py`、`knowledge.py`、`model_generator.py`、`generation.py`、`records.py`、`tasks.py`、`session.py`。

## File Map

- Create: `src/scaffolding/model_extractor.py` — 解析正文、组成两条消息、模型提炼方。
- Create: `tests/test_model_objective_parsing.py`
- Create: `tests/test_model_objective_prompt.py`
- Create: `tests/test_model_objective_extraction.py`
- Create: `tests/test_model_objective_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-19-model-objective-extractor-design.md`
- Do not modify: `src/scaffolding/objectives.py`、`knowledge.py`、`model_generator.py`、`generation.py`、`records.py`、`tasks.py`、`session.py`

---

### Task 1: 把模型正文解析成目标草稿

**Files:**
- Create: `src/scaffolding/model_extractor.py`
- Test: `tests/test_model_objective_parsing.py`

**Interfaces:**
- Consumes: `Rejected`、`ObjectiveDraft`，来自 `scaffolding.objectives`。`LessonRetrieval`、`LessonSource`、`StageRetrieval`，来自 `scaffolding.knowledge`。
- Produces: `parse_objectives(text: str, retrieval: LessonRetrieval | StageRetrieval) -> tuple[ObjectiveDraft, ...]`。合格形状按数组先后返回草稿。「教材」且这次有教材来源时，来源是 `retrieval.lesson_source`。「课标」时，来源是 `retrieval.standard_source`。其余来源字，以及只给学段时的「教材」，草稿来源是 `LessonSource(标签, 标签, 标签, 标签, 标签)`，交给现有筛选丢掉。空数组返回 `()`。形状不对、代码块、值不是字符串，或 `text` 不是字符串时，抛出目标库的 `Rejected`。表述为空白或维度不在四维之中时仍返回草稿。

- [ ] **Step 1: Write the failing test**

Create `tests/test_model_objective_parsing.py`:

```python
import json

import pytest

from scaffolding.knowledge import CurriculumStandard, LessonSource
from scaffolding.model_extractor import parse_objectives
from scaffolding.objectives import ObjectiveDraft, Rejected
from tests.objective_helpers import sample_base


def _retrieval():
    return sample_base().retrieve_lesson("人教版", "必修一", "信息系统的组成")


def _body(items: list[dict] | None = None, **extra) -> str:
    body = {
        "目标": [
            {"维度": "信息意识", "表述": "能识别信息", "来源": "教材"},
            {"维度": "其他", "表述": "  ", "来源": "课标"},
        ]
    }
    if items is not None:
        body["目标"] = items
    body.update(extra)
    return json.dumps(body, ensure_ascii=False)


def test_drafts_keep_array_order_and_use_retrieval_sources():
    retrieval = _retrieval()

    assert parse_objectives("\n" + _body() + " ", retrieval) == (
        ObjectiveDraft("信息意识", "能识别信息", retrieval.lesson_source),
        ObjectiveDraft("其他", "  ", retrieval.standard_source),
    )


def test_an_empty_array_returns_no_drafts():
    assert parse_objectives(_body(items=[]), _retrieval()) == ()


def test_an_unmapped_label_is_returned_for_the_existing_filter():
    retrieval = _retrieval()
    stage = sample_base()
    stage.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    stage_retrieval = stage.retrieve_stage("初中")

    assert parse_objectives(
        _body(items=[{"维度": "信息意识", "表述": "其他来源", "来源": "其他"}]),
        retrieval,
    ) == (ObjectiveDraft("信息意识", "其他来源", LessonSource("其他", "其他", "其他", "其他", "其他")),)
    assert parse_objectives(
        _body(items=[{"维度": "信息意识", "表述": "没有教材", "来源": "教材"}]),
        stage_retrieval,
    ) == (ObjectiveDraft("信息意识", "没有教材", LessonSource("教材", "教材", "教材", "教材", "教材")),)


def test_a_code_fence_wrong_shape_or_non_string_is_rejected():
    retrieval = _retrieval()
    extra = json.loads(_body())
    extra["其他"] = []
    missing = {"目标": [{"维度": "信息意识", "表述": "能识别信息"}]}
    number = {"目标": [{"维度": "信息意识", "表述": "能识别信息", "来源": 1}]}
    for text in (
        "```json\n" + _body() + "\n```",
        json.dumps(extra, ensure_ascii=False),
        json.dumps(missing, ensure_ascii=False),
        json.dumps(number, ensure_ascii=False),
        None,
    ):
        with pytest.raises(Rejected):
            parse_objectives(text, retrieval)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_objective_parsing.py -v`

Expected: FAIL because `scaffolding.model_extractor` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `src/scaffolding/model_extractor.py`:

```python
import json

from scaffolding.knowledge import LessonRetrieval, LessonSource, StageRetrieval
from scaffolding.objectives import ObjectiveDraft, Rejected


_ITEM_KEYS = {"维度", "表述", "来源"}


def parse_objectives(text: str, retrieval: LessonRetrieval | StageRetrieval) -> tuple[ObjectiveDraft, ...]:
    if not isinstance(text, str):
        raise Rejected("model reply is not the objective JSON")
    try:
        body = json.loads(text.strip())
    except json.JSONDecodeError as error:
        raise Rejected("model reply is not the objective JSON") from error
    if not isinstance(body, dict) or set(body) != {"目标"} or not isinstance(body["目标"], list):
        raise Rejected("model reply is not the objective JSON")
    drafts = []
    for item in body["目标"]:
        if not isinstance(item, dict) or set(item) != _ITEM_KEYS:
            raise Rejected("model reply is not the objective JSON")
        if any(type(item[key]) is not str for key in _ITEM_KEYS):
            raise Rejected("model reply is not the objective JSON")
        drafts.append(ObjectiveDraft(item["维度"], item["表述"], _source(item["来源"], retrieval)))
    return tuple(drafts)


def _source(label: str, retrieval: LessonRetrieval | StageRetrieval):
    if label == "教材" and isinstance(retrieval, LessonRetrieval):
        return retrieval.lesson_source
    if label == "课标":
        return retrieval.standard_source
    return LessonSource(label, label, label, label, label)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_objective_parsing.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/model_extractor.py tests/test_model_objective_parsing.py
git commit -m "feat: parse model objective JSON into drafts"
```

---

### Task 2: 组成系统消息和用户消息

**Files:**
- Modify: `src/scaffolding/model_extractor.py`
- Test: `tests/test_model_objective_prompt.py`

**Interfaces:**
- Consumes: `LessonRetrieval`、`StageRetrieval`。
- Produces: `build_messages(retrieval: LessonRetrieval | StageRetrieval) -> tuple[dict[str, str], dict[str, str]]`。第一条是 `role="system"`，第二条是 `role="user"`。

- [ ] **Step 1: Write the failing test**

Create `tests/test_model_objective_prompt.py`:

```python
from scaffolding.knowledge import CurriculumStandard
from scaffolding.model_extractor import build_messages
from tests.objective_helpers import sample_base


def test_a_lesson_prompt_contains_both_texts_and_both_sources():
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")

    system, user = build_messages(retrieval)

    assert system == {
        "role": "system",
        "content": (
            "你是高中信息科技教师。只回一份 JSON 对象，不要代码块，不要其他文字。\n"
            "JSON 有且只有一个键：目标。它的值是数组。数组可以是空的。\n"
            "每条目标都有且只有这些键：维度、表述、来源。三个值都是字符串。\n"
            "维度只能是信息意识、计算思维、数字化学习与创新、信息社会责任。\n"
            "来源写成「教材」或「课标」，并且必须是这次交回的来源。\n"
            "表述不能为空白。空白不算已填写。"
        ),
    }
    assert user == {
        "role": "user",
        "content": (
            "教材原文：\n"
            "课时原文\n"
            "\n"
            "教材来源：版本 人教版，册次 必修一，课时 信息系统的组成，学段 高中，页码 12-15\n"
            "\n"
            "课标原文：\n"
            "课标全文\n"
            "\n"
            "课标来源：名称 普通高中信息科技课程标准，学段 高中，条款号 1.1.2，现行课标"
        ),
    }
    assert base.get_lesson("人教版", "必修一", "信息系统的组成").text == "课时原文"


def test_a_stage_prompt_contains_only_the_standard():
    base = sample_base()
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    retrieval = base.retrieve_stage("初中")

    system, user = build_messages(retrieval)

    assert system["role"] == "system"
    assert "来源只能写成「课标」，并且必须是这次交回的课标来源。" in system["content"]
    assert "来源写成「教材」或「课标」" not in system["content"]
    assert user == {
        "role": "user",
        "content": (
            "课标原文：\n"
            "初中课标全文\n"
            "\n"
            "课标来源：名称 义务教育信息科技课程标准，学段 初中，条款号 2.1，现行课标"
        ),
    }
    assert "教材原文" not in user["content"]
    assert "课时原文" not in user["content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_objective_prompt.py -v`

Expected: FAIL because `build_messages` is not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `src/scaffolding/model_extractor.py`:

```python
_LESSON_SYSTEM = (
    "你是高中信息科技教师。只回一份 JSON 对象，不要代码块，不要其他文字。\n"
    "JSON 有且只有一个键：目标。它的值是数组。数组可以是空的。\n"
    "每条目标都有且只有这些键：维度、表述、来源。三个值都是字符串。\n"
    "维度只能是信息意识、计算思维、数字化学习与创新、信息社会责任。\n"
    "来源写成「教材」或「课标」，并且必须是这次交回的来源。\n"
    "表述不能为空白。空白不算已填写。"
)

_STAGE_SYSTEM = (
    "你是高中信息科技教师。只回一份 JSON 对象，不要代码块，不要其他文字。\n"
    "JSON 有且只有一个键：目标。它的值是数组。数组可以是空的。\n"
    "每条目标都有且只有这些键：维度、表述、来源。三个值都是字符串。\n"
    "维度只能是信息意识、计算思维、数字化学习与创新、信息社会责任。\n"
    "来源只能写成「课标」，并且必须是这次交回的课标来源。\n"
    "表述不能为空白。空白不算已填写。"
)


def build_messages(retrieval: LessonRetrieval | StageRetrieval) -> tuple[dict[str, str], dict[str, str]]:
    if isinstance(retrieval, LessonRetrieval):
        lesson = retrieval.lesson_source
        standard = retrieval.standard_source
        content = (
            "教材原文：\n"
            + retrieval.lesson_text
            + "\n\n教材来源：版本 "
            + lesson.version
            + "，册次 "
            + lesson.volume
            + "，课时 "
            + lesson.lesson
            + "，学段 "
            + lesson.stage
            + "，页码 "
            + lesson.pages
            + "\n\n课标原文：\n"
            + retrieval.standard_text
            + "\n\n课标来源：名称 "
            + standard.name
            + "，学段 "
            + standard.stage
            + "，条款号 "
            + standard.clauses
            + "，现行课标"
        )
        return ({"role": "system", "content": _LESSON_SYSTEM}, {"role": "user", "content": content})
    standard = retrieval.standard_source
    content = (
        "课标原文：\n"
        + retrieval.standard_text
        + "\n\n课标来源：名称 "
        + standard.name
        + "，学段 "
        + standard.stage
        + "，条款号 "
        + standard.clauses
        + "，现行课标"
    )
    return ({"role": "system", "content": _STAGE_SYSTEM}, {"role": "user", "content": content})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_objective_prompt.py tests/test_model_objective_parsing.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/model_extractor.py tests/test_model_objective_prompt.py
git commit -m "feat: prompt DeepSeek from one retrieval"
```

---

### Task 3: 用模型正文保存合格目标

**Files:**
- Modify: `src/scaffolding/model_extractor.py`
- Test: `tests/test_model_objective_extraction.py`

**Interfaces:**
- Consumes: `parse_objectives`、`build_messages`。`ObjectiveCatalog`、`Rejected`。`KnowledgeBase.retrieve_lesson`。
- Produces: `ModelObjectiveExtractor(complete)`。`extract(self, retrieval) -> tuple[ObjectiveDraft, ...]`。它把 `build_messages` 的返回值调用一次 `complete`，再交给 `parse_objectives`。`complete` 抛出的异常原样传出。

- [ ] **Step 1: Write the failing test**

Create `tests/test_model_objective_extraction.py`:

```python
import json

import pytest

from scaffolding.knowledge import CurriculumStandard, KnowledgeBase, TextbookLesson
from scaffolding.model_extractor import ModelObjectiveExtractor, build_messages
from scaffolding.objectives import ObjectiveCatalog, Rejected
from tests.objective_helpers import sample_base


class RecordingComplete:
    def __init__(self, text: str = "", error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.calls = []

    def __call__(self, messages):
        self.calls.append(messages)
        if self.error is not None:
            raise self.error
        return self.text


class EmptyAfterSave(KnowledgeBase):
    def __init__(self) -> None:
        super().__init__()
        self.saved = False

    def retrieve_lesson(self, version: str, volume: str, lesson: str):
        if self.saved:
            return None
        return super().retrieve_lesson(version, volume, lesson)


def _reply(items: list[dict] | None = None) -> str:
    if items is None:
        items = [
            {"维度": "信息意识", "表述": "能识别信息", "来源": "教材"},
            {"维度": "其他", "表述": "丢掉", "来源": "教材"},
            {"维度": "信息社会责任", "表述": " ", "来源": "课标"},
            {"维度": "计算思维", "表述": "能分解问题", "来源": "其他"},
            {"维度": "数字化学习与创新", "表述": "能选用工具", "来源": "课标"},
        ]
    return json.dumps({"目标": items}, ensure_ascii=False)


def _catalog(base: KnowledgeBase, complete: RecordingComplete) -> ObjectiveCatalog:
    return ObjectiveCatalog(base, ModelObjectiveExtractor(complete))


def test_a_mixed_reply_saves_only_valid_objectives_in_order():
    base = sample_base()
    stored = base.get_lesson("人教版", "必修一", "信息系统的组成")
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    complete = RecordingComplete(_reply())
    catalog = _catalog(base, complete)

    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")

    assert [item.objective_id for item in saved] == ["objective-1", "objective-2"]
    assert [item.statement for item in saved] == ["能识别信息", "能选用工具"]
    assert saved[0].source == retrieval.lesson_source
    assert saved[1].source == retrieval.standard_source
    assert complete.calls == [build_messages(retrieval)]
    assert base.get_lesson("人教版", "必修一", "信息系统的组成") is stored

    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    stage_retrieval = base.retrieve_stage("初中")
    stage_complete = RecordingComplete(_reply([
        {"维度": "信息意识", "表述": "没有教材", "来源": "教材"},
        {"维度": "信息社会责任", "表述": "遵守规范", "来源": "课标"},
    ]))
    stage_saved = ObjectiveCatalog(base, ModelObjectiveExtractor(stage_complete)).extract_stage("初中")
    assert [item.statement for item in stage_saved] == ["遵守规范"]
    assert stage_saved[0].source == stage_retrieval.standard_source
    assert stage_saved[0].objective_id == "objective-1"
    assert len(stage_complete.calls) == 1


def test_nothing_valid_allocates_no_id_and_can_run_again():
    base = sample_base()
    complete = RecordingComplete(_reply([]))
    catalog = _catalog(base, complete)

    assert catalog.extract_lesson("人教版", "必修一", "信息系统的组成") == ()
    complete.text = _reply([{"维度": "信息意识", "表述": "能识别信息", "来源": "教材"}])
    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")

    assert [item.objective_id for item in saved] == ["objective-1"]
    assert len(complete.calls) == 2


def test_a_bad_reply_or_completer_error_saves_nothing():
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    first = RecordingComplete(_reply([{"维度": "信息意识", "表述": "先保存", "来源": "教材"}]))
    catalog = _catalog(base, first)
    catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    fenced = RecordingComplete("```json\n" + _reply() + "\n```")
    separate = sample_base()
    fenced_catalog = _catalog(separate, fenced)

    with pytest.raises(Rejected):
        fenced_catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    failing = RecordingComplete(error=RuntimeError("down"))
    with pytest.raises(RuntimeError):
        _catalog(sample_base(), failing).extract_lesson("人教版", "必修一", "信息系统的组成")

    assert len(fenced.calls) == 1
    assert len(failing.calls) == 1
    assert fenced_catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "先保存"
    assert retrieval.lesson_text == "课时原文"


def test_existing_records_and_empty_retrievals_do_not_call_the_completer():
    base = EmptyAfterSave()
    base.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "课时原文"))
    base.add_standard(CurriculumStandard("普通高中信息科技课程标准", "高中", "1.1.2", "课标全文"))
    complete = RecordingComplete(_reply([{"维度": "信息意识", "表述": "能识别信息", "来源": "教材"}]))
    catalog = _catalog(base, complete)
    catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    base.saved = True

    with pytest.raises(Rejected):
        catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    assert catalog.extract_lesson("沪科教版", "必修一", "信息系统的组成") == ()
    assert len(complete.calls) == 1
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能识别信息"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_objective_extraction.py -v`

Expected: FAIL because `ModelObjectiveExtractor` is not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `src/scaffolding/model_extractor.py`:

```python
class ModelObjectiveExtractor:
    def __init__(self, complete) -> None:
        self._complete = complete

    def extract(self, retrieval: LessonRetrieval | StageRetrieval) -> tuple[ObjectiveDraft, ...]:
        return parse_objectives(self._complete(build_messages(retrieval)), retrieval)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_objective_extraction.py tests/test_model_objective_prompt.py tests/test_model_objective_parsing.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/model_extractor.py tests/test_model_objective_extraction.py
git commit -m "feat: extract objectives from a model reply"
```

---

### Task 4: 规格验收

**Files:**
- Create: `tests/test_model_objective_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-19-model-objective-extractor-design.md`

**Interfaces:**
- Consumes: Task 1 到 Task 3 的全部公开接口，以及已有的 `deepseek_complete`。规格文件来自 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-19-model-objective-extractor-design.md`，即本地 `master` 的 `77fc49d`。原样复制，不要改写。
- Produces: 验收测试。不新增生产行为。

- [ ] **Step 1: Write the failing test**

Create `tests/test_model_objective_acceptance.py`:

```python
import json
from pathlib import Path

import pytest

from scaffolding.knowledge import CurriculumStandard
from scaffolding.model_extractor import ModelObjectiveExtractor
from scaffolding.model_generator import DEEPSEEK_URL, deepseek_complete
from scaffolding.objectives import ObjectiveCatalog, Rejected
from tests.objective_helpers import sample_base


def _reply() -> str:
    return json.dumps(
        {"目标": [
            {"维度": "信息意识", "表述": "能识别信息", "来源": "教材"},
            {"维度": "其他", "表述": "丢掉", "来源": "课标"},
        ]},
        ensure_ascii=False,
    )


def test_model_objective_extractor_spec_is_in_the_workspace():
    spec = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "specs" / "2026-10-19-model-objective-extractor-design.md"
    assert spec.is_file()


def test_extraction_uses_one_reply_and_keeps_existing_objective_rules():
    base = sample_base()
    stored = base.get_lesson("人教版", "必修一", "信息系统的组成")
    calls = []

    def complete(messages):
        calls.append(messages)
        return _reply()

    catalog = ObjectiveCatalog(base, ModelObjectiveExtractor(complete))
    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")

    assert [item.objective_id for item in saved] == ["objective-1"]
    assert saved[0].statement == "能识别信息"
    assert saved[0].source == base.retrieve_lesson("人教版", "必修一", "信息系统的组成").lesson_source
    assert len(calls) == 1
    assert "课时原文" in calls[0][1]["content"]
    assert "课标全文" in calls[0][1]["content"]
    with pytest.raises(Rejected):
        catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    assert len(calls) == 1
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能识别信息"

    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    stage_calls = []

    def stage_complete(messages):
        stage_calls.append(messages)
        return json.dumps(
            {"目标": [{"维度": "信息社会责任", "表述": "遵守规范", "来源": "课标"}]},
            ensure_ascii=False,
        )

    stage_catalog = ObjectiveCatalog(base, ModelObjectiveExtractor(stage_complete))
    stage_saved = stage_catalog.extract_stage("初中")
    assert stage_saved[0].objective_id == "objective-1"
    assert stage_saved[0].source == base.retrieve_stage("初中").standard_source
    assert "教材原文" not in stage_calls[0][1]["content"]
    assert "来源只能写成「课标」" in stage_calls[0][0]["content"]

    sent = []

    def post(url, headers, payload):
        sent.append((url, headers, payload))
        return 200, {"choices": [{"message": {"content": _reply()}}]}

    assert deepseek_complete(calls[0], post=post, api_key="secret") == _reply()
    assert sent[0][0] == DEEPSEEK_URL
    assert sent[0][1]["Authorization"] == "Bearer secret"
    assert sent[0][2]["model"] == "deepseek-flash"
    assert sent[0][2]["stream"] is False
    assert sent[0][2]["thinking"] == {"type": "disabled"}
    assert "reasoning_effort" not in sent[0][2]
    assert base.get_lesson("人教版", "必修一", "信息系统的组成") is stored
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_objective_acceptance.py -v`

Expected: FAIL because the spec file is not in the worktree yet. If the spec file is already present and the other assertions fail, stop and report the failure. Do not change production code.

- [ ] **Step 3: Copy the spec and keep the test**

Copy `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-19-model-objective-extractor-design.md` to `docs/superpowers/specs/2026-10-19-model-objective-extractor-design.md` in the worktree. Do not edit the spec. Do not change production code.

- [ ] **Step 4: Run the full suite**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS, including the previous knowledge, objective, task, scaffolding, generation, and DeepSeek tests.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_model_objective_acceptance.py docs/superpowers/specs/2026-10-19-model-objective-extractor-design.md
git commit -m "test: accept DeepSeek objective extraction from a retrieval"
```
