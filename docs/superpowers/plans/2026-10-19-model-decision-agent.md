# 模型决策智能体 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 DeepSeek 按一份任务记录交回预设提问，并在学生求助后交回六类支架中的一类。

**Architecture:** 新的 `model_decision.py` 提供解析、提示词和模型决策智能体。`Session` 不改，只把模型决策智能体当作原来的决策智能体传入。DeepSeek 请求复用 `deepseek_complete`。测试注入事先写好的正文，不打开套接字。

**Tech Stack:** Python 3.14，pytest 9，标准库。实现从 `origin/main` 建工作区。规格在本地 `master` 的 `a43438d`，文件是 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-19-model-decision-agent-design.md`。工作区里若没有这份规格，从该提交原样复制，不要改写。测试命令是 `.\.venv\Scripts\python.exe -m pytest`。PowerShell 下不要使用 `&&` 或 bash heredoc；提交用 `git commit -m "message"`。不要改 git config，不要 push。

## Global Constraints

- 本计划只把决策智能体换成 DeepSeek。支架智能体、任务生成方和目标提炼方不在这里。
- 会话怎样接收决策智能体、求助失败时怎样留下已有支架和预设提问，仍按支架闭环规格执行。
- 测试不访问网络。
- 模型决策智能体实现 `suggest(record)` 和 `choose_type(record, question)`。它不保存记录，不读取密钥，也不调用支架智能体。
- 完成函数是已有的 `deepseek_complete`。测试换上返回事先写好正文的函数。不修改 `model_generator.py`。
- 两条系统消息都是固定说明。更新预设提问时，顶层只有「预设提问」，值是字符串数组，数组可以是空的，每一条都不能为空白，不要写出学情。选定类型时，顶层只有「类型」，值正好是反馈、提示、指导、解释、示范、提问之一，不要写出学情。
- 用户消息只写这一份任务记录：按题目顺序写题型、题干、选项或作答要求、参考答案、解析、当前作答、修改痕迹，末尾写停留的秒数和历次求助。选定类型时再写这次提问的原话。用拼接组成，不对这段正文做字符串格式化。
- 正文去掉前后空白后必须直接是约定的 JSON。完成函数交回的不是字符串时，也算解析失败。
- 去掉前后空白后还有字的预设提问按模型原文保留，顺序不变，重复的也保留。只有空白的丢掉。一条合格的都没有时返回空元组。
- 解析失败抛出模型决策智能体自己的 `Rejected`。这个异常不属于任务发布。完成函数抛出的异常原样传出。完成函数只调用一次，不重试。
- 求助时异常被会话接住，已有支架和预设提问保留。改作答时作答先写入；取预设提问失败则异常传到调用方，预设提问仍是上一次的。返回空元组时，会话把预设提问更新为空。打开会话时第一次取预设提问就失败，会话建不起来。
- 空白不算已填写。
- 不修改 `session.py`、`agents.py`、`scripted.py`、`tasks.py`、`records.py`、`model_generator.py`、`model_extractor.py`、`objectives.py`、`knowledge.py`、`generation.py`。

## File Map

- Create: `src/scaffolding/model_decision.py` — 解析正文、组成两条消息、模型决策智能体。
- Create: `tests/test_model_decision_parsing.py`
- Create: `tests/test_model_decision_prompt.py`
- Create: `tests/test_model_decision_agent.py`
- Create: `tests/test_model_decision_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-19-model-decision-agent-design.md`
- Do not modify: `src/scaffolding/session.py`、`agents.py`、`scripted.py`、`tasks.py`、`records.py`、`model_generator.py`、`model_extractor.py`、`objectives.py`、`knowledge.py`、`generation.py`

---

### Task 1: 把模型正文解析成预设提问或支架类型

**Files:**
- Create: `src/scaffolding/model_decision.py`
- Test: `tests/test_model_decision_parsing.py`

**Interfaces:**
- Consumes: 无。
- Produces: `Rejected`。`parse_presets(text: str) -> tuple[str, ...]`。`parse_scaffold_type(text: str) -> str`。`parse_presets` 在形状通过后丢掉只有空白的条目，其余按原文和数组先后返回；空数组或全部为空白时返回 `()`。`parse_scaffold_type` 只接受正好是反馈、提示、指导、解释、示范、提问之一的字符串。形状不对、代码块、值不是字符串，类型带空白，或 `text` 不是字符串时，抛出本模块的 `Rejected`。

- [ ] **Step 1: Write the failing test**

Create `tests/test_model_decision_parsing.py`:

```python
import json

import pytest

from scaffolding.model_decision import Rejected, parse_presets, parse_scaffold_type
from scaffolding.tasks import Rejected as TaskRejected


def _presets(items: list[str] | None = None, **extra) -> str:
    body = {"预设提问": ["先看题目", " ", "先看题目", "  能再看一看条件吗？"]}
    if items is not None:
        body["预设提问"] = items
    body.update(extra)
    return json.dumps(body, ensure_ascii=False)


def test_presets_drop_blanks_and_keep_order_duplicates_and_original_text():
    assert parse_presets("\n" + _presets() + " ") == (
        "先看题目",
        "先看题目",
        "  能再看一看条件吗？",
    )
    assert Rejected is not TaskRejected


def test_an_empty_or_all_blank_preset_array_returns_nothing():
    assert parse_presets(_presets(items=[])) == ()
    assert parse_presets(_presets(items=[" ", ""])) == ()


@pytest.mark.parametrize("scaffold_type", ["反馈", "提示", "指导", "解释", "示范", "提问"])
def test_each_scaffold_type_is_accepted(scaffold_type: str):
    assert parse_scaffold_type(json.dumps({"类型": scaffold_type}, ensure_ascii=False)) == scaffold_type


def test_a_code_fence_wrong_shape_or_non_string_is_rejected():
    extra = json.loads(_presets())
    extra["其他"] = []
    missing = {"预设提问": ["先看题目"]}
    missing.pop("预设提问")
    number = {"预设提问": ["先看题目", 1]}
    spaced = {"类型": " 提示"}
    for text in (
        "```json\n" + _presets() + "\n```",
        json.dumps(extra, ensure_ascii=False),
        json.dumps(missing, ensure_ascii=False),
        json.dumps(number, ensure_ascii=False),
        json.dumps(spaced, ensure_ascii=False),
        json.dumps({"类型": "第4级"}, ensure_ascii=False),
        None,
    ):
        with pytest.raises(Rejected):
            parse_presets(text)
        with pytest.raises(Rejected):
            parse_scaffold_type(text)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_decision_parsing.py -v`

Expected: FAIL because `scaffolding.model_decision` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `src/scaffolding/model_decision.py`:

```python
import json


class Rejected(Exception):
    pass


_SCAFFOLD_TYPES = frozenset({"反馈", "提示", "指导", "解释", "示范", "提问"})


def parse_presets(text: str) -> tuple[str, ...]:
    items = _object(text, "预设提问")
    if not isinstance(items, list):
        raise Rejected("model reply is not the decision JSON")
    kept = []
    for item in items:
        if type(item) is not str:
            raise Rejected("model reply is not the decision JSON")
        if item.strip() == "":
            continue
        kept.append(item)
    return tuple(kept)


def parse_scaffold_type(text: str) -> str:
    value = _object(text, "类型")
    if type(value) is not str or value not in _SCAFFOLD_TYPES:
        raise Rejected("model reply is not the decision JSON")
    return value


def _object(text: str, key: str):
    if type(text) is not str:
        raise Rejected("model reply is not the decision JSON")
    try:
        body = json.loads(text.strip())
    except json.JSONDecodeError as error:
        raise Rejected("model reply is not the decision JSON") from error
    if not isinstance(body, dict) or set(body) != {key}:
        raise Rejected("model reply is not the decision JSON")
    return body[key]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_decision_parsing.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/model_decision.py tests/test_model_decision_parsing.py
git commit -m "feat: parse model decision replies into presets and a scaffold type"
```

---

### Task 2: 组成系统消息和用户消息

**Files:**
- Modify: `src/scaffolding/model_decision.py`
- Test: `tests/test_model_decision_prompt.py`

**Interfaces:**
- Consumes: `TaskRecord`、`ChoiceQuestion`、`TrueFalseQuestion`、`OpenQuestion`、`ItemAnswer`、`Behavior`、`HelpEvent`、`HelpSource`、`SelectionMode`，来自 `scaffolding.records`。
- Produces: `build_preset_messages(record: TaskRecord) -> tuple[dict[str, str], dict[str, str]]`。`build_type_messages(record: TaskRecord, question: str) -> tuple[dict[str, str], dict[str, str]]`。两条都是先 `role="system"`，后 `role="user"`。类型消息的用户正文是预设提问消息的用户正文，再接这次提问的原话。

- [ ] **Step 1: Write the failing test**

Create `tests/test_model_decision_prompt.py`:

```python
from scaffolding.model_decision import build_preset_messages, build_type_messages
from scaffolding.records import (
    Behavior,
    ChoiceQuestion,
    HelpEvent,
    HelpSource,
    ItemAnswer,
    OpenQuestion,
    SelectionMode,
    TaskRecord,
    TrueFalseQuestion,
)


def _record() -> TaskRecord:
    return TaskRecord(
        (
            ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "天气"), ("人员",), "人员是组成"),
            ChoiceQuestion("选出组成", SelectionMode.MULTIPLE, ("人员", "硬件", "天气"), ("人员", "硬件"), "天气不是组成"),
            TrueFalseQuestion("判断说法", "正确", "题目里有依据"),
            OpenQuestion("完成作品", "写出组成"),
        ),
        (
            ItemAnswer(selected=("人员",), selected_revisions=(("天气",),)),
            ItemAnswer(selected=("人员", "硬件"), selected_revisions=(("人员",), ("硬件", "天气"))),
            ItemAnswer(),
            ItemAnswer(text="第二稿", text_revisions=("第一稿",)),
        ),
        Behavior(
            dwell_seconds=3.5,
            helps=(
                HelpEvent("先看题目", HelpSource.PRESET),
                HelpEvent("这题怎么做？", HelpSource.OWN),
            ),
        ),
    )


def test_a_preset_prompt_lists_the_task_record():
    system, user = build_preset_messages(_record())

    assert system == {
        "role": "system",
        "content": (
            "只回一份 JSON 对象，不要代码块，不要其他文字。\n"
            "顶层只有「预设提问」。它的值是字符串数组，数组可以是空的。\n"
            "每一条都不能为空白。空白不算已填写。\n"
            "不要写出学情。"
        ),
    }
    assert user == {
        "role": "user",
        "content": (
            "题目1\n"
            "题型：单选\n"
            "题干：选出人员\n"
            "选项：人员、天气\n"
            "参考答案：人员\n"
            "解析：人员是组成\n"
            "当前作答：人员\n"
            "修改痕迹：\n"
            "天气\n"
            "\n"
            "题目2\n"
            "题型：多选\n"
            "题干：选出组成\n"
            "选项：人员、硬件、天气\n"
            "参考答案：人员、硬件\n"
            "解析：天气不是组成\n"
            "当前作答：人员、硬件\n"
            "修改痕迹：\n"
            "人员\n"
            "硬件、天气\n"
            "\n"
            "题目3\n"
            "题型：判断\n"
            "题干：判断说法\n"
            "选项：正确、错误\n"
            "参考答案：正确\n"
            "解析：题目里有依据\n"
            "当前作答：\n"
            "修改痕迹：\n"
            "\n"
            "题目4\n"
            "题型：综合\n"
            "题干：完成作品\n"
            "作答要求：写出组成\n"
            "参考答案：\n"
            "解析：\n"
            "当前作答：第二稿\n"
            "修改痕迹：\n"
            "第一稿\n"
            "\n"
            "停留时间：3.5\n"
            "求助：\n"
            "预设提问：先看题目\n"
            "自己写的：这题怎么做？"
        ),
    }


def test_a_type_prompt_appends_the_question_without_formatting():
    _, preset_user = build_preset_messages(_record())
    system, user = build_type_messages(_record(), "还缺{什么}？")

    assert system == {
        "role": "system",
        "content": (
            "只回一份 JSON 对象，不要代码块，不要其他文字。\n"
            "顶层只有「类型」。它的值是字符串，并且正好是反馈、提示、指导、解释、示范、提问之一。\n"
            "不要写出学情。"
        ),
    }
    assert "预设提问" not in system["content"]
    assert user["content"] == preset_user["content"] + "\n\n这次提问：还缺{什么}？"


def test_an_empty_selection_trace_is_a_blank_line():
    record = TaskRecord(
        (TrueFalseQuestion("判断说法", "正确", "题目里有依据"),),
        (ItemAnswer(selected=("正确",), selected_revisions=((),))),
        Behavior(),
    )

    _, user = build_preset_messages(record)

    assert user["content"].endswith("修改痕迹：\n\n\n停留时间：0.0\n求助：\n")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_decision_prompt.py -v`

Expected: FAIL because `build_preset_messages` is not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `src/scaffolding/model_decision.py`:

```python
from scaffolding.records import ChoiceQuestion, ItemAnswer, OpenQuestion, TaskRecord, TrueFalseQuestion


_PRESET_SYSTEM = (
    "只回一份 JSON 对象，不要代码块，不要其他文字。\n"
    "顶层只有「预设提问」。它的值是字符串数组，数组可以是空的。\n"
    "每一条都不能为空白。空白不算已填写。\n"
    "不要写出学情。"
)

_TYPE_SYSTEM = (
    "只回一份 JSON 对象，不要代码块，不要其他文字。\n"
    "顶层只有「类型」。它的值是字符串，并且正好是反馈、提示、指导、解释、示范、提问之一。\n"
    "不要写出学情。"
)


def build_preset_messages(record: TaskRecord) -> tuple[dict[str, str], dict[str, str]]:
    return ({"role": "system", "content": _PRESET_SYSTEM}, {"role": "user", "content": _record_text(record)})


def build_type_messages(record: TaskRecord, question: str) -> tuple[dict[str, str], dict[str, str]]:
    content = _record_text(record) + "\n\n这次提问：" + question
    return ({"role": "system", "content": _TYPE_SYSTEM}, {"role": "user", "content": content})


def _record_text(record: TaskRecord) -> str:
    blocks = [
        _block(number, question, answer)
        for number, (question, answer) in enumerate(zip(record.questions, record.answers, strict=True), start=1)
    ]
    helps = "\n".join(event.source.value + "：" + event.text for event in record.behavior.helps)
    return "\n\n".join(blocks) + "\n\n停留时间：" + str(record.behavior.dwell_seconds) + "\n求助：\n" + helps


def _block(number: int, question, answer: ItemAnswer) -> str:
    if isinstance(question, ChoiceQuestion):
        return _lines(
            number,
            question.selection.value,
            (
                "题干：" + question.prompt,
                "选项：" + "、".join(question.choices),
                "参考答案：" + "、".join(question.answer),
                "解析：" + question.explanation,
                "当前作答：" + "、".join(answer.selected),
                _selected_traces(answer),
            ),
        )
    if isinstance(question, TrueFalseQuestion):
        return _lines(
            number,
            "判断",
            (
                "题干：" + question.prompt,
                "选项：正确、错误",
                "参考答案：" + question.answer,
                "解析：" + question.explanation,
                "当前作答：" + "、".join(answer.selected),
                _selected_traces(answer),
            ),
        )
    if isinstance(question, OpenQuestion):
        return _lines(
            number,
            "综合",
            (
                "题干：" + question.prompt,
                "作答要求：" + question.requirements,
                "参考答案：" + question.answer,
                "解析：" + question.explanation,
                "当前作答：" + answer.text,
                _text_traces(answer),
            ),
        )
    raise TypeError("unknown question")


def _lines(number: int, kind: str, rows: tuple[str, ...]) -> str:
    return "题目" + str(number) + "\n题型：" + kind + "\n" + "\n".join(rows)


def _selected_traces(answer: ItemAnswer) -> str:
    if not answer.selected_revisions:
        return "修改痕迹："
    return "修改痕迹：\n" + "\n".join("、".join(item) for item in answer.selected_revisions)


def _text_traces(answer: ItemAnswer) -> str:
    if not answer.text_revisions:
        return "修改痕迹："
    return "修改痕迹：\n" + "\n".join(answer.text_revisions)
```

`_block` 末尾对未知题型抛出 `TypeError`。`Rejected` 已在文件前面定义，只用于模型正文解析失败。

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_decision_prompt.py tests/test_model_decision_parsing.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/model_decision.py tests/test_model_decision_prompt.py
git commit -m "feat: prompt DeepSeek from one task record"
```

---

### Task 3: 用模型正文交回预设提问和支架类型

**Files:**
- Modify: `src/scaffolding/model_decision.py`
- Test: `tests/test_model_decision_agent.py`

**Interfaces:**
- Consumes: `parse_presets`、`parse_scaffold_type`、`build_preset_messages`、`build_type_messages`、`Rejected`。
- Produces: `ModelDecisionAgent(complete)`。`suggest(self, record) -> tuple[str, ...]` 把 `build_preset_messages` 的返回值调用一次 `complete`，再交给 `parse_presets`。`choose_type(self, record, question) -> str` 把 `build_type_messages` 的返回值调用一次 `complete`，再交给 `parse_scaffold_type`。`complete` 抛出的异常原样传出。

- [ ] **Step 1: Write the failing test**

Create `tests/test_model_decision_agent.py`:

```python
import json

import pytest

from scaffolding.model_decision import (
    ModelDecisionAgent,
    Rejected,
    build_preset_messages,
    build_type_messages,
)
from scaffolding.records import Behavior, ItemAnswer, TaskRecord, TrueFalseQuestion


def _record() -> TaskRecord:
    return TaskRecord(
        (TrueFalseQuestion("判断说法", "正确", "题目里有依据"),),
        (ItemAnswer(selected=("正确",)),),
        Behavior(dwell_seconds=1.0, helps=()),
    )


class QueueComplete:
    def __init__(self, replies: list) -> None:
        self.replies = list(replies)
        self.calls = []

    def __call__(self, messages):
        self.calls.append(messages)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def _presets() -> str:
    return json.dumps(
        {"预设提问": ["先看题目", " ", "先看题目", "  能再看一看条件吗？"]},
        ensure_ascii=False,
    )


def test_suggest_drops_blanks_and_calls_the_completer_once():
    complete = QueueComplete([_presets()])
    agent = ModelDecisionAgent(complete)
    record = _record()

    assert agent.suggest(record) == ("先看题目", "先看题目", "  能再看一看条件吗？")
    assert complete.calls == [build_preset_messages(record)]


def test_empty_preset_replies_return_nothing():
    record = _record()
    empty = QueueComplete([json.dumps({"预设提问": []}, ensure_ascii=False)])
    blank = QueueComplete([json.dumps({"预设提问": [" ", ""]}, ensure_ascii=False)])

    assert ModelDecisionAgent(empty).suggest(record) == ()
    assert ModelDecisionAgent(blank).suggest(record) == ()
    assert len(empty.calls) == 1
    assert len(blank.calls) == 1


def test_a_bad_reply_or_completer_error_propagates():
    record = _record()
    fenced = QueueComplete(["```json\n" + _presets() + "\n```"])
    failing = QueueComplete([RuntimeError("down")])
    agent = ModelDecisionAgent(fenced)

    with pytest.raises(Rejected):
        agent.suggest(record)
    with pytest.raises(RuntimeError):
        ModelDecisionAgent(failing).choose_type(record, "还缺什么？")

    assert len(fenced.calls) == 1
    assert len(failing.calls) == 1
    assert failing.calls == [build_type_messages(record, "还缺什么？")]


def test_choose_type_returns_the_model_type():
    record = _record()
    complete = QueueComplete([json.dumps({"类型": "提示"}, ensure_ascii=False)])

    assert ModelDecisionAgent(complete).choose_type(record, "还缺什么？") == "提示"
    assert complete.calls == [build_type_messages(record, "还缺什么？")]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_decision_agent.py -v`

Expected: FAIL because `ModelDecisionAgent` is not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `src/scaffolding/model_decision.py`:

```python
class ModelDecisionAgent:
    def __init__(self, complete) -> None:
        self._complete = complete

    def suggest(self, record: TaskRecord) -> tuple[str, ...]:
        return parse_presets(self._complete(build_preset_messages(record)))

    def choose_type(self, record: TaskRecord, question: str) -> str:
        return parse_scaffold_type(self._complete(build_type_messages(record, question)))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_decision_agent.py tests/test_model_decision_prompt.py tests/test_model_decision_parsing.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/model_decision.py tests/test_model_decision_agent.py
git commit -m "feat: choose presets and a scaffold type from a model reply"
```

---

### Task 4: 规格验收

**Files:**
- Create: `tests/test_model_decision_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-19-model-decision-agent-design.md`

**Interfaces:**
- Consumes: Task 1 到 Task 3 的全部公开接口，以及已有的 `deepseek_complete`、`Session`、`open_session`。规格文件来自 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-19-model-decision-agent-design.md`，即本地 `master` 的 `a43438d`。原样复制，不要改写。
- Produces: 验收测试。不新增生产行为。

- [ ] **Step 1: Write the failing test**

Create `tests/test_model_decision_acceptance.py`:

```python
import json
from pathlib import Path

import pytest

from scaffolding.agents import ScaffoldDraft
from scaffolding.model_decision import ModelDecisionAgent
from scaffolding.model_generator import DEEPSEEK_URL, deepseek_complete
from scaffolding.records import HelpSource
from scaffolding.scripted import ScriptedScaffoldAgent
from tests.helpers import open_session


class QueueComplete:
    def __init__(self, replies: list) -> None:
        self.replies = list(replies)
        self.calls = []

    def __call__(self, messages):
        self.calls.append(messages)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def _presets(*items: str) -> str:
    return json.dumps({"预设提问": list(items)}, ensure_ascii=False)


def _type(value: str) -> str:
    return json.dumps({"类型": value}, ensure_ascii=False)


def test_model_decision_agent_spec_is_in_the_workspace():
    spec = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "specs" / "2026-10-19-model-decision-agent-design.md"
    assert spec.is_file()


def test_the_session_keeps_its_existing_rules():
    complete = QueueComplete([
        _presets("先看题目", " ", "先看题目"),
        _type("提示"),
        _type(" 提示"),
        _presets(" ", ""),
    ])
    agent = ModelDecisionAgent(complete)
    scaffold_agent = ScriptedScaffoldAgent(ScaffoldDraft(text="一条提示"))
    session = open_session(agent, scaffold_agent)

    assert session.view().presets == ("先看题目", "先看题目")
    assert "参考答案：正确" in complete.calls[0][1]["content"]
    assert "停留时间：" in complete.calls[0][1]["content"]
    helped = session.ask("这题怎么做？", HelpSource.OWN)
    assert helped.scaffold is not None
    assert helped.scaffold.text == "一条提示"
    assert helped.presets == ("先看题目", "先看题目")
    assert complete.calls[1][1]["content"].endswith("这次提问：这题怎么做？")
    assert "类型" in complete.calls[1][0]["content"]
    again = session.ask("还缺什么？", HelpSource.OWN)
    assert again.scaffold.text == "一条提示"
    assert again.presets == ("先看题目", "先看题目")
    assert len(scaffold_agent.calls) == 1
    cleared = session.edit_answer(0, selected=("错误",))
    assert cleared.presets == ()
    assert session.work.answers[0].selected == ("错误",)

    with pytest.raises(RuntimeError):
        open_session(ModelDecisionAgent(QueueComplete([RuntimeError("down")])), ScriptedScaffoldAgent())

    failing = QueueComplete([_presets("先看题目"), RuntimeError("down")])
    refreshing = open_session(ModelDecisionAgent(failing), ScriptedScaffoldAgent())
    with pytest.raises(RuntimeError):
        refreshing.edit_answer(0, selected=("正确",))
    assert refreshing.view().presets == ("先看题目",)
    assert refreshing.work.answers[0].selected == ("正确",)

    sent = []

    def post(url, headers, payload):
        sent.append((url, headers, payload))
        return 200, {"choices": [{"message": {"content": _presets("先看题目")}}]}

    assert deepseek_complete(complete.calls[0], post=post, api_key="secret") == _presets("先看题目")
    assert sent[0][0] == DEEPSEEK_URL
    assert sent[0][1]["Authorization"] == "Bearer secret"
    assert sent[0][2]["model"] == "deepseek-flash"
    assert sent[0][2]["stream"] is False
    assert sent[0][2]["thinking"] == {"type": "disabled"}
    assert "reasoning_effort" not in sent[0][2]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_decision_acceptance.py -v`

Expected: FAIL because the spec file is not in the worktree yet. If the spec file is already present and the other assertions fail, stop and report the failure. Do not change production code.

- [ ] **Step 3: Copy the spec and keep the test**

Copy `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-19-model-decision-agent-design.md` to `docs/superpowers/specs/2026-10-19-model-decision-agent-design.md` in the worktree. Do not edit the spec. Do not change production code.

- [ ] **Step 4: Run the full suite**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS, including the previous scaffolding, publishing, knowledge, objective, generation, and DeepSeek tests.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_model_decision_acceptance.py docs/superpowers/specs/2026-10-19-model-decision-agent-design.md
git commit -m "test: accept DeepSeek decision from a task record"
```
