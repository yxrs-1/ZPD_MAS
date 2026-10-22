from scaffolding.generation import LessonOrigin, StageOrigin, TaskGeneration
from scaffolding.objectives import ObjectiveDraft
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import response_for
from tests.generation_helpers import ScriptedGenerator
from tests.objective_helpers import ScriptedExtractor, sample_base
from tests.teacher_objectives_helpers import form, make_page, text
from tests.test_text_generation_record import ScriptedTextGenerator
from tests.text_generation_helpers import choice, dumped
from tests.text_generation_helpers import opened as opened_question


def test_objective_generation_opens_the_new_task_and_records_the_query_origin():
    base = sample_base()
    lesson = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    stage = base.retrieve_stage("高中")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (
        ObjectiveDraft("信息意识", "能识别信息", lesson.lesson_source),
    )
    extractor.stage_results = (
        ObjectiveDraft("信息社会责任", "遵守规范", stage.standard_source),
    )
    catalog = TaskCatalog()
    questions = ScriptedGenerator()
    text_generator = ScriptedTextGenerator()
    text_generator.reply = dumped(
        reading={"单选": 2, "多选": "未指定", "判断": 0, "综合": "未指定"},
        questions={
            "单选": [choice("第一"), choice("第二")],
            "多选": [],
            "判断": [],
            "综合": [opened_question("综合题")],
        },
    )
    page, objectives = make_page(base, extractor, catalog)
    generation = TaskGeneration(objectives, catalog, questions, text_generator)
    page.generation = generation
    response_for(page, "POST", "/objectives", form(
        mode="课时", version="人教版", volume="必修一", lesson="信息系统的组成", action="提炼"
    ))
    response_for(page, "POST", "/objectives", form(
        mode="学段", stage="高中", action="提炼"
    ))
    loose = generation.generate_from_text("出一道题")

    opened = text(response_for(page, "POST", "/objectives", form(
        mode="课时", version="人教版", volume="必修一", lesson="信息系统的组成", action="按目标生成"
    )))
    again = text(response_for(page, "POST", "/objectives", form(
        mode="课时", version="人教版", volume="必修一", lesson="信息系统的组成", action="按目标生成"
    )))
    listed = text(response_for(page, "GET", "/", ""))
    viewed = text(response_for(page, "POST", "/objectives", form(
        mode="课时", version="人教版", volume="必修一", lesson="信息系统的组成", action="查看"
    )))
    staged = text(response_for(page, "POST", "/objectives", form(
        mode="学段", stage="高中", action="按目标生成"
    )))
    stage_view = text(response_for(page, "POST", "/objectives", form(
        mode="学段", stage="高中", action="查看"
    )))

    assert opened.index("第一") < opened.index("第二") < opened.index("综合题")
    assert "未发布" in opened
    assert "生成失败，没有创建任务" not in opened
    assert text_generator.calls[1:] == [
        "维度：信息意识\n表述：能识别信息\n没有指定题型和数量。",
        "维度：信息意识\n表述：能识别信息\n没有指定题型和数量。",
        "维度：信息社会责任\n表述：遵守规范\n没有指定题型和数量。",
    ]
    assert questions.calls == []
    assert generation.origin("task-2") == LessonOrigin("人教版", "必修一", "信息系统的组成")
    assert generation.origin("task-3") == LessonOrigin("人教版", "必修一", "信息系统的组成")
    assert generation.origin(loose.task_id) is None
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能识别信息"
    assert "task-2" in listed and "task-3" in listed
    assert "task-2" in viewed and "task-3" in viewed
    assert loose.task_id not in viewed
    assert "未发布" in again
    assert generation.origin("task-4") == StageOrigin("高中")
    assert "task-4" in staged
    assert "task-4" in stage_view
    assert "task-2" not in stage_view
