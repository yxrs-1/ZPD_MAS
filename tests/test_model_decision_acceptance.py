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
