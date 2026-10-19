import json
from pathlib import Path

import pytest

from scaffolding.knowledge import CurriculumStandard
from scaffolding.model_extractor import ModelObjectiveExtractor
from scaffolding.model_generator import DEEPSEEK_URL, deepseek_complete
from scaffolding.objectives import ObjectiveCatalog, Rejected
from tests.objective_helpers import sample_base


def _reply() -> str:
    return json.dumps(
        {"目标": [
            {"维度": "信息意识", "表述": "能识别信息", "来源": "教材"},
            {"维度": "其他", "表述": "丢掉", "来源": "课标"},
        ]},
        ensure_ascii=False,
    )


def test_model_objective_extractor_spec_is_in_the_workspace():
    spec = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "specs" / "2026-10-19-model-objective-extractor-design.md"
    assert spec.is_file()


def test_extraction_uses_one_reply_and_keeps_existing_objective_rules():
    base = sample_base()
    stored = base.get_lesson("人教版", "必修一", "信息系统的组成")
    calls = []

    def complete(messages):
        calls.append(messages)
        return _reply()

    catalog = ObjectiveCatalog(base, ModelObjectiveExtractor(complete))
    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")

    assert [item.objective_id for item in saved] == ["objective-1"]
    assert saved[0].statement == "能识别信息"
    assert saved[0].source == base.retrieve_lesson("人教版", "必修一", "信息系统的组成").lesson_source
    assert len(calls) == 1
    assert "课时原文" in calls[0][1]["content"]
    assert "课标全文" in calls[0][1]["content"]
    with pytest.raises(Rejected):
        catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    assert len(calls) == 1
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能识别信息"

    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    stage_calls = []

    def stage_complete(messages):
        stage_calls.append(messages)
        return json.dumps(
            {"目标": [{"维度": "信息社会责任", "表述": "遵守规范", "来源": "课标"}]},
            ensure_ascii=False,
        )

    stage_catalog = ObjectiveCatalog(base, ModelObjectiveExtractor(stage_complete))
    stage_saved = stage_catalog.extract_stage("初中")
    assert stage_saved[0].objective_id == "objective-1"
    assert stage_saved[0].source == base.retrieve_stage("初中").standard_source
    assert "教材原文" not in stage_calls[0][1]["content"]
    assert "来源只能写成「课标」" in stage_calls[0][0]["content"]

    sent = []

    def post(url, headers, payload):
        sent.append((url, headers, payload))
        return 200, {"choices": [{"message": {"content": _reply()}}]}

    assert deepseek_complete(calls[0], post=post, api_key="secret") == _reply()
    assert sent[0][0] == DEEPSEEK_URL
    assert sent[0][1]["Authorization"] == "Bearer secret"
    assert sent[0][2]["model"] == "deepseek-flash"
    assert sent[0][2]["stream"] is False
    assert sent[0][2]["thinking"] == {"type": "disabled"}
    assert "reasoning_effort" not in sent[0][2]
    assert base.get_lesson("人教版", "必修一", "信息系统的组成") is stored
