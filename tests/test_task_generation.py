from scaffolding.generation import LessonOrigin, QuestionCounts, StageOrigin, TaskGeneration
from scaffolding.knowledge import CurriculumStandard
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft
from scaffolding.tasks import TaskCatalog
from tests.generation_helpers import ScriptedGenerator, judged, multiple, opened, prepared_objectives, single
from tests.objective_helpers import ScriptedExtractor


def test_lesson_generation_creates_an_unpublished_task_and_records_the_lesson():
    base, objectives = prepared_objectives()
    stored_lesson = base.get_lesson("人教版", "必修一", "信息系统的组成")
    stored_objective = objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0]
    generator = ScriptedGenerator()
    generator.questions = (opened(), multiple(), single("单选乙"), judged(), single("单选甲"))
    tasks = TaskCatalog()
    generation = TaskGeneration(objectives, tasks, generator)

    task = generation.generate_lesson(
        "人教版", "必修一", "信息系统的组成", single=2, multiple=1, true_false=1, open_ended=1
    )

    assert task.published is False
    assert task.task_id == "task-1"
    assert [question.prompt for question in task.questions] == ["单选乙", "单选甲", "多选题", "判断题", "综合题"]
    assert generation.origin(task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")
    assert generator.calls == [
        (QuestionCounts(2, 1, 1, 1), objectives.lesson_objectives("人教版", "必修一", "信息系统的组成"))
    ]
    assert tasks.student_tasks() == ()
    assert base.get_lesson("人教版", "必修一", "信息系统的组成") is stored_lesson
    assert objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")[0] == stored_objective


def test_a_zero_count_omits_that_type():
    _, objectives = prepared_objectives()
    generator = ScriptedGenerator()
    generator.questions = (single(),)
    generation = TaskGeneration(objectives, TaskCatalog(), generator)

    task = generation.generate_lesson(
        "人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0
    )

    assert [type(question).__name__ for question in task.questions] == ["ChoiceQuestion"]
    assert task.questions[0].selection.value == "单选"


def test_stage_origin_is_independent_of_the_lesson_origin():
    base, objectives = prepared_objectives()
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    stage_retrieval = base.retrieve_stage("初中")
    extractor = ScriptedExtractor()
    extractor.stage_results = (ObjectiveDraft("信息社会责任", "遵守规范", stage_retrieval.standard_source),)
    stage_objectives = ObjectiveCatalog(base, extractor)
    stage_objectives.extract_stage("初中")
    generator = ScriptedGenerator()
    generator.questions = (single(),)
    tasks = TaskCatalog()
    lesson_generation = TaskGeneration(objectives, tasks, generator)
    lesson_task = lesson_generation.generate_lesson(
        "人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0
    )
    generator.questions = (opened(),)
    stage_generation = TaskGeneration(stage_objectives, tasks, generator)
    stage_task = stage_generation.generate_stage("初中", single=0, multiple=0, true_false=0, open_ended=1)

    assert lesson_generation.origin(lesson_task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")
    assert stage_generation.origin(stage_task.task_id) == StageOrigin("初中")
    assert stage_task.questions[0].prompt == "综合题"
