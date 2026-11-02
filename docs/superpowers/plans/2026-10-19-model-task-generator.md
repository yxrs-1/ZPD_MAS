# 模型生成题目 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 DeepSeek 按一份已保存的目标记录交回题目，并仍由现有任务生成创建未发布任务。

**Architecture:** 新的 `model_generator.py` 提供解析、提示词、模型生成方和 DeepSeek 完成函数。`TaskGeneration` 不改，只把模型生成方当作原来的生成方传入。网络请求由注入的发送函数发出，测试不打开套接字。

**Tech Stack:** Python 3.14，pytest 9，标准库。实现从 `origin/main` 建工作区。规格在本地 `master` 的 `e42e9d7`，文件是 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-19-model-task-generator-design.md`。工作区里若没有这份规格，从该提交原样复制，不要改写。测试命令是 `.\.venv\Scripts\python.exe -m pytest`。PowerShell 下不要使用 `&&` 或 bash heredoc；提交用 `git commit -m "message"`。不要改 git config，不要 push。

## Global Constraints

- 本计划只把任务生成方换成 DeepSeek。目标提炼方、决策智能体和支架智能体不在这里。
- 数量检查、题目排列、未发布任务和教师查看的来源记录仍按任务生成规格执行。
- 现有题目对象的规则不改。教师发布前仍可按任务发布规格修改题目，选择题至少保留两个互不相同的非空选项。
- 测试不访问网络。
- 模型生成方实现 `generate(counts, objectives)`。它不创建任务，不写来源记录，不改知识库和目标库，也不读取密钥。
- 完成函数接收系统消息和用户消息，返回正文。生产使用 DeepSeek 完成函数。测试换上返回事先写好正文的函数。
- DeepSeek 请求发往 `https://api.deepseek.com/chat/completions`，模型是 `deepseek-flash`，非流式，`thinking` 的 `type` 是 `disabled`，不带 `reasoning_effort`。
- 密钥从 `DEEPSEEK_API_KEY` 读取，放在 `Authorization` 里，形式是 `Bearer` 加上这个密钥。未设置或去掉空白后为空时不发送请求。
- 状态码是 200，且 `choices[0].message.content` 是字符串时，只把这段正文交回。
- 系统消息写明 JSON 形状和题目规则。用户消息只写四种数量，以及这一份记录里每条目标的维度、表述和来源。目标标识、教材原文、课标原文、其他目标记录和学生作答不写入。
- 正文去掉前后空白后必须直接是约定的 JSON。四个键是单选、多选、判断、综合，不能多也不能少。数量为 0 的那一类是空数组，键仍保留。
- 单选和多选的选项必须正好四个，互不相同，去掉空白后都不为空。这一条由模型生成方检查。
- 同一类数组里的先后，就是交回给现有流程的先后。
- 失败抛出任务生成的 `Rejected`。题目对象拒绝也变成这个 `Rejected`。不创建任务，不保存来源记录，已有任务保持不变。完成函数只调用一次，不重试。
- 数量不合法、四种数量都是 0，或没有这份目标记录时，不调用完成函数。
- JSON 形状通过但某一类数量与指定的不一致时，仍由现有检查拒绝。这次完成函数已经被调用过一次。
- 不修改 `records.py`、`generation.py`、`knowledge.py`、`objectives.py`、`tasks.py`、`session.py`。

## File Map

- Create: `src/scaffolding/model_generator.py` — 解析正文、组成两条消息、模型生成方、DeepSeek 完成函数。
- Create: `tests/test_model_question_parsing.py`
- Create: `tests/test_model_prompt.py`
- Create: `tests/test_model_generation.py`
- Create: `tests/test_deepseek_completion.py`
- Create: `tests/test_model_generation_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-19-model-task-generator-design.md`
- Do not modify: `src/scaffolding/records.py`、`generation.py`、`knowledge.py`、`objectives.py`、`tasks.py`、`session.py`

---

### Task 1: 把模型正文解析成现有题目

**Files:**
- Create: `src/scaffolding/model_generator.py`
- Test: `tests/test_model_question_parsing.py`

**Interfaces:**
- Consumes: `Rejected`，来自 `scaffolding.generation`。`ChoiceQuestion`、`TrueFalseQuestion`、`OpenQuestion`、`SelectionMode`，来自 `scaffolding.records`。
- Produces: `parse_questions(text: str) -> tuple`。合格时按单选、多选、判断、综合返回现有题目对象。同一类保持数组里的先后。形状、类型、选项数量或题目对象拒绝时抛出 `Rejected`。

- [ ] **Step 1: Write the failing test**

Create `tests/test_model_question_parsing.py`:

```python
import json

import pytest

from scaffolding.generation import Rejected
from scaffolding.model_generator import parse_questions
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion


def _body(**overrides) -> str:
    body = {
        "单选": [
            {"题目": "单选乙", "选项": ["甲", "乙", "丙", "丁"], "参考答案": ["乙"], "解析": "原因乙"},
            {"题目": "单选甲", "选项": ["甲", "乙", "丙", "丁"], "参考答案": ["甲"], "解析": "原因甲"},
        ],
        "多选": [
            {"题目": "多选题", "选项": ["甲", "乙", "丙", "丁"], "参考答案": ["甲", "丙"], "解析": "原因"},
        ],
        "判断": [
            {"题目": "判断题", "参考答案": "错误", "解析": "原因"},
        ],
        "综合": [
            {"题目": "综合题", "作答要求": "写出过程", "参考答案": "", "解析": ""},
        ],
    }
    body.update(overrides)
    return json.dumps(body, ensure_ascii=False)


def test_questions_keep_array_order_and_existing_types():
    questions = parse_questions("\n" + _body() + " ")

    assert questions == (
        ChoiceQuestion("单选乙", SelectionMode.SINGLE, ("甲", "乙", "丙", "丁"), ("乙",), "原因乙"),
        ChoiceQuestion("单选甲", SelectionMode.SINGLE, ("甲", "乙", "丙", "丁"), ("甲",), "原因甲"),
        ChoiceQuestion("多选题", SelectionMode.MULTIPLE, ("甲", "乙", "丙", "丁"), ("甲", "丙"), "原因"),
        TrueFalseQuestion("判断题", "错误", "原因"),
        OpenQuestion("综合题", "写出过程", "", ""),
    )


def test_an_empty_array_contributes_no_questions():
    questions = parse_questions(_body(综合=[]))

    assert [type(question) for question in questions] == [ChoiceQuestion, ChoiceQuestion, ChoiceQuestion, TrueFalseQuestion]


def test_a_code_fence_or_wrong_shape_is_rejected():
    fenced = "```json\n" + _body() + "\n```"
    extra = json.loads(_body())
    extra["其他"] = []
    missing = json.loads(_body())
    del missing["判断"]
    with pytest.raises(Rejected):
        parse_questions(fenced)
    with pytest.raises(Rejected):
        parse_questions(json.dumps(extra, ensure_ascii=False))
    with pytest.raises(Rejected):
        parse_questions(json.dumps(missing, ensure_ascii=False))


def test_choice_options_must_be_exactly_four_distinct_filled_strings():
    three = json.loads(_body())
    three["单选"][0]["选项"] = ["甲", "乙", "丙"]
    five = json.loads(_body())
    five["单选"][0]["选项"] = ["甲", "乙", "丙", "丁", "戊"]
    duplicate = json.loads(_body())
    duplicate["单选"][0]["选项"] = ["甲", "甲", "丙", "丁"]
    blank = json.loads(_body())
    blank["多选"][0]["选项"] = ["甲", " ", "丙", "丁"]
    for body in (three, five, duplicate, blank):
        with pytest.raises(Rejected):
            parse_questions(json.dumps(body, ensure_ascii=False))


def test_wrong_fields_types_or_question_rules_are_rejected():
    extra_field = json.loads(_body())
    extra_field["判断"][0]["多余"] = "不要"
    string_options = json.loads(_body())
    string_options["单选"][0]["选项"] = "甲乙丙丁"
    blank_prompt = json.loads(_body())
    blank_prompt["综合"][0]["题目"] = " "
    bad_answer = json.loads(_body())
    bad_answer["判断"][0]["参考答案"] = "不知道"
    for body in (extra_field, string_options, blank_prompt, bad_answer):
        with pytest.raises(Rejected):
            parse_questions(json.dumps(body, ensure_ascii=False))


def test_existing_choice_questions_still_allow_two_options():
    question = ChoiceQuestion("教师改过", SelectionMode.SINGLE, ("甲", "乙"), ("甲",), "解析")

    assert question.choices == ("甲", "乙")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_question_parsing.py -v`

Expected: FAIL because `scaffolding.model_generator` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `src/scaffolding/model_generator.py`:

```python
import json

from scaffolding.generation import Rejected
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion


_TOP_KEYS = ("单选", "多选", "判断", "综合")
_CHOICE_KEYS = {"题目", "选项", "参考答案", "解析"}
_JUDGED_KEYS = {"题目", "参考答案", "解析"}
_OPEN_KEYS = {"题目", "作答要求", "参考答案", "解析"}


def parse_questions(text: str) -> tuple:
    if not isinstance(text, str):
        raise Rejected("model reply is not the question JSON")
    try:
        body = json.loads(text.strip())
    except json.JSONDecodeError as error:
        raise Rejected("model reply is not the question JSON") from error
    if not isinstance(body, dict) or set(body) != set(_TOP_KEYS):
        raise Rejected("model reply is not the question JSON")
    return (
        *_choices(body["单选"], SelectionMode.SINGLE),
        *_choices(body["多选"], SelectionMode.MULTIPLE),
        *_judged(body["判断"]),
        *_opened(body["综合"]),
    )


def _items(value: object, keys: set[str]) -> list[dict]:
    if not isinstance(value, list):
        raise Rejected("model reply is not the question JSON")
    items = []
    for item in value:
        if not isinstance(item, dict) or set(item) != keys:
            raise Rejected("model reply is not the question JSON")
        items.append(item)
    return items


def _string_list(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, list) or any(type(item) is not str for item in value):
        return None
    return tuple(value)


def _choices(value: object, selection: SelectionMode) -> tuple[ChoiceQuestion, ...]:
    questions = []
    for item in _items(value, _CHOICE_KEYS):
        options = _string_list(item["选项"])
        answers = _string_list(item["参考答案"])
        if (
            options is None
            or answers is None
            or len(options) != 4
            or len(set(options)) != 4
            or any(option.strip() == "" for option in options)
            or type(item["题目"]) is not str
            or type(item["解析"]) is not str
        ):
            raise Rejected("model reply is not the question JSON")
        try:
            questions.append(ChoiceQuestion(item["题目"], selection, options, answers, item["解析"]))
        except ValueError as error:
            raise Rejected("model reply is not the question JSON") from error
    return tuple(questions)


def _judged(value: object) -> tuple[TrueFalseQuestion, ...]:
    questions = []
    for item in _items(value, _JUDGED_KEYS):
        if any(type(item[key]) is not str for key in _JUDGED_KEYS):
            raise Rejected("model reply is not the question JSON")
        try:
            questions.append(TrueFalseQuestion(item["题目"], item["参考答案"], item["解析"]))
        except ValueError as error:
            raise Rejected("model reply is not the question JSON") from error
    return tuple(questions)


def _opened(value: object) -> tuple[OpenQuestion, ...]:
    questions = []
    for item in _items(value, _OPEN_KEYS):
        if any(type(item[key]) is not str for key in _OPEN_KEYS):
            raise Rejected("model reply is not the question JSON")
        try:
            questions.append(OpenQuestion(item["题目"], item["作答要求"], item["参考答案"], item["解析"]))
        except ValueError as error:
            raise Rejected("model reply is not the question JSON") from error
    return tuple(questions)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_question_parsing.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/model_generator.py tests/test_model_question_parsing.py
git commit -m "feat: parse model question JSON into existing question types"
```

---

### Task 2: 组成系统消息和用户消息

**Files:**
- Modify: `src/scaffolding/model_generator.py`
- Test: `tests/test_model_prompt.py`

**Interfaces:**
- Consumes: `QuestionCounts`，来自 `scaffolding.generation`。`Objective`，来自 `scaffolding.objectives`。`LessonSource` 和 `StandardSource`，来自 `scaffolding.knowledge`。
- Produces: `SYSTEM_MESSAGE: str`。`build_messages(counts: QuestionCounts, objectives: tuple[Objective, ...]) -> tuple[dict[str, str], dict[str, str]]`。第一条是 `role="system"`，第二条是 `role="user"`。

- [ ] **Step 1: Write the failing test**

Create `tests/test_model_prompt.py`:

```python
from scaffolding.generation import QuestionCounts
from scaffolding.knowledge import StandardSource
from scaffolding.model_generator import build_messages
from scaffolding.objectives import Objective
from tests.generation_helpers import prepared_objectives


def test_messages_carry_rules_counts_and_only_this_records_objectives():
    base, catalog = prepared_objectives()
    lesson = catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")[0]
    standard = Objective(
        "objective-2",
        "信息社会责任",
        "遵守规范",
        StandardSource("普通高中信息科技课程标准", "高中", "1.1.2"),
    )

    system, user = build_messages(QuestionCounts(2, 0, 1, 1), (lesson, standard))

    assert system == {
        "role": "system",
        "content": (
            "你是高中信息科技教师。只回一份 JSON 对象，不要代码块，不要其他文字。\n"
            "JSON 有且只有四个键：单选、多选、判断、综合。每个键的值都是数组。某一类数量是 0 时，那个数组是空的。\n"
            "单选和多选的每一项都有且只有这些键：题目、选项、参考答案、解析。"
            "选项正好四个，互不相同，且都不能为空白。选项和参考答案是字符串数组。"
            "单选的参考答案是其中一个选项。多选的参考答案至少包含一个选项，且每一项都在选项里、互不相同。"
            "题目和解析都不能为空白。\n"
            "判断的每一项都有且只有这些键：题目、参考答案、解析。参考答案是「正确」或「错误」。题目和解析都不能为空白。\n"
            "综合的每一项都有且只有这些键：题目、作答要求、参考答案、解析。题目和作答要求都不能为空白。参考答案和解析可以空着。\n"
            "空白不算已填写。"
        ),
    }
    assert user == {
        "role": "user",
        "content": (
            "单选：2\n"
            "多选：0\n"
            "判断：1\n"
            "综合：1\n"
            "\n"
            "目标：\n"
            "1. 维度：信息意识\n"
            "表述：能识别信息\n"
            "来源：版本 人教版，册次 必修一，课时 信息系统的组成，学段 高中，页码 12-15\n"
            "2. 维度：信息社会责任\n"
            "表述：遵守规范\n"
            "来源：名称 普通高中信息科技课程标准，学段 高中，条款号 1.1.2，现行课标"
        ),
    }
    assert "objective-1" not in user["content"]
    assert "objective-2" not in user["content"]
    assert "课时原文" not in user["content"]
    assert "课标全文" not in user["content"]
    assert base.get_lesson("人教版", "必修一", "信息系统的组成").text == "课时原文"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_prompt.py -v`

Expected: FAIL because `build_messages` is not defined.

- [ ] **Step 3: Write minimal implementation**

Replace the import block at the top of `src/scaffolding/model_generator.py` with:

```python
import json

from scaffolding.generation import QuestionCounts, Rejected
from scaffolding.knowledge import LessonSource
from scaffolding.objectives import Objective
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion
```

Append the following after `parse_questions` and its helpers:

```python
SYSTEM_MESSAGE = (
    "你是高中信息科技教师。只回一份 JSON 对象，不要代码块，不要其他文字。\n"
    "JSON 有且只有四个键：单选、多选、判断、综合。每个键的值都是数组。某一类数量是 0 时，那个数组是空的。\n"
    "单选和多选的每一项都有且只有这些键：题目、选项、参考答案、解析。"
    "选项正好四个，互不相同，且都不能为空白。选项和参考答案是字符串数组。"
    "单选的参考答案是其中一个选项。多选的参考答案至少包含一个选项，且每一项都在选项里、互不相同。"
    "题目和解析都不能为空白。\n"
    "判断的每一项都有且只有这些键：题目、参考答案、解析。参考答案是「正确」或「错误」。题目和解析都不能为空白。\n"
    "综合的每一项都有且只有这些键：题目、作答要求、参考答案、解析。题目和作答要求都不能为空白。参考答案和解析可以空着。\n"
    "空白不算已填写。"
)


def build_messages(counts: QuestionCounts, objectives: tuple[Objective, ...]) -> tuple[dict[str, str], dict[str, str]]:
    lines = [
        f"单选：{counts.single}",
        f"多选：{counts.multiple}",
        f"判断：{counts.true_false}",
        f"综合：{counts.open_ended}",
        "",
        "目标：",
    ]
    for number, objective in enumerate(objectives, start=1):
        lines.append(f"{number}. 维度：{objective.dimension}")
        lines.append(f"表述：{objective.statement}")
        lines.append(f"来源：{_source_text(objective.source)}")
    return (
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": "\n".join(lines)},
    )


def _source_text(source: object) -> str:
    if isinstance(source, LessonSource):
        return f"版本 {source.version}，册次 {source.volume}，课时 {source.lesson}，学段 {source.stage}，页码 {source.pages}"
    return f"名称 {source.name}，学段 {source.stage}，条款号 {source.clauses}，现行课标"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_prompt.py tests/test_model_question_parsing.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/model_generator.py tests/test_model_prompt.py
git commit -m "feat: prompt DeepSeek from one saved objective record"
```

---

### Task 3: 用模型正文创建未发布任务

**Files:**
- Modify: `src/scaffolding/model_generator.py`
- Test: `tests/test_model_generation.py`

**Interfaces:**
- Consumes: `parse_questions`、`build_messages`。`TaskGeneration`、`LessonOrigin`、`StageOrigin`、`Rejected`、`QuestionCounts`。`TaskCatalog`。
- Produces: `ModelQuestionGenerator(complete)`。`generate(self, counts: QuestionCounts, objectives: tuple) -> tuple`。它把 `build_messages` 的返回值调用一次 `complete`，再交给 `parse_questions`。`complete` 抛出的异常原样传出。

- [ ] **Step 1: Write the failing test**

Create `tests/test_model_generation.py`:

```python
import json

import pytest

from scaffolding.generation import LessonOrigin, QuestionCounts, Rejected, StageOrigin, TaskGeneration
from scaffolding.knowledge import CurriculumStandard
from scaffolding.model_generator import ModelQuestionGenerator, build_messages
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft
from scaffolding.records import ChoiceQuestion, SelectionMode
from scaffolding.tasks import TaskCatalog
from tests.generation_helpers import prepared_objectives
from tests.objective_helpers import ScriptedExtractor


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


def _reply(**overrides) -> str:
    body = {
        "单选": [
            {"题目": "单选乙", "选项": ["甲", "乙", "丙", "丁"], "参考答案": ["乙"], "解析": "原因"},
            {"题目": "单选甲", "选项": ["甲", "乙", "丙", "丁"], "参考答案": ["甲"], "解析": "原因"},
        ],
        "多选": [],
        "判断": [
            {"题目": "判断题", "参考答案": "正确", "解析": "原因"},
        ],
        "综合": [],
    }
    body.update(overrides)
    return json.dumps(body, ensure_ascii=False)


def test_a_matching_reply_creates_an_unpublished_task_for_each_origin():
    base, objectives = prepared_objectives()
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    junior = base.retrieve_stage("初中")
    extractor = ScriptedExtractor()
    extractor.stage_results = (ObjectiveDraft("信息社会责任", "遵守规范", junior.standard_source),)
    stage_objectives = ObjectiveCatalog(base, extractor)
    stage_objectives.extract_stage("初中")
    complete = RecordingComplete(_reply())
    tasks = TaskCatalog()
    generation = TaskGeneration(objectives, tasks, ModelQuestionGenerator(complete))

    task = generation.generate_lesson(
        "人教版", "必修一", "信息系统的组成", single=2, multiple=0, true_false=1, open_ended=0
    )

    assert task.published is False
    assert [question.prompt for question in task.questions] == ["单选乙", "单选甲", "判断题"]
    assert generation.origin(task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")
    assert complete.calls == [
        build_messages(
            QuestionCounts(2, 0, 1, 0),
            objectives.lesson_objectives("人教版", "必修一", "信息系统的组成"),
        )
    ]
    stage_complete = RecordingComplete(_reply(单选=[], 判断=[{"题目": "学段判断", "参考答案": "正确", "解析": "原因"}]))
    stage_generation = TaskGeneration(stage_objectives, tasks, ModelQuestionGenerator(stage_complete))
    stage_task = stage_generation.generate_stage("初中", single=0, multiple=0, true_false=1, open_ended=0)
    assert stage_generation.origin(stage_task.task_id) == StageOrigin("初中")
    assert len(stage_complete.calls) == 1


def test_guards_do_not_call_the_completer():
    _, objectives = prepared_objectives()
    complete = RecordingComplete(_reply())
    tasks = TaskCatalog()
    generation = TaskGeneration(objectives, tasks, ModelQuestionGenerator(complete))

    with pytest.raises(Rejected):
        generation.generate_lesson("沪科教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0)
    with pytest.raises(Rejected):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=0, multiple=0, true_false=0, open_ended=0)
    with pytest.raises(Rejected):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=1.5, multiple=0, true_false=0, open_ended=0)

    assert complete.calls == []


def test_a_bad_reply_or_count_mismatch_creates_nothing():
    _, objectives = prepared_objectives()
    tasks = TaskCatalog()
    existing = tasks.create((ChoiceQuestion("已有题", SelectionMode.SINGLE, ("甲", "乙"), ("甲",), "解析"),))
    fenced = RecordingComplete("```json\n" + _reply() + "\n```")
    generation = TaskGeneration(objectives, tasks, ModelQuestionGenerator(fenced))

    with pytest.raises(Rejected):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=2, multiple=0, true_false=1, open_ended=0)
    mismatched = RecordingComplete(_reply())
    mismatched_generation = TaskGeneration(objectives, tasks, ModelQuestionGenerator(mismatched))
    with pytest.raises(Rejected):
        mismatched_generation.generate_lesson(
            "人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0
        )
    failing = RecordingComplete(error=RuntimeError("down"))
    failed = TaskGeneration(objectives, tasks, ModelQuestionGenerator(failing))
    with pytest.raises(RuntimeError):
        failed.generate_lesson("人教版", "必修一", "信息系统的组成", single=2, multiple=0, true_false=1, open_ended=0)

    assert len(fenced.calls) == 1
    assert len(mismatched.calls) == 1
    assert len(failing.calls) == 1
    assert tasks.get(existing.task_id).questions[0].prompt == "已有题"
    assert generation.origin(existing.task_id) is None
    with pytest.raises(KeyError):
        tasks.get("task-2")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_generation.py -v`

Expected: FAIL because `ModelQuestionGenerator` is not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `src/scaffolding/model_generator.py`:

```python
class ModelQuestionGenerator:
    def __init__(self, complete) -> None:
        self._complete = complete

    def generate(self, counts: QuestionCounts, objectives: tuple) -> tuple:
        text = self._complete(build_messages(counts, objectives))
        if not isinstance(text, str):
            raise Rejected("model reply is not the question JSON")
        return parse_questions(text)
```

`Rejected` 和 `QuestionCounts` 使用文件里已经导入的名字。

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_generation.py tests/test_model_prompt.py tests/test_model_question_parsing.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/model_generator.py tests/test_model_generation.py
git commit -m "feat: create an unpublished task from a model reply"
```

---

### Task 4: 调用 DeepSeek 并只取正文

**Files:**
- Modify: `src/scaffolding/model_generator.py`
- Test: `tests/test_deepseek_completion.py`

**Interfaces:**
- Consumes: `Rejected`。
- Produces: `DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"`。`deepseek_complete(messages, *, post, api_key: str | None = None) -> str`。`post(url: str, headers: dict[str, str], payload: dict) -> tuple[int, object]`。`api_key is None` 时读取 `DEEPSEEK_API_KEY`。密钥缺失、发送函数抛出异常、状态码不是 200，或没有字符串正文时，抛出 `Rejected` 并且不再调用发送函数。

- [ ] **Step 1: Write the failing test**

Create `tests/test_deepseek_completion.py`:

```python
import pytest

from scaffolding.generation import Rejected
from scaffolding.model_generator import DEEPSEEK_URL, deepseek_complete


class RecordingPost:
    def __init__(self, status: int = 200, response: object | None = None, error: Exception | None = None) -> None:
        self.status = status
        self.response = response
        self.error = error
        self.calls = []

    def __call__(self, url, headers, payload):
        self.calls.append((url, headers, payload))
        if self.error is not None:
            raise self.error
        return self.status, self.response


def _response(content: object = "{\"单选\":[]}") -> dict:
    return {"choices": [{"message": {"content": content}}]}


def test_a_successful_request_returns_only_the_content(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "from-env")
    messages = ({"role": "system", "content": "规则"}, {"role": "user", "content": "数量"})
    post = RecordingPost(response=_response("正文"))

    assert deepseek_complete(messages, post=post, api_key="secret") == "正文"

    url, headers, payload = post.calls[0]
    assert url == DEEPSEEK_URL
    assert headers["Authorization"] == "Bearer secret"
    assert headers["Content-Type"] == "application/json"
    assert payload == {
        "model": "deepseek-flash",
        "messages": [{"role": "system", "content": "规则"}, {"role": "user", "content": "数量"}],
        "stream": False,
        "thinking": {"type": "disabled"},
    }
    assert "reasoning_effort" not in payload
    env_post = RecordingPost(response=_response("环境"))
    assert deepseek_complete(messages, post=env_post) == "环境"
    assert env_post.calls[0][1]["Authorization"] == "Bearer from-env"


def test_a_missing_key_does_not_send(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    post = RecordingPost()

    with pytest.raises(Rejected):
        deepseek_complete((), post=post)
    with pytest.raises(Rejected):
        deepseek_complete((), post=post, api_key="  ")

    assert post.calls == []


def test_a_failed_request_is_rejected_once():
    messages = ({"role": "user", "content": "数量"},)
    for post in (
        RecordingPost(status=500, response=_response("错误")),
        RecordingPost(response={"choices": []}),
        RecordingPost(response={"choices": [{"message": {"content": None}}]}),
        RecordingPost(error=RuntimeError("down")),
    ):
        with pytest.raises(Rejected):
            deepseek_complete(messages, post=post, api_key="secret")
        assert len(post.calls) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_deepseek_completion.py -v`

Expected: FAIL because `deepseek_complete` is not defined.

- [ ] **Step 3: Write minimal implementation**

Add `import os` directly below `import json` in `src/scaffolding/model_generator.py`. Append the following at the end of that file:

```python
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


def deepseek_complete(messages, *, post, api_key: str | None = None) -> str:
    key = os.environ.get("DEEPSEEK_API_KEY") if api_key is None else api_key
    if key is None or key.strip() == "":
        raise Rejected("DeepSeek API key is missing")
    payload = {
        "model": "deepseek-flash",
        "messages": [dict(message) for message in messages],
        "stream": False,
        "thinking": {"type": "disabled"},
    }
    try:
        status, response = post(
            DEEPSEEK_URL,
            {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            payload,
        )
    except Rejected:
        raise
    except Exception as error:
        raise Rejected("DeepSeek request failed") from error
    content = _content(status, response)
    if content is None:
        raise Rejected("DeepSeek reply has no content")
    return content


def _content(status: object, response: object) -> str | None:
    if status != 200 or not isinstance(response, dict):
        return None
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return None
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if type(content) is not str:
        return None
    return content
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_deepseek_completion.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/model_generator.py tests/test_deepseek_completion.py
git commit -m "feat: call DeepSeek and return only the reply text"
```

---

### Task 5: 规格验收

**Files:**
- Create: `tests/test_model_generation_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-19-model-task-generator-design.md`

**Interfaces:**
- Consumes: Task 1 到 Task 4 的全部公开接口。规格文件来自 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-19-model-task-generator-design.md`，即本地 `master` 的 `e42e9d7`。原样复制，不要改写。
- Produces: 验收测试。不新增生产行为。

- [ ] **Step 1: Write the failing test**

Create `tests/test_model_generation_acceptance.py`:

```python
import json
from pathlib import Path

import pytest

from scaffolding.generation import LessonOrigin, Rejected, StageOrigin, TaskGeneration
from scaffolding.knowledge import CurriculumStandard
from scaffolding.model_generator import DEEPSEEK_URL, ModelQuestionGenerator, deepseek_complete
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft
from scaffolding.records import ChoiceQuestion, SelectionMode
from scaffolding.tasks import TaskCatalog
from tests.generation_helpers import prepared_objectives
from tests.objective_helpers import ScriptedExtractor


def _reply() -> str:
    return json.dumps(
        {
            "单选": [
                {"题目": "单选甲", "选项": ["甲", "乙", "丙", "丁"], "参考答案": ["甲"], "解析": "原因"},
            ],
            "多选": [],
            "判断": [],
            "综合": [],
        },
        ensure_ascii=False,
    )


def test_model_task_generator_spec_is_in_the_workspace():
    spec = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "specs" / "2026-10-19-model-task-generator-design.md"
    assert spec.is_file()


def test_generation_uses_one_reply_and_keeps_existing_task_rules():
    base, objectives = prepared_objectives()
    stored_lesson = base.get_lesson("人教版", "必修一", "信息系统的组成")
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    junior = base.retrieve_stage("初中")
    extractor = ScriptedExtractor()
    extractor.stage_results = (ObjectiveDraft("信息社会责任", "遵守规范", junior.standard_source),)
    stage_objectives = ObjectiveCatalog(base, extractor)
    stage_objectives.extract_stage("初中")
    calls = []

    def complete(messages):
        calls.append(messages)
        return _reply()

    tasks = TaskCatalog()
    existing = tasks.create((ChoiceQuestion("已有题", SelectionMode.SINGLE, ("甲", "乙"), ("甲",), "解析"),))
    generation = TaskGeneration(objectives, tasks, ModelQuestionGenerator(complete))
    task = generation.generate_lesson(
        "人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0
    )

    assert task.published is False
    assert [question.prompt for question in task.questions] == ["单选甲"]
    assert task.questions[0].choices == ("甲", "乙", "丙", "丁")
    assert generation.origin(task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")
    assert len(calls) == 1
    assert "课时原文" not in calls[0][1]["content"]
    assert "objective-1" not in calls[0][1]["content"]

    def fail(messages):
        calls.append(messages)
        return "```json\n" + _reply() + "\n```"

    with pytest.raises(Rejected):
        TaskGeneration(objectives, tasks, ModelQuestionGenerator(fail)).generate_lesson(
            "人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0
        )
    assert tasks.get(existing.task_id).questions[0].prompt == "已有题"
    with pytest.raises(KeyError):
        tasks.get("task-3")

    stage_calls = []

    def stage_complete(messages):
        stage_calls.append(messages)
        return json.dumps(
            {
                "单选": [],
                "多选": [],
                "判断": [{"题目": "学段判断", "参考答案": "正确", "解析": "原因"}],
                "综合": [],
            },
            ensure_ascii=False,
        )

    stage_generation = TaskGeneration(stage_objectives, tasks, ModelQuestionGenerator(stage_complete))
    stage_task = stage_generation.generate_stage("初中", single=0, multiple=0, true_false=1, open_ended=0)
    assert stage_generation.origin(stage_task.task_id) == StageOrigin("初中")
    assert stage_task.questions[0].prompt == "学段判断"
    assert len(stage_calls) == 1
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
    assert base.get_lesson("人教版", "必修一", "信息系统的组成") is stored_lesson
    ChoiceQuestion("两个选项", SelectionMode.SINGLE, ("甲", "乙"), ("甲",), "解析")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_generation_acceptance.py -v`

Expected: FAIL because the spec file is not in the worktree yet. If the spec file is already present and the other assertions fail, stop and report the failure. Do not change production code.

- [ ] **Step 3: Copy the spec and keep the test**

Copy `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-19-model-task-generator-design.md` to `docs/superpowers/specs/2026-10-19-model-task-generator-design.md` in the worktree. Do not edit the spec. Do not change production code.

- [ ] **Step 4: Run the full suite**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS, including the previous knowledge, objective, task, scaffolding, and generation tests.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_model_generation_acceptance.py docs/superpowers/specs/2026-10-19-model-task-generator-design.md
git commit -m "test: accept DeepSeek question generation from saved objectives"
```
