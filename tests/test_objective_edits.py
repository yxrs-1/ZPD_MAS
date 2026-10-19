import pytest

from scaffolding.knowledge import CurriculumStandard
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft, Rejected
from tests.objective_helpers import ScriptedExtractor, sample_base


def _catalog():
    base = sample_base()
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    lesson_retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    stage_retrieval = base.retrieve_stage("初中")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (
        ObjectiveDraft("计算思维", "能描述组成", lesson_retrieval.lesson_source),
        ObjectiveDraft("信息意识", "能识别信息", lesson_retrieval.standard_source),
        ObjectiveDraft("信息社会责任", "遵守规范", lesson_retrieval.lesson_source),
    )
    extractor.stage_results = (ObjectiveDraft("信息意识", "学段目标", stage_retrieval.standard_source),)
    catalog = ObjectiveCatalog(base, extractor)
    catalog.extract_lesson("人教版", "必修一", "信息系统的组成")
    catalog.extract_stage("初中")
    return base, extractor, catalog


def test_edit_changes_only_the_statement():
    base, extractor, catalog = _catalog()
    stored_lesson = base.get_lesson("人教版", "必修一", "信息系统的组成")
    before = catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")
    calls = len(extractor.calls)

    edited = catalog.edit_statement("objective-2", " 改后的表述 ")
    after = catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")

    assert edited.statement == " 改后的表述 "
    assert (edited.objective_id, edited.dimension, edited.source) == ("objective-2", "信息意识", before[1].source)
    assert after[0] is before[0]
    assert after[2] is before[2]
    assert after[1] == edited
    assert catalog.stage_objectives("初中")[0].statement == "学段目标"
    assert len(extractor.calls) == calls
    assert base.get_lesson("人教版", "必修一", "信息系统的组成") is stored_lesson


def test_blank_or_missing_edit_keeps_the_stored_objective():
    _, extractor, catalog = _catalog()
    before = catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")
    calls = len(extractor.calls)

    with pytest.raises(Rejected):
        catalog.edit_statement("objective-1", " ")
    with pytest.raises(Rejected):
        catalog.edit_statement("objective-missing", "新表述")

    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == before
    assert before[0] is catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")[0]
    assert len(extractor.calls) == calls


def test_delete_keeps_the_remaining_ids_and_order():
    base, extractor, catalog = _catalog()
    calls = len(extractor.calls)

    catalog.delete("objective-2")
    remaining = catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")

    assert [(item.objective_id, item.statement) for item in remaining] == [
        ("objective-1", "能描述组成"),
        ("objective-3", "遵守规范"),
    ]
    assert catalog.stage_objectives("初中")[0].objective_id == "objective-4"
    with pytest.raises(Rejected):
        catalog.delete("objective-2")
    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == remaining
    assert len(extractor.calls) == calls
    assert base.lesson_count() == 1


def test_deleting_the_last_objective_allows_extract_again_with_a_new_id():
    base, extractor, catalog = _catalog()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    for objective_id in ("objective-1", "objective-2", "objective-3"):
        catalog.delete(objective_id)

    assert catalog.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
    extractor.lesson_results = (ObjectiveDraft("计算思维", "重新提炼", retrieval.lesson_source),)
    again = catalog.extract_lesson("人教版", "必修一", "信息系统的组成")

    assert again[0].objective_id == "objective-5"
    assert again[0].statement == "重新提炼"
    assert catalog.stage_objectives("初中")[0].objective_id == "objective-4"
