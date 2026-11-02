import json

import pytest

from scaffolding.model_scaffold import ModelScaffoldAgent
from scaffolding.model_trace import install_trace_sender
from scaffolding.records import ItemAnswer, TrueFalseQuestion


@pytest.fixture
def traces():
    found = []
    install_trace_sender(found.append)
    try:
        yield found
    finally:
        install_trace_sender(None)


def test_a_rewritten_scaffold_records_the_final_wording(traces):
    first = json.dumps({"文字": "引导学生看空序列。", "源码": ""}, ensure_ascii=False)
    second = json.dumps({"文字": "你看空序列。", "源码": ""}, ensure_ascii=False)
    replies = [first, second]
    questions = (TrueFalseQuestion("判断说法", "正确", "题目里有依据"),)
    answers = (ItemAnswer(selected=("正确",)),)

    draft = ModelScaffoldAgent(lambda _messages: replies.pop(0)).produce(
        "反馈",
        "还缺什么？",
        questions,
        answers,
    )

    assert draft.text == "你看空序列。"
    assert len(traces) == 1
    assert traces[0]["metadata"]["支架类型"] == "反馈"
    assert traces[0]["metadata"]["支架正文"] == "你看空序列。"
    assert traces[0]["output"] == first


def test_a_failed_rewrite_keeps_the_first_record(traces):
    first = json.dumps({"文字": "引导学生看空序列。", "源码": ""}, ensure_ascii=False)
    replies = [first, RuntimeError("down")]
    questions = (TrueFalseQuestion("判断说法", "正确", "题目里有依据"),)
    answers = (ItemAnswer(selected=("正确",)),)

    def complete(_messages):
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    with pytest.raises(RuntimeError):
        ModelScaffoldAgent(complete).produce("反馈", "还缺什么？", questions, answers)

    assert len(traces) == 1
    assert traces[0]["output"] == first
    assert "支架正文" not in traces[0]["metadata"]
