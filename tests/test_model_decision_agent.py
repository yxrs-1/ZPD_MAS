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
