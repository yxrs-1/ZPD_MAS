import pytest

from scaffolding.generation import Rejected, TaskGeneration
from scaffolding.tasks import TaskCatalog
from tests.generation_helpers import ScriptedGenerator, prepared_objectives, single
from tests.text_generation_helpers import dumped


class ScriptedTextGenerator:
    def __init__(self):
        self.reply = dumped()
        self.error = None
        self.calls = []

    def generate(self, text):
        self.calls.append(text)
        if self.error is not None:
            raise self.error
        return self.reply


def test_text_generation_creates_an_unpublished_task_without_an_origin():
    base, objectives = prepared_objectives()
    catalog = TaskCatalog()
    questions = ScriptedGenerator()
    text_generator = ScriptedTextGenerator()
    generation = TaskGeneration(objectives, catalog, questions, text_generator)

    task = generation.generate_from_text("  出一道单选  ")

    assert task.published is False
    assert [item.prompt for item in task.questions] == ["第一", "综合题"]
    assert generation.origin(task.task_id) is None
    assert text_generator.calls == ["  出一道单选  "]
    assert questions.calls == []
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能识别信息"
    assert base.retrieve_lesson("人教版", "必修一", "信息系统的组成").lesson_text == "课时原文"


def test_a_bad_text_reply_does_not_create_a_task():
    _base, objectives = prepared_objectives()
    catalog = TaskCatalog()
    text_generator = ScriptedTextGenerator()
    text_generator.reply = "```"
    generation = TaskGeneration(objectives, catalog, ScriptedGenerator(), text_generator)

    with pytest.raises(Rejected):
        generation.generate_from_text("出题")

    assert catalog._tasks == {}


def test_lesson_generation_still_records_its_origin():
    _base, objectives = prepared_objectives()
    catalog = TaskCatalog()
    questions = ScriptedGenerator()
    questions.questions = (single(),)
    generation = TaskGeneration(objectives, catalog, questions)

    task = generation.generate_lesson(
        "人教版", "必修一", "信息系统的组成",
        single=1, multiple=0, true_false=0, open_ended=0,
    )

    assert generation.origin(task.task_id).lesson == "信息系统的组成"
