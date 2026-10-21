from scaffolding.knowledge import TextbookLesson
from scaffolding.teacher_page import response_for
from tests.objective_helpers import ScriptedExtractor, sample_base
from tests.teacher_objectives_helpers import form, make_page, text


def test_viewing_a_lesson_shows_both_texts_and_does_not_extract():
    base = sample_base()
    base.add_lesson(TextbookLesson("人教版", "必修一", "数据编码", "高中", "16", "<课时"))
    extractor = ScriptedExtractor()
    page, _objectives = make_page(base, extractor)

    opened = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        stage="初中",
        action="查看",
    ), ))
    again = text(response_for(page, "GET", "/objectives", ""))
    escaped = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="数据编码",
        action="查看",
    ), ))

    assert "课时原文" in opened
    assert "课标全文" in opened
    assert "12-15" in opened
    assert "1.1.2" in opened
    assert "现行" in opened
    assert "没有检索到资料" not in opened
    assert "提炼" in opened
    assert extractor.calls == []
    assert "课时原文" not in again
    assert "&lt;课时" in escaped
    assert "<课时" not in escaped


def test_an_incomplete_or_unknown_lesson_query_stays_on_the_page():
    base = sample_base()
    extractor = ScriptedExtractor()
    page, _objectives = make_page(base, extractor)

    blank = response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="   ",
        volume="必修一",
        lesson="信息系统的组成",
        action="查看",
    ), )
    missing = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="没有这一课",
        action="查看",
    ), ))
    unknown = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        action="发布",
    ), ))

    assert blank.status == 200
    assert "先填完整再查询" in text(blank)
    assert "课时原文" not in text(blank)
    assert "没有检索到资料" in missing
    assert "课时原文" not in missing
    assert "课标全文" not in missing
    assert "任务不存在" not in unknown
    assert "课时原文" not in unknown
    assert extractor.calls == []
