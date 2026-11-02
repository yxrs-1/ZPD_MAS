# 任务生成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按教师指定的题量，从一份已保存的目标记录生成未发布任务，并把用过的目标记录按任务标识留给教师查看。

**Architecture:** `arrange_questions` 把生成方交回的题目排成单选、多选、判断、综合，并核对数量。`TaskGeneration` 只在检查通过后调用现有的 `TaskCatalog.create`。来源记录存在 `TaskGeneration` 里，不写进任务、学生列表或智能体读到的 `TaskRecord`。本计划不接真实模型，也不重做发布后的作答。

**Tech Stack:** Python 3.14，pytest 9，标准库。实现从 `origin/main` 建工作区。规格在 `master` 的 `de7a461`。工作区里若没有规格文件，把 `docs/superpowers/specs/2026-10-19-task-generation-design.md` 从该提交原样复制进来，不要改写。测试命令是 `.\.venv\Scripts\python.exe -m pytest`。PowerShell 下不要使用 `&&` 或 bash heredoc；提交用 `git commit -m "message"`。不要改 git config，不要 push。

## Global Constraints

- 发布后的作答、求助和提交不在本计划里。
- 生成方是可替换接口。测试使用事先写好的题目，不接真实模型。
- 知识库和目标库都不被修改。
- 生成成功后创建未发布任务。题目顺序是单选、多选、判断、综合。数量为 0 的那一类不出现。同一类保持生成方交回的先后。
- 来源记录按任务标识另存。课时记录是版本、册次、课时。学段记录是学段。两种只存一种。
- 来源记录只供教师按任务标识查看。学生页面、待办列表和两个支架智能体都读不到它。
- 没有目标记录、四种数量都是 0，或某个数量不是零或正整数时，不调用生成方，也不创建任务。
- 数量不一致、题目不符合现有题型规则，或生成方调用失败时，整次拒绝。不创建任务，也不保存来源记录。已有任务保持不变。
- 生成方只能读到四种数量，以及这份记录里每条目标的维度、表述和来源。
- 之后修改或删除目标，任务和来源记录保持生成时的样子。发布前修改题目和发布本身都不删除来源记录。
- 空白不算已填写。选择题、判断题、综合题沿用任务发布规格里的题目规则。

## File Map

- Create: `src/scaffolding/generation.py` — 排序、生成和教师来源记录。
- Create: `tests/generation_helpers.py` — 测试用的脚本生成方和样题。
- Create: `tests/test_question_arrangement.py`
- Create: `tests/test_task_generation.py`
- Create: `tests/test_task_generation_refusal.py`
- Create: `tests/test_task_generation_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-19-task-generation-design.md`
- Do not modify: `src/scaffolding/knowledge.py`、`objectives.py`、`tasks.py`、`session.py`

---

### Task 1: 按题型排好并核对数量

**Files:**
- Create: `src/scaffolding/generation.py`
- Test: `tests/test_question_arrangement.py`

**Interfaces:**
- Consumes: `ChoiceQuestion`、`TrueFalseQuestion`、`OpenQuestion`、`SelectionMode`，来自 `scaffolding.records`。
- Produces: `QuestionCounts(single: int, multiple: int, true_false: int, open_ended: int)`。`arrange_questions(questions: Sequence[object], counts: QuestionCounts) -> tuple[Question, ...] | None`。合格时返回单选、多选、判断、综合这个顺序。同一类保持输入里的先后。数量不符或出现这三类以外的对象时返回 `None`。

- [ ] **Step 1: Write the failing test**

Create `tests/test_question_arrangement.py`:

```python
from scaffolding.generation import QuestionCounts, arrange_questions
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion


def _single(prompt: str) -> ChoiceQuestion:
    return ChoiceQuestion(prompt, SelectionMode.SINGLE, ("甲", "乙"), ("甲",), "解析")


def test_questions_are_grouped_and_keep_order_within_each_type():
    later_single = _single("单选乙")
    earlier_single = _single("单选甲")
    multiple = ChoiceQuestion("多选题", SelectionMode.MULTIPLE, ("甲", "乙", "丙"), ("甲", "丙"), "解析")
    judged = TrueFalseQuestion("判断题", "正确", "解析")
    opened = OpenQuestion("综合题", "写出过程")
    counts = QuestionCounts(single=2, multiple=1, true_false=1, open_ended=1)

    arranged = arrange_questions((opened, multiple, later_single, judged, earlier_single), counts)

    assert arranged == (later_single, earlier_single, multiple, judged, opened)


def test_a_zero_count_rejects_a_question_of_that_type():
    counts = QuestionCounts(single=1, multiple=0, true_false=0, open_ended=0)

    assert arrange_questions((_single("单选甲"), OpenQuestion("综合题", "写出过程")), counts) is None


def test_a_non_question_is_rejected():
    counts = QuestionCounts(single=0, multiple=0, true_false=0, open_ended=0)

    assert arrange_questions(("不是题目",), counts) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_question_arrangement.py -v`

Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `scaffolding.generation`.

- [ ] **Step 3: Write minimal implementation**

Create `src/scaffolding/generation.py`:

```python
from collections.abc import Sequence
from dataclasses import dataclass

from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion

Question = ChoiceQuestion | TrueFalseQuestion | OpenQuestion


@dataclass(frozen=True)
class QuestionCounts:
    single: int
    multiple: int
    true_false: int
    open_ended: int


def arrange_questions(questions: Sequence[object], counts: QuestionCounts) -> tuple[Question, ...] | None:
    singles: list[ChoiceQuestion] = []
    multiples: list[ChoiceQuestion] = []
    judged: list[TrueFalseQuestion] = []
    opened: list[OpenQuestion] = []
    for question in questions:
        if isinstance(question, ChoiceQuestion) and question.selection == SelectionMode.SINGLE:
            singles.append(question)
        elif isinstance(question, ChoiceQuestion) and question.selection == SelectionMode.MULTIPLE:
            multiples.append(question)
        elif isinstance(question, TrueFalseQuestion):
            judged.append(question)
        elif isinstance(question, OpenQuestion):
            opened.append(question)
        else:
            return None
    if (
        len(singles) != counts.single
        or len(multiples) != counts.multiple
        or len(judged) != counts.true_false
        or len(opened) != counts.open_ended
    ):
        return None
    return tuple(singles + multiples + judged + opened)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_question_arrangement.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/generation.py tests/test_question_arrangement.py
git commit -m "feat: arrange generated questions by type and count"
```

---

### Task 2: 从一份目标记录创建未发布任务

**Files:**
- Modify: `src/scaffolding/generation.py`
- Create: `tests/generation_helpers.py`
- Test: `tests/test_task_generation.py`

**Interfaces:**
- Consumes: `arrange_questions`、`QuestionCounts`、`ObjectiveCatalog.lesson_objectives`、`ObjectiveCatalog.stage_objectives`、`TaskCatalog.create`。生成方提供 `generate(counts: QuestionCounts, objectives: tuple[Objective, ...]) -> tuple[Question, ...]`。
- Produces: `LessonOrigin(version: str, volume: str, lesson: str)`、`StageOrigin(stage: str)`、`TaskGeneration(objectives, tasks, generator)`。`generate_lesson(version, volume, lesson, *, single, multiple, true_false, open_ended) -> Task`。`generate_stage(stage, *, single, multiple, true_false, open_ended) -> Task`。`origin(task_id: str) -> LessonOrigin | StageOrigin | None`。没有来源记录时返回 `None`。

- [ ] **Step 1: Write the failing test**

Create `tests/generation_helpers.py`:

```python
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion
from tests.objective_helpers import ScriptedExtractor, sample_base


class ScriptedGenerator:
    def __init__(self) -> None:
        self.questions = ()
        self.error = None
        self.calls = []

    def generate(self, counts, objectives):
        self.calls.append((counts, objectives))
        if self.error is not None:
            raise self.error
        return self.questions


def single(prompt: str = "单选题") -> ChoiceQuestion:
    return ChoiceQuestion(prompt, SelectionMode.SINGLE, ("甲", "乙"), ("甲",), "解析")


def multiple() -> ChoiceQuestion:
    return ChoiceQuestion("多选题", SelectionMode.MULTIPLE, ("甲", "乙", "丙"), ("甲", "丙"), "解析")


def judged() -> TrueFalseQuestion:
    return TrueFalseQuestion("判断题", "正确", "解析")


def opened() -> OpenQuestion:
    return OpenQuestion("综合题", "写出过程")


def prepared_objectives():
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (ObjectiveDraft("信息意识", "能识别信息", retrieval.lesson_source),)
    objectives = ObjectiveCatalog(base, extractor)
    objectives.extract_lesson("人教版", "必修一", "信息系统的组成")
    return base, objectives
```

Create `tests/test_task_generation.py`:

```python
from scaffolding.generation import LessonOrigin, QuestionCounts, StageOrigin, TaskGeneration
from scaffolding.knowledge import CurriculumStandard
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft
from scaffolding.tasks import TaskCatalog
from tests.generation_helpers import ScriptedGenerator, judged, multiple, opened, prepared_objectives, single
from tests.objective_helpers import ScriptedExtractor


def test_lesson_generation_creates_an_unpublished_task_and_records_the_lesson():
    base, objectives = prepared_objectives()
    stored_lesson = base.get_lesson("人教版", "必修一", "信息系统的组成")
    stored_objective = objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0]
    generator = ScriptedGenerator()
    generator.questions = (opened(), multiple(), single("单选乙"), judged(), single("单选甲"))
    tasks = TaskCatalog()
    generation = TaskGeneration(objectives, tasks, generator)

    task = generation.generate_lesson(
        "人教版", "必修一", "信息系统的组成", single=2, multiple=1, true_false=1, open_ended=1
    )

    assert task.published is False
    assert task.task_id == "task-1"
    assert [question.prompt for question in task.questions] == ["单选乙", "单选甲", "多选题", "判断题", "综合题"]
    assert generation.origin(task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")
    assert generator.calls == [
        (QuestionCounts(2, 1, 1, 1), objectives.lesson_objectives("人教版", "必修一", "信息系统的组成"))
    ]
    assert tasks.student_tasks() == ()
    assert base.get_lesson("人教版", "必修一", "信息系统的组成") is stored_lesson
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0] == stored_objective


def test_a_zero_count_omits_that_type():
    _, objectives = prepared_objectives()
    generator = ScriptedGenerator()
    generator.questions = (single(),)
    generation = TaskGeneration(objectives, TaskCatalog(), generator)

    task = generation.generate_lesson(
        "人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0
    )

    assert [type(question).__name__ for question in task.questions] == ["ChoiceQuestion"]
    assert task.questions[0].selection.value == "单选"


def test_stage_origin_is_independent_of_the_lesson_origin():
    base, objectives = prepared_objectives()
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    stage_retrieval = base.retrieve_stage("初中")
    extractor = ScriptedExtractor()
    extractor.stage_results = (ObjectiveDraft("信息社会责任", "遵守规范", stage_retrieval.standard_source),)
    stage_objectives = ObjectiveCatalog(base, extractor)
    stage_objectives.extract_stage("初中")
    generator = ScriptedGenerator()
    generator.questions = (single(),)
    tasks = TaskCatalog()
    lesson_generation = TaskGeneration(objectives, tasks, generator)
    lesson_task = lesson_generation.generate_lesson(
        "人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0
    )
    generator.questions = (opened(),)
    stage_generation = TaskGeneration(stage_objectives, tasks, generator)
    stage_task = stage_generation.generate_stage("初中", single=0, multiple=0, true_false=0, open_ended=1)

    assert lesson_generation.origin(lesson_task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")
    assert stage_generation.origin(stage_task.task_id) == StageOrigin("初中")
    assert stage_task.questions[0].prompt == "综合题"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_task_generation.py -v`

Expected: FAIL with `ImportError` for `TaskGeneration`.

- [ ] **Step 3: Write minimal implementation**

Add this to `src/scaffolding/generation.py`. Keep `QuestionCounts` and `arrange_questions`.

```python
from scaffolding.objectives import Objective, ObjectiveCatalog
from scaffolding.tasks import Task, TaskCatalog


@dataclass(frozen=True)
class LessonOrigin:
    version: str
    volume: str
    lesson: str


@dataclass(frozen=True)
class StageOrigin:
    stage: str


class TaskGeneration:
    def __init__(self, objectives: ObjectiveCatalog, tasks: TaskCatalog, generator) -> None:
        self._objectives = objectives
        self._tasks = tasks
        self._generator = generator
        self._origins: dict[str, LessonOrigin | StageOrigin] = {}

    def generate_lesson(
        self, version: str, volume: str, lesson: str, *, single: int, multiple: int, true_false: int, open_ended: int
    ) -> Task:
        return self._generate(
            self._objectives.lesson_objectives(version, volume, lesson),
            LessonOrigin(version, volume, lesson),
            single,
            multiple,
            true_false,
            open_ended,
        )

    def generate_stage(self, stage: str, *, single: int, multiple: int, true_false: int, open_ended: int) -> Task:
        return self._generate(
            self._objectives.stage_objectives(stage),
            StageOrigin(stage),
            single,
            multiple,
            true_false,
            open_ended,
        )

    def origin(self, task_id: str) -> LessonOrigin | StageOrigin | None:
        return self._origins.get(task_id)

    def _generate(
        self,
        objectives: tuple[Objective, ...],
        origin: LessonOrigin | StageOrigin,
        single: int,
        multiple: int,
        true_false: int,
        open_ended: int,
    ) -> Task:
        counts = QuestionCounts(single, multiple, true_false, open_ended)
        ordered = arrange_questions(self._generator.generate(counts, objectives), counts)
        task = self._tasks.create(ordered)
        self._origins[task.task_id] = origin
        return task
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_question_arrangement.py tests/test_task_generation.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/generation.py tests/generation_helpers.py tests/test_task_generation.py
git commit -m "feat: create an unpublished task from one objective record"
```

---

### Task 3: 拒绝不合格的生成

**Files:**
- Modify: `src/scaffolding/generation.py`
- Test: `tests/test_task_generation_refusal.py`

**Interfaces:**
- Consumes: Task 2 的 `TaskGeneration.generate_lesson`、`generate_stage`、`origin`。
- Produces: `Rejected`。数量不合法、没有目标记录、数量不一致、题目无法排成要求的数量，或任务创建失败时，不调用之后的步骤，不保存来源记录。生成方抛出的异常原样传出。

- [ ] **Step 1: Write the failing test**

Create `tests/test_task_generation_refusal.py`:

```python
import pytest

from scaffolding.generation import Rejected, TaskGeneration
from scaffolding.records import ChoiceQuestion, SelectionMode
from scaffolding.tasks import TaskCatalog
from tests.generation_helpers import ScriptedGenerator, prepared_objectives, single


class FailingCatalog(TaskCatalog):
    def create(self, questions):
        raise RuntimeError("create failed")


def test_missing_record_and_bad_counts_do_not_call_the_generator():
    _, objectives = prepared_objectives()
    generator = ScriptedGenerator()
    generator.questions = (single(),)
    tasks = TaskCatalog()
    existing = tasks.create((single("已有题"),))
    generation = TaskGeneration(objectives, tasks, generator)

    with pytest.raises(Rejected):
        generation.generate_lesson("沪科教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0)
    with pytest.raises(Rejected):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=0, multiple=0, true_false=0, open_ended=0)
    with pytest.raises(Rejected):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=-1, multiple=0, true_false=0, open_ended=0)
    with pytest.raises(Rejected):
        generation.generate_stage("高中 ", single=1, multiple=0, true_false=0, open_ended=0)

    assert generator.calls == []
    assert tasks.get(existing.task_id).questions[0].prompt == "已有题"
    assert generation.origin(existing.task_id) is None
    with pytest.raises(KeyError):
        tasks.get("task-2")


def test_count_mismatch_creates_nothing():
    _, objectives = prepared_objectives()
    generator = ScriptedGenerator()
    generator.questions = (single("单选甲"), single("单选乙"))
    tasks = TaskCatalog()
    generation = TaskGeneration(objectives, tasks, generator)

    with pytest.raises(Rejected):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0)

    assert generation.origin("task-1") is None
    with pytest.raises(KeyError):
        tasks.get("task-1")


def test_invalid_question_and_generator_failure_create_nothing():
    _, objectives = prepared_objectives()
    tasks = TaskCatalog()
    invalid = ScriptedGenerator()

    def generate(counts, objectives):
        invalid.calls.append((counts, objectives))
        ChoiceQuestion(" ", SelectionMode.SINGLE, ("甲", "乙"), ("甲",), "解析")
        return ()

    invalid.generate = generate
    generation = TaskGeneration(objectives, tasks, invalid)
    with pytest.raises(ValueError):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0)

    failing = ScriptedGenerator()
    failing.error = RuntimeError("down")
    failing.questions = (single(),)
    generation = TaskGeneration(objectives, tasks, failing)
    with pytest.raises(RuntimeError, match="down"):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0)

    assert generation.origin("task-1") is None
    with pytest.raises(KeyError):
        tasks.get("task-1")


def test_failed_create_does_not_store_an_origin():
    _, objectives = prepared_objectives()
    generator = ScriptedGenerator()
    generator.questions = (single(),)
    generation = TaskGeneration(objectives, FailingCatalog(), generator)

    with pytest.raises(RuntimeError, match="create failed"):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0)

    assert generation.origin("task-1") is None
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能识别信息"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_task_generation_refusal.py -v`

Expected: FAIL because a missing record still calls the generator or creates a task.

- [ ] **Step 3: Write minimal implementation**

Add `Rejected` and replace `_generate` in `src/scaffolding/generation.py`:

```python
class Rejected(Exception):
    pass


def _usable_count(value: object) -> bool:
    return type(value) is int and value >= 0
```

```python
    def _generate(
        self,
        objectives: tuple[Objective, ...],
        origin: LessonOrigin | StageOrigin,
        single: int,
        multiple: int,
        true_false: int,
        open_ended: int,
    ) -> Task:
        if not all(_usable_count(value) for value in (single, multiple, true_false, open_ended)):
            raise Rejected("counts must be zero or a positive integer")
        if (single, multiple, true_false, open_ended) == (0, 0, 0, 0) or not objectives:
            raise Rejected("there is no objective record to generate from")
        counts = QuestionCounts(single, multiple, true_false, open_ended)
        ordered = arrange_questions(self._generator.generate(counts, objectives), counts)
        if ordered is None:
            raise Rejected("generated questions do not match the requested counts")
        task = self._tasks.create(ordered)
        self._origins[task.task_id] = origin
        return task
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_question_arrangement.py tests/test_task_generation.py tests/test_task_generation_refusal.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/generation.py tests/test_task_generation_refusal.py
git commit -m "feat: reject task generation that does not match the request"
```

---

### Task 4: 规格验收

**Files:**
- Create: `tests/test_task_generation_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-19-task-generation-design.md`

**Interfaces:**
- Consumes: Task 1 到 Task 3 的全部公开接口。规格文件来自 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-19-task-generation-design.md`，即 `master` 的 `de7a461`。原样复制，不要改写。
- Produces: 验收测试。不新增生产行为。

- [ ] **Step 1: Write the failing test**

Copy the spec file unchanged to `docs/superpowers/specs/2026-10-19-task-generation-design.md`.

Create `tests/test_task_generation_acceptance.py`:

```python
from pathlib import Path

import pytest

from scaffolding.generation import LessonOrigin, Rejected, StageOrigin, TaskGeneration
from scaffolding.knowledge import CurriculumStandard
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft
from scaffolding.scripted import ScriptedScaffoldAgent
from scaffolding.session import Session
from scaffolding.tasks import TaskCatalog
from tests.generation_helpers import ScriptedGenerator, judged, multiple, opened, prepared_objectives, single
from tests.objective_helpers import ScriptedExtractor


class RecordingDecision:
    def __init__(self) -> None:
        self.records = []

    def suggest(self, record):
        self.records.append(record)
        return ()


def test_task_generation_spec_is_in_the_workspace():
    spec = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "specs" / "2026-10-19-task-generation-design.md"
    assert spec.is_file()


def test_generation_matches_the_spec():
    base, objectives = prepared_objectives()
    stored_lesson = base.get_lesson("人教版", "必修一", "信息系统的组成")
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    junior = base.retrieve_stage("初中")
    extractor = ScriptedExtractor()
    extractor.stage_results = (ObjectiveDraft("信息社会责任", "遵守规范", junior.standard_source),)
    stage_objectives = ObjectiveCatalog(base, extractor)
    stage_objectives.extract_stage("初中")
    generator = ScriptedGenerator()
    generator.questions = (opened(), multiple(), single("单选乙"), judged(), single("单选甲"))
    tasks = TaskCatalog()
    hand_made = tasks.create((single("教师自编"),))
    generation = TaskGeneration(objectives, tasks, generator)

    task = generation.generate_lesson(
        "人教版", "必修一", "信息系统的组成", single=2, multiple=1, true_false=1, open_ended=1
    )

    assert task.published is False
    assert [question.prompt for question in task.questions] == ["单选乙", "单选甲", "多选题", "判断题", "综合题"]
    assert generation.origin(task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")
    assert generation.origin(hand_made.task_id) is None
    assert tasks.student_tasks() == ()

    calls = len(generator.calls)
    with pytest.raises(Rejected):
        generation.generate_lesson("沪科教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0)
    with pytest.raises(Rejected):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=0, multiple=0, true_false=0, open_ended=0)
    with pytest.raises(Rejected):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=1.5, multiple=0, true_false=0, open_ended=0)
    assert len(generator.calls) == calls
    assert tasks.get(hand_made.task_id).questions[0].prompt == "教师自编"

    generator.questions = (single(), single())
    with pytest.raises(Rejected):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0)
    failing = ScriptedGenerator()
    failing.error = RuntimeError("down")
    failed = TaskGeneration(objectives, tasks, failing)
    with pytest.raises(RuntimeError):
        failed.generate_lesson("人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0)
    assert generation.origin(task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")

    stage_generator = ScriptedGenerator()
    stage_generator.questions = (judged(),)
    stage_generation = TaskGeneration(stage_objectives, tasks, stage_generator)
    stage_task = stage_generation.generate_stage("初中", single=0, multiple=0, true_false=1, open_ended=0)
    assert stage_generation.origin(stage_task.task_id) == StageOrigin("初中")
    assert generation.origin(task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")

    objectives.edit_statement("objective-1", "改后的目标")
    objectives.delete("objective-1")
    assert [question.prompt for question in tasks.get(task.task_id).questions] == ["单选乙", "单选甲", "多选题", "判断题", "综合题"]
    assert generation.origin(task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")
    tasks.update(task.task_id, (single("教师改过"),))
    tasks.publish(task.task_id)
    assert generation.origin(task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")
    assert base.get_lesson("人教版", "必修一", "信息系统的组成") is stored_lesson

    listed = tasks.student_tasks()
    assert len(listed) == 1
    assert not hasattr(listed[0], "origin")
    decision = RecordingDecision()
    Session(tasks, tasks.start(task.task_id), decision, ScriptedScaffoldAgent())
    assert decision.records[0].questions == tasks.get(task.task_id).questions
    assert not hasattr(decision.records[0], "origin")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_task_generation_acceptance.py -v`

Expected: FAIL because the spec file is not in the worktree yet. If the spec file is already present and the other tests pass, copy nothing and continue.

- [ ] **Step 3: Copy the spec and keep the test**

Copy `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-19-task-generation-design.md` to `docs/superpowers/specs/2026-10-19-task-generation-design.md` in the worktree. Do not edit the spec. Do not change production code unless a test shows a real bug; in that case stop and report it.

- [ ] **Step 4: Run the full suite**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS, including the previous knowledge, objective, task, and scaffolding tests.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_task_generation_acceptance.py docs/superpowers/specs/2026-10-19-task-generation-design.md
git commit -m "test: accept task generation from saved objectives"
```
