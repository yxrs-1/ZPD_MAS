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
