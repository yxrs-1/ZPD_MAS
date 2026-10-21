from scaffolding.knowledge import TextbookLesson
from scaffolding.teacher_page import response_for
from tests.objective_helpers import ScriptedExtractor, sample_base
from tests.teacher_objectives_helpers import form, make_page, text


def test_viewing_a_stage_shows_only_the_standard():
    base = sample_base()
    extractor = ScriptedExtractor()
    page, _objectives = make_page(base, extractor)

    opened = text(response_for(page, "POST", "/objectives", form(
        mode="学段",
        stage="高中",
        version="没有的版本",
        volume="必修一",
        lesson="信息系统的组成",
        action="查看",
    ), ))

    assert "课标全文" in opened
    assert "1.1.2" in opened
    assert "现行" in opened
    assert "课时原文" not in opened
    assert "没有检索到资料" not in opened
    assert extractor.calls == []


def test_a_different_lesson_and_a_half_retrieval_stay_separate():
    base = sample_base()
    base.add_lesson(TextbookLesson("沪科教版", "必修一", "信息系统的组成", "高中", "8", "沪科原文"))
    base.add_lesson(TextbookLesson("人教版", "必修一", "没有课标的课", "初中", "3", "半份原文"))
    extractor = ScriptedExtractor()
    page, _objectives = make_page(base, extractor)

    other = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="沪科教版",
        volume="必修一",
        lesson="信息系统的组成",
        action="查看",
    ), ))
    half = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="没有课标的课",
        action="查看",
    ), ))
    blank_stage = text(response_for(page, "POST", "/objectives", form(
        mode="学段",
        stage="  ",
        action="查看",
    ), ))

    assert "沪科原文" in other
    assert "12-15" not in other
    assert "没有检索到资料" in half
    assert "半份原文" not in half
    assert "先填完整再查询" in blank_stage
    assert extractor.calls == []
