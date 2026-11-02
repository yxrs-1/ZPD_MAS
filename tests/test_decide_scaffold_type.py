import asyncio
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from scaffolding.records import ScaffoldType
from scaffolding.scaffold_decision import PreviousScaffold, decide_scaffold_type


class _Completions:
    def __init__(self, content: str) -> None:
        self.content = content
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _Client:
    def __init__(self, content: str) -> None:
        self.completions = _Completions(content)
        self.chat = SimpleNamespace(completions=self.completions)


def test_returns_the_model_choice_without_changing_it():
    client = _Client(
        json.dumps(
            {"scaffold_type": "示范", "reason": "学生反复改写，需要看一个同类例子"},
            ensure_ascii=False,
        )
    )

    decision = asyncio.run(
        decide_scaffold_type(
            "首次求助",
            "我选了 A",
            [PreviousScaffold(scaffold_type=ScaffoldType.FEEDBACK, content="先看条件")],
            client=client,
        )
    )

    assert decision.scaffold_type is ScaffoldType.MODELING
    assert decision.reason == "学生反复改写，需要看一个同类例子"
    sent = client.completions.kwargs["messages"][1]["content"]
    assert "首次求助" in sent
    assert "我选了 A" in sent
    assert "先看条件" in sent
    assert client.completions.kwargs["response_format"] == {"type": "json_object"}
    assert client.completions.kwargs["model"] == "deepseek-flash"


def test_invalid_label_is_not_replaced():
    client = _Client('{"scaffold_type": "直接给答案", "reason": "不行"}')

    with pytest.raises(ValidationError):
        asyncio.run(decide_scaffold_type("尝试中", "不会", [], client=client))
