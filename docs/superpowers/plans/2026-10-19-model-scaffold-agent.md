# 模型支架智能体 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 DeepSeek 按一次求助交回文字和 HTML，并仍由现有会话从 HTML 抽出四类素材。

**Architecture:** 新的 `model_scaffold.py` 提供解析、提示词和模型支架智能体。`Session` 不改，只把模型支架智能体当作原来的支架智能体传入。DeepSeek 请求复用 `deepseek_complete`。测试注入事先写好的正文，不打开套接字。

**Tech Stack:** Python 3.14，pytest 9，标准库。实现从 `origin/main` 建工作区。规格在本地 `master` 的 `22b2f6b`，文件是 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-19-model-scaffold-agent-design.md`。工作区里若没有这份规格，从该提交原样复制，不要改写。测试命令是 `.\.venv\Scripts\python.exe -m pytest`。PowerShell 下不要使用 `&&` 或 bash heredoc；提交用 `git commit -m "message"`。不要改 git config，不要 push。

## Global Constraints

- 本计划只把支架智能体换成 DeepSeek。决策智能体、任务生成方和目标提炼方不在这里。
- 会话怎样接收支架智能体、空支架或调用失败时怎样留下已有支架，仍按支架闭环规格执行。
- 测试不访问网络。
- 模型支架智能体实现 `produce(scaffold_type, question, questions, answers)`。它不保存记录，不读取密钥，也不读取行为记录。
- 完成函数是已有的 `deepseek_complete`。测试换上返回事先写好正文的函数。不修改 `model_generator.py`。
- 系统消息要求只回一个 JSON 对象。顶层只有「文字」和「HTML」，两个值都是字符串，可以是空字符串。HTML 只用四类素材的 asset 标签。支架的文字和 HTML 不要写出参考答案，也不要写出学情。
- 用户消息按题目顺序写题型、题干、选项或作答要求、参考答案、解析、当前作答、修改痕迹，末尾写这次的支架类型和这次提问的原话。用拼接组成。不放停留时间、求助记录、学情、其他任务、知识库或教学目标。
- 正文去掉前后空白后必须直接是约定的 JSON。完成函数交回的不是字符串时，也算解析失败。文字和 HTML 按模型原文放进草稿，素材列表为空。
- 不检查文字或 HTML 里有没有参考答案原文。不检查传入的类型是不是六类之一。
- 解析失败抛出模型支架智能体自己的 `Rejected`。这个异常不属于任务发布。完成函数抛出的异常原样传出。完成函数只调用一次，不重试。
- 空字符串、只有空白的文字、抽不出四类素材的 HTML，不是调用失败。会话把没有可见文字和素材的草稿当成空支架，留下上一次的支架。
- 打开会话时不调用支架智能体。
- 不修改 `session.py`、`html_assets.py`、`agents.py`、`scripted.py`、`tasks.py`、`records.py`、`model_decision.py`、`model_generator.py`、`model_extractor.py`、`objectives.py`、`knowledge.py`、`generation.py`。

## File Map

- Create: `src/scaffolding/model_scaffold.py` — 解析正文、组成两条消息、模型支架智能体。
- Create: `tests/test_model_scaffold_parsing.py`
- Create: `tests/test_model_scaffold_prompt.py`
- Create: `tests/test_model_scaffold_agent.py`
- Create: `tests/test_model_scaffold_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-19-model-scaffold-agent-design.md`
- Do not modify: `src/scaffolding/session.py`、`html_assets.py`、`agents.py`、`scripted.py`、`tasks.py`、`records.py`、`model_decision.py`、`model_generator.py`、`model_extractor.py`、`objectives.py`、`knowledge.py`、`generation.py`

题目块的排版与决策智能体的题目块相同。不要调用 `model_decision._record_text`，那份正文含有停留时间和求助记录。

---

### Task 1: 把模型正文解析成支架草稿

**Files:**
- Create: `src/scaffolding/model_scaffold.py`
- Test: `tests/test_model_scaffold_parsing.py`

**Interfaces:**
- Consumes: `ScaffoldDraft`，来自 `scaffolding.agents`。
- Produces: `Rejected`。`parse_scaffold(text: str) -> ScaffoldDraft`。形状通过后，`text` 是「文字」的原文，`html` 是「HTML」的原文，`assets` 是 `()`。空字符串和只有空白的文字也交回草稿。形状不对、代码块、值不是字符串，或 `text` 不是字符串时，抛出本模块的 `Rejected`。

- [ ] **Step 1: Write the failing test**

Create `tests/test_model_scaffold_parsing.py`:

```python
import json

import pytest

from scaffolding.agents import ScaffoldDraft
from scaffolding.model_scaffold import Rejected, parse_scaffold
from scaffolding.tasks import Rejected as TaskRejected


def _body(text: str = "  先看 ", html: str = "<p>说明</p>", **extra) -> str:
    body = {"文字": text, "HTML": html}
    body.update(extra)
    return json.dumps(body, ensure_ascii=False)


def test_text_and_html_keep_the_model_wording_and_assets_stay_empty():
    assert parse_scaffold("\n" + _body() + " ") == ScaffoldDraft(text="  先看 ", html="<p>说明</p>")
    assert Rejected is not TaskRejected


def test_empty_strings_return_an_empty_draft():
    assert parse_scaffold(_body(text="", html="")) == ScaffoldDraft()
    assert parse_scaffold(_body(text="  ", html="  ")) == ScaffoldDraft(text="  ", html="  ")


def test_a_code_fence_wrong_shape_or_non_string_is_rejected():
    extra = json.loads(_body())
    extra["其他"] = []
    missing = {"文字": "先看"}
    number = {"文字": "先看", "HTML": 1}
    for text in (
        "```json\n" + _body() + "\n```",
        json.dumps(extra, ensure_ascii=False),
        json.dumps(missing, ensure_ascii=False),
        json.dumps(number, ensure_ascii=False),
        None,
    ):
        with pytest.raises(Rejected):
            parse_scaffold(text)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_scaffold_parsing.py -v`

Expected: FAIL because `scaffolding.model_scaffold` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `src/scaffolding/model_scaffold.py`:

```python
import json

from scaffolding.agents import ScaffoldDraft


class Rejected(Exception):
    pass


_KEYS = {"文字", "HTML"}


def parse_scaffold(text: str) -> ScaffoldDraft:
    if type(text) is not str:
        raise Rejected("model reply is not the scaffold JSON")
    try:
        body = json.loads(text.strip())
    except json.JSONDecodeError as error:
        raise Rejected("model reply is not the scaffold JSON") from error
    if not isinstance(body, dict) or set(body) != _KEYS:
        raise Rejected("model reply is not the scaffold JSON")
    if type(body["文字"]) is not str or type(body["HTML"]) is not str:
        raise Rejected("model reply is not the scaffold JSON")
    return ScaffoldDraft(text=body["文字"], html=body["HTML"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_scaffold_parsing.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/model_scaffold.py tests/test_model_scaffold_parsing.py
git commit -m "feat: parse a model scaffold reply into a draft"
```

---

### Task 2: 组成系统消息和用户消息

**Files:**
- Modify: `src/scaffolding/model_scaffold.py`
- Test: `tests/test_model_scaffold_prompt.py`

**Interfaces:**
- Consumes: `ChoiceQuestion`、`TrueFalseQuestion`、`OpenQuestion`、`ItemAnswer`、`SelectionMode`，来自 `scaffolding.records`。
- Produces: `build_messages(scaffold_type: str, question: str, questions: tuple, answers: tuple) -> tuple[dict[str, str], dict[str, str]]`。第一条是 `role="system"`，第二条是 `role="user"`。用户正文末尾是支架类型和这次提问的原话。

- [ ] **Step 1: Write the failing test**

Create `tests/test_model_scaffold_prompt.py`:

```python
from scaffolding.model_scaffold import build_messages
from scaffolding.records import (
    ChoiceQuestion,
    ItemAnswer,
    OpenQuestion,
    SelectionMode,
    TrueFalseQuestion,
)


def _questions():
    return (
        ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "天气"), ("人员",), "人员是组成"),
        ChoiceQuestion("选出组成", SelectionMode.MULTIPLE, ("人员", "硬件", "天气"), ("人员", "硬件"), "天气不是组成"),
        TrueFalseQuestion("判断说法", "正确", "题目里有依据"),
        OpenQuestion("完成作品", "写出组成"),
    )


def _answers():
    return (
        ItemAnswer(selected=("人员",), selected_revisions=(("天气",),)),
        ItemAnswer(selected=("人员", "硬件"), selected_revisions=(("人员",), ("硬件", "天气"))),
        ItemAnswer(),
        ItemAnswer(text="第二稿", text_revisions=("第一稿",)),
    )


def test_the_prompt_lists_the_task_and_this_question():
    system, user = build_messages("提示", "还缺{什么}？", _questions(), _answers())

    assert system == {
        "role": "system",
        "content": (
            "只回一份 JSON 对象，不要代码块，不要其他文字。\n"
            "顶层只有「文字」和「HTML」。两个值都是字符串，可以是空字符串。\n"
            "HTML 里只放四类素材，写成 <asset kind=\"…\" name=\"…\">…</asset>。\n"
            "kind 是图片素材、思维导图、结构图、微格动画之一，name 是文件名。\n"
            "支架的文字和 HTML 不要写出参考答案，也不要写出学情。"
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
            "支架类型：提示\n"
            "这次提问：还缺{什么}？"
        ),
    }
    assert "停留时间" not in user["content"]
    assert "求助：" not in user["content"]


def test_an_empty_selection_trace_is_a_blank_line():
    _, user = build_messages(
        "提示",
        "还缺什么？",
        (TrueFalseQuestion("判断说法", "正确", "题目里有依据"),),
        (ItemAnswer(selected=("正确",), selected_revisions=((),)),),
    )

    assert user["content"].endswith("修改痕迹：\n\n\n支架类型：提示\n这次提问：还缺什么？")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_scaffold_prompt.py -v`

Expected: FAIL because `build_messages` is not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `src/scaffolding/model_scaffold.py`:

```python
from scaffolding.records import ChoiceQuestion, ItemAnswer, OpenQuestion, TrueFalseQuestion


_SYSTEM = (
    "只回一份 JSON 对象，不要代码块，不要其他文字。\n"
    "顶层只有「文字」和「HTML」。两个值都是字符串，可以是空字符串。\n"
    "HTML 里只放四类素材，写成 <asset kind=\"…\" name=\"…\">…</asset>。\n"
    "kind 是图片素材、思维导图、结构图、微格动画之一，name 是文件名。\n"
    "支架的文字和 HTML 不要写出参考答案，也不要写出学情。"
)


def build_messages(scaffold_type: str, question: str, questions: tuple, answers: tuple) -> tuple[dict[str, str], dict[str, str]]:
    blocks = [
        _block(number, item, answer)
        for number, (item, answer) in enumerate(zip(questions, answers, strict=True), start=1)
    ]
    content = "\n\n".join(blocks) + "\n\n支架类型：" + scaffold_type + "\n这次提问：" + question
    return ({"role": "system", "content": _SYSTEM}, {"role": "user", "content": content})


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

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_scaffold_prompt.py tests/test_model_scaffold_parsing.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/model_scaffold.py tests/test_model_scaffold_prompt.py
git commit -m "feat: prompt DeepSeek for one scaffold"
```

---

### Task 3: 用模型正文交回支架草稿

**Files:**
- Modify: `src/scaffolding/model_scaffold.py`
- Test: `tests/test_model_scaffold_agent.py`

**Interfaces:**
- Consumes: `parse_scaffold`、`build_messages`、`Rejected`、`ScaffoldDraft`。
- Produces: `ModelScaffoldAgent(complete)`。`produce(self, scaffold_type, question, questions, answers) -> ScaffoldDraft`。它把 `build_messages` 的返回值调用一次 `complete`，再交给 `parse_scaffold`。`complete` 抛出的异常原样传出。

- [ ] **Step 1: Write the failing test**

Create `tests/test_model_scaffold_agent.py`:

```python
import json

import pytest

from scaffolding.agents import ScaffoldDraft
from scaffolding.model_scaffold import ModelScaffoldAgent, Rejected, build_messages
from scaffolding.records import ItemAnswer, TrueFalseQuestion


def _materials():
    return (TrueFalseQuestion("判断说法", "正确", "题目里有依据"),), (ItemAnswer(selected=("正确",)),)


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


def _reply(text: str = "  先看 ", html: str = "<p>说明</p>") -> str:
    return json.dumps({"文字": text, "HTML": html}, ensure_ascii=False)


def test_produce_returns_the_model_wording_and_calls_once():
    complete = QueueComplete([_reply()])
    agent = ModelScaffoldAgent(complete)
    questions, answers = _materials()

    assert agent.produce("提示", "还缺什么？", questions, answers) == ScaffoldDraft(text="  先看 ", html="<p>说明</p>")
    assert complete.calls == [build_messages("提示", "还缺什么？", questions, answers)]


def test_empty_strings_do_not_fail():
    questions, answers = _materials()
    complete = QueueComplete([_reply(text="", html="")])

    assert ModelScaffoldAgent(complete).produce("提示", "还缺什么？", questions, answers) == ScaffoldDraft()
    assert len(complete.calls) == 1


def test_a_bad_reply_or_completer_error_propagates():
    questions, answers = _materials()
    fenced = QueueComplete(["```json\n" + _reply() + "\n```"])
    failing = QueueComplete([RuntimeError("down")])

    with pytest.raises(Rejected):
        ModelScaffoldAgent(fenced).produce("提示", "还缺什么？", questions, answers)
    with pytest.raises(RuntimeError):
        ModelScaffoldAgent(failing).produce("示范", "还缺{什么}？", questions, answers)

    assert len(fenced.calls) == 1
    assert failing.calls == [build_messages("示范", "还缺{什么}？", questions, answers)]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_scaffold_agent.py -v`

Expected: FAIL because `ModelScaffoldAgent` is not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `src/scaffolding/model_scaffold.py`:

```python
class ModelScaffoldAgent:
    def __init__(self, complete) -> None:
        self._complete = complete

    def produce(self, scaffold_type: str, question: str, questions: tuple, answers: tuple) -> ScaffoldDraft:
        return parse_scaffold(self._complete(build_messages(scaffold_type, question, questions, answers)))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_scaffold_agent.py tests/test_model_scaffold_prompt.py tests/test_model_scaffold_parsing.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/model_scaffold.py tests/test_model_scaffold_agent.py
git commit -m "feat: produce a scaffold draft from a model reply"
```

---

### Task 4: 规格验收

**Files:**
- Create: `tests/test_model_scaffold_acceptance.py`
- Copy: `docs/superpowers/specs/2026-10-19-model-scaffold-agent-design.md`

**Interfaces:**
- Consumes: Task 1 到 Task 3 的全部公开接口，以及已有的 `deepseek_complete`、`Session`、`open_session`、`ScriptedDecisionAgent`。规格文件来自 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-19-model-scaffold-agent-design.md`，即本地 `master` 的 `22b2f6b`。原样复制，不要改写。
- Produces: 验收测试。不新增生产行为。

- [ ] **Step 1: Write the failing test**

Create `tests/test_model_scaffold_acceptance.py`:

```python
import json
from pathlib import Path

import pytest

from scaffolding.model_generator import DEEPSEEK_URL, deepseek_complete
from scaffolding.model_scaffold import ModelScaffoldAgent
from scaffolding.records import AssetKind, HelpSource
from scaffolding.scripted import ScriptedDecisionAgent
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


def _reply(text: str, html: str) -> str:
    return json.dumps({"文字": text, "HTML": html}, ensure_ascii=False)


def test_model_scaffold_agent_spec_is_in_the_workspace():
    spec = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "specs" / "2026-10-19-model-scaffold-agent-design.md"
    assert spec.is_file()


def test_the_session_shows_text_and_assets_and_keeps_an_existing_scaffold():
    html = '<asset kind="思维导图" name="组成.svg">人员—硬件</asset>'
    shown = _reply("先看人员和硬件是否都写到了。", html)
    complete = QueueComplete([
        shown,
        "```json\n" + shown + "\n```",
        _reply("", ""),
    ])
    decision = ScriptedDecisionAgent(presets=("先看题目",), scaffold_type="提示")
    session = open_session(decision, ModelScaffoldAgent(complete))
    session.note_dwell(12.5)

    assert complete.calls == []
    view = session.ask("旧求助原文", HelpSource.OWN)
    assert view.scaffold is not None
    assert view.scaffold.text == "先看人员和硬件是否都写到了。"
    assert view.scaffold.assets[0].kind == AssetKind.MIND_MAP
    assert view.scaffold.assets[0].filename == "组成.svg"
    assert view.scaffold.assets[0].content == "人员—硬件".encode()
    assert view.presets == ("先看题目",)
    assert "参考答案：正确" in complete.calls[0][1]["content"]
    assert "支架类型：提示" in complete.calls[0][1]["content"]
    assert complete.calls[0][1]["content"].endswith("这次提问：旧求助原文")
    assert "不要写出参考答案" in complete.calls[0][0]["content"]
    assert "12.5" not in complete.calls[0][1]["content"]
    assert "停留时间" not in complete.calls[0][1]["content"]

    fenced = session.ask("这题怎么做？", HelpSource.OWN)
    assert fenced.scaffold.text == "先看人员和硬件是否都写到了。"
    assert fenced.presets == ("先看题目",)
    assert "旧求助原文" not in complete.calls[1][1]["content"]

    cleared = session.ask("再问一次", HelpSource.OWN)
    assert cleared.scaffold.text == "先看人员和硬件是否都写到了。"
    assert cleared.presets == ("先看题目",)

    failing = QueueComplete([shown, RuntimeError("down")])
    again = open_session(decision, ModelScaffoldAgent(failing))
    again.ask("旧求助原文", HelpSource.OWN)
    kept = again.ask("调用失败", HelpSource.OWN)
    assert kept.scaffold.text == "先看人员和硬件是否都写到了。"
    assert kept.presets == ("先看题目",)

    sent = []

    def post(url, headers, payload):
        sent.append((url, headers, payload))
        return 200, {"choices": [{"message": {"content": shown}}]}

    assert deepseek_complete(complete.calls[0], post=post, api_key="secret") == shown
    assert sent[0][0] == DEEPSEEK_URL
    assert sent[0][1]["Authorization"] == "Bearer secret"
    assert sent[0][2]["model"] == "deepseek-flash"
    assert sent[0][2]["stream"] is False
    assert sent[0][2]["thinking"] == {"type": "disabled"}
    assert "reasoning_effort" not in sent[0][2]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_model_scaffold_acceptance.py -v`

Expected: FAIL because the spec file is not in the worktree yet. If the spec file is already present and the other assertions fail, stop and report the failure. Do not change production code.

- [ ] **Step 3: Copy the spec and keep the test**

Copy `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-19-model-scaffold-agent-design.md` to `docs/superpowers/specs/2026-10-19-model-scaffold-agent-design.md` in the worktree. Do not edit the spec. Do not change production code.

- [ ] **Step 4: Run the full suite**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS, including the previous scaffolding, publishing, knowledge, objective, generation, and DeepSeek tests.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_model_scaffold_acceptance.py docs/superpowers/specs/2026-10-19-model-scaffold-agent-design.md
git commit -m "test: accept DeepSeek scaffold generation for one help request"
```
