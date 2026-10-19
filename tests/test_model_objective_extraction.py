import json

import pytest

from scaffolding.knowledge import CurriculumStandard, KnowledgeBase, TextbookLesson
from scaffolding.model_extractor import ModelObjectiveExtractor, build_messages
from scaffolding.objectives import ObjectiveCatalog, Rejected
from tests.objective_helpers import sample_base


class RecordingComplete:
    def __init__(self, text: str = "", error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.calls = []

    def __call__(self, messages):
        self.calls.append(messages)
        if self.error is not None:
            raise self.error
        return self.text


class EmptyAfterSave(KnowledgeBase):
    def __init__(self) -> None:
        super().__init__()
        self.saved = False

    def retrieve_lesson(self, version: str, volume: str, lesson: str):
        if self.saved:
            return None
        return super().retrieve_lesson(version, volume, lesson)


def _reply(items: list[dict] | None = None) -> str:
    if items is None:
        items = [
            {"维度": "信息意识", "表述": "能识别信息", "来源": "教材"},
            {"维度": "其他", "表述": "丢掉", "来源": "教材"},
            {"维度": "信息社会责任", "表述": " ", "来源": "课标"},
            {"维度": "计算思维", "表述": "能分解问题", "来源": "其他"},
            {"维度": "数字化学习与创新", "表述": "能选用工具", "来源": "课标"},
        ]
    return json.dumps({"目标": items}, ensure_ascii=False)


def _catalog(base: KnowledgeBase, complete: RecordingComplete) -> ObjectiveCatalog:
    return ObjectiveCatalog(base, ModelObjectiveExtractor(complete))


def test_a_mixed_reply_saves_only_valid_objectives_in_order():
    base = sample_base()
    stored = base.get_lesson("人教版", "必修一", "信息系统的组成")
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    complete = RecordingComplete(_reply())
    catalog = _catalog(base, complete)

    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")

    assert [item.objective_id for item in saved] == ["objective-1", "objective-2"]
    assert [item.statement for item in saved] == ["能识别信息", "能选用工具"]
    assert saved[0].source == retrieval.lesson_source
    assert saved[1].source == retrieval.standard_source
    assert complete.calls == [build_messages(retrieval)]
    assert base.get_lesson("人教版", "必修一", "信息系统的组成") is stored

    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    stage_retrieval = base.retrieve_stage("初中")
    stage_complete = RecordingComplete(_reply([
        {"维度": "信息意识", "表述": "没有教材", "来源": "教材"},
        {"维度": "信息社会责任", "表述": "遵守规范", "来源": "课标"},
    ]))
    stage_saved = ObjectiveCatalog(base, ModelObjectiveExtractor(stage_complete)).extract_stage("初中")
    assert [item.statement for item in stage_saved] == ["遵守规范"]
    assert stage_saved[0].source == stage_retrieval.standard_source
    assert stage_saved[0].objective_id == "objective-1"
    assert len(stage_complete.calls) == 1


def test_nothing_valid_allocates_no_id_and_can_run_again():
    base = sample_base()
    complete = RecordingComplete(_reply([]))
    catalog = _catalog(base, complete)

    assert catalog.extract_lesson("人教版", "必修一", "信息系统的组成") == ()
    complete.text = _reply([{"维度": "信息意识", "表述": "能识别信息", "来源": "教材"}])
    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")

    assert [item.objective_id for item in saved] == ["objective-1"]
    assert len(complete.calls) == 2


def test_a_bad_reply_or_completer_error_saves_nothing():
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    first = RecordingComplete(_reply([{"维度": "信息意识", "表述": "先保存", "来源": "教材"}]))
    catalog = _catalog(base, first)
    catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    fenced = RecordingComplete("```json\n" + _reply() + "\n```")
    separate = sample_base()
    fenced_catalog = _catalog(separate, fenced)

    with pytest.raises(Rejected):
        fenced_catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    failing = RecordingComplete(error=RuntimeError("down"))
    with pytest.raises(RuntimeError):
        _catalog(sample_base(), failing).extract_lesson("人教版", "必修一", "信息系统的组成")

    assert len(fenced.calls) == 1
    assert len(failing.calls) == 1
    assert fenced_catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "先保存"
    assert retrieval.lesson_text == "课时原文"


def test_existing_records_and_empty_retrievals_do_not_call_the_completer():
    base = EmptyAfterSave()
    base.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "课时原文"))
    base.add_standard(CurriculumStandard("普通高中信息科技课程标准", "高中", "1.1.2", "课标全文"))
    complete = RecordingComplete(_reply([{"维度": "信息意识", "表述": "能识别信息", "来源": "教材"}]))
    catalog = _catalog(base, complete)
    catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    base.saved = True

    with pytest.raises(Rejected):
        catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    assert catalog.extract_lesson("沪科教版", "必修一", "信息系统的组成") == ()
    assert len(complete.calls) == 1
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能识别信息"
