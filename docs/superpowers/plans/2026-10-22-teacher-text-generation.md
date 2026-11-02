# 按文字生成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让教师在目标页进入生成页，提交一段文字，由模型交回的读法、目标和题目创建一份未发布任务。

**Architecture:** 新的 `parse_text_task` 只核对交回，不创建任务。`TaskGeneration.generate_from_text` 调用可替换的文字生成方，核对通过后用现有任务目录创建任务，不写来源。`ModelTextGenerator` 使用课堂里已有的补全。生成页并进现有 `TeacherPage`，路径是 `/generation`。测试调用 `response_for`，不监听端口。

**Tech Stack:** Python 3.14，pytest 9，标准库。实现从 `origin/main` 建工作区。规格在本地 `master` 的 `8f5b573`，文件是 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-22-teacher-text-generation-design.md`。工作区里若没有这份规格，在 Task 6 从该文件原样复制，不要改写。测试命令是 `.\.venv\Scripts\python.exe -m pytest`。PowerShell 下不要使用 `&&` 或 bash heredoc；提交用 `git commit -m "message"`。不要改 git config，不要 push。不要提交本计划。

## Global Constraints

- 生成页并进现有教师页。路径是 `/generation`。课堂里带 `/teacher`，单独调用教师页时不带前缀。末尾多一个斜杠不影响。查询字符串不参与判断。
- 任务生成记录增加按文字生成。一次提交最多调用一次。没有任务生成记录时不调用。这一入口不读取知识库，也不读取已经保存的课时目标或学段目标。课时生成和学段生成仍按原来的规则工作。
- 生成页不另记草稿。每次提交只带这次的文字。文字框的名字是 `text`。同一次提交取最后一项。没有 `text` 时，文字算空的。空白不算已填写。
- 目标页的查询表单旁有「生成」，一打开查询表单就有。点它只打开生成页。教师列表和 `/` 不增加「生成」。
- 目标只供这次核对，不写入目标库。核对通过后创建未发布任务，不写入课时来源或学段来源。任务出现在任务列表。目标页的任务链接里没有它。
- 正式运行使用课堂里已有的补全。测试注入事先写好的交回。测试不调用 `serve`，不打开浏览器，不访问网络。
- GET 只显示文字框和「生成」。失败停在生成页，状态 200，文字框留下提交的原文，显示「生成失败，没有创建任务」。成功时这次响应就是现有任务页，状态 200，标为未发布。
- 原文、题目和标识都按文字写进页面。HTML 用拼接，不用 `str.format`。
- 交回有且只有读法、目标、题目。读法有且只有单选、多选、判断、综合。值是大于或等于 0 的整数，或「未指定」。整数必须是数字，不能是字符串、小数或布尔值。
- 目标至少一条。每条有且只有维度和表述。维度是信息意识、计算思维、数字化学习与创新、信息社会责任之一。表述去掉两端空白后还有内容。
- 题目有且只有这四类数组。顺序是单选、多选、判断、综合，同一类保持交回的先后。单选和多选的选项至少两个，互不相同且不能为空白。单选的参考答案只有一项。多选至少一项。判断的参考答案是「正确」或「错误」。综合的题目和作答要求不能为空白，参考答案和解析可以空着。
- 指定数量必须一致。指定为 0 的那一类不能有题。未指定的类接受交回的题数，可以是 0。四类合起来至少一道。
- 空白、没有任务生成记录、模型调用失败、交回无法接受，都是同一句失败，不创建任务。空白和没有生成记录时不调用模型。知识库、目标库和已有任务保持原样。
- 学生地址 `/student/generation` 仍是「任务不存在」，状态 404。教师页上不认识的地址仍是「任务不存在」。
- 不修改 `tasks.py`、`session.py`、`html_assets.py`、`agents.py`、`scripted.py`、`records.py`、`model_decision.py`、`model_scaffold.py`、`model_generator.py`、`model_extractor.py`、`objectives.py`、`knowledge.py`、`student_page.py`。

## File Map

- Create: `src/scaffolding/text_generation.py` — 核对模型交回并返回排好序的题目。
- Modify: `src/scaffolding/generation.py` — `generate_from_text`。
- Create: `src/scaffolding/model_text.py` — 用已有补全请求文字任务。
- Modify: `src/scaffolding/teacher_page.py` — 生成页和目标页链接。
- Modify: `src/scaffolding/classroom.py` — 正式运行装上文字生成方。
- Create: `tests/text_generation_helpers.py`
- Create: `tests/test_text_generation_parse.py`
- Create: `tests/test_text_generation_record.py`
- Create: `tests/test_model_text_generator.py`
- Create: `tests/test_teacher_text_generation_page.py`
- Create: `tests/test_teacher_text_generation_success.py`
- Create: `tests/test_teacher_text_generation_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-22-teacher-text-generation-design.md`

---

### Task 1: 核对文字生成的交回

**Files:**
- Create: `src/scaffolding/text_generation.py`
- Create: `tests/text_generation_helpers.py`
- Test: `tests/test_text_generation_parse.py`

**Interfaces:**
- Consumes: `scaffolding.generation.Rejected`。`ChoiceQuestion`、`TrueFalseQuestion`、`OpenQuestion`、`SelectionMode`。
- Produces: `parse_text_task(reply: str) -> tuple`。合格时按单选、多选、判断、综合返回题目。不合格时抛出 `Rejected`。不创建任务，不写目标库。

- [ ] **Step 1: Write the failing test**

Create `tests/text_generation_helpers.py`:

```python
import json


def choice(prompt, answers=("甲",)):
    return {"题目": prompt, "选项": ["甲", "乙"], "参考答案": list(answers), "解析": "解析"}


def judged(prompt="判断题", answer="正确"):
    return {"题目": prompt, "参考答案": answer, "解析": "解析"}


def opened(prompt="综合题"):
    return {"题目": prompt, "作答要求": "写出过程", "参考答案": "", "解析": ""}


def body(reading=None, objectives=None, questions=None):
    if reading is None:
        reading = {"单选": 1, "多选": "未指定", "判断": 0, "综合": "未指定"}
    if objectives is None:
        objectives = [{"维度": "信息意识", "表述": "能识别信息"}]
    if questions is None:
        questions = {
            "单选": [choice("第一")],
            "多选": [],
            "判断": [],
            "综合": [opened()],
        }
    return {"读法": reading, "目标": objectives, "题目": questions}


def dumped(**kwargs):
    return json.dumps(body(**kwargs), ensure_ascii=False)
```

Create `tests/test_text_generation_parse.py`:

```python
import json

import pytest

from scaffolding.generation import Rejected
from scaffolding.text_generation import parse_text_task
from tests.text_generation_helpers import body, choice, dumped, judged, opened


def test_parse_orders_specified_and_unspecified_questions():
    questions = parse_text_task(dumped(
        reading={"单选": 2, "多选": "未指定", "判断": 0, "综合": "未指定"},
        questions={
            "单选": [choice("第一"), choice("第二")],
            "多选": [],
            "判断": [],
            "综合": [opened("综合题")],
        },
    ))

    assert [item.prompt for item in questions] == ["第一", "第二", "综合题"]


def test_parse_rejects_an_unacceptable_reply():
    readings = [
        {"多选": "未指定", "判断": 0, "综合": "未指定"},
        {"单选": 1, "多选": "未指定", "判断": 0, "综合": "未指定", "填空": 1},
        {"单选": "1", "多选": "未指定", "判断": 0, "综合": "未指定"},
        {"单选": 1.0, "多选": "未指定", "判断": 0, "综合": "未指定"},
        {"单选": True, "多选": "未指定", "判断": 0, "综合": "未指定"},
        {"单选": -1, "多选": "未指定", "判断": 0, "综合": "未指定"},
    ]
    objectives = [
        [],
        [{"维度": "超纲", "表述": "能识别信息"}],
        [{"维度": "信息意识", "表述": "   "}],
        [{"维度": "信息意识", "表述": "能识别信息", "来源": "教材"}],
    ]
    questions = [
        {"单选": [choice("第一")], "多选": [], "判断": [judged()], "综合": []},
        {"单选": [], "多选": [], "判断": [], "综合": []},
        {"单选": [choice("第一", answers=("甲", "乙"))], "多选": [], "判断": [], "综合": []},
        {"单选": [choice("第一")], "多选": [], "判断": [], "综合": [opened()], "填空": []},
    ]
    samples = [json.dumps({**body(), "读法": item}) for item in readings]
    one_option = {"题目": "单选题", "选项": ["甲"], "参考答案": ["甲"], "解析": "解析"}
    questions.append({"单选": [one_option], "多选": [], "判断": [], "综合": [opened()]})
    samples += [json.dumps({"读法": body()["读法"], "目标": item, "题目": body()["题目"]}) for item in objectives]
    samples += [json.dumps({"读法": body()["读法"], "目标": body()["目标"], "题目": item}) for item in questions]
    samples.append(json.dumps({
        **body(),
        "读法": {"单选": 2, "多选": "未指定", "判断": 0, "综合": "未指定"},
        "题目": {
            "单选": [choice("只有一道")],
            "多选": [],
            "判断": [],
            "综合": [opened()],
        },
    }))
    samples.append("```")

    for sample in samples:
        with pytest.raises(Rejected):
            parse_text_task(sample)
```

The zero-judge sample uses the default reading, where 判断 is 0, so a judge question must be rejected. The empty question sample has a specified 单选 and no questions, so the total is 0. The two-answer 单选 violates the single-answer rule. The one-option 单选 violates the two-option rule. The final object asks for two 单选 questions but returns one, while 综合 still makes the total nonzero.

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_text_generation_parse.py -v`

Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `scaffolding.text_generation`

- [ ] **Step 3: Write minimal implementation**

Create `src/scaffolding/text_generation.py`:

```python
import json

from scaffolding.generation import Rejected
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion


_KINDS = ("单选", "多选", "判断", "综合")
_DIMENSIONS = frozenset({
    "信息意识",
    "计算思维",
    "数字化学习与创新",
    "信息社会责任",
})
_CHOICE_KEYS = {"题目", "选项", "参考答案", "解析"}
_JUDGED_KEYS = {"题目", "参考答案", "解析"}
_OPEN_KEYS = {"题目", "作答要求", "参考答案", "解析"}


def parse_text_task(reply: str) -> tuple:
    if not isinstance(reply, str):
        raise Rejected("text task reply is not acceptable")
    try:
        loaded = json.loads(reply.strip())
    except json.JSONDecodeError as error:
        raise Rejected("text task reply is not acceptable") from error
    if not isinstance(loaded, dict) or set(loaded) != {"读法", "目标", "题目"}:
        raise Rejected("text task reply is not acceptable")
    counts = _counts(loaded["读法"])
    _objectives(loaded["目标"])
    questions = _questions(loaded["题目"])
    if sum(len(items) for items in questions.values()) == 0:
        raise Rejected("text task reply is not acceptable")
    for kind in _KINDS:
        if counts[kind] is not None and len(questions[kind]) != counts[kind]:
            raise Rejected("text task reply is not acceptable")
    return questions["单选"] + questions["多选"] + questions["判断"] + questions["综合"]


def _counts(reading):
    if not isinstance(reading, dict) or set(reading) != set(_KINDS):
        raise Rejected("text task reply is not acceptable")
    counts = {}
    for kind in _KINDS:
        value = reading[kind]
        if type(value) is int and value >= 0:
            counts[kind] = value
        elif value == "未指定":
            counts[kind] = None
        else:
            raise Rejected("text task reply is not acceptable")
    return counts


def _objectives(objectives):
    if not isinstance(objectives, list) or objectives == []:
        raise Rejected("text task reply is not acceptable")
    for item in objectives:
        if not isinstance(item, dict) or set(item) != {"维度", "表述"}:
            raise Rejected("text task reply is not acceptable")
        if type(item["维度"]) is not str or item["维度"] not in _DIMENSIONS:
            raise Rejected("text task reply is not acceptable")
        if type(item["表述"]) is not str or item["表述"].strip() == "":
            raise Rejected("text task reply is not acceptable")


def _questions(questions):
    if not isinstance(questions, dict) or set(questions) != set(_KINDS):
        raise Rejected("text task reply is not acceptable")
    return {
        "单选": _choices(questions["单选"], SelectionMode.SINGLE),
        "多选": _choices(questions["多选"], SelectionMode.MULTIPLE),
        "判断": _judged(questions["判断"]),
        "综合": _opened(questions["综合"]),
    }


def _objects(value, keys):
    if not isinstance(value, list):
        raise Rejected("text task reply is not acceptable")
    items = []
    for item in value:
        if not isinstance(item, dict) or set(item) != keys:
            raise Rejected("text task reply is not acceptable")
        items.append(item)
    return items


def _strings(value):
    if not isinstance(value, list) or any(type(item) is not str for item in value):
        return None
    return tuple(value)


def _choices(value, selection):
    questions = []
    for item in _objects(value, _CHOICE_KEYS):
        options = _strings(item["选项"])
        answers = _strings(item["参考答案"])
        if options is None or answers is None or type(item["题目"]) is not str or type(item["解析"]) is not str:
            raise Rejected("text task reply is not acceptable")
        try:
            questions.append(ChoiceQuestion(
                item["题目"], selection, options, answers, item["解析"]
            ))
        except ValueError as error:
            raise Rejected("text task reply is not acceptable") from error
    return tuple(questions)


def _judged(value):
    questions = []
    for item in _objects(value, _JUDGED_KEYS):
        if any(type(item[key]) is not str for key in _JUDGED_KEYS):
            raise Rejected("text task reply is not acceptable")
        try:
            questions.append(TrueFalseQuestion(item["题目"], item["参考答案"], item["解析"]))
        except ValueError as error:
            raise Rejected("text task reply is not acceptable") from error
    return tuple(questions)


def _opened(value):
    questions = []
    for item in _objects(value, _OPEN_KEYS):
        if any(type(item[key]) is not str for key in _OPEN_KEYS):
            raise Rejected("text task reply is not acceptable")
        try:
            questions.append(OpenQuestion(
                item["题目"], item["作答要求"], item["参考答案"], item["解析"]
            ))
        except ValueError as error:
            raise Rejected("text task reply is not acceptable") from error
    return tuple(questions)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_text_generation_parse.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/text_generation.py tests/text_generation_helpers.py tests/test_text_generation_parse.py
git commit -m "feat: parse a text generation reply"
```

---

### Task 2: 按文字创建未发布任务

**Files:**
- Modify: `src/scaffolding/generation.py`
- Test: `tests/test_text_generation_record.py`

**Interfaces:**
- Consumes: `parse_text_task(reply)`。现有 `TaskGeneration(objectives, tasks, generator)`。`TaskCatalog.create`。
- Produces: `TaskGeneration(objectives, tasks, generator, text_generator=None)`。`generate_from_text(text) -> Task`。不写 `_origins`。文字生成方的方法是 `generate(text) -> str`。

- [ ] **Step 1: Write the failing test**

Create `tests/test_text_generation_record.py`:

```python
import pytest

from scaffolding.generation import Rejected, TaskGeneration
from scaffolding.tasks import TaskCatalog
from tests.generation_helpers import ScriptedGenerator, prepared_objectives, single
from tests.text_generation_helpers import dumped


class ScriptedTextGenerator:
    def __init__(self):
        self.reply = dumped()
        self.error = None
        self.calls = []

    def generate(self, text):
        self.calls.append(text)
        if self.error is not None:
            raise self.error
        return self.reply


def test_text_generation_creates_an_unpublished_task_without_an_origin():
    base, objectives = prepared_objectives()
    catalog = TaskCatalog()
    questions = ScriptedGenerator()
    text_generator = ScriptedTextGenerator()
    generation = TaskGeneration(objectives, catalog, questions, text_generator)

    task = generation.generate_from_text("  出一道单选  ")

    assert task.published is False
    assert [item.prompt for item in task.questions] == ["第一", "综合题"]
    assert generation.origin(task.task_id) is None
    assert text_generator.calls == ["  出一道单选  "]
    assert questions.calls == []
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能识别信息"
    assert base.retrieve_lesson("人教版", "必修一", "信息系统的组成").lesson_text == "课时原文"


def test_a_bad_text_reply_does_not_create_a_task():
    _base, objectives = prepared_objectives()
    catalog = TaskCatalog()
    text_generator = ScriptedTextGenerator()
    text_generator.reply = "```"
    generation = TaskGeneration(objectives, catalog, ScriptedGenerator(), text_generator)

    with pytest.raises(Rejected):
        generation.generate_from_text("出题")

    assert catalog._tasks == {}


def test_lesson_generation_still_records_its_origin():
    _base, objectives = prepared_objectives()
    catalog = TaskCatalog()
    questions = ScriptedGenerator()
    questions.questions = (single(),)
    generation = TaskGeneration(objectives, catalog, questions)

    task = generation.generate_lesson(
        "人教版", "必修一", "信息系统的组成",
        single=1, multiple=0, true_false=0, open_ended=0,
    )

    assert generation.origin(task.task_id).lesson == "信息系统的组成"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_text_generation_record.py -v`

Expected: FAIL because `TaskGeneration` does not accept `text_generator` or has no `generate_from_text`

- [ ] **Step 3: Write minimal implementation**

Replace the `TaskGeneration.__init__` signature and add the method. Keep the existing body and add `text_generator=None`.

```python
def __init__(self, objectives: ObjectiveCatalog, tasks: TaskCatalog, generator, text_generator=None) -> None:
    self._objectives = objectives
    self._tasks = tasks
    self._generator = generator
    self._text_generator = text_generator
    self._origins: dict[str, LessonOrigin | StageOrigin] = {}
```

Add this method after `origin`:

```python
def generate_from_text(self, text: str) -> Task:
    from scaffolding.text_generation import parse_text_task

    if self._text_generator is None:
        raise Rejected("there is no text generator")
    reply = self._text_generator.generate(text)
    return self._tasks.create(parse_text_task(reply))
```

The import stays inside the method so `generation.py` and `text_generation.py` do not import each other while the modules are loading.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_text_generation_record.py tests/test_task_generation.py tests/test_task_generation_acceptance.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/generation.py tests/test_text_generation_record.py
git commit -m "feat: create an unpublished task from text"
```

---

### Task 3: 用已有补全请求文字任务

**Files:**
- Create: `src/scaffolding/model_text.py`
- Test: `tests/test_model_text_generator.py`

**Interfaces:**
- Consumes: `scaffolding.generation.Rejected`。补全函数接收消息元组并返回字符串。
- Produces: `ModelTextGenerator(complete)`。`generate(text) -> str`。`build_text_messages(text)`。`__init__` 不调用补全。

- [ ] **Step 1: Write the failing test**

Create `tests/test_model_text_generator.py`:

```python
import pytest

from scaffolding.generation import Rejected
from scaffolding.model_text import TEXT_SYSTEM, ModelTextGenerator, build_text_messages


def test_the_prompt_carries_the_teacher_text_and_the_reply_rules():
    system, user = build_text_messages("出一道关于信息意识的单选")

    assert system == {"role": "system", "content": TEXT_SYSTEM}
    assert user == {"role": "user", "content": "出一道关于信息意识的单选"}
    assert "未指定" in TEXT_SYSTEM
    assert "至少两个" in TEXT_SYSTEM


def test_the_generator_returns_the_completion_without_calling_it_early():
    calls = []

    def complete(messages):
        calls.append(messages)
        return "{\"ok\": true}"

    generator = ModelTextGenerator(complete)
    assert calls == []

    assert generator.generate("出题") == "{\"ok\": true}"
    assert calls == [build_text_messages("出题")]


def test_a_non_text_completion_is_rejected():
    generator = ModelTextGenerator(lambda _messages: {"ok": True})

    with pytest.raises(Rejected):
        generator.generate("出题")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_text_generator.py -v`

Expected: FAIL with `ImportError` for `scaffolding.model_text`

- [ ] **Step 3: Write minimal implementation**

Create `src/scaffolding/model_text.py`:

```python
from scaffolding.generation import Rejected


TEXT_SYSTEM = (
    "你是高中信息科技教师。只回一份 JSON 对象，不要代码块，不要其他文字。\n"
    "JSON 有且只有三个键：读法、目标、题目。\n"
    "读法有且只有单选、多选、判断、综合。"
    "教师文字里同时写明了某一种和数量时，该值是大于或等于 0 的整数。"
    "没有写明的类，值是「未指定」。"
    "数量说不清，或出现这四种以外的题型时，不要返回这份成功对象。\n"
    "目标是数组，至少一条。每条有且只有维度和表述。"
    "维度是信息意识、计算思维、数字化学习与创新、信息社会责任之一。"
    "表述不能为空白。\n"
    "题目有且只有单选、多选、判断、综合，每个值都是数组。\n"
    "单选和多选的每一项都有且只有题目、选项、参考答案、解析。"
    "选项至少两个，互不相同，且都不能为空白。选项和参考答案是字符串数组。"
    "单选的参考答案只有一项。多选的参考答案至少一项，且每一项都在选项里、互不相同。"
    "题目和解析都不能为空白。\n"
    "判断的每一项都有且只有题目、参考答案、解析。参考答案是「正确」或「错误」。题目和解析都不能为空白。\n"
    "综合的每一项都有且只有题目、作答要求、参考答案、解析。题目和作答要求都不能为空白。参考答案和解析可以空着。\n"
    "空白不算已填写。四类合起来至少一道。"
)


def build_text_messages(text: str) -> tuple[dict[str, str], dict[str, str]]:
    return (
        {"role": "system", "content": TEXT_SYSTEM},
        {"role": "user", "content": text},
    )


class ModelTextGenerator:
    def __init__(self, complete) -> None:
        self._complete = complete

    def generate(self, text: str) -> str:
        reply = self._complete(build_text_messages(text))
        if not isinstance(reply, str):
            raise Rejected("model reply is not the text task JSON")
        return reply
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_text_generator.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/model_text.py tests/test_model_text_generator.py
git commit -m "feat: ask the model for a text task"
```

---

### Task 4: 打开生成页并报告失败

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Test: `tests/test_teacher_text_generation_page.py`

**Interfaces:**
- Consumes: `TeacherPage(..., generation=None)`。`TaskGeneration.generate_from_text`。`tests.teacher_objectives_helpers.form`、`make_page`、`text`。`tests.test_text_generation_record.ScriptedTextGenerator`。
- Produces: GET `/generation` 返回空白生成页。POST `/generation` 在失败时返回状态 200 和「生成失败，没有创建任务」。目标页查询表单后有 `prefix + "/generation"` 的链接。

- [ ] **Step 1: Write the failing test**

Create `tests/test_teacher_text_generation_page.py`:

```python
from scaffolding.generation import TaskGeneration
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import response_for
from tests.generation_helpers import ScriptedGenerator
from tests.teacher_objectives_helpers import form, make_page, text
from tests.test_text_generation_record import ScriptedTextGenerator


def _page(generator=None, prefix=""):
    catalog = TaskCatalog()
    page, _objectives = make_page(catalog=catalog, prefix=prefix)
    if generator is not None:
        page.generation = TaskGeneration(
            page.objectives, catalog, ScriptedGenerator(), generator
        )
    return page, generator


def test_the_objectives_form_links_to_a_blank_generation_page():
    page, _generator = _page(prefix="/teacher")

    opened = text(response_for(page, "GET", "/objectives", ""))
    generated = text(response_for(page, "GET", "/generation/?ready=1", ""))
    listed = text(response_for(page, "GET", "/", ""))

    assert 'href="/teacher/generation">生成</a>' in opened
    assert 'action="/teacher/objectives"' in opened
    assert "<textarea name=\"text\"></textarea>" in generated
    assert "生成失败，没有创建任务" not in generated
    assert 'action="/teacher/generation"' in generated
    assert 'href="/teacher/generation"' not in listed


def test_blank_text_and_a_missing_generator_do_not_call_the_model():
    generator = ScriptedTextGenerator()
    page, _generator = _page(generator)
    bare, _none = make_page()

    blank = response_for(page, "POST", "/generation/", form(text="   "))
    absent = response_for(page, "POST", "/generation", "")
    missing = response_for(bare, "POST", "/generation", form(text=["先", "<需求"]))

    assert blank.status == 200
    assert "生成失败，没有创建任务" in text(blank)
    assert "<textarea name=\"text\">   </textarea>" in text(blank)
    assert absent.status == 200
    assert "生成失败，没有创建任务" in text(absent)
    assert generator.calls == []
    assert missing.status == 200
    assert "生成失败，没有创建任务" in text(missing)
    assert "<textarea name=\"text\">&lt;需求</textarea>" in text(missing)
    assert "<需求" not in text(missing)
    assert bare.catalog._tasks == {}


def test_a_rejected_reply_keeps_the_text_and_the_existing_task():
    generator = ScriptedTextGenerator()
    generator.error = RuntimeError("boom")
    page, _generator = _page(generator)
    kept = page.catalog.create(())

    failed = response_for(page, "POST", "/generation", form(text="出题"))

    assert failed.status == 200
    assert "生成失败，没有创建任务" in text(failed)
    assert "<textarea name=\"text\">出题</textarea>" in text(failed)
    assert list(page.catalog._tasks) == [kept.task_id]
    assert generator.calls == ["出题"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_text_generation_page.py -v`

Expected: FAIL because `/generation` is still 「任务不存在」 and the objectives page has no generation link

- [ ] **Step 3: Write minimal implementation**

In `_query_form`, change the final `return` so the link sits after the form:

```python
    return (
        body
        + "</form><a href=\""
        + _with_prefix(page.prefix, "/generation")
        + "\">生成</a>"
    )
```

Add these methods to `TeacherPage`:

```python
    def open_generation(self, message: str = "", text: str = "") -> str:
        action = _with_prefix(self.prefix, "/generation")
        body = "<h1>生成</h1>"
        if message:
            body += "<p>" + escape(message) + "</p>"
        body += (
            "<form method=\"post\" action=\"" + action + "\">"
            + "<textarea name=\"text\">" + escape(text) + "</textarea>"
            + "<button type=\"submit\">生成</button></form>"
        )
        return _document(body)

    def apply_generation(self, text: str) -> str:
        if text.strip() == "" or self.generation is None:
            return self.open_generation("生成失败，没有创建任务", text)
        try:
            task = self.generation.generate_from_text(text)
        except Exception:
            return self.open_generation("生成失败，没有创建任务", text)
        return _render(self, task.task_id)
```

In `response_for`, before the final `return _html(_missing(), 404)`, add:

```python
    if parts == ["generation"] and method == "GET":
        return _html(page.open_generation())
    if parts == ["generation"] and method == "POST":
        fields = parse_qs(body, keep_blank_values=True)
        text = fields.get("text", [""])[-1]
        return _html(page.apply_generation(text))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_text_generation_page.py tests/test_teacher_objectives_open.py tests/test_teacher_page_list.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/teacher_page.py tests/test_teacher_text_generation_page.py
git commit -m "feat: open the teacher text generation page"
```

---

### Task 5: 显示按文字生成的任务

**Files:**
- Test: `tests/test_teacher_text_generation_success.py`
- Modify: `src/scaffolding/teacher_page.py`

**Interfaces:**
- Consumes: Task 4 的 POST `/generation`。`generate_from_text`。`prepared_objectives`。`dumped`。
- Produces: 成功响应是未发布任务页。目标库不变。任务没有来源。目标页的任务链接不包含它。

- [ ] **Step 1: Write the failing test**

Create `tests/test_teacher_text_generation_success.py`:

```python
from scaffolding.generation import TaskGeneration
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import response_for
from tests.generation_helpers import ScriptedGenerator, prepared_objectives
from tests.teacher_objectives_helpers import form, text
from tests.test_text_generation_record import ScriptedTextGenerator
from tests.text_generation_helpers import choice, dumped, opened


def test_a_text_request_opens_the_new_unpublished_task():
    base, objectives = prepared_objectives()
    catalog = TaskCatalog()
    questions = ScriptedGenerator()
    text_generator = ScriptedTextGenerator()
    text_generator.reply = dumped(
        questions={
            "单选": [choice("第一"), choice("第二")],
            "多选": [],
            "判断": [],
            "综合": [opened("综合题")],
        },
        reading={"单选": 2, "多选": "未指定", "判断": 0, "综合": "未指定"},
    )
    generation = TaskGeneration(objectives, catalog, questions, text_generator)
    from scaffolding.teacher_page import TeacherPage
    page = TeacherPage(
        catalog, knowledge=base, objectives=objectives, generation=generation
    )

    opened = text(response_for(page, "POST", "/generation", form(text="  出两道单选  ")))
    listed = text(response_for(page, "GET", "/", ""))
    again = text(response_for(page, "GET", "/generation", ""))
    viewed = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        action="查看",
    )))

    assert opened.index("第一") < opened.index("第二") < opened.index("综合题")
    assert "未发布" in opened
    assert "生成失败，没有创建任务" not in opened
    assert text_generator.calls == ["  出两道单选  "]
    assert questions.calls == []
    assert generation.origin("task-1") is None
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能识别信息"
    assert "task-1" in listed
    assert "<textarea name=\"text\"></textarea>" in again
    assert "task-1" not in viewed
    assert "能识别信息" in viewed
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_text_generation_success.py -v`

Expected: FAIL if the success path is missing. If Task 4 already implemented it, this test PASSes immediately; keep it and continue. Do not weaken the assertions.

- [ ] **Step 3: Write minimal implementation**

`apply_generation` must return the existing task page after a successful call:

```python
    def apply_generation(self, text: str) -> str:
        if text.strip() == "" or self.generation is None:
            return self.open_generation("生成失败，没有创建任务", text)
        try:
            task = self.generation.generate_from_text(text)
        except Exception:
            return self.open_generation("生成失败，没有创建任务", text)
        return _render(self, task.task_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_text_generation_success.py tests/test_teacher_text_generation_page.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add tests/test_teacher_text_generation_success.py src/scaffolding/teacher_page.py
git commit -m "feat: show a task generated from text"
```

---

### Task 6: 课堂验收

**Files:**
- Modify: `src/scaffolding/classroom.py`
- Create: `tests/test_teacher_text_generation_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-22-teacher-text-generation-design.md`

**Interfaces:**
- Consumes: `ModelTextGenerator(complete)`。`TaskGeneration(..., text_generator)`。`production_classroom`。`Classroom.response_for`。
- Produces: 正式课堂的 `room.generation._text_generator` 是 `ModelTextGenerator`，并且和 `room.teacher.generation` 是同一份记录。构造时不调用补全。

- [ ] **Step 1: Write the failing test**

If `docs/superpowers/specs/2026-10-22-teacher-text-generation-design.md` is missing in this worktree, copy `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-22-teacher-text-generation-design.md` unchanged. Do not edit it.

Create `tests/test_teacher_text_generation_acceptance.py`:

```python
from pathlib import Path

from scaffolding.classroom import production_classroom, response_for, serve
from scaffolding.model_text import ModelTextGenerator
from tests.classroom_helpers import text


def test_the_classroom_links_generation_from_objectives_only():
    from scaffolding.classroom import Classroom
    from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
    from scaffolding.tasks import TaskCatalog

    room = Classroom(TaskCatalog(), ScriptedDecisionAgent(), ScriptedScaffoldAgent())

    home = text(response_for(room, "GET", "/", "", 0))
    listed = text(response_for(room, "GET", "/teacher", "", 0))
    objectives = text(response_for(room, "GET", "/teacher/objectives/", "", 0))
    opened = text(response_for(room, "GET", "/teacher/generation?ready=1", "", 0))
    student = response_for(room, "GET", "/student/generation", "", 1)

    assert 'href="/teacher/generation"' not in home
    assert 'href="/teacher/generation"' not in listed
    assert 'href="/teacher/objectives"' in listed
    assert 'href="/teacher/generation">生成</a>' in objectives
    assert "<textarea name=\"text\"></textarea>" in opened
    assert "查看" not in opened
    assert student.status == 404
    assert "任务不存在" in text(student)


def test_production_prepares_the_text_generator_without_calling_it():
    def post(_request):
        raise AssertionError("network")

    room = production_classroom(post=post)

    assert isinstance(room.generation._text_generator, ModelTextGenerator)
    assert room.teacher.generation is room.generation
    assert room.generation._tasks is room.catalog


def test_the_spec_is_present_and_the_listener_is_not_started():
    assert Path("docs/superpowers/specs/2026-10-22-teacher-text-generation-design.md").is_file()
    assert callable(serve)
    assert callable(production_classroom)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_teacher_text_generation_acceptance.py -v`

Expected: FAIL because `production_classroom` does not set `_text_generator`, or the objectives link is absent

- [ ] **Step 3: Write minimal implementation**

In `classroom.py`, import `ModelTextGenerator`:

```python
from scaffolding.model_text import ModelTextGenerator
```

Pass it as the fourth argument of `TaskGeneration` inside `production_classroom`:

```python
    generation = TaskGeneration(
        objectives,
        catalog,
        ModelQuestionGenerator(complete),
        ModelTextGenerator(complete),
    )
```

No test calls `serve`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS. The count is the previous suite plus the new text-generation tests. No test calls `serve`.

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/classroom.py tests/test_teacher_text_generation_acceptance.py docs/superpowers/specs/2026-10-22-teacher-text-generation-design.md
git commit -m "test: accept text generation in the classroom"
```

The spec file in this commit must be the unchanged copy from `8f5b573`.
