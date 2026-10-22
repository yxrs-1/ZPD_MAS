import pytest

from scaffolding.generation import LessonOrigin, Rejected, StageOrigin, TaskGeneration
from scaffolding.objectives import Objective
from scaffolding.tasks import TaskCatalog
from tests.generation_helpers import ScriptedGenerator, prepared_objectives
from tests.test_text_generation_record import ScriptedTextGenerator


def _pair(saved):
    source = saved.source
    return (
        saved,
        Objective("objective-9", "计算思维", "  能分解步骤  ", source),
    )


def test_saved_objectives_create_an_unpublished_task_with_the_given_origin():
    base, objectives = prepared_objectives()
    catalog = TaskCatalog()
    questions = ScriptedGenerator()
    text_generator = ScriptedTextGenerator()
    generation = TaskGeneration(objectives, catalog, questions, text_generator)
    saved = objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0]

    task = generation.generate_from_objectives(
        _pair(saved),
        LessonOrigin("人教版", "必修一", "信息系统的组成"),
    )

    assert task.published is False
    assert [item.prompt for item in task.questions] == ["第一", "综合题"]
    assert generation.origin(task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")
    assert text_generator.calls == [
        "维度：信息意识\n表述：能识别信息\n维度：计算思维\n表述：  能分解步骤  \n没有指定题型和数量。"
    ]
    assert questions.calls == []
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能识别信息"
    assert base.retrieve_lesson("人教版", "必修一", "信息系统的组成").lesson_text == "课时原文"


def test_a_stage_origin_is_stored_as_given():
    _base, objectives = prepared_objectives()
    saved = objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0]
    generation = TaskGeneration(
        objectives, TaskCatalog(), ScriptedGenerator(), ScriptedTextGenerator()
    )

    task = generation.generate_from_objectives((saved,), StageOrigin("高中"))

    assert generation.origin(task.task_id) == StageOrigin("高中")


def test_no_objectives_or_no_text_generator_does_not_call_the_model():
    _base, objectives = prepared_objectives()
    text_generator = ScriptedTextGenerator()
    generation = TaskGeneration(
        objectives, TaskCatalog(), ScriptedGenerator(), text_generator
    )
    bare = TaskGeneration(objectives, TaskCatalog(), ScriptedGenerator())

    with pytest.raises(Rejected):
        generation.generate_from_objectives((), LessonOrigin("人教版", "必修一", "信息系统的组成"))
    with pytest.raises(Rejected):
        bare.generate_from_objectives(
            objectives.lesson_objectives("人教版", "必修一", "信息系统的组成"),
            LessonOrigin("人教版", "必修一", "信息系统的组成"),
        )

    assert text_generator.calls == []


def test_a_bad_reply_does_not_create_a_task_or_an_origin():
    _base, objectives = prepared_objectives()
    catalog = TaskCatalog()
    text_generator = ScriptedTextGenerator()
    text_generator.reply = "```"
    generation = TaskGeneration(objectives, catalog, ScriptedGenerator(), text_generator)
    saved = objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")

    with pytest.raises(Rejected):
        generation.generate_from_objectives(
            saved, LessonOrigin("人教版", "必修一", "信息系统的组成")
        )

    assert catalog._tasks == {}
    assert generation.origin("task-1") is None
