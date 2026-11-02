# 任务发布 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 教师发布一份由选择题、判断题、综合题组成的任务；学生提交前可以作答和求助，提交后作答只读、对话只能看历史，参考答案和解析这时才给学生看。

**Architecture:** `TaskCatalog` 保存每份任务的标识、题目和三项事实：是否已发布、学生是否已开始、学生是否已提交。待办和已完成只从这三项显示出来，锁定和删除不读取这两个名称。学生进入任务时得到一份 `StudentWork`。`Session` 仍把决策智能体和支架智能体隔开，但它们读到的是这道任务的题目、参考答案、解析和全部作答。测试不调用大模型。

**Tech Stack:** Python 3.14，pytest 9，标准库。实现从 `origin/main` 建工作区，那个分支上已有支架闭环。本计划在 `master` 的 `5c08d64`。工作区里若没有规格文件，把 `docs/superpowers/specs/2026-10-18-task-publishing-design.md` 从 `5c08d64` 加入该分支。测试命令是 `.\.venv\Scripts\python.exe -m pytest`。

## Global Constraints

- 任务生成、知识库和教学目标不在本计划里。
- 支架的六类、求助交接、HTML 四类内容和导出，仍按 `docs/superpowers/specs/2026-10-18-scaffolding-loop-design.md`。
- 六类支架的原词是：反馈、提示、指导、解释、示范、提问。
- HTML 支架只保留：图片素材、思维导图、结构图、微格动画。
- 学情说明只留在决策智能体内部，不传给支架智能体。支架智能体不读行为记录。
- 两个智能体只读当前这份任务的数据。
- 执行状态的展示名称是「待办」和「已完成」。教师不填写。后端不读取这两个名称。
- 学生进入任务才算开始。只出现在待办列表里不算开始。
- 有学生开始后，任务不能修改，只能删除，并删除该任务的学生端数据。

---

### Task 1: 三种题目

**Files:**
- Modify: `src/scaffolding/records.py`
- Test: `tests/test_questions.py`

**Interfaces:**
- Consumes: 无。
- Produces: `SelectionMode.SINGLE = "单选"`，`SelectionMode.MULTIPLE = "多选"`，`ChoiceQuestion(prompt: str, selection: SelectionMode, choices: tuple[str, ...], answer: tuple[str, ...], explanation: str)`，`TrueFalseQuestion(prompt: str, answer: str, explanation: str)`，`OpenQuestion(prompt: str, requirements: str, answer: str = "", explanation: str = "")`。不合格的题目在构造时抛出 `ValueError`。本任务不删除已有的 `TaskStatement`。

- [ ] **Step 1: Write the failing test**

```python
import pytest

from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion


def test_choice_question_stores_single_and_multiple_keys():
    single = ChoiceQuestion("信息系统包含哪些部分？", SelectionMode.SINGLE, ("人员", "只有硬件"), ("人员",), "人员是组成部分")
    multi = ChoiceQuestion("选出组成", SelectionMode.MULTIPLE, ("人员", "硬件", "天气"), ("人员", "硬件"), "天气不是组成")

    assert single.selection == SelectionMode.SINGLE
    assert single.answer == ("人员",)
    assert multi.answer == ("人员", "硬件")


def test_true_false_and_open_questions_keep_their_fields():
    judged = TrueFalseQuestion("网络属于信息系统", "正确", "网络负责传送")
    opened = OpenQuestion("完成组成说明", "写人员、硬件、软件、数据和网络")

    assert judged.answer == "正确"
    assert opened.answer == ""
    assert opened.explanation == ""


@pytest.mark.parametrize(
    "build",
    [
        lambda: ChoiceQuestion(" ", SelectionMode.SINGLE, ("人员", "硬件"), ("人员",), "解析"),
        lambda: ChoiceQuestion("题目", SelectionMode.SINGLE, ("人员",), ("人员",), "解析"),
        lambda: ChoiceQuestion("题目", SelectionMode.SINGLE, ("人员", "人员"), ("人员",), "解析"),
        lambda: ChoiceQuestion("题目", SelectionMode.SINGLE, ("人员", " "), ("人员",), "解析"),
        lambda: ChoiceQuestion("题目", SelectionMode.SINGLE, ("人员", "硬件"), ("天气",), "解析"),
        lambda: ChoiceQuestion("题目", SelectionMode.SINGLE, ("人员", "硬件"), ("人员", "硬件"), "解析"),
        lambda: ChoiceQuestion("题目", SelectionMode.MULTIPLE, ("人员", "硬件"), (), "解析"),
        lambda: ChoiceQuestion("题目", SelectionMode.SINGLE, ("人员", "硬件"), ("人员",), " "),
        lambda: TrueFalseQuestion(" ", "正确", "解析"),
        lambda: TrueFalseQuestion("题目", "对", "解析"),
        lambda: TrueFalseQuestion("题目", "正确", " "),
        lambda: OpenQuestion(" ", "写出组成"),
        lambda: OpenQuestion("完成说明", " "),
    ],
)
def test_invalid_questions_are_rejected(build):
    with pytest.raises(ValueError):
        build()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_questions.py -v`

Expected: FAIL with `ImportError` for `ChoiceQuestion`.

- [ ] **Step 3: Write minimal implementation**

Append to `src/scaffolding/records.py`:

```python
class SelectionMode(StrEnum):
    SINGLE = "单选"
    MULTIPLE = "多选"


def _filled(value: str) -> bool:
    return value.strip() != ""


@dataclass(frozen=True)
class ChoiceQuestion:
    prompt: str
    selection: SelectionMode
    choices: tuple[str, ...]
    answer: tuple[str, ...]
    explanation: str

    def __post_init__(self) -> None:
        distinct = len(set(self.choices)) == len(self.choices)
        filled = all(_filled(choice) for choice in self.choices)
        if not _filled(self.prompt) or not _filled(self.explanation):
            raise ValueError("choice question needs a prompt and explanation")
        if len(self.choices) < 2 or not distinct or not filled:
            raise ValueError("choice question needs two distinct choices")
        if self.selection == SelectionMode.SINGLE and len(self.answer) != 1:
            raise ValueError("single choice answer must be one choice")
        if self.selection == SelectionMode.MULTIPLE and len(self.answer) < 1:
            raise ValueError("multiple choice answer must be chosen from the choices")
        if any(item not in self.choices for item in self.answer) or len(set(self.answer)) != len(self.answer):
            raise ValueError("answer must be chosen from the choices")


@dataclass(frozen=True)
class TrueFalseQuestion:
    prompt: str
    answer: str
    explanation: str

    def __post_init__(self) -> None:
        if not _filled(self.prompt) or not _filled(self.explanation) or self.answer not in {"正确", "错误"}:
            raise ValueError("true/false question needs a prompt, 正确 or 错误, and explanation")


@dataclass(frozen=True)
class OpenQuestion:
    prompt: str
    requirements: str
    answer: str = ""
    explanation: str = ""

    def __post_init__(self) -> None:
        if not _filled(self.prompt) or not _filled(self.requirements):
            raise ValueError("open question needs a prompt and requirements")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_questions.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/scaffolding/records.py tests/test_questions.py
git commit -m "feat: validate choice, true-false, and open questions"
```

---

### Task 2: 发布、展示和删除

**Files:**
- Create: `src/scaffolding/tasks.py`
- Test: `tests/test_catalog.py`

**Interfaces:**
- Consumes: `ChoiceQuestion`, `OpenQuestion`, `SelectionMode`, `TrueFalseQuestion`。
- Produces: `Rejected(Exception)`，`Task(task_id: str, questions: tuple[Question, ...], published: bool = False, started: bool = False, submitted: bool = False)`，`ListedQuestion(prompt: str, choices: tuple[str, ...] = (), requirements: str = "", selection: str = "")`，`ListedTask(task_id: str, status: str, questions: tuple[ListedQuestion, ...])`，`display_status(task: Task) -> str | None`，`TaskCatalog.create(questions) -> Task`，`get(task_id) -> Task`，`update(task_id, questions) -> Task`，`publish(task_id) -> Task`，`delete(task_id) -> None`，`student_tasks() -> tuple[ListedTask, ...]`。`display_status` 在未发布时返回 `None`，已发布且未提交时返回 `"待办"`，已提交时返回 `"已完成"`。

- [ ] **Step 1: Write the failing test**

```python
import pytest

from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.tasks import ListedQuestion, TaskCatalog


def _questions():
    return (
        ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "天气"), ("人员",), "人员是组成"),
        TrueFalseQuestion("网络负责传送", "正确", "网络是通道"),
        OpenQuestion("写出组成", "覆盖五类组成"),
    )


def test_student_sees_only_published_tasks_as_todo_without_keys():
    catalog = TaskCatalog()
    draft = catalog.create(_questions())
    visible = catalog.create(_questions())
    catalog.publish(visible.task_id)

    assert catalog.student_tasks() == (
        catalog.student_tasks()[0],
    )
    listed = catalog.student_tasks()[0]
    assert listed.task_id == visible.task_id
    assert listed.status == "待办"
    assert listed.questions[0] == ListedQuestion("选出人员", ("人员", "天气"), selection="单选")
    assert listed.questions[1] == ListedQuestion("网络负责传送", ("正确", "错误"))
    assert listed.questions[2] == ListedQuestion("写出组成", requirements="覆盖五类组成")
    assert "人员是组成" not in repr(listed)
    assert draft.task_id not in [item.task_id for item in catalog.student_tasks()]


def test_teacher_can_edit_before_a_student_starts_and_can_delete():
    catalog = TaskCatalog()
    task = catalog.create(_questions())
    catalog.publish(task.task_id)
    revised = (OpenQuestion("改后的综合题", "只写网络"),)
    updated = catalog.update(task.task_id, revised)

    assert updated.published is True
    assert updated.questions == revised
    catalog.delete(task.task_id)
    assert catalog.student_tasks() == ()


def test_started_task_cannot_be_edited_and_delete_removes_it():
    catalog = TaskCatalog()
    task = catalog.create(_questions())
    catalog.publish(task.task_id)
    catalog.start(task.task_id)

    with pytest.raises(Exception):
        catalog.update(task.task_id, (OpenQuestion("不能改", "不能改"),))
    assert catalog.get(task.task_id).questions[0].prompt == "选出人员"
    catalog.delete(task.task_id)
    with pytest.raises(KeyError):
        catalog.get(task.task_id)


def test_empty_task_cannot_be_published_or_started():
    catalog = TaskCatalog()
    task = catalog.create(())

    with pytest.raises(Exception):
        catalog.publish(task.task_id)
    with pytest.raises(Exception):
        catalog.start(task.task_id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_catalog.py -v`

Expected: FAIL with `ImportError` for `TaskCatalog`.

- [ ] **Step 3: Write minimal implementation**

Create `src/scaffolding/tasks.py`:

```python
from dataclasses import dataclass, replace

from scaffolding.records import ChoiceQuestion, OpenQuestion, TrueFalseQuestion

Question = ChoiceQuestion | TrueFalseQuestion | OpenQuestion


class Rejected(Exception):
    pass


@dataclass(frozen=True)
class Task:
    task_id: str
    questions: tuple[Question, ...]
    published: bool = False
    started: bool = False
    submitted: bool = False


@dataclass(frozen=True)
class ListedQuestion:
    prompt: str
    choices: tuple[str, ...] = ()
    requirements: str = ""
    selection: str = ""


@dataclass(frozen=True)
class ListedTask:
    task_id: str
    status: str
    questions: tuple[ListedQuestion, ...]


def display_status(task: Task) -> str | None:
    if not task.published:
        return None
    if task.submitted:
        return "已完成"
    return "待办"


def _public(question: Question) -> ListedQuestion:
    if isinstance(question, ChoiceQuestion):
        return ListedQuestion(question.prompt, question.choices, selection=question.selection.value)
    if isinstance(question, TrueFalseQuestion):
        return ListedQuestion(question.prompt, ("正确", "错误"))
    return ListedQuestion(question.prompt, requirements=question.requirements)


class TaskCatalog:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._next_id = 1

    def create(self, questions: tuple[Question, ...]) -> Task:
        task = Task(f"task-{self._next_id}", questions)
        self._next_id += 1
        self._tasks[task.task_id] = task
        return task

    def get(self, task_id: str) -> Task:
        return self._tasks[task_id]

    def update(self, task_id: str, questions: tuple[Question, ...]) -> Task:
        task = self.get(task_id)
        if task.started:
            raise Rejected("started tasks can only be deleted")
        updated = replace(task, questions=questions)
        self._tasks[task_id] = updated
        return updated

    def publish(self, task_id: str) -> Task:
        task = self.get(task_id)
        if task.questions == ():
            raise Rejected("a task needs a question before publish")
        updated = replace(task, published=True)
        self._tasks[task_id] = updated
        return updated

    def delete(self, task_id: str) -> None:
        del self._tasks[task_id]

    def student_tasks(self) -> tuple[ListedTask, ...]:
        listed = []
        for task in self._tasks.values():
            status = display_status(task)
            if status is None:
                continue
            listed.append(ListedTask(task.task_id, status, tuple(_public(question) for question in task.questions)))
        return tuple(listed)

    def start(self, task_id: str) -> Task:
        task = self.get(task_id)
        if not task.published or task.started or task.questions == ():
            raise Rejected("student cannot start")
        updated = replace(task, started=True)
        self._tasks[task_id] = updated
        return updated
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_catalog.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/scaffolding/tasks.py tests/test_catalog.py
git commit -m "feat: publish tasks and lock them after a student starts"
```

---

### Task 3: 每题作答

**Files:**
- Modify: `src/scaffolding/records.py`
- Modify: `src/scaffolding/tasks.py`
- Test: `tests/test_item_answers.py`

**Interfaces:**
- Consumes: Task 1 的三种题目，Task 2 的 `TaskCatalog.start`。
- Produces: `ItemAnswer(text: str = "", selected: tuple[str, ...] = (), text_revisions: tuple[str, ...] = (), selected_revisions: tuple[tuple[str, ...], ...] = ())`，`apply_answer(question, current, *, text: str | None = None, selected: tuple[str, ...] | None = None) -> ItemAnswer`，`StudentWork(task_id: str, questions: tuple[Question, ...])`。`StudentWork.answers` 初始每题都是空的 `ItemAnswer`。`StudentWork.edit(index, *, text=None, selected=None)` 用 `apply_answer` 替换该题作答。`TaskCatalog.start` 改为返回 `StudentWork`，并在目录里记住它。`TaskCatalog.work(task_id) -> StudentWork`。`delete` 同时丢掉这份 `StudentWork`。

- [ ] **Step 1: Write the failing test**

```python
import pytest

from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.tasks import TaskCatalog


def test_each_question_starts_blank_and_keeps_its_own_revision():
    catalog = TaskCatalog()
    task = catalog.create(
        (
            ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "天气"), ("人员",), "人员是组成"),
            ChoiceQuestion("选出组成", SelectionMode.MULTIPLE, ("人员", "硬件"), ("人员", "硬件"), "两项都是"),
            TrueFalseQuestion("网络负责传送", "错误", "网络是通道"),
            OpenQuestion("写出组成", "覆盖五类组成"),
        )
    )
    catalog.publish(task.task_id)
    work = catalog.start(task.task_id)

    assert all(answer.text == "" and answer.selected == () for answer in work.answers)
    work.edit(0, selected=("人员",))
    work.edit(0, selected=("天气",))
    work.edit(1, selected=("硬件", "人员"))
    work.edit(2, selected=("正确",))
    work.edit(3, text="只写了人员")

    assert work.answers[0].selected == ("天气",)
    assert work.answers[0].selected_revisions == ((), ("人员",))
    assert work.answers[1].selected == ("硬件", "人员")
    assert work.answers[2].selected == ("正确",)
    assert work.answers[3].text == "只写了人员"
    assert work.answers[3].text_revisions == ("",)


@pytest.mark.parametrize(
    ("index", "kwargs"),
    [
        (0, {"selected": ("人员", "天气")}),
        (0, {"selected": ("教室",)}),
        (1, {"selected": ("教室",)}),
        (2, {"selected": ("也许",)}),
        (2, {"text": "一段文字"}),
        (3, {"selected": ("人员",)}),
    ],
)
def test_invalid_answers_leave_the_previous_answer(index: int, kwargs: dict):
    catalog = TaskCatalog()
    task = catalog.create(
        (
            ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "天气"), ("人员",), "人员是组成"),
            ChoiceQuestion("选出组成", SelectionMode.MULTIPLE, ("人员", "硬件"), ("人员", "硬件"), "两项都是"),
            TrueFalseQuestion("网络负责传送", "正确", "网络是通道"),
            OpenQuestion("写出组成", "覆盖五类组成"),
        )
    )
    catalog.publish(task.task_id)
    work = catalog.start(task.task_id)
    before = work.answers[index]

    with pytest.raises(Exception):
        work.edit(index, **kwargs)

    assert work.answers[index] == before


def test_delete_removes_the_student_work():
    catalog = TaskCatalog()
    task = catalog.create((OpenQuestion("写出组成", "覆盖五类组成"),))
    catalog.publish(task.task_id)
    catalog.start(task.task_id)

    catalog.delete(task.task_id)

    with pytest.raises(KeyError):
        catalog.work(task.task_id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_item_answers.py -v`

Expected: FAIL because `start` returns `Task` and has no `edit`.

- [ ] **Step 3: Write minimal implementation**

Append `ItemAnswer` to `src/scaffolding/records.py`:

```python
@dataclass(frozen=True)
class ItemAnswer:
    text: str = ""
    selected: tuple[str, ...] = ()
    text_revisions: tuple[str, ...] = ()
    selected_revisions: tuple[tuple[str, ...], ...] = ()
```

Add to `src/scaffolding/tasks.py`:

```python
from scaffolding.records import ChoiceQuestion, ItemAnswer, OpenQuestion, SelectionMode, TrueFalseQuestion


def apply_answer(question, current: ItemAnswer, *, text: str | None = None, selected: tuple[str, ...] | None = None) -> ItemAnswer:
    if isinstance(question, OpenQuestion):
        if selected not in (None, ()):
            raise Rejected("open questions have no choices")
        new_text = current.text if text is None else text
        revisions = current.text_revisions + ((current.text,) if new_text != current.text else ())
        return ItemAnswer(text=new_text, text_revisions=revisions)
    if text not in (None, ""):
        raise Rejected("this question stores selected options")
    new_selected = current.selected if selected is None else selected
    if isinstance(question, TrueFalseQuestion) and new_selected not in ((), ("正确",), ("错误",)):
        raise Rejected("true/false answers are 正确 or 错误")
    if isinstance(question, ChoiceQuestion):
        if any(item not in question.choices for item in new_selected) or len(set(new_selected)) != len(new_selected):
            raise Rejected("selection must be one of the choices")
        if question.selection == SelectionMode.SINGLE and len(new_selected) > 1:
            raise Rejected("single choice takes one option")
    revisions = current.selected_revisions + ((current.selected,) if new_selected != current.selected else ())
    return ItemAnswer(selected=new_selected, selected_revisions=revisions)


class StudentWork:
    def __init__(self, task_id: str, questions: tuple) -> None:
        self.task_id = task_id
        self.questions = questions
        self.answers = tuple(ItemAnswer() for _ in questions)
        self.submitted = False

    def edit(self, index: int, *, text: str | None = None, selected: tuple[str, ...] | None = None) -> None:
        if self.submitted:
            raise Rejected("submitted answers are read only")
        updated = apply_answer(self.questions[index], self.answers[index], text=text, selected=selected)
        answers = list(self.answers)
        answers[index] = updated
        self.answers = tuple(answers)
```

Change `TaskCatalog` to store works:

```python
def __init__(self) -> None:
    self._tasks: dict[str, Task] = {}
    self._works: dict[str, StudentWork] = {}
    self._next_id = 1

def start(self, task_id: str) -> StudentWork:
    task = self.get(task_id)
    if not task.published or task.started or task.questions == ():
        raise Rejected("student cannot start")
    self._tasks[task_id] = replace(task, started=True)
    work = StudentWork(task_id, task.questions)
    self._works[task_id] = work
    return work

def work(self, task_id: str) -> StudentWork:
    return self._works[task_id]

def delete(self, task_id: str) -> None:
    del self._tasks[task_id]
    self._works.pop(task_id, None)
```

Update `tests/test_catalog.py` so `catalog.start` is still called, but the return value is no longer treated as `Task`. The existing catalog tests already use `catalog.get` after start, so they stay valid.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_item_answers.py tests/test_catalog.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/scaffolding/records.py src/scaffolding/tasks.py tests/test_item_answers.py tests/test_catalog.py
git commit -m "feat: store one answer and its revisions per question"
```

---

### Task 4: 闭环改读这份任务

**Files:**
- Modify: `src/scaffolding/records.py`
- Modify: `src/scaffolding/agents.py`
- Modify: `src/scaffolding/scripted.py`
- Modify: `src/scaffolding/session.py`
- Modify: `src/scaffolding/tasks.py`
- Create: `tests/helpers.py`
- Modify: `tests/test_records.py`
- Modify: `tests/test_session_presets.py`
- Modify: `tests/test_edit_answer.py`
- Modify: `tests/test_help_handoff.py`
- Modify: `tests/test_failures.py`
- Modify: `tests/test_assets.py`
- Modify: `tests/test_acceptance.py`

**Interfaces:**
- Consumes: `StudentWork`, `ItemAnswer`, `Question`, `TaskCatalog`, `Rejected`。
- Produces: `TaskRecord(questions: tuple[Question, ...], answers: tuple[ItemAnswer, ...], behavior: Behavior = Behavior())`。删除 `TaskStatement` 和 `AnswerState`。`DecisionAgent.suggest(record: TaskRecord) -> tuple[str, ...]`，`choose_type(record: TaskRecord, question: str) -> str`。`ScaffoldAgent.produce(scaffold_type: str, question: str, questions: tuple, answers: tuple[ItemAnswer, ...]) -> ScaffoldDraft`。`StudentWork.behavior: Behavior`，`StudentWork.dialogue: tuple[DialogueTurn, ...]`。`DialogueTurn(question: str, source: HelpSource, scaffold: Scaffold | None)`。`Session(catalog: TaskCatalog, work: StudentWork, decision: DecisionAgent, scaffold_agent: ScaffoldAgent)`。`Session.edit_answer(index: int, *, text: str | None = None, selected: tuple[str, ...] | None = None) -> PageView`。`Session.ask(question: str, source: HelpSource) -> PageView`。`Session.note_dwell(seconds: float) -> None`。`PageView(presets, scaffold, dialogue=(), answers_locked=False, send_closed=False, revealed=(), status="待办")`。

- [ ] **Step 1: Write the failing test**

Replace `tests/test_session_presets.py` with:

```python
from scaffolding.records import OpenQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.tasks import TaskCatalog
from scaffolding.session import Session


def test_before_help_the_page_shows_presets_and_no_scaffold():
    decision = ScriptedDecisionAgent(presets=("这一步要判断什么？", "作品还缺哪一部分？"))
    catalog = TaskCatalog()
    task = catalog.create((OpenQuestion("完成作品并判断说法", "写出组成"),))
    catalog.publish(task.task_id)
    session = Session(catalog, catalog.start(task.task_id), decision, ScriptedScaffoldAgent())

    view = session.view()

    assert view.presets == ("这一步要判断什么？", "作品还缺哪一部分？")
    assert view.scaffold is None
    assert view.status == "待办"
    assert decision.choose_calls == []
```

Replace `tests/test_help_handoff.py` with:

```python
from scaffolding.agents import ScaffoldDraft
from scaffolding.records import Asset, AssetKind, HelpSource, ItemAnswer, OpenQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.session import Session
from scaffolding.tasks import TaskCatalog


def _session(scaffold_agent: ScriptedScaffoldAgent):
    decision = ScriptedDecisionAgent(presets=("这一步要判断什么？",), scaffold_type="示范")
    catalog = TaskCatalog()
    task = catalog.create((OpenQuestion("完成作品并判断说法", "写出组成说明", answer="五类都要写", explanation="人员硬件软件数据和网络"),))
    catalog.publish(task.task_id)
    work = catalog.start(task.task_id)
    work.edit(0, text="人员已经写了")
    session = Session(catalog, work, decision, scaffold_agent)
    return session, decision


def test_clicking_a_preset_passes_that_sentence_type_and_keys():
    scaffold_agent = ScriptedScaffoldAgent(ScaffoldDraft(text="示范：这一步要判断什么？"))
    session, decision = _session(scaffold_agent)

    view = session.ask("这一步要判断什么？", HelpSource.PRESET)

    assert decision.choose_calls[0][1] == "这一步要判断什么？"
    call = scaffold_agent.calls[0]
    assert call["scaffold_type"] == "示范"
    assert call["question"] == "这一步要判断什么？"
    assert set(call) == {"scaffold_type", "question", "questions", "answers"}
    assert call["questions"][0].explanation == "人员硬件软件数据和网络"
    assert call["answers"] == (ItemAnswer(text="人员已经写了", text_revisions=("",)),)
    assert "dwell_seconds" not in call
    assert view.scaffold is not None
    assert view.scaffold.text == "示范：这一步要判断什么？"


def test_an_owned_question_is_passed_verbatim():
    scaffold_agent = ScriptedScaffoldAgent(ScaffoldDraft(text="提示：我自己的问题"))
    session, _decision = _session(scaffold_agent)

    session.ask("我自己的问题", HelpSource.OWN)

    assert scaffold_agent.calls[0]["question"] == "我自己的问题"
    assert session.record.behavior.helps[-1].source == HelpSource.OWN
    assert session.view().dialogue[-1].question == "我自己的问题"


def test_behavior_is_not_given_to_the_scaffold_agent():
    scaffold_agent = ScriptedScaffoldAgent(ScaffoldDraft(assets=(Asset(AssetKind.IMAGE, "figure.png", b"png"),)))
    session, _decision = _session(scaffold_agent)
    session.note_dwell(42)

    session.ask("我自己的问题", HelpSource.OWN)

    call = scaffold_agent.calls[0]
    assert "42" not in repr(call["answers"])
    assert "更早的问题" not in repr(call)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_session_presets.py tests/test_help_handoff.py -v`

Expected: FAIL while `Session` still takes `TaskRecord`.

- [ ] **Step 3: Write minimal implementation**

Replace `TaskStatement`, `AnswerState`, and `TaskRecord` in `src/scaffolding/records.py` with:

```python
@dataclass(frozen=True)
class TaskRecord:
    questions: tuple
    answers: tuple[ItemAnswer, ...]
    behavior: Behavior = Behavior()
```

把 `TaskRecord` 放在三种题目和 `ItemAnswer` 之后，字段写成 `questions: tuple[ChoiceQuestion | TrueFalseQuestion | OpenQuestion, ...]`。`Session` 保存 `self._catalog`、`self.work`、`self._decision` 和 `self._scaffold_agent`。

Replace `ScaffoldAgent.produce` in `src/scaffolding/agents.py`:

```python
def produce(self, scaffold_type: str, question: str, questions: tuple, answers: tuple) -> ScaffoldDraft:
    ...
```

Remove the `TaskStatement` and `AnswerState` imports from `agents.py`.

Change `ScriptedScaffoldAgent.produce` so the recorded dict uses `questions` and `answers` instead of `statement` and `answer`.

Add `behavior = Behavior()` and `dialogue: tuple = ()` on `StudentWork`.

Replace `src/scaffolding/session.py` with a session that:

- builds `TaskRecord` from `work.questions`, `work.answers`, and `work.behavior`
- on init calls `decision.suggest(record)` and stores presets
- `edit_answer` calls `work.edit`, then refreshes presets, and does not clear `_scaffold`
- `note_dwell` replaces only `work.behavior.dwell_seconds`
- `ask` returns the current view when `question.strip() == ""` and does not record a help event
- otherwise appends `HelpEvent` before choosing a type
- on an illegal type, a decision exception, a scaffold exception, or an empty visible scaffold, appends `DialogueTurn(question, source, None)` and returns the existing view
- on success, stores the visible scaffold and appends `DialogueTurn(question, source, scaffold)`
- `view` returns presets, the current scaffold, dialogue, `status="待办"`, and empty revealed keys
- `produce` is called as `produce(scaffold_type, question, work.questions, work.answers)`

Keep `_visible_scaffold` unchanged.

Create `tests/helpers.py`:

```python
from scaffolding.records import OpenQuestion, TrueFalseQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.session import Session
from scaffolding.tasks import TaskCatalog


def open_session(decision=None, scaffold_agent=None, prompt="判断说法"):
    catalog = TaskCatalog()
    task = catalog.create((TrueFalseQuestion(prompt, "正确", "题目里有依据"),))
    catalog.publish(task.task_id)
    work = catalog.start(task.task_id)
    return Session(
        catalog,
        work,
        decision if decision is not None else ScriptedDecisionAgent(),
        scaffold_agent if scaffold_agent is not None else ScriptedScaffoldAgent(),
    )
```

Update the remaining tests to use `open_session` or an `OpenQuestion` session:

- `tests/test_records.py`: delete the `TaskStatement` test. Keep the help-source test and the vocabulary test.
- `tests/test_edit_answer.py`: build an `OpenQuestion("完成作品", "写出组成")`. `edit_answer(0, text="第一次写了人员")`. Assert `session.work.questions[0].prompt == "完成作品"`, `answers[0].text == "第一次写了人员"`, and `text_revisions == ("",)`. The changing decision reads `record.answers[0].text`.
- `tests/test_failures.py`: `_session` uses `open_session`. Empty-answer assertion becomes `session.work.answers[0].selected == ()`. Behavior assertions stay on `session.record.behavior`.
- `tests/test_assets.py`: replace both `Session(TaskRecord(...))` constructions with `open_session(decision, scaffold_agent, prompt="完成作品")`.
- `tests/test_acceptance.py`: build one published task containing `TrueFalseQuestion("判断说法", "正确", "按题目判断")` and `OpenQuestion("完成一份信息系统组成说明", "说明人员、硬件、软件、数据和网络")`. Drive answers with `edit_answer`. Assert the scaffold call keys are `questions` and `answers`, and that the open-question text contains the student's words. Leave the export assertions as they are.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/scaffolding tests
git commit -m "feat: open the scaffolding loop on one published task"
```

---

### Task 5: 提交锁定

**Files:**
- Modify: `src/scaffolding/tasks.py`
- Modify: `src/scaffolding/session.py`
- Test: `tests/test_submit.py`

**Interfaces:**
- Consumes: Task 4 的 `Session`、`PageView`、`DialogueTurn`、`StudentWork`。
- Produces: `Revealed(answer: str | tuple[str, ...], explanation: str)`，`TaskCatalog.mark_submitted(task_id: str) -> Task`，`Session.submit() -> PageView`。`mark_submitted` 只把 `Task.submitted` 设为 `True`。已开始的任务仍然不能 `update`。提交后的 `PageView.answers_locked` 和 `send_closed` 为 `True`，`status` 为 `"已完成"`，`presets` 为 `()`，`revealed` 按题目顺序给出参考答案和解析，`dialogue` 保留提交前的记录。

- [ ] **Step 1: Write the failing test**

```python
import pytest

from scaffolding.agents import ScaffoldDraft
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.session import Session
from scaffolding.tasks import TaskCatalog
from scaffolding.records import HelpSource


def _session():
    catalog = TaskCatalog()
    secret = catalog.create((OpenQuestion("其他任务", "不要读到机密解析", explanation="机密解析"),))
    catalog.publish(secret.task_id)
    task = catalog.create(
        (
            ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "天气"), ("人员",), "人员是组成"),
            OpenQuestion("写出组成", "覆盖五类组成"),
        )
    )
    catalog.publish(task.task_id)
    decision = ScriptedDecisionAgent(presets=("还缺什么？",), scaffold_type="提示")
    scaffold_agent = ScriptedScaffoldAgent(ScaffoldDraft(text="提示：还缺什么？"))
    session = Session(catalog, catalog.start(task.task_id), decision, scaffold_agent)
    return catalog, session, secret


def test_keys_stay_hidden_until_submit_and_then_the_page_locks():
    catalog, session, _secret = _session()
    session.edit_answer(1, text="只写了人员")
    session.ask("还缺什么？", HelpSource.PRESET)
    before = session.view()

    assert before.revealed == ()
    assert before.answers_locked is False
    assert "人员是组成" not in repr(catalog.student_tasks())

    after = session.submit()

    assert after.answers_locked is True
    assert after.send_closed is True
    assert after.status == "已完成"
    assert after.presets == ()
    assert after.revealed[0].answer == ("人员",)
    assert after.revealed[0].explanation == "人员是组成"
    assert after.revealed[1].answer == ""
    assert after.dialogue[-1].question == "还缺什么？"
    assert after.scaffold is not None
    assert catalog.student_tasks()[1].status == "已完成"
    with pytest.raises(Exception):
        session.edit_answer(1, text="提交后再改")
    with pytest.raises(Exception):
        session.ask("还能问吗？", HelpSource.OWN)
    assert session.work.answers[1].text == "只写了人员"


def test_agents_do_not_receive_another_task():
    _catalog, session, secret = _session()
    decision = session._decision
    session.ask("还缺什么？", HelpSource.PRESET)

    assert "机密解析" not in repr(decision.choose_calls)
    assert "其他任务" not in repr(session._scaffold_agent.calls)


def test_empty_answers_can_be_submitted():
    catalog = TaskCatalog()
    task = catalog.create((OpenQuestion("写出组成", "覆盖五类组成"),))
    catalog.publish(task.task_id)
    session = Session(catalog, catalog.start(task.task_id), ScriptedDecisionAgent(), ScriptedScaffoldAgent())

    view = session.submit()

    assert session.work.answers[0].text == ""
    assert view.answers_locked is True
    assert view.revealed[0].answer == ""


def test_submit_does_not_let_the_teacher_edit():
    catalog, session, secret = _session()
    session.submit()

    with pytest.raises(Exception):
        catalog.update(session.work.task_id, (OpenQuestion("提交后改题", "不允许"),))
    catalog.delete(session.work.task_id)
    assert [item.task_id for item in catalog.student_tasks()] == [secret.task_id]
```

The second listed task is `secret` only if it was published before `task`. Assert the status of the task the session started: `catalog.get(session.work.task_id)` is submitted, and `display_status` of that task is `"已完成"`. Do not depend on list position. Use `next(item for item in catalog.student_tasks() if item.task_id == session.work.task_id)`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_submit.py -v`

Expected: FAIL because `Session.submit` does not exist.

- [ ] **Step 3: Write minimal implementation**

Add to `src/scaffolding/session.py`:

```python
@dataclass(frozen=True)
class Revealed:
    answer: str | tuple[str, ...]
    explanation: str


def _revealed(question) -> Revealed:
    if isinstance(question, OpenQuestion):
        return Revealed(question.answer, question.explanation)
    if isinstance(question, TrueFalseQuestion):
        return Revealed(question.answer, question.explanation)
    return Revealed(question.answer, question.explanation)
```

`Session.submit`:

```python
def submit(self) -> PageView:
    if self.work.submitted:
        raise Rejected("already submitted")
    self.work.submitted = True
    self._catalog.mark_submitted(self.work.task_id)
    self._presets = ()
    return self.view()
```

`view` uses `tuple(_revealed(question) for question in self.work.questions)` only when `self.work.submitted`. It sets `answers_locked` and `send_closed` from `self.work.submitted`, and `status` to `"已完成"` when submitted, otherwise `"待办"`.

`edit_answer` and `ask` raise `Rejected` when `self.work.submitted` before changing answers, behavior, or dialogue.

`TaskCatalog.mark_submitted`:

```python
def mark_submitted(self, task_id: str) -> Task:
    task = self.get(task_id)
    if not task.started:
        raise Rejected("cannot submit before start")
    updated = replace(task, submitted=True)
    self._tasks[task_id] = updated
    return updated
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/scaffolding/tasks.py src/scaffolding/session.py tests/test_submit.py
git commit -m "feat: lock answers and dialogue after the student submits"
```

---

### Task 6: 规格验收

**Files:**
- Create: `tests/test_task_acceptance.py`
- The spec file `docs/superpowers/specs/2026-10-18-task-publishing-design.md` must be in the worktree.

**Interfaces:**
- Consumes: Tasks 1–5 的公开类型。
- Produces: 无新的生产接口。

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

import pytest

from scaffolding.agents import ScaffoldDraft
from scaffolding.records import ChoiceQuestion, HelpSource, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.session import Session
from scaffolding.tasks import TaskCatalog


def test_task_publishing_spec_is_in_the_workspace():
    spec = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "specs" / "2026-10-18-task-publishing-design.md"
    assert spec.is_file()


def test_published_task_matches_the_spec():
    catalog = TaskCatalog()
    task = catalog.create(
        (
            ChoiceQuestion("选出人员", SelectionMode.MULTIPLE, ("人员", "硬件", "天气"), ("人员", "硬件"), "天气不是组成"),
            TrueFalseQuestion("网络负责传送", "正确", "网络是通道"),
            OpenQuestion("写出组成", "覆盖五类组成"),
        )
    )
    assert catalog.student_tasks() == ()
    catalog.publish(task.task_id)
    assert catalog.student_tasks()[0].status == "待办"

    decision = ScriptedDecisionAgent(presets=("还缺哪一类？",), scaffold_type="提示")
    scaffold_agent = ScriptedScaffoldAgent(ScaffoldDraft(text="提示：还缺哪一类？"))
    session = Session(catalog, catalog.start(task.task_id), decision, scaffold_agent)
    with pytest.raises(Exception):
        catalog.update(task.task_id, (OpenQuestion("开始后不能改", "开始后不能改"),))

    session.edit_answer(0, selected=("人员",))
    asked = session.ask("还缺哪一类？", HelpSource.PRESET)
    assert asked.revealed == ()
    assert asked.scaffold is not None
    assert scaffold_agent.calls[0]["questions"][0].explanation == "天气不是组成"
    assert "behavior" not in scaffold_agent.calls[0]

    blank = session.ask("   ", HelpSource.OWN)
    assert blank.scaffold.text == "提示：还缺哪一类？"
    assert len(scaffold_agent.calls) == 1

    done = session.submit()
    assert done.answers_locked is True
    assert done.send_closed is True
    assert done.dialogue[0].question == "还缺哪一类？"
    assert done.revealed[2].answer == ""
    assert catalog.get(task.task_id).submitted is True

    catalog.delete(task.task_id)
    assert catalog.student_tasks() == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_task_acceptance.py -v`

Expected: FAIL only if the spec file is missing. If the file is already present and Tasks 1–5 passed, this test should already PASS; then skip straight to the commit after confirming PASS.

- [ ] **Step 3: Add the spec file when it is missing**

Copy `docs/superpowers/specs/2026-10-18-task-publishing-design.md` from commit `5c08d64` into the worktree. Do not rewrite it.

- [ ] **Step 4: Run the whole suite**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_task_acceptance.py docs/superpowers/specs/2026-10-18-task-publishing-design.md
git commit -m "test: accept a published task through submit"
```
