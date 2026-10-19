import pytest

from scaffolding.knowledge import CurriculumStandard, KnowledgeBase, LessonRetrieval, TextbookLesson
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft, Rejected
from tests.objective_helpers import ScriptedExtractor, sample_base


class EmptyOnSecondLessonRetrieve(KnowledgeBase):
    def __init__(self) -> None:
        super().__init__()
        self.lesson_retrieves = 0

    def retrieve_lesson(self, version: str, volume: str, lesson: str) -> LessonRetrieval | None:
        self.lesson_retrieves += 1
        if self.lesson_retrieves > 1:
            return None
        return super().retrieve_lesson(version, volume, lesson)


def test_lesson_extract_saves_valid_objectives_in_order():
    base = sample_base()
    stored_lesson = base.get_lesson("人教版", "必修一", "信息系统的组成")
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (
        ObjectiveDraft("计算思维", "能描述组成", retrieval.lesson_source),
        ObjectiveDraft("超纲维度", "不算", retrieval.lesson_source),
        ObjectiveDraft("信息意识", "能识别信息", retrieval.standard_source),
        ObjectiveDraft("信息意识", "能再举一例", retrieval.lesson_source),
    )
    catalog = ObjectiveCatalog(base, extractor)

    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")

    assert [(item.objective_id, item.dimension, item.statement) for item in saved] == [
        ("objective-1", "计算思维", "能描述组成"),
        ("objective-2", "信息意识", "能识别信息"),
        ("objective-3", "信息意识", "能再举一例"),
    ]
    assert saved[0].source == retrieval.lesson_source
    assert saved[1].source == retrieval.standard_source
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == saved
    assert extractor.calls == [retrieval]
    assert base.get_lesson("人教版", "必修一", "信息系统的组成") is stored_lesson


def test_stage_record_is_independent_of_the_lesson_record():
    base = sample_base()
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    lesson_retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    stage_retrieval = base.retrieve_stage("初中")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (ObjectiveDraft("信息意识", "课时目标", lesson_retrieval.lesson_source),)
    extractor.stage_results = (
        ObjectiveDraft("信息意识", "不该留下", lesson_retrieval.lesson_source),
        ObjectiveDraft("信息社会责任", "遵守规范", stage_retrieval.standard_source),
    )
    catalog = ObjectiveCatalog(base, extractor)

    lesson_saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    stage_saved = catalog.extract_stage("初中")

    assert stage_saved[0].objective_id == "objective-2"
    assert stage_saved[0].source == stage_retrieval.standard_source
    assert catalog.stage_objectives("初中") == stage_saved
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == lesson_saved
    assert catalog.stage_objectives("高中") == ()


def test_a_different_version_is_another_record():
    base = sample_base()
    base.add_lesson(TextbookLesson("沪科教版", "必修一", "信息系统的组成", "高中", "8", "另一课时原文"))
    first = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    second = base.retrieve_lesson("沪科教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (ObjectiveDraft("计算思维", "第一份", first.lesson_source),)
    catalog = ObjectiveCatalog(base, extractor)
    catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    extractor.lesson_results = (ObjectiveDraft("计算思维", "第二份", second.lesson_source),)

    other = catalog.extract_lesson("沪科教版", "必修一", "信息系统的组成")

    assert other[0].statement == "第二份"
    assert other[0].objective_id == "objective-2"
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "第一份"


def test_empty_retrieval_does_not_call_the_extractor_or_save():
    base = sample_base()
    extractor = ScriptedExtractor()
    catalog = ObjectiveCatalog(base, extractor)

    assert catalog.extract_lesson("人教版", "必修一", "没有的课") == ()
    assert catalog.extract_stage("高中 ") == ()
    assert extractor.calls == []
    assert catalog.lesson_objectives("人教版", "必修一", "没有的课") == ()
    assert catalog.stage_objectives("高中") == ()


def test_no_valid_objective_does_not_save_or_consume_an_id():
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (ObjectiveDraft("超纲维度", "不算", retrieval.lesson_source),)
    catalog = ObjectiveCatalog(base, extractor)

    assert catalog.extract_lesson("人教版", "必修一", "信息系统的组成") == ()
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
    extractor.lesson_results = (ObjectiveDraft("信息意识", "稍后保存", retrieval.lesson_source),)
    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    assert saved[0].objective_id == "objective-1"


def test_extractor_failure_does_not_save():
    base = sample_base()
    extractor = ScriptedExtractor()
    extractor.lesson_error = RuntimeError("down")
    extractor.lesson_results = (
        ObjectiveDraft("信息意识", "不会保存", base.retrieve_lesson("人教版", "必修一", "信息系统的组成").lesson_source),
    )
    catalog = ObjectiveCatalog(base, extractor)

    with pytest.raises(RuntimeError, match="down"):
        catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
    extractor.lesson_error = None
    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    assert saved[0].objective_id == "objective-1"


def test_second_extract_is_rejected_and_existing_objectives_stay():
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (ObjectiveDraft("信息意识", "原目标", retrieval.lesson_source),)
    catalog = ObjectiveCatalog(base, extractor)
    saved = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    extractor.lesson_error = RuntimeError("down")

    with pytest.raises(Rejected):
        catalog.extract_lesson("人教版", "必修一", "信息系统的组成")

    assert extractor.calls == [retrieval]
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == saved


def test_existing_record_is_rejected_even_when_the_second_retrieval_is_empty():
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
