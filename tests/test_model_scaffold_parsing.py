import json

import pytest

from scaffolding.agents import ScaffoldDraft
from scaffolding.model_scaffold import Rejected, parse_scaffold
from scaffolding.tasks import Rejected as TaskRejected


def _body(text: str = "  先看 ", source: str = "", **extra) -> str:
    body = {"文字": text, "源码": source}
    body.update(extra)
    return json.dumps(body, ensure_ascii=False)


def test_text_and_source_keep_the_model_wording_and_assets_stay_empty():
    assert parse_scaffold("\n" + _body() + " ") == ScaffoldDraft(text="  先看 ")
    assert Rejected is not TaskRejected


def test_empty_strings_return_an_empty_draft():
    assert parse_scaffold(_body(text="", source="")) == ScaffoldDraft()
    assert parse_scaffold(_body(text="  ", source="  ")) == ScaffoldDraft(text="  ", source="  ")


def test_a_code_fence_wrong_shape_or_non_string_is_rejected():
    extra = json.loads(_body())
    extra["其他"] = []
    missing = {"文字": "先看"}
    number = {"文字": "先看", "源码": 1}
    for text in (
        "```json\n" + _body() + "\n```",
        json.dumps(extra, ensure_ascii=False),
        json.dumps(missing, ensure_ascii=False),
        json.dumps(number, ensure_ascii=False),
        None,
    ):
        with pytest.raises(Rejected):
            parse_scaffold(text)
