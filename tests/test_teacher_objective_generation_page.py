from scaffolding.generation import TaskGeneration
from scaffolding.knowledge import KnowledgeBase
from scaffolding.objectives import ObjectiveDraft
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import response_for
from tests.generation_helpers import ScriptedGenerator
from tests.objective_helpers import ScriptedExtractor, sample_base
from tests.teacher_objectives_helpers import form, make_page, text
from tests.test_text_generation_record import ScriptedTextGenerator


def _lesson(**extra):
    fields = {
        "mode": "课时",
        "version": "人教版",
        "volume": "必修一",
        "lesson": "信息系统的组成",
    }
    fields.update(extra)
    return form(**fields)


def _ready(generator=None, statements=("能识别信息", "能分解步骤")):
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    extractor.lesson_results = tuple(
        ObjectiveDraft(dimension, statement, retrieval.lesson_source)
        for dimension, statement in zip(("信息意识", "计算思维"), statements)
    )
    catalog = TaskCatalog()
    page, objectives = make_page(base, extractor, catalog)
    if generator is not None:
        page.generation = TaskGeneration(
            objectives, catalog, ScriptedGenerator(), generator
        )
    extracted = text(response_for(page, "POST", "/objectives", _lesson(action="提炼")))
    return page, generator, catalog, extracted


def test_the_button_appears_only_beside_saved_objectives():
    page, _generator, _catalog, extracted = _ready(None, statements=("<需求", "能分解步骤"))

    opened = text(response_for(page, "GET", "/objectives", ""))
    viewed = text(response_for(page, "POST", "/objectives", _lesson(action="查看")))
    edited = text(response_for(page, "POST", "/objectives", _lesson(
        objective="objective-1", statement="能认出信息", action="修改"
    )))
    listed = text(response_for(page, "GET", "/", ""))

    assert 'value="按目标生成"' in extracted
    assert extracted.index("&lt;需求") < extracted.index('value="按目标生成"')
    assert "<需求" not in extracted
    assert "按目标生成" not in opened
    assert viewed.count('value="按目标生成"') == 1
    assert viewed.index("能分解步骤") < viewed.index('value="按目标生成"')
    assert '<input type="hidden" name="mode" value="课时">' in viewed
    assert '<input type="hidden" name="lesson" value="信息系统的组成">' in viewed
    assert "</form>" in viewed.split('value="按目标生成"')[0]
    assert 'href="/generation">生成</a>' in viewed
    assert 'value="按目标生成"' in edited
    assert "能认出信息" in edited
    assert 'href="/generation">生成</a>' not in listed
    assert "按目标生成" not in listed


def test_removing_the_last_objective_removes_the_button():
    page, _generator, _catalog, _extracted = _ready(ScriptedTextGenerator())

    remaining = text(response_for(page, "POST", "/objectives", _lesson(
        objective="objective-1", action="删除"
    )))
    gone = text(response_for(page, "POST", "/objectives", _lesson(
        objective="objective-2", action="删除"
    )))

    assert 'value="按目标生成"' in remaining
    assert "能分解步骤" in remaining
    assert 'value="按目标生成"' not in gone


def test_failures_keep_the_query_and_do_not_call_the_model():
    generator = ScriptedTextGenerator()
    page, _generator, catalog, _extracted = _ready(generator)
    idle = ScriptedGenerator()
    bare_extractor = ScriptedExtractor()
    bare, _bare_objectives = make_page(sample_base(), bare_extractor)
    bare_retrieval = bare.knowledge.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    bare_extractor.lesson_results = (
        ObjectiveDraft("信息意识", "能识别信息", bare_retrieval.lesson_source),
    )
    response_for(bare, "POST", "/objectives", _lesson(action="提炼"))

    absent = text(response_for(page, "POST", "/objectives", form(
        mode="课时", version="人教版", volume="必修一", lesson="没有这一课", action="按目标生成"
    )))
    missing_record = response_for(bare, "POST", "/objectives", _lesson(action="按目标生成"))
    page.generation = TaskGeneration(page.objectives, catalog, idle)
    missing_generator = response_for(page, "POST", "/objectives", _lesson(action="按目标生成"))

    assert "生成失败，没有创建任务" in absent
    assert "没有检索到资料" not in absent
    assert 'value="按目标生成"' not in absent
    assert "课时原文" not in absent
    assert generator.calls == []
    assert missing_record.status == 200
    assert "生成失败，没有创建任务" in text(missing_record)
    assert "能识别信息" in text(missing_record)
    assert "课时原文" in text(missing_record)
    assert missing_generator.status == 200
    assert "生成失败，没有创建任务" in text(missing_generator)
    assert idle.calls == []

    page.generation = TaskGeneration(page.objectives, catalog, ScriptedGenerator(), generator)
    sent = "维度：信息意识\n表述：能识别信息\n维度：计算思维\n表述：能分解步骤\n没有指定题型和数量。"
    generator.error = RuntimeError("boom")
    failed = response_for(page, "POST", "/objectives", _lesson(action="按目标生成"))
    generator.error = None
    generator.reply = "```"
    rejected = response_for(page, "POST", "/objectives", _lesson(action="按目标生成"))
    before = len(generator.calls)
    incomplete = response_for(page, "POST", "/objectives", form(
        mode="课时", version="   ", volume="必修一", lesson="信息系统的组成", action="按目标生成"
    ))
    unknown = text(response_for(page, "POST", "/objectives", _lesson(action="发布")))
    assert len(generator.calls) == before
    page.knowledge = KnowledgeBase()
    kept = text(response_for(page, "POST", "/objectives", _lesson(action="查看")))
    empty = text(response_for(page, "POST", "/objectives", _lesson(action="按目标生成")))

    assert failed.status == 200
    assert "生成失败，没有创建任务" in text(failed)
    assert "能识别信息" in text(failed)
    assert "课时原文" in text(failed)
    assert rejected.status == 200
    assert "生成失败，没有创建任务" in text(rejected)
    assert list(catalog._tasks) == []
    assert generator.calls[0] == sent
    assert generator.calls[1] == sent
    assert incomplete.status == 200
    assert "先填完整再查询" in text(incomplete)
    assert "生成失败，没有创建任务" not in unknown
    assert "课时原文" not in unknown
    assert "没有检索到资料" in kept
    assert 'value="按目标生成"' in kept
    assert "能识别信息" in kept
    assert "生成失败，没有创建任务" in empty
    assert "没有检索到资料" not in empty
    assert "能识别信息" in empty
    assert "课时原文" not in empty
    assert generator.calls[2] == sent
