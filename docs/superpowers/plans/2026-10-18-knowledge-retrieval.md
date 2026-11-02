# 知识库检索 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 知识库按版本、册次和课时交回该课时原文及其学段的现行课标；只给学段时只交回现行课标。每份结果都带来源。

**Architecture:** `KnowledgeBase` 在内存里保存教材课时和每个学段的一份现行课标。写入时拒绝空白和重复。检索按原文精确对应，缺课时或缺现行课标时返回 `None`，不交回一半。本计划不提炼教学目标，也不生成任务。

**Tech Stack:** Python 3.14，pytest 9，标准库。实现从 `origin/main` 建工作区。规格在 `master` 的 `d10c433`。工作区里若没有规格文件，把 `docs/superpowers/specs/2026-10-18-knowledge-retrieval-design.md` 从 `d10c433` 加入该分支。测试命令是 `.\.venv\Scripts\python.exe -m pytest`。

## Global Constraints

- 提炼四维教学目标、生成任务、发布和作答不在本计划里。
- 教材原文和课标事先写入知识库。检索不访问网络，也不从文件现读。
- 同一个版本、册次和课时只能有一条教材记录。每个学段只保存一份现行课标。
- 版本、册次、课时、学段、页码、原文、课标名称、条款号和课标全文都不能为空白。空白不算已填写。
- 指定版本、册次和课时时，必须同时交回课时原文和该学段现行课标。缺一则结果为空。
- 只给学段时，只交回该学段的现行课标，不交回教材。
- 检索按版本、册次、课时和学段的原文精确对应。
- 教材来源是版本、册次、课时、学段、页码。课标来源是名称、学段、条款号，并标明现行。

---

### Task 1: 教材课时和现行课标

**Files:**
- Create: `src/scaffolding/knowledge.py`
- Test: `tests/test_knowledge_records.py`

**Interfaces:**
- Consumes: 无。
- Produces: `LessonSource(version: str, volume: str, lesson: str, stage: str, pages: str)`，`StandardSource(name: str, stage: str, clauses: str, current: bool = True)`，`TextbookLesson(version: str, volume: str, lesson: str, stage: str, pages: str, text: str)`，`CurriculumStandard(name: str, stage: str, clauses: str, text: str)`。`TextbookLesson.source() -> LessonSource`。`CurriculumStandard.source() -> StandardSource`，其中 `current` 为 `True`。空白字段在构造时抛出 `ValueError`。

- [ ] **Step 1: Write the failing test**

```python
import pytest

from scaffolding.knowledge import CurriculumStandard, LessonSource, TextbookLesson


def test_lesson_and_standard_keep_their_sources():
    lesson = TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "人员、硬件、软件、数据和网络")
    standard = CurriculumStandard("普通高中信息科技课程标准", "高中", "1.1.2", "信息意识、计算思维、数字化学习与创新、信息社会责任")

    assert lesson.source() == LessonSource("人教版", "必修一", "信息系统的组成", "高中", "12-15")
    assert lesson.text == "人员、硬件、软件、数据和网络"
    assert standard.source().name == "普通高中信息科技课程标准"
    assert standard.source().stage == "高中"
    assert standard.source().clauses == "1.1.2"
    assert standard.source().current is True
    assert standard.text.startswith("信息意识")


@pytest.mark.parametrize(
    "build",
    [
        lambda: TextbookLesson(" ", "必修一", "组成", "高中", "12", "原文"),
        lambda: TextbookLesson("人教版", " ", "组成", "高中", "12", "原文"),
        lambda: TextbookLesson("人教版", "必修一", " ", "高中", "12", "原文"),
        lambda: TextbookLesson("人教版", "必修一", "组成", " ", "12", "原文"),
        lambda: TextbookLesson("人教版", "必修一", "组成", "高中", " ", "原文"),
        lambda: TextbookLesson("人教版", "必修一", "组成", "高中", "12", " "),
        lambda: CurriculumStandard(" ", "高中", "1.1", "全文"),
        lambda: CurriculumStandard("课标", " ", "1.1", "全文"),
        lambda: CurriculumStandard("课标", "高中", " ", "全文"),
        lambda: CurriculumStandard("课标", "高中", "1.1", " "),
    ],
)
def test_blank_fields_are_rejected(build):
    with pytest.raises(ValueError):
        build()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_knowledge_records.py -v`

Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `scaffolding.knowledge`.

- [ ] **Step 3: Write minimal implementation**

Create `src/scaffolding/knowledge.py`:

```python
from dataclasses import dataclass


def _filled(value: str) -> bool:
    return value.strip() != ""


@dataclass(frozen=True)
class LessonSource:
    version: str
    volume: str
    lesson: str
    stage: str
    pages: str


@dataclass(frozen=True)
class StandardSource:
    name: str
    stage: str
    clauses: str
    current: bool = True


@dataclass(frozen=True)
class TextbookLesson:
    version: str
    volume: str
    lesson: str
    stage: str
    pages: str
    text: str

    def __post_init__(self) -> None:
        if not all(_filled(value) for value in (self.version, self.volume, self.lesson, self.stage, self.pages, self.text)):
            raise ValueError("lesson fields must be filled")

    def source(self) -> LessonSource:
        return LessonSource(self.version, self.volume, self.lesson, self.stage, self.pages)


@dataclass(frozen=True)
class CurriculumStandard:
    name: str
    stage: str
    clauses: str
    text: str

    def __post_init__(self) -> None:
        if not all(_filled(value) for value in (self.name, self.stage, self.clauses, self.text)):
            raise ValueError("standard fields must be filled")

    def source(self) -> StandardSource:
        return StandardSource(self.name, self.stage, self.clauses, current=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_knowledge_records.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/scaffolding/knowledge.py tests/test_knowledge_records.py
git commit -m "feat: store a textbook lesson and the current standard with sources"
```

---

### Task 2: 写入时拒绝重复

**Files:**
- Modify: `src/scaffolding/knowledge.py`
- Test: `tests/test_knowledge_store.py`

**Interfaces:**
- Consumes: `TextbookLesson`，`CurriculumStandard`。
- Produces: `Rejected(Exception)`，`KnowledgeBase.add_lesson(lesson: TextbookLesson) -> None`，`KnowledgeBase.add_standard(standard: CurriculumStandard) -> None`。重复的版本、册次、课时，或同一学段的第二份现行课标，抛出 `Rejected`，已保存的记录不变。

- [ ] **Step 1: Write the failing test**

```python
import pytest

from scaffolding.knowledge import CurriculumStandard, KnowledgeBase, Rejected, TextbookLesson


def _lesson(lesson: str = "信息系统的组成", version: str = "人教版", volume: str = "必修一") -> TextbookLesson:
    return TextbookLesson(version, volume, lesson, "高中", "12-15", "人员、硬件、软件、数据和网络")


def _standard(stage: str = "高中", name: str = "普通高中信息科技课程标准") -> CurriculumStandard:
    return CurriculumStandard(name, stage, "1.1.2", "四个核心素养")


def test_duplicate_lesson_and_standard_keep_the_original():
    base = KnowledgeBase()
    original = _lesson()
    base.add_lesson(original)
    base.add_standard(_standard())

    with pytest.raises(Rejected):
        base.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "99", "另一份原文"))
    with pytest.raises(Rejected):
        base.add_standard(_standard(name="另一份课标"))

    assert base.lesson_count() == 1
    assert base.standard_count() == 1
    stored = base.get_lesson("人教版", "必修一", "信息系统的组成")
    assert stored is original
    assert base.get_standard("高中").name == "普通高中信息科技课程标准"


def test_a_different_lesson_key_can_be_stored():
    base = KnowledgeBase()
    base.add_lesson(_lesson())
    base.add_lesson(_lesson(version="沪科教版"))
    base.add_lesson(_lesson(volume="必修二"))
    base.add_lesson(_lesson(lesson="数据与编码"))
    base.add_standard(_standard())
    base.add_standard(_standard(stage="初中", name="义务教育信息科技课程标准"))

    assert base.lesson_count() == 4
    assert base.standard_count() == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_knowledge_store.py -v`

Expected: FAIL because `KnowledgeBase` is not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `src/scaffolding/knowledge.py`:

```python
class Rejected(Exception):
    pass


class KnowledgeBase:
    def __init__(self) -> None:
        self._lessons: dict[tuple[str, str, str], TextbookLesson] = {}
        self._standards: dict[str, CurriculumStandard] = {}

    def add_lesson(self, lesson: TextbookLesson) -> None:
        key = (lesson.version, lesson.volume, lesson.lesson)
        if key in self._lessons:
            raise Rejected("this lesson is already stored")
        self._lessons[key] = lesson

    def add_standard(self, standard: CurriculumStandard) -> None:
        if standard.stage in self._standards:
            raise Rejected("this stage already has a current standard")
        self._standards[standard.stage] = standard

    def get_lesson(self, version: str, volume: str, lesson: str) -> TextbookLesson:
        return self._lessons[(version, volume, lesson)]

    def get_standard(self, stage: str) -> CurriculumStandard:
        return self._standards[stage]

    def lesson_count(self) -> int:
        return len(self._lessons)

    def standard_count(self) -> int:
        return len(self._standards)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_knowledge_store.py tests/test_knowledge_records.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/scaffolding/knowledge.py tests/test_knowledge_store.py
git commit -m "feat: reject duplicate lessons and a second current standard"
```

---

### Task 3: 按课时或学段检索

**Files:**
- Modify: `src/scaffolding/knowledge.py`
- Test: `tests/test_knowledge_retrieval.py`

**Interfaces:**
- Consumes: Task 2 的 `KnowledgeBase`。
- Produces: `LessonRetrieval(lesson_text: str, lesson_source: LessonSource, standard_text: str, standard_source: StandardSource)`，`StageRetrieval(standard_text: str, standard_source: StandardSource)`，`KnowledgeBase.retrieve_lesson(version: str, volume: str, lesson: str) -> LessonRetrieval | None`，`KnowledgeBase.retrieve_stage(stage: str) -> StageRetrieval | None`。`retrieve_lesson` 在课时不存在或该学段没有现行课标时返回 `None`。`retrieve_stage` 在该学段没有现行课标时返回 `None`，并且结果里没有教材字段。

- [ ] **Step 1: Write the failing test**

```python
from scaffolding.knowledge import CurriculumStandard, KnowledgeBase, TextbookLesson


def _base() -> KnowledgeBase:
    base = KnowledgeBase()
    base.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "课时原文"))
    base.add_standard(CurriculumStandard("普通高中信息科技课程标准", "高中", "1.1.2", "课标全文"))
    return base


def test_lesson_retrieval_returns_the_text_and_both_sources():
    found = _base().retrieve_lesson("人教版", "必修一", "信息系统的组成")

    assert found is not None
    assert found.lesson_text == "课时原文"
    assert found.lesson_source.version == "人教版"
    assert found.lesson_source.volume == "必修一"
    assert found.lesson_source.lesson == "信息系统的组成"
    assert found.lesson_source.stage == "高中"
    assert found.lesson_source.pages == "12-15"
    assert found.standard_text == "课标全文"
    assert found.standard_source.name == "普通高中信息科技课程标准"
    assert found.standard_source.stage == "高中"
    assert found.standard_source.clauses == "1.1.2"
    assert found.standard_source.current is True


def test_stage_retrieval_returns_only_the_current_standard():
    found = _base().retrieve_stage("高中")

    assert found is not None
    assert found.standard_text == "课标全文"
    assert found.standard_source.current is True
    assert not hasattr(found, "lesson_text")
    assert not hasattr(found, "lesson_source")


def test_missing_half_returns_nothing():
    lesson_only = KnowledgeBase()
    lesson_only.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "课时原文"))
    standard_only = KnowledgeBase()
    standard_only.add_standard(CurriculumStandard("普通高中信息科技课程标准", "高中", "1.1.2", "课标全文"))

    assert lesson_only.retrieve_lesson("人教版", "必修一", "信息系统的组成") is None
    assert standard_only.retrieve_lesson("人教版", "必修一", "信息系统的组成") is None
    assert KnowledgeBase().retrieve_stage("高中") is None


def test_a_different_key_does_not_return_the_stored_lesson():
    base = _base()

    assert base.retrieve_lesson("沪科教版", "必修一", "信息系统的组成") is None
    assert base.retrieve_lesson("人教版", "必修二", "信息系统的组成") is None
    assert base.retrieve_lesson("人教版", "必修一", "数据与编码") is None
    assert base.retrieve_stage("初中") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_knowledge_retrieval.py -v`

Expected: FAIL because `retrieve_lesson` does not exist.

- [ ] **Step 3: Write minimal implementation**

Append to `src/scaffolding/knowledge.py`:

```python
@dataclass(frozen=True)
class LessonRetrieval:
    lesson_text: str
    lesson_source: LessonSource
    standard_text: str
    standard_source: StandardSource


@dataclass(frozen=True)
class StageRetrieval:
    standard_text: str
    standard_source: StandardSource
```

Add these methods to `KnowledgeBase`:

```python
def retrieve_lesson(self, version: str, volume: str, lesson: str) -> LessonRetrieval | None:
    stored = self._lessons.get((version, volume, lesson))
    if stored is None:
        return None
    standard = self._standards.get(stored.stage)
    if standard is None:
        return None
    return LessonRetrieval(stored.text, stored.source(), standard.text, standard.source())


def retrieve_stage(self, stage: str) -> StageRetrieval | None:
    standard = self._standards.get(stage)
    if standard is None:
        return None
    return StageRetrieval(standard.text, standard.source())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_knowledge_records.py tests/test_knowledge_store.py tests/test_knowledge_retrieval.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/scaffolding/knowledge.py tests/test_knowledge_retrieval.py
git commit -m "feat: retrieve a lesson with its current standard or the standard alone"
```

---

### Task 4: 规格验收

**Files:**
- Create: `tests/test_knowledge_acceptance.py`
- The spec file `docs/superpowers/specs/2026-10-18-knowledge-retrieval-design.md` must be in the worktree.

**Interfaces:**
- Consumes: Tasks 1–3 的公开类型。
- Produces: 无新的生产接口。

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

import pytest

from scaffolding.knowledge import CurriculumStandard, KnowledgeBase, Rejected, TextbookLesson


def test_knowledge_retrieval_spec_is_in_the_workspace():
    spec = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "specs" / "2026-10-18-knowledge-retrieval-design.md"
    assert spec.is_file()


def test_retrieval_matches_the_spec():
    base = KnowledgeBase()
    base.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "课时原文"))
    base.add_standard(CurriculumStandard("普通高中信息科技课程标准", "高中", "1.1.2", "课标全文"))

    found = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    assert found is not None
    assert found.lesson_text == "课时原文"
    assert (found.lesson_source.version, found.lesson_source.volume, found.lesson_source.lesson, found.lesson_source.stage, found.lesson_source.pages) == ("人教版", "必修一", "信息系统的组成", "高中", "12-15")
    assert found.standard_source.current is True

    stage_only = base.retrieve_stage("高中")
    assert stage_only is not None
    assert stage_only.standard_text == "课标全文"
    assert not hasattr(stage_only, "lesson_text")

    assert base.retrieve_lesson("人教版", "必修一", "不存在的课时") is None
    bare = KnowledgeBase()
    bare.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "课时原文"))
    assert bare.retrieve_lesson("人教版", "必修一", "信息系统的组成") is None

    with pytest.raises(Rejected):
        base.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "20", "新原文"))
    with pytest.raises(Rejected):
        base.add_standard(CurriculumStandard("另一份高中课标", "高中", "2.1", "另一份全文"))
    assert base.get_lesson("人教版", "必修一", "信息系统的组成").text == "课时原文"
    assert base.retrieve_lesson("沪科教版", "必修一", "信息系统的组成") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_knowledge_acceptance.py -v`

Expected: FAIL because the spec file is missing. The retrieval assertions should already pass after Task 3. If the spec file is already present, confirm the whole file PASSes and go to the commit.

- [ ] **Step 3: Add the spec file when it is missing**

Copy `docs/superpowers/specs/2026-10-18-knowledge-retrieval-design.md` from commit `d10c433` into the worktree. Do not rewrite it.

- [ ] **Step 4: Run the whole suite**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_knowledge_acceptance.py docs/superpowers/specs/2026-10-18-knowledge-retrieval-design.md
git commit -m "test: accept lesson and stage retrieval from the knowledge base"
```
