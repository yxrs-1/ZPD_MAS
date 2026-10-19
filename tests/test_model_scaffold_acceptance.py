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
