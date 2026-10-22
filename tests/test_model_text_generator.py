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
