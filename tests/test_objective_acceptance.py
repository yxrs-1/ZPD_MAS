from pathlib import Path

import pytest

from scaffolding.knowledge import CurriculumStandard, KnowledgeBase, LessonRetrieval, TextbookLesson
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft, Rejected
from tests.objective_helpers import ScriptedExtractor, sample_base


def test_objective_extraction_spec_is_in_the_workspace():
    spec = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "specs" / "2026-10-19-objective-extraction-design.md"
    assert spec.is_file()


class EmptyOnSecondLessonRetrieve(KnowledgeBase):
    def __init__(self) -> None:
        super().__init__()
        self.lesson_retrieves = 0

    def retrieve_lesson(self, version: str, volume: str, lesson: str) -> LessonRetrieval | None:
        self.lesson_retrieves += 1
        if self.lesson_retrieves > 1:
            return None
        return super().retrieve_lesson(version, volume, lesson)


def test_extraction_matches_the_spec():
    base = sample_base()
    stored_lesson = base.get_lesson("人教版", "必修一", "信息系统的组成")
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    base.add_lesson(TextbookLesson("沪科教版", "必修一", "信息系统的组成", "高中", "8", "另一课时原文"))
    lesson_retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    other_retrieval = base.retrieve_lesson("沪科教版", "必修一", "信息系统的组成")
    junior = base.retrieve_stage("初中")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (
        ObjectiveDraft("计算思维", "能描述组成", lesson_retrieval.lesson_source),
        ObjectiveDraft("超纲维度", "不算", lesson_retrieval.lesson_source),
        ObjectiveDraft("信息意识", " ", lesson_retrieval.standard_source),
        ObjectiveDraft("信息意识", "能识别信息", lesson_retrieval.standard_source),
        ObjectiveDraft("信息意识", "外来目标", other_retrieval.lesson_source),
    )
    extractor.stage_results = (ObjectiveDraft("课外", "不算", junior.standard_source),)
    catalog = ObjectiveCatalog(base, extractor)

    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    assert [(item.objective_id, item.dimension, item.statement, item.source) for item in saved] == [
        ("objective-1", "计算思维", "能描述组成", lesson_retrieval.lesson_source),
        ("objective-2", "信息意识", "能识别信息", lesson_retrieval.standard_source),
    ]
    assert catalog.extract_stage("初中") == ()
    assert catalog.stage_objectives("初中") == ()

    extractor.stage_results = (ObjectiveDraft("信息社会责任", "遵守规范", junior.standard_source),)
    stage_saved = catalog.extract_stage("初中")
    assert stage_saved[0].source == junior.standard_source
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == saved

    extractor.lesson_results = (ObjectiveDraft("计算思维", "另一版本", other_retrieval.lesson_source),)
    other = catalog.extract_lesson("沪科教版", "必修一", "信息系统的组成")
    assert other[0].statement == "另一版本"
    assert other[0].objective_id == "objective-4"

    calls = len(extractor.calls)
    assert catalog.extract_lesson("人教版", "必修一", "没有的课") == ()
    assert len(extractor.calls) == calls

    failing = ScriptedExtractor()
    failing.lesson_error = RuntimeError("down")
    failed = ObjectiveCatalog(base, failing)
    with pytest.raises(RuntimeError):
        failed.extract_lesson("人教版", "必修一", "信息系统的组成")
    assert failed.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()

    calls = len(extractor.calls)
    with pytest.raises(Rejected):
        catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    assert len(extractor.calls) == calls
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == saved

    edited = catalog.edit_statement("objective-1", "改后的表述")
    assert (edited.objective_id, edited.dimension, edited.source, edited.statement) == (
        "objective-1",
        "计算思维",
        lesson_retrieval.lesson_source,
        "改后的表述",
    )
    with pytest.raises(Rejected):
        catalog.edit_statement("objective-1", " ")
    with pytest.raises(Rejected):
        catalog.edit_statement("objective-missing", "新表述")
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "改后的表述"

    catalog.delete("objective-2")
    remaining = catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")
    assert [item.objective_id for item in remaining] == ["objective-1"]
    with pytest.raises(Rejected):
        catalog.delete("objective-2")
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == remaining
    catalog.delete("objective-1")
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
    extractor.lesson_results = (ObjectiveDraft("信息意识", "重新提炼", lesson_retrieval.lesson_source),)
    again = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    assert again[0].objective_id == "objective-5"
    assert base.get_lesson("人教版", "必修一", "信息系统的组成") is stored_lesson
    assert stage_saved[0].statement == "遵守规范"


def test_existing_record_is_still_rejected_when_retrieval_becomes_empty():
    base = EmptyOnSecondLessonRetrieve()
    base.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "课时原文"))
    base.add_standard(CurriculumStandard("普通高中信息科技课程标准", "高中", "1.1.2", "课标全文"))
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    base.lesson_retrieves = 0
    extractor = ScriptedExtractor()
    extractor.lesson_results = (ObjectiveDraft("信息意识", "原目标", retrieval.lesson_source),)
    catalog = ObjectiveCatalog(base, extractor)
    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")

    with pytest.raises(Rejected):
        catalog.extract_lesson("人教版", "必修一", "信息系统的组成")

    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == saved
    assert len(extractor.calls) == 1
