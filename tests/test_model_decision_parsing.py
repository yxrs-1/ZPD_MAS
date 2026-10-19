import json

import pytest

from scaffolding.model_decision import Rejected, parse_presets, parse_scaffold_type
from scaffolding.tasks import Rejected as TaskRejected


def _presets(items: list[str] | None = None, **extra) -> str:
    body = {"预设提问": ["先看题目", " ", "先看题目", "  能再看一看条件吗？"]}
    if items is not None:
        body["预设提问"] = items
    body.update(extra)
    return json.dumps(body, ensure_ascii=False)


def test_presets_drop_blanks_and_keep_order_duplicates_and_original_text():
    assert parse_presets("\n" + _presets() + " ") == (
        "先看题目",
        "先看题目",
        "  能再看一看条件吗？",
    )
    assert Rejected is not TaskRejected


def test_an_empty_or_all_blank_preset_array_returns_nothing():
    assert parse_presets(_presets(items=[])) == ()
    assert parse_presets(_presets(items=[" ", ""])) == ()


@pytest.mark.parametrize("scaffold_type", ["反馈", "提示", "指导", "解释", "示范", "提问"])
def test_each_scaffold_type_is_accepted(scaffold_type: str):
    assert parse_scaffold_type(json.dumps({"类型": scaffold_type}, ensure_ascii=False)) == scaffold_type


def test_a_code_fence_wrong_shape_or_non_string_is_rejected():
    extra = json.loads(_presets())
    extra["其他"] = []
    missing = {"预设提问": ["先看题目"]}
    missing.pop("预设提问")
    number = {"预设提问": ["先看题目", 1]}
    spaced = {"类型": " 提示"}
    for text in (
        "```json\n" + _presets() + "\n```",
        json.dumps(extra, ensure_ascii=False),
        json.dumps(missing, ensure_ascii=False),
        json.dumps(number, ensure_ascii=False),
        json.dumps(spaced, ensure_ascii=False),
        json.dumps({"类型": "第4级"}, ensure_ascii=False),
        None,
    ):
        with pytest.raises(Rejected):
            parse_presets(text)
        with pytest.raises(Rejected):
            parse_scaffold_type(text)
