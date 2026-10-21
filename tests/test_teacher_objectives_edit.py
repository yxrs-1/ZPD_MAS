from scaffolding.knowledge import CurriculumStandard
from scaffolding.objectives import ObjectiveDraft
from scaffolding.teacher_page import response_for
from tests.objective_helpers import ScriptedExtractor, sample_base
from tests.teacher_objectives_helpers import form, make_page, text


def _prepare():
    base = sample_base()
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    lesson = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    stage = base.retrieve_stage("初中")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (
        ObjectiveDraft("计算思维", "能描述组成", lesson.lesson_source),
        ObjectiveDraft("信息意识", "能识别信息", lesson.standard_source),
    )
    extractor.stage_results = (ObjectiveDraft("信息社会责任", "遵守规范", stage.standard_source),)
    page, objectives = make_page(base, extractor)
    response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        action="提炼",
    ), )
    response_for(page, "POST", "/objectives", form(
        mode="学段",
        stage="初中",
        action="提炼",
    ), )
    return page, objectives, base


def test_edit_changes_only_the_statement_in_the_current_query():
    page, objectives, base = _prepare()
    stored = base.get_lesson("人教版", "必修一", "信息系统的组成")

    edited = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        objective="objective-1",
        statement="能说明组成",
        action="修改",
    ), ))
    blank = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        objective="objective-1",
        statement="  ",
        action="修改",
    ), ))
    other = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        objective="objective-3",
        statement="不该改学段",
        action="修改",
    ), ))

    assert "能说明组成" in edited
    assert "计算思维" in edited
    assert "课时原文" in edited
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能说明组成"
    assert "表述不能为空" in blank
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能说明组成"
    assert "目标不存在" in other
    assert objectives.stage_objectives("初中")[0].statement == "遵守规范"
    assert base.get_lesson("人教版", "必修一", "信息系统的组成") is stored


def test_delete_keeps_the_remaining_ids_and_allows_extract_when_none_remain():
    page, objectives, _base = _prepare()

    deleted = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        objective="objective-1",
        action="删除",
    ), ))

    assert "objective-1" not in deleted
    assert "objective-2" in deleted
    assert "能识别信息" in deleted
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].objective_id == "objective-2"

    cleared = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        objective="objective-2",
        action="删除",
    ), ))
    assert "提炼" in cleared
    assert "课时原文" in cleared
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
    assert objectives.stage_objectives("初中")[0].statement == "遵守规范"
