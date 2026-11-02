import json

import pytest

from scaffolding.agents import ScaffoldDraft
from scaffolding.model_scaffold import (
    ModelScaffoldAgent,
    Rejected,
    begin_scaffold_progress,
    build_messages,
    clear_scaffold_progress,
    end_scaffold_progress,
    feed_scaffold_stream,
)
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


def _reply(text: str = "  先看 ", source: str = "") -> str:
    return json.dumps({"文字": text, "源码": source}, ensure_ascii=False)


def test_produce_returns_the_model_wording_and_calls_once():
    complete = QueueComplete([_reply()])
    agent = ModelScaffoldAgent(complete)
    questions, answers = _materials()

    assert agent.produce("提示", "还缺什么？", questions, answers) == ScaffoldDraft(text="  先看 ")
    assert complete.calls == [build_messages("提示", "还缺什么？", questions, answers)]


def test_empty_strings_do_not_fail():
    questions, answers = _materials()
    complete = QueueComplete([_reply(text="", source="")])

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


def _follow(previous: str) -> dict[str, str]:
    return {
        "role": "user",
        "content": "上一稿是在对教师说话，按规则改成直接对学生说的话。\n上一稿：" + previous,
    }


def test_teacher_voice_is_rewritten_once_with_the_same_materials():
    questions, answers = _materials()
    previous = "引导学生看空序列。"
    complete = QueueComplete([_reply(previous), _reply("你看空序列。")])
    passages = (("笔记.txt", "空序列"),)

    draft = ModelScaffoldAgent(complete).produce(
        "提示",
        "还缺什么？",
        questions,
        answers,
        passages=passages,
        example_source="网络\n  空\n",
    )

    system, user = build_messages(
        "提示",
        "还缺什么？",
        questions,
        answers,
        passages,
        example_source="网络\n  空\n",
    )
    assert draft == ScaffoldDraft(text="你看空序列。")
    assert complete.calls == [(system, user), (system, user, _follow(previous))]


def test_a_second_teacher_voice_reply_is_returned():
    questions, answers = _materials()
    complete = QueueComplete([_reply("引导学生。"), _reply("你让学生再看一次。")])

    draft = ModelScaffoldAgent(complete).produce("反馈", "还缺什么？", questions, answers)

    assert draft.text == "你让学生再看一次。"
    assert len(complete.calls) == 2


def test_blank_text_and_a_marked_source_do_not_retry():
    questions, answers = _materials()
    blank = QueueComplete([_reply(text="   ")])
    marked = QueueComplete([_reply("你看这个节点。", source="节点：学生")])

    assert ModelScaffoldAgent(blank).produce("反馈", "还缺什么？", questions, answers) == ScaffoldDraft(text="   ")
    assert ModelScaffoldAgent(marked).produce("提示", "还缺什么？", questions, answers) == ScaffoldDraft(
        text="你看这个节点。",
        source="节点：学生",
    )
    assert len(blank.calls) == 1
    assert len(marked.calls) == 1


def test_the_first_failure_does_not_retry():
    questions, answers = _materials()
    fenced = QueueComplete(["```json\n" + _reply("引导学生。") + "\n```"])
    extra = QueueComplete([json.dumps({"文字": "引导学生。", "源码": "", "多余": ""}, ensure_ascii=False)])
    failing = QueueComplete([RuntimeError("down")])
    foreign = QueueComplete([{"文字": "引导学生。"}])

    with pytest.raises(Rejected):
        ModelScaffoldAgent(fenced).produce("提示", "还缺什么？", questions, answers)
    with pytest.raises(Rejected):
        ModelScaffoldAgent(extra).produce("提示", "还缺什么？", questions, answers)
    with pytest.raises(RuntimeError):
        ModelScaffoldAgent(failing).produce("提示", "还缺什么？", questions, answers)
    with pytest.raises(Rejected):
        ModelScaffoldAgent(foreign).produce("提示", "还缺什么？", questions, answers)

    assert len(fenced.calls) == 1
    assert len(extra.calls) == 1
    assert len(failing.calls) == 1
    assert len(foreign.calls) == 1


def test_the_second_failure_propagates_and_stops():
    questions, answers = _materials()
    fenced = QueueComplete([_reply("引导学生。"), "```json\n" + _reply("你看空序列。") + "\n```"])
    failing = QueueComplete([_reply("引导学生。"), RuntimeError("down")])

    with pytest.raises(Rejected):
        ModelScaffoldAgent(fenced).produce("提示", "还缺什么？", questions, answers)
    with pytest.raises(RuntimeError):
        ModelScaffoldAgent(failing).produce("提示", "还缺什么？", questions, answers)

    assert len(fenced.calls) == 2
    assert len(failing.calls) == 2


def test_clear_scaffold_progress_emits_the_same_partial_again():
    seen = []
    token = begin_scaffold_progress(seen.append)
    try:
        feed_scaffold_stream('{"文字": "先看"')
        feed_scaffold_stream('{"文字": "先看"')
        assert seen == ["先看"]
        clear_scaffold_progress()
        feed_scaffold_stream('{"文字": "先看"')
        assert seen == ["先看", "先看"]
    finally:
        end_scaffold_progress(token)


def test_a_rewrite_clears_the_stream_before_the_second_reply():
    seen = []
    token = begin_scaffold_progress(seen.append)
    chunks = [
        ['{"文字": "引导学生"'],
        ['{"文字": "引导学生"', '{"文字": "你看空序列。"'],
    ]

    def complete(messages):
        complete.calls.append(messages)
        for raw in chunks.pop(0):
            feed_scaffold_stream(raw)
        return complete.replies.pop(0)

    complete.calls = []
    complete.replies = [_reply("引导学生"), _reply("你看空序列。")]
    questions, answers = _materials()
    try:
        draft = ModelScaffoldAgent(complete).produce("反馈", "还缺什么？", questions, answers)
    finally:
        end_scaffold_progress(token)

    assert draft.text == "你看空序列。"
    assert seen == ["引导学生", "引导学生", "你看空序列。"]
