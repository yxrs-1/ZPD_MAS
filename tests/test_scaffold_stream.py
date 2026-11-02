import json

from scaffolding.model_generator import deepseek_stream
from scaffolding.model_scaffold import (
    begin_scaffold_progress,
    end_scaffold_progress,
    feed_scaffold_stream,
    partial_scaffold_text,
)
from scaffolding.records import HelpSource
from scaffolding.scripted import ScriptedDecisionAgent
from scaffolding.model_scaffold import ModelScaffoldAgent
from tests.helpers import open_session


def test_partial_text_follows_the_json_string():
    assert partial_scaffold_text("") == ""
    assert partial_scaffold_text('{"文字": "先') == "先"
    assert partial_scaffold_text('{"文字": "先看这张图。"}') == "先看这张图。"
    assert partial_scaffold_text('{"文字": "第一行\\n第二行"') == "第一行\n第二行"
    assert partial_scaffold_text('{"文字": "未写完的斜杠\\') == "未写完的斜杠"


def test_ask_reports_the_figure_and_the_text_as_it_arrives():
    seen = []
    kinds = []

    def complete(messages):
        feed_scaffold_stream('{"文字": "先')
        feed_scaffold_stream('{"文字": "先看这张图。", "源码": ""}')
        return json.dumps({"文字": "先看这张图。", "源码": ""}, ensure_ascii=False)

    session = open_session(
        ScriptedDecisionAgent(presets=("先看题目",), scaffold_type="提示"),
        ModelScaffoldAgent(complete),
    )
    session.ask(
        "这题怎么看",
        HelpSource.OWN,
        on_text=seen.append,
        on_kind=kinds.append,
    )

    assert kinds == ["思维导图"]
    assert seen == ["先", "先看这张图。"]


def test_a_text_only_scaffold_reports_an_empty_kind():
    kinds = []
    session = open_session(
        ScriptedDecisionAgent(presets=("先看题目",), scaffold_type="反馈"),
        ModelScaffoldAgent(lambda messages: json.dumps({"文字": "再看一遍你的选择。", "源码": ""}, ensure_ascii=False)),
    )
    session.ask("这题怎么看", HelpSource.OWN, on_kind=kinds.append)
    assert kinds == [""]


class _Stream:
    status = 200

    def __iter__(self):
        yield (
            "data: "
            + json.dumps({"choices": [{"delta": {"content": '{"文字": "看'}}]}, ensure_ascii=False)
            + "\n"
        ).encode()
        yield b"\n"
        yield b"data: [DONE]\n"

    def close(self):
        pass


def test_the_model_stream_publishes_text_as_pieces_arrive():
    captured = {}

    def opener(request, timeout):
        captured["payload"] = json.loads(request.data.decode())
        captured["timeout"] = timeout
        return _Stream()

    seen = []
    token = begin_scaffold_progress(seen.append)
    try:
        text = deepseek_stream(
            ({"role": "user", "content": "hi"},),
            opener=opener,
            api_key="test-key",
        )
    finally:
        end_scaffold_progress(token)

    assert captured["payload"]["stream"] is True
    assert captured["payload"]["thinking"] == {"type": "disabled"}
    assert seen == ["看"]
    assert text == '{"文字": "看'
