from scaffolding.generation import TaskGeneration
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import response_for
from tests.generation_helpers import ScriptedGenerator, prepared_objectives
from tests.teacher_objectives_helpers import form, text
from tests.test_text_generation_record import ScriptedTextGenerator
from tests.text_generation_helpers import choice, dumped, opened as opened_item


def test_a_text_request_opens_the_new_unpublished_task():
    base, objectives = prepared_objectives()
    catalog = TaskCatalog()
    questions = ScriptedGenerator()
    text_generator = ScriptedTextGenerator()
    text_generator.reply = dumped(
        questions={
            "单选": [choice("第一"), choice("第二")],
            "多选": [],
            "判断": [],
            "综合": [opened_item("综合题")],
        },
        reading={"单选": 2, "多选": "未指定", "判断": 0, "综合": "未指定"},
    )
    generation = TaskGeneration(objectives, catalog, questions, text_generator)
    from scaffolding.teacher_page import TeacherPage
    page = TeacherPage(
        catalog, knowledge=base, objectives=objectives, generation=generation
    )

    opened = text(response_for(page, "POST", "/generation", form(text="  出两道单选  ")))
    listed = text(response_for(page, "GET", "/", ""))
    again = text(response_for(page, "GET", "/generation", ""))
    viewed = text(response_for(page, "GET", "/objectives", ""))

    assert opened.index("第一") < opened.index("第二") < opened.index("综合题")
    assert "未发布" in opened
    assert "生成失败，没有创建任务" not in opened
    assert text_generator.calls == ["  出两道单选  "]
    assert questions.calls == []
    assert generation.origin("task-1") is None
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能识别信息"
    assert "task-1" in listed
    assert "<textarea name=\"text\"></textarea>" in again
    assert "task-1" not in viewed
