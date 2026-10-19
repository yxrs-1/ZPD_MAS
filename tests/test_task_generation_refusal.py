import pytest

from scaffolding.generation import Rejected, TaskGeneration
from scaffolding.records import ChoiceQuestion, SelectionMode
from scaffolding.tasks import TaskCatalog
from tests.generation_helpers import ScriptedGenerator, prepared_objectives, single


class FailingCatalog(TaskCatalog):
    def create(self, questions):
        raise RuntimeError("create failed")


def test_missing_record_and_bad_counts_do_not_call_the_generator():
    _, objectives = prepared_objectives()
    generator = ScriptedGenerator()
    generator.questions = (single(),)
    tasks = TaskCatalog()
    existing = tasks.create((single("已有题"),))
    generation = TaskGeneration(objectives, tasks, generator)

    with pytest.raises(Rejected):
        generation.generate_lesson("沪科教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0)
    with pytest.raises(Rejected):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=0, multiple=0, true_false=0, open_ended=0)
    with pytest.raises(Rejected):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=-1, multiple=0, true_false=0, open_ended=0)
    with pytest.raises(Rejected):
        generation.generate_stage("高中 ", single=1, multiple=0, true_false=0, open_ended=0)

    assert generator.calls == []
    assert tasks.get(existing.task_id).questions[0].prompt == "已有题"
    assert generation.origin(existing.task_id) is None
    with pytest.raises(KeyError):
        tasks.get("task-2")


def test_count_mismatch_creates_nothing():
    _, objectives = prepared_objectives()
    generator = ScriptedGenerator()
    generator.questions = (single("单选甲"), single("单选乙"))
    tasks = TaskCatalog()
    generation = TaskGeneration(objectives, tasks, generator)

    with pytest.raises(Rejected):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0)

    assert generation.origin("task-1") is None
    with pytest.raises(KeyError):
        tasks.get("task-1")


def test_invalid_question_and_generator_failure_create_nothing():
    _, objectives = prepared_objectives()
    tasks = TaskCatalog()
    invalid = ScriptedGenerator()

    def generate(counts, objectives):
        invalid.calls.append((counts, objectives))
        ChoiceQuestion(" ", SelectionMode.SINGLE, ("甲", "乙"), ("甲",), "解析")
        return ()

    invalid.generate = generate
    generation = TaskGeneration(objectives, tasks, invalid)
    with pytest.raises(ValueError):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0)

    failing = ScriptedGenerator()
    failing.error = RuntimeError("down")
    failing.questions = (single(),)
    generation = TaskGeneration(objectives, tasks, failing)
    with pytest.raises(RuntimeError, match="down"):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0)

    assert generation.origin("task-1") is None
    with pytest.raises(KeyError):
        tasks.get("task-1")


def test_failed_create_does_not_store_an_origin():
    _, objectives = prepared_objectives()
    generator = ScriptedGenerator()
    generator.questions = (single(),)
    generation = TaskGeneration(objectives, FailingCatalog(), generator)

    with pytest.raises(RuntimeError, match="create failed"):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0)

    assert generation.origin("task-1") is None
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0].statement == "能识别信息"
