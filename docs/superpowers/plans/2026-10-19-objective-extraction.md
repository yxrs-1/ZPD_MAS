# 四维教学目标 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从一次知识库检索中提炼四维教学目标并保存；教师只能改表述，也可以删除。再次提炼在记录还在时被拒绝。

**Architecture:** `ObjectiveCatalog` 调用已有的 `KnowledgeBase`，把检索结果交给可替换的提炼方。`select_objectives` 丢掉维度、表述或来源不合格的草稿，剩下的分配 `objective-N` 标识后按课时或学段保存。知识库的原文和来源不改。本计划不生成任务。

**Tech Stack:** Python 3.14，pytest 9，标准库。实现从 `origin/main` 建工作区。规格在 `master` 的 `5048602`。工作区里若没有规格文件，把 `docs/superpowers/specs/2026-10-19-objective-extraction-design.md` 从该提交原样复制进来，不要改写。测试命令是 `.\.venv\Scripts\python.exe -m pytest`。PowerShell 下不要使用 `&&` 或 bash heredoc；提交用 `git commit -m "message"`。不要改 git config，不要 push。

## Global Constraints

- 生成任务、发布和作答不在本计划里。
- 教材原文和课标来自知识库检索。提炼不访问网络，也不从文件现读。知识库里的原文和来源保持不变。
- 提炼方是一个可替换的接口。测试使用事先写好的提炼结果，不接真实模型。
- 课时记录按版本、册次、课时保存。学段记录按学段保存。同一学段的两种记录互不影响。
- 版本、册次、课时或学段的文字有一处不同，就是另一份记录。
- 一条目标记下标识、维度、表述和一处来源。标识在目标库内唯一，保存后不变。
- 维度是信息意识、计算思维、数字化学习与创新、信息社会责任之一。
- 教材来源是版本、册次、课时、学段、页码。课标来源是名称、学段、条款号，并标明现行。来源按这些内容的原文精确对应。
- 表述为空白的目标不合格。空白不算已填写。
- 已有记录时再次提炼被拒绝，不调用提炼方。这时即使检索没有资料，也仍然是拒绝。
- 还没有记录且检索没有资料时，结果为空，不调用提炼方，也不保存。
- 不合格目标被丢掉，合格目标按原顺序保存。一条合格目标都没有时，不保存记录。
- 提炼方调用失败时，不保存记录。已有记录保持不变。
- 教师只能改表述。标识、维度和来源不变。空白修改和找不到的目标都被拒绝，原记录保持不变。
- 删除一条后，其余目标的标识和顺序不变。最后一条被删掉后记录消失，可以重新提炼。

## File Map

- Create: `src/scaffolding/objectives.py` — 草稿、筛选、目标库。
- Create: `tests/objective_helpers.py` — 测试用的脚本提炼方。
- Create: `tests/test_objective_selection.py` — 只测筛选。
- Create: `tests/test_objective_catalog.py` — 提炼和保存。
- Create: `tests/test_objective_edits.py` — 修改表述和删除。
- Create: `tests/test_objective_acceptance.py` — 规格验收。
- Copy: `docs/superpowers/specs/2026-10-19-objective-extraction-design.md`
- Do not modify: `src/scaffolding/knowledge.py`

---

### Task 1: 丢掉不合格的目标草稿

**Files:**
- Create: `src/scaffolding/objectives.py`
- Test: `tests/test_objective_selection.py`

**Interfaces:**
- Consumes: `LessonRetrieval`、`StageRetrieval`、`LessonSource`、`StandardSource`，来自 `scaffolding.knowledge`。
- Produces: `ObjectiveDraft(dimension: str, statement: str, source: LessonSource | StandardSource)`。`select_objectives(drafts: tuple[ObjectiveDraft, ...], retrieval: LessonRetrieval | StageRetrieval) -> tuple[ObjectiveDraft, ...]`。合格草稿按输入顺序返回。维度不在四维之中、表述空白、或来源不是这次检索来源的草稿被丢掉。

- [ ] **Step 1: Write the failing test**

Create `tests/test_objective_selection.py`:

```python
from scaffolding.knowledge import (
    CurriculumStandard,
    LessonRetrieval,
    LessonSource,
    StageRetrieval,
    StandardSource,
    TextbookLesson,
)
from scaffolding.objectives import ObjectiveDraft, select_objectives


def _retrieval():
    lesson = TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "课时原文")
    standard = CurriculumStandard("普通高中信息科技课程标准", "高中", "1.1.2", "课标全文")
    return LessonRetrieval(lesson.text, lesson.source(), standard.text, standard.source())


def test_valid_drafts_keep_their_order_and_a_missing_dimension_stays_missing():
    retrieval = _retrieval()
    drafts = (
        ObjectiveDraft("计算思维", "能描述组成", retrieval.lesson_source),
        ObjectiveDraft("超纲维度", "不算", retrieval.lesson_source),
        ObjectiveDraft("信息意识", " ", retrieval.standard_source),
        ObjectiveDraft("信息意识", "能识别信息", retrieval.standard_source),
        ObjectiveDraft("信息社会责任", "外来目标", LessonSource("其他版", "必修一", "其他课", "高中", "1")),
        ObjectiveDraft("数字化学习与创新", "现行标记不对", StandardSource("普通高中信息科技课程标准", "高中", "1.1.2", current=False)),
        ObjectiveDraft("信息意识", " 能再举一例 ", retrieval.lesson_source),
    )

    kept = select_objectives(drafts, retrieval)

    assert [(item.dimension, item.statement, item.source) for item in kept] == [
        ("计算思维", "能描述组成", retrieval.lesson_source),
        ("信息意识", "能识别信息", retrieval.standard_source),
        ("信息意识", " 能再举一例 ", retrieval.lesson_source),
    ]


def test_stage_retrieval_keeps_only_the_standard_source():
    standard = CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文")
    retrieval = StageRetrieval(standard.text, standard.source())
    lesson_source = LessonSource("人教版", "必修一", "信息系统的组成", "初中", "12-15")
    drafts = (
        ObjectiveDraft("信息社会责任", "遵守规范", retrieval.standard_source),
        ObjectiveDraft("信息意识", "课时目标", lesson_source),
    )

    kept = select_objectives(drafts, retrieval)

    assert kept == (drafts[0],)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_objective_selection.py -v`

Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `scaffolding.objectives`.

- [ ] **Step 3: Write minimal implementation**

Create `src/scaffolding/objectives.py`:

```python
from collections.abc import Sequence
from dataclasses import dataclass

from scaffolding.knowledge import LessonRetrieval, LessonSource, StageRetrieval, StandardSource


def _filled(value: str) -> bool:
    return value.strip() != ""


_DIMENSIONS = frozenset({
    "信息意识",
    "计算思维",
    "数字化学习与创新",
    "信息社会责任",
})


@dataclass(frozen=True)
class ObjectiveDraft:
    dimension: str
    statement: str
    source: LessonSource | StandardSource


def select_objectives(
    drafts: Sequence[ObjectiveDraft],
    retrieval: LessonRetrieval | StageRetrieval,
) -> tuple[ObjectiveDraft, ...]:
    if isinstance(retrieval, LessonRetrieval):
        allowed = (retrieval.lesson_source, retrieval.standard_source)
    else:
        allowed = (retrieval.standard_source,)
    return tuple(
        draft
        for draft in drafts
        if draft.dimension in _DIMENSIONS and _filled(draft.statement) and draft.source in allowed
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_objective_selection.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/objectives.py tests/test_objective_selection.py
git commit -m "feat: drop objective drafts outside the retrieval"
```

---

### Task 2: 按课时或学段提炼并保存

**Files:**
- Modify: `src/scaffolding/objectives.py`
- Create: `tests/objective_helpers.py`
- Test: `tests/test_objective_catalog.py`

**Interfaces:**
- Consumes: `ObjectiveDraft`，`select_objectives`，`KnowledgeBase.retrieve_lesson(version, volume, lesson) -> LessonRetrieval | None`，`KnowledgeBase.retrieve_stage(stage) -> StageRetrieval | None`。提炼方提供 `extract(retrieval: LessonRetrieval | StageRetrieval) -> tuple[ObjectiveDraft, ...]`。
- Produces: `Rejected`。`Objective(objective_id: str, dimension: str, statement: str, source: LessonSource | StandardSource)`。`ObjectiveCatalog(knowledge, extractor)`。`extract_lesson(version: str, volume: str, lesson: str) -> tuple[Objective, ...]`。`extract_stage(stage: str) -> tuple[Objective, ...]`。`lesson_objectives(version: str, volume: str, lesson: str) -> tuple[Objective, ...]`。`stage_objectives(stage: str) -> tuple[Objective, ...]`。没有记录时后两个方法返回 `()`。标识从 `objective-1` 递增，失败或空结果不占用标识。

- [ ] **Step 1: Write the failing test**

Create `tests/objective_helpers.py`:

```python
from scaffolding.knowledge import (
    CurriculumStandard,
    KnowledgeBase,
    LessonRetrieval,
    StageRetrieval,
    TextbookLesson,
)


class ScriptedExtractor:
    def __init__(self) -> None:
        self.lesson_results = ()
        self.stage_results = ()
        self.lesson_error = None
        self.stage_error = None
        self.calls = []

    def extract(self, retrieval):
        self.calls.append(retrieval)
        if isinstance(retrieval, LessonRetrieval):
            if self.lesson_error is not None:
                raise self.lesson_error
            return self.lesson_results
        if isinstance(retrieval, StageRetrieval):
            if self.stage_error is not None:
                raise self.stage_error
            return self.stage_results
        raise AssertionError("extractor received something other than a retrieval")


def sample_base() -> KnowledgeBase:
    base = KnowledgeBase()
    base.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "课时原文"))
    base.add_standard(CurriculumStandard("普通高中信息科技课程标准", "高中", "1.1.2", "课标全文"))
    return base
```

Create `tests/test_objective_catalog.py`:

```python
import pytest

from scaffolding.knowledge import CurriculumStandard, KnowledgeBase, LessonRetrieval, TextbookLesson
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft, Rejected
from tests.objective_helpers import ScriptedExtractor, sample_base


class EmptyOnSecondLessonRetrieve(KnowledgeBase):
    def __init__(self) -> None:
        super().__init__()
        self.lesson_retrieves = 0

    def retrieve_lesson(self, version: str, volume: str, lesson: str) -> LessonRetrieval | None:
        self.lesson_retrieves += 1
        if self.lesson_retrieves > 1:
            return None
        return super().retrieve_lesson(version, volume, lesson)


def test_lesson_extract_saves_valid_objectives_in_order():
    base = sample_base()
    stored_lesson = base.get_lesson("人教版", "必修一", "信息系统的组成")
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (
        ObjectiveDraft("计算思维", "能描述组成", retrieval.lesson_source),
        ObjectiveDraft("超纲维度", "不算", retrieval.lesson_source),
        ObjectiveDraft("信息意识", "能识别信息", retrieval.standard_source),
        ObjectiveDraft("信息意识", "能再举一例", retrieval.lesson_source),
    )
    catalog = ObjectiveCatalog(base, extractor)

    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")

    assert [(item.objective_id, item.dimension, item.statement) for item in saved] == [
        ("objective-1", "计算思维", "能描述组成"),
        ("objective-2", "信息意识", "能识别信息"),
        ("objective-3", "信息意识", "能再举一例"),
    ]
    assert saved[0].source == retrieval.lesson_source
    assert saved[1].source == retrieval.standard_source
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == saved
    assert extractor.calls == [retrieval]
    assert base.get_lesson("人教版", "必修一", "信息系统的组成") is stored_lesson


def test_stage_record_is_independent_of_the_lesson_record():
    base = sample_base()
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    lesson_retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    stage_retrieval = base.retrieve_stage("初中")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (ObjectiveDraft("信息意识", "课时目标", lesson_retrieval.lesson_source),)
    extractor.stage_results = (
        ObjectiveDraft("信息意识", "不该留下", lesson_retrieval.lesson_source),
        ObjectiveDraft("信息社会责任", "遵守规范", stage_retrieval.standard_source),
    )
    catalog = ObjectiveCatalog(base, extractor)

    lesson_saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    stage_saved = catalog.extract_stage("初中")

    assert stage_saved[0].objective_id == "objective-2"
    assert stage_saved[0].source == stage_retrieval.standard_source
    assert catalog.stage_objectives("初中") == stage_saved
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == lesson_saved
    assert catalog.stage_objectives("高中") == ()


def test_a_different_version_is_another_record():
    base = sample_base()
    base.add_lesson(TextbookLesson("沪科教版", "必修一", "信息系统的组成", "高中", "8", "另一课时原文"))
    first = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    second = base.retrieve_lesson("沪科教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (ObjectiveDraft("计算思维", "第一份", first.lesson_source),)
    catalog = ObjectiveCatalog(base, extractor)
    catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    extractor.lesson_results = (ObjectiveDraft("计算思维", "第二份", second.lesson_source),)

    other = catalog.extract_lesson("沪科教版", "必修一", "信息系统的组成")

    assert other[0].statement == "第二份"
    assert other[0].objective_id == "objective-2"
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "第一份"


def test_empty_retrieval_does_not_call_the_extractor_or_save():
    base = sample_base()
    extractor = ScriptedExtractor()
    catalog = ObjectiveCatalog(base, extractor)

    assert catalog.extract_lesson("人教版", "必修一", "没有的课") == ()
    assert catalog.extract_stage("高中 ") == ()
    assert extractor.calls == []
    assert catalog.lesson_objectives("人教版", "必修一", "没有的课") == ()
    assert catalog.stage_objectives("高中") == ()


def test_no_valid_objective_does_not_save_or_consume_an_id():
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (ObjectiveDraft("超纲维度", "不算", retrieval.lesson_source),)
    catalog = ObjectiveCatalog(base, extractor)

    assert catalog.extract_lesson("人教版", "必修一", "信息系统的组成") == ()
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
    extractor.lesson_results = (ObjectiveDraft("信息意识", "稍后保存", retrieval.lesson_source),)
    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    assert saved[0].objective_id == "objective-1"


def test_extractor_failure_does_not_save():
    base = sample_base()
    extractor = ScriptedExtractor()
    extractor.lesson_error = RuntimeError("down")
    extractor.lesson_results = (
        ObjectiveDraft("信息意识", "不会保存", base.retrieve_lesson("人教版", "必修一", "信息系统的组成").lesson_source),
    )
    catalog = ObjectiveCatalog(base, extractor)

    with pytest.raises(RuntimeError, match="down"):
        catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
    extractor.lesson_error = None
    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    assert saved[0].objective_id == "objective-1"


def test_second_extract_is_rejected_and_existing_objectives_stay():
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (ObjectiveDraft("信息意识", "原目标", retrieval.lesson_source),)
    catalog = ObjectiveCatalog(base, extractor)
    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    extractor.lesson_error = RuntimeError("down")

    with pytest.raises(Rejected):
        catalog.extract_lesson("人教版", "必修一", "信息系统的组成")

    assert extractor.calls == [retrieval]
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == saved


def test_existing_record_is_rejected_even_when_the_second_retrieval_is_empty():
    base = EmptyOnSecondLessonRetrieve()
    base.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "课时原文"))
    base.add_standard(CurriculumStandard("普通高中信息科技课程标准", "高中", "1.1.2", "课标全文"))
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    base.lesson_retrieves = 0
    extractor = ScriptedExtractor()
    extractor.lesson_results = (ObjectiveDraft("信息意识", "原目标", retrieval.lesson_source),)
    catalog = ObjectiveCatalog(base, extractor)
    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")

    with pytest.raises(Rejected):
        catalog.extract_lesson("人教版", "必修一", "信息系统的组成")

    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == saved
    assert len(extractor.calls) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_objective_catalog.py -v`

Expected: FAIL with `ImportError` for `ObjectiveCatalog`.

- [ ] **Step 3: Write minimal implementation**

Add this to `src/scaffolding/objectives.py`. Keep `ObjectiveDraft` and `select_objectives` as they are.

```python
from scaffolding.knowledge import KnowledgeBase


class Rejected(Exception):
    pass


@dataclass(frozen=True)
class Objective:
    objective_id: str
    dimension: str
    statement: str
    source: LessonSource | StandardSource


class ObjectiveCatalog:
    def __init__(self, knowledge: KnowledgeBase, extractor) -> None:
        self._knowledge = knowledge
        self._extractor = extractor
        self._lessons: dict[tuple[str, str, str], tuple[Objective, ...]] = {}
        self._stages: dict[str, tuple[Objective, ...]] = {}
        self._next_id = 1

    def extract_lesson(self, version: str, volume: str, lesson: str) -> tuple[Objective, ...]:
        key = (version, volume, lesson)
        if key in self._lessons:
            raise Rejected("lesson objectives already exist")
        return self._save(self._lessons, key, self._knowledge.retrieve_lesson(version, volume, lesson))

    def extract_stage(self, stage: str) -> tuple[Objective, ...]:
        if stage in self._stages:
            raise Rejected("stage objectives already exist")
        return self._save(self._stages, stage, self._knowledge.retrieve_stage(stage))

    def lesson_objectives(self, version: str, volume: str, lesson: str) -> tuple[Objective, ...]:
        return self._lessons.get((version, volume, lesson), ())

    def stage_objectives(self, stage: str) -> tuple[Objective, ...]:
        return self._stages.get(stage, ())

    def _save(self, store: dict, key: object, retrieval: LessonRetrieval | StageRetrieval | None) -> tuple[Objective, ...]:
        if retrieval is None:
            return ()
        kept = select_objectives(self._extractor.extract(retrieval), retrieval)
        if not kept:
            return ()
        saved = tuple(self._allocate(draft) for draft in kept)
        store[key] = saved
        return saved

    def _allocate(self, draft: ObjectiveDraft) -> Objective:
        objective = Objective(f"objective-{self._next_id}", draft.dimension, draft.statement, draft.source)
        self._next_id += 1
        return objective
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_objective_selection.py tests/test_objective_catalog.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/objectives.py tests/objective_helpers.py tests/test_objective_catalog.py
git commit -m "feat: save extracted lesson and stage objectives"
```

---

### Task 3: 修改表述和删除

**Files:**
- Modify: `src/scaffolding/objectives.py`
- Test: `tests/test_objective_edits.py`

**Interfaces:**
- Consumes: `ObjectiveCatalog.extract_lesson`，`extract_stage`，`lesson_objectives`，`stage_objectives`，`_filled`。`Objective(objective_id, dimension, statement, source)`。
- Produces: `edit_statement(objective_id: str, statement: str) -> Objective`。`delete(objective_id: str) -> None`。空白表述或找不到的标识抛出 `Rejected`，已保存的目标对象保持原样。删光一个键下的目标后，该键消失。标识不回收。

- [ ] **Step 1: Write the failing test**

Create `tests/test_objective_edits.py`:

```python
import pytest

from scaffolding.knowledge import CurriculumStandard
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft, Rejected
from tests.objective_helpers import ScriptedExtractor, sample_base


def _catalog():
    base = sample_base()
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    lesson_retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    stage_retrieval = base.retrieve_stage("初中")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (
        ObjectiveDraft("计算思维", "能描述组成", lesson_retrieval.lesson_source),
        ObjectiveDraft("信息意识", "能识别信息", lesson_retrieval.standard_source),
        ObjectiveDraft("信息社会责任", "遵守规范", lesson_retrieval.lesson_source),
    )
    extractor.stage_results = (ObjectiveDraft("信息意识", "学段目标", stage_retrieval.standard_source),)
    catalog = ObjectiveCatalog(base, extractor)
    catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    catalog.extract_stage("初中")
    return base, extractor, catalog


def test_edit_changes_only_the_statement():
    base, extractor, catalog = _catalog()
    stored_lesson = base.get_lesson("人教版", "必修一", "信息系统的组成")
    before = catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")
    calls = len(extractor.calls)

    edited = catalog.edit_statement("objective-2", " 改后的表述 ")
    after = catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")

    assert edited.statement == " 改后的表述 "
    assert (edited.objective_id, edited.dimension, edited.source) == ("objective-2", "信息意识", before[1].source)
    assert after[0] is before[0]
    assert after[2] is before[2]
    assert after[1] == edited
    assert catalog.stage_objectives("初中")[0].statement == "学段目标"
    assert len(extractor.calls) == calls
    assert base.get_lesson("人教版", "必修一", "信息系统的组成") is stored_lesson


def test_blank_or_missing_edit_keeps_the_stored_objective():
    _, extractor, catalog = _catalog()
    before = catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")
    calls = len(extractor.calls)

    with pytest.raises(Rejected):
        catalog.edit_statement("objective-1", " ")
    with pytest.raises(Rejected):
        catalog.edit_statement("objective-missing", "新表述")

    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == before
    assert before[0] is catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")[0]
    assert len(extractor.calls) == calls


def test_delete_keeps_the_remaining_ids_and_order():
    base, extractor, catalog = _catalog()
    calls = len(extractor.calls)

    catalog.delete("objective-2")
    remaining = catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")

    assert [(item.objective_id, item.statement) for item in remaining] == [
        ("objective-1", "能描述组成"),
        ("objective-3", "遵守规范"),
    ]
    assert catalog.stage_objectives("初中")[0].objective_id == "objective-4"
    with pytest.raises(Rejected):
        catalog.delete("objective-2")
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == remaining
    assert len(extractor.calls) == calls
    assert base.lesson_count() == 1


def test_deleting_the_last_objective_allows_extract_again_with_a_new_id():
    base, extractor, catalog = _catalog()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    for objective_id in ("objective-1", "objective-2", "objective-3"):
        catalog.delete(objective_id)

    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
    extractor.lesson_results = (ObjectiveDraft("计算思维", "重新提炼", retrieval.lesson_source),)
    again = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")

    assert again[0].objective_id == "objective-5"
    assert again[0].statement == "重新提炼"
    assert catalog.stage_objectives("初中")[0].objective_id == "objective-4"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_objective_edits.py -v`

Expected: FAIL with `AttributeError` for `edit_statement`.

- [ ] **Step 3: Write minimal implementation**

Add these methods to `ObjectiveCatalog`:

```python
    def edit_statement(self, objective_id: str, statement: str) -> Objective:
        located = self._locate(objective_id)
        if located is None:
            raise Rejected("objective was not found")
        if not _filled(statement):
            raise Rejected("objective statement must be filled")
        store, key, index = located
        current = store[key][index]
        updated = Objective(current.objective_id, current.dimension, statement, current.source)
        store[key] = store[key][:index] + (updated,) + store[key][index + 1 :]
        return updated

    def delete(self, objective_id: str) -> None:
        located = self._locate(objective_id)
        if located is None:
            raise Rejected("objective was not found")
        store, key, index = located
        remaining = store[key][:index] + store[key][index + 1 :]
        if remaining:
            store[key] = remaining
        else:
            del store[key]

    def _locate(self, objective_id: str):
        for store in (self._lessons, self._stages):
            for key, objectives in store.items():
                for index, objective in enumerate(objectives):
                    if objective.objective_id == objective_id:
                        return store, key, index
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_objective_selection.py tests/test_objective_catalog.py tests/test_objective_edits.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/objectives.py tests/test_objective_edits.py
git commit -m "feat: edit an objective statement and delete objectives"
```

---

### Task 4: 规格验收

**Files:**
- Create: `tests/test_objective_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-19-objective-extraction-design.md`

**Interfaces:**
- Consumes: Task 1 到 Task 3 的全部公开接口。规格文件来自 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-19-objective-extraction-design.md`，即 `master` 的 `5048602`。原样复制，不要改写。
- Produces: 验收测试。不新增生产行为。

- [ ] **Step 1: Write the failing test**

Copy the spec file unchanged to `docs/superpowers/specs/2026-10-19-objective-extraction-design.md`.

Create `tests/test_objective_acceptance.py`:

```python
from pathlib import Path

import pytest

from scaffolding.knowledge import CurriculumStandard, KnowledgeBase, LessonRetrieval, TextbookLesson
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft, Rejected
from tests.objective_helpers import ScriptedExtractor, sample_base


def test_objective_extraction_spec_is_in_the_workspace():
    spec = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "specs" / "2026-10-19-objective-extraction-design.md"
    assert spec.is_file()


class EmptyOnSecondLessonRetrieve(KnowledgeBase):
    def __init__(self) -> None:
        super().__init__()
        self.lesson_retrieves = 0

    def retrieve_lesson(self, version: str, volume: str, lesson: str) -> LessonRetrieval | None:
        self.lesson_retrieves += 1
        if self.lesson_retrieves > 1:
            return None
        return super().retrieve_lesson(version, volume, lesson)


def test_extraction_matches_the_spec():
    base = sample_base()
    stored_lesson = base.get_lesson("人教版", "必修一", "信息系统的组成")
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    base.add_lesson(TextbookLesson("沪科教版", "必修一", "信息系统的组成", "高中", "8", "另一课时原文"))
    lesson_retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    other_retrieval = base.retrieve_lesson("沪科教版", "必修一", "信息系统的组成")
    junior = base.retrieve_stage("初中")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (
        ObjectiveDraft("计算思维", "能描述组成", lesson_retrieval.lesson_source),
        ObjectiveDraft("超纲维度", "不算", lesson_retrieval.lesson_source),
        ObjectiveDraft("信息意识", " ", lesson_retrieval.standard_source),
        ObjectiveDraft("信息意识", "能识别信息", lesson_retrieval.standard_source),
        ObjectiveDraft("信息意识", "外来目标", other_retrieval.lesson_source),
    )
    extractor.stage_results = (ObjectiveDraft("课外", "不算", junior.standard_source),)
    catalog = ObjectiveCatalog(base, extractor)

    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    assert [(item.objective_id, item.dimension, item.statement, item.source) for item in saved] == [
        ("objective-1", "计算思维", "能描述组成", lesson_retrieval.lesson_source),
        ("objective-2", "信息意识", "能识别信息", lesson_retrieval.standard_source),
    ]
    assert catalog.extract_stage("初中") == ()
    assert catalog.stage_objectives("初中") == ()

    extractor.stage_results = (ObjectiveDraft("信息社会责任", "遵守规范", junior.standard_source),)
    stage_saved = catalog.extract_stage("初中")
    assert stage_saved[0].source == junior.standard_source
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == saved

    extractor.lesson_results = (ObjectiveDraft("计算思维", "另一版本", other_retrieval.lesson_source),)
    other = catalog.extract_lesson("沪科教版", "必修一", "信息系统的组成")
    assert other[0].statement == "另一版本"
    assert other[0].objective_id == "objective-4"

    calls = len(extractor.calls)
    assert catalog.extract_lesson("人教版", "必修一", "没有的课") == ()
    assert len(extractor.calls) == calls

    failing = ScriptedExtractor()
    failing.lesson_error = RuntimeError("down")
    failed = ObjectiveCatalog(base, failing)
    with pytest.raises(RuntimeError):
        failed.extract_lesson("人教版", "必修一", "信息系统的组成")
    assert failed.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()

    calls = len(extractor.calls)
    with pytest.raises(Rejected):
        catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    assert len(extractor.calls) == calls
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == saved

    edited = catalog.edit_statement("objective-1", "改后的表述")
    assert (edited.objective_id, edited.dimension, edited.source, edited.statement) == (
        "objective-1",
        "计算思维",
        lesson_retrieval.lesson_source,
        "改后的表述",
    )
    with pytest.raises(Rejected):
        catalog.edit_statement("objective-1", " ")
    with pytest.raises(Rejected):
        catalog.edit_statement("objective-missing", "新表述")
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "改后的表述"

    catalog.delete("objective-2")
    remaining = catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")
    assert [item.objective_id for item in remaining] == ["objective-1"]
    with pytest.raises(Rejected):
        catalog.delete("objective-2")
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == remaining
    catalog.delete("objective-1")
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
    extractor.lesson_results = (ObjectiveDraft("信息意识", "重新提炼", lesson_retrieval.lesson_source),)
    again = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    assert again[0].objective_id == "objective-5"
    assert base.get_lesson("人教版", "必修一", "信息系统的组成") is stored_lesson
    assert stage_saved[0].statement == "遵守规范"


def test_existing_record_is_still_rejected_when_retrieval_becomes_empty():
    base = EmptyOnSecondLessonRetrieve()
    base.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "课时原文"))
    base.add_standard(CurriculumStandard("普通高中信息科技课程标准", "高中", "1.1.2", "课标全文"))
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    base.lesson_retrieves = 0
    extractor = ScriptedExtractor()
    extractor.lesson_results = (ObjectiveDraft("信息意识", "原目标", retrieval.lesson_source),)
    catalog = ObjectiveCatalog(base, extractor)
    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")

    with pytest.raises(Rejected):
        catalog.extract_lesson("人教版", "必修一", "信息系统的组成")

    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == saved
    assert len(extractor.calls) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_objective_acceptance.py -v`

Expected: FAIL because the spec file is not in the worktree yet. If the spec file is already present, this step passes and the next step only adds the test.

- [ ] **Step 3: Copy the spec and keep the test**

Copy `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-19-objective-extraction-design.md` to `docs/superpowers/specs/2026-10-19-objective-extraction-design.md` in the worktree. Do not edit the spec. Do not change `src/scaffolding/objectives.py` unless a test shows a real bug; in that case stop and report it.

- [ ] **Step 4: Run the full suite**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS, including the previous knowledge, task, and scaffolding tests.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_objective_acceptance.py docs/superpowers/specs/2026-10-19-objective-extraction-design.md
git commit -m "test: accept four-dimensional objective extraction"
```
