from scaffolding.objectives import ObjectiveDraft
from scaffolding.teacher_page import response_for
from tests.objective_helpers import ScriptedExtractor, sample_base
from tests.teacher_objectives_helpers import form, make_page, text


def _lesson_form(**extra):
    fields = {
        "mode": "课时",
        "version": "人教版",
        "volume": "必修一",
        "lesson": "信息系统的组成",
        "action": "提炼",
    }
    fields.update(extra)
    return form(**fields)


def test_extract_keeps_valid_objectives_and_drops_the_rest():
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (
        ObjectiveDraft("计算思维", "能描述组成", retrieval.lesson_source),
        ObjectiveDraft("超纲维度", "不算", retrieval.lesson_source),
        ObjectiveDraft("信息意识", "   ", retrieval.lesson_source),
        ObjectiveDraft("信息意识", "能识别信息", retrieval.standard_source),
        ObjectiveDraft("信息意识", "能再举一例", retrieval.lesson_source),
    )
    page, objectives = make_page(base, extractor)

    opened = text(response_for(page, "POST", "/objectives", _lesson_form(), ))

    assert opened.index("objective-1") < opened.index("objective-2")
    assert "能描述组成" in opened
    assert "能识别信息" in opened
    assert "能再举一例" in opened
    assert opened.index("能识别信息") < opened.index("能再举一例")
    assert "不算" not in opened
    assert "计算思维" in opened
    assert "页码：" in opened
    assert "提炼" not in opened
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能描述组成"
    assert extractor.calls == [retrieval]


def test_extract_reports_empty_invalid_and_failed_results():
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    page, objectives = make_page(base, extractor)

    empty = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="没有这一课",
        action="提炼",
    ), ))
    assert "没有检索到资料" in empty
    assert extractor.calls == []
    extractor.lesson_results = (ObjectiveDraft("超纲维度", "不算", retrieval.lesson_source),)
    invalid = text(response_for(page, "POST", "/objectives", _lesson_form(), ))
    extractor.lesson_error = RuntimeError("boom")
    failed = text(response_for(page, "POST", "/objectives", _lesson_form(), ))
    assert "没有留下可保存的目标" in invalid
    assert "课时原文" in invalid
    assert "提炼" in invalid
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
    assert "提炼失败，没有保存目标" in failed
    assert "课时原文" in failed
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()


def test_an_existing_record_rejects_extract_without_calling_the_extractor():
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (ObjectiveDraft("计算思维", "能描述组成", retrieval.lesson_source),)
    page, objectives = make_page(base, extractor)
    response_for(page, "POST", "/objectives", _lesson_form(), )
    calls = list(extractor.calls)
    page.knowledge = type(page.knowledge)()

    rejected = response_for(page, "POST", "/objectives", _lesson_form(), )
    rejected_text = text(rejected)

    assert rejected.status == 200
    assert "已有目标，不能再次提炼" in rejected_text
    assert "没有检索到资料" not in rejected_text
    assert "能描述组成" in rejected_text
    assert 'value="提炼"' not in rejected_text
    assert extractor.calls == calls
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能描述组成"
