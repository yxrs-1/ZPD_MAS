from scaffolding.generation import TaskGeneration
from scaffolding.knowledge import CurriculumStandard
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft
from scaffolding.records import TrueFalseQuestion
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage, response_for
from tests.generation_helpers import ScriptedGenerator, single
from tests.objective_helpers import ScriptedExtractor, sample_base
from tests.teacher_objectives_helpers import form, text


def _page():
    base = sample_base()
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    lesson = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    stage = base.retrieve_stage("初中")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (ObjectiveDraft("计算思维", "能描述组成", lesson.lesson_source),)
    extractor.stage_results = (ObjectiveDraft("信息社会责任", "遵守规范", stage.standard_source),)
    objectives = ObjectiveCatalog(base, extractor)
    objectives.extract_lesson("人教版", "必修一", "信息系统的组成")
    objectives.extract_stage("初中")
    catalog = TaskCatalog()
    generator = ScriptedGenerator()
    generation = TaskGeneration(objectives, catalog, generator)
    generator.questions = (single("课时甲"),)
    first = generation.generate_lesson(
        "人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0
    )
    catalog.create((TrueFalseQuestion("手写题干", "正确", "手写解析"),))
    generator.questions = (single("课时乙"),)
    second = generation.generate_lesson(
        "人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0
    )
    generator.questions = (single("学段题"),)
    stage_task = generation.generate_stage("初中", single=1, multiple=0, true_false=0, open_ended=0)
    catalog.publish(first.task_id)
    catalog.start(first.task_id)
    page = TeacherPage(
        catalog,
        knowledge=base,
        objectives=objectives,
        generation=generation,
    )
    return page, generator, first, second, stage_task


def test_lesson_links_follow_catalog_order_and_skip_other_origins():
    page, generator, first, second, stage_task = _page()
    calls = list(generator.calls)

    opened = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        action="查看",
    ), ))
    page.catalog.delete(second.task_id)
    after_delete = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        action="查看",
    ), ))

    assert 'href="/tasks/' + first.task_id + '"' in opened
    assert 'href="/tasks/' + second.task_id + '"' in opened
    assert opened.index(first.task_id) < opened.index(second.task_id)
    assert stage_task.task_id not in opened
    assert "task-2" not in opened
    assert "课时甲" not in opened
    assert "手写题干" not in opened
    assert "学段题" not in opened
    assert generator.calls == calls
    assert second.task_id not in after_delete
    assert first.task_id in after_delete


def test_stage_links_and_the_teacher_prefix_do_not_call_generation():
    page, generator, _first, _second, stage_task = _page()
    page.prefix = "/teacher"
    calls = list(generator.calls)

    opened = text(response_for(page, "POST", "/objectives", form(
        mode="学段",
        stage="初中",
        action="查看",
    ), ))

    assert 'href="/teacher/tasks/' + stage_task.task_id + '"' in opened
    assert "task-1" not in opened
    assert "学段题" not in opened
    assert generator.calls == calls


def test_a_hand_written_task_has_no_objectives_link():
    base = sample_base()
    objectives = ObjectiveCatalog(base, ScriptedExtractor())
    catalog = TaskCatalog()
    catalog.create((TrueFalseQuestion("手写题干", "正确", "手写解析"),))
    generation = TaskGeneration(objectives, catalog, ScriptedGenerator())
    page = TeacherPage(catalog, knowledge=base, objectives=objectives, generation=generation)

    opened = text(response_for(page, "POST", "/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        action="查看",
    ), ))

    assert "课时原文" in opened
    assert 'href="/tasks/' not in opened
    assert "手写题干" not in opened
