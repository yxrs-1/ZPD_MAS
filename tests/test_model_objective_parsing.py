import json

import pytest

from scaffolding.knowledge import CurriculumStandard, LessonSource
from scaffolding.model_extractor import parse_objectives
from scaffolding.objectives import ObjectiveDraft, Rejected
from tests.objective_helpers import sample_base


def _retrieval():
    return sample_base().retrieve_lesson("人教版", "必修一", "信息系统的组成")


def _body(items: list[dict] | None = None, **extra) -> str:
    body = {
        "目标": [
            {"维度": "信息意识", "表述": "能识别信息", "来源": "教材"},
            {"维度": "其他", "表述": "  ", "来源": "课标"},
        ]
    }
    if items is not None:
        body["目标"] = items
    body.update(extra)
    return json.dumps(body, ensure_ascii=False)


def test_drafts_keep_array_order_and_use_retrieval_sources():
    retrieval = _retrieval()

    assert parse_objectives("\n" + _body() + " ", retrieval) == (
        ObjectiveDraft("信息意识", "能识别信息", retrieval.lesson_source),
        ObjectiveDraft("其他", "  ", retrieval.standard_source),
    )


def test_an_empty_array_returns_no_drafts():
    assert parse_objectives(_body(items=[]), _retrieval()) == ()


def test_an_unmapped_label_is_returned_for_the_existing_filter():
    retrieval = _retrieval()
    stage = sample_base()
    stage.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    stage_retrieval = stage.retrieve_stage("初中")

    assert parse_objectives(
        _body(items=[{"维度": "信息意识", "表述": "其他来源", "来源": "其他"}]),
        retrieval,
    ) == (ObjectiveDraft("信息意识", "其他来源", LessonSource("其他", "其他", "其他", "其他", "其他")),)
    assert parse_objectives(
        _body(items=[{"维度": "信息意识", "表述": "没有教材", "来源": "教材"}]),
        stage_retrieval,
    ) == (ObjectiveDraft("信息意识", "没有教材", LessonSource("教材", "教材", "教材", "教材", "教材")),)


def test_a_code_fence_wrong_shape_or_non_string_is_rejected():
    retrieval = _retrieval()
    extra = json.loads(_body())
    extra["其他"] = []
    missing = {"目标": [{"维度": "信息意识", "表述": "能识别信息"}]}
    number = {"目标": [{"维度": "信息意识", "表述": "能识别信息", "来源": 1}]}
    for text in (
        "```json\n" + _body() + "\n```",
        json.dumps(extra, ensure_ascii=False),
        json.dumps(missing, ensure_ascii=False),
        json.dumps(number, ensure_ascii=False),
        None,
    ):
        with pytest.raises(Rejected):
            parse_objectives(text, retrieval)
