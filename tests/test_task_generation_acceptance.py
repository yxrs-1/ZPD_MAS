from pathlib import Path

import pytest

from scaffolding.generation import LessonOrigin, Rejected, StageOrigin, TaskGeneration
from scaffolding.knowledge import CurriculumStandard
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft
from scaffolding.scripted import ScriptedScaffoldAgent
from scaffolding.session import Session
from scaffolding.tasks import TaskCatalog
from tests.generation_helpers import ScriptedGenerator, judged, multiple, opened, prepared_objectives, single
from tests.objective_helpers import ScriptedExtractor


class RecordingDecision:
    def __init__(self) -> None:
        self.records = []

    def suggest(self, record):
        self.records.append(record)
        return ()


def test_task_generation_spec_is_in_the_workspace():
    spec = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "specs" / "2026-10-19-task-generation-design.md"
    assert spec.is_file()


def test_generation_matches_the_spec():
    base, objectives = prepared_objectives()
    stored_lesson = base.get_lesson("人教版", "必修一", "信息系统的组成")
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    junior = base.retrieve_stage("初中")
    extractor = ScriptedExtractor()
    extractor.stage_results = (ObjectiveDraft("信息社会责任", "遵守规范", junior.standard_source),)
    stage_objectives = ObjectiveCatalog(base, extractor)
    stage_objectives.extract_stage("初中")
    generator = ScriptedGenerator()
    generator.questions = (opened(), multiple(), single("单选乙"), judged(), single("单选甲"))
    tasks = TaskCatalog()
    hand_made = tasks.create((single("教师自编"),))
    generation = TaskGeneration(objectives, tasks, generator)

    task = generation.generate_lesson(
        "人教版", "必修一", "信息系统的组成", single=2, multiple=1, true_false=1, open_ended=1
    )

    assert task.published is False
    assert [question.prompt for question in task.questions] == ["单选乙", "单选甲", "多选题", "判断题", "综合题"]
    assert generation.origin(task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")
    assert generation.origin(hand_made.task_id) is None
    assert tasks.student_tasks() == ()

    calls = len(generator.calls)
    with pytest.raises(Rejected):
        generation.generate_lesson("沪科教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0)
    with pytest.raises(Rejected):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=0, multiple=0, true_false=0, open_ended=0)
    with pytest.raises(Rejected):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=1.5, multiple=0, true_false=0, open_ended=0)
    assert len(generator.calls) == calls
    assert tasks.get(hand_made.task_id).questions[0].prompt == "教师自编"

    generator.questions = (single(), single())
    with pytest.raises(Rejected):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0)
    failing = ScriptedGenerator()
    failing.error = RuntimeError("down")
    failed = TaskGeneration(objectives, tasks, failing)
    with pytest.raises(RuntimeError):
        failed.generate_lesson("人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0)
    assert generation.origin(task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")

    stage_generator = ScriptedGenerator()
    stage_generator.questions = (judged(),)
    stage_generation = TaskGeneration(stage_objectives, tasks, stage_generator)
    stage_task = stage_generation.generate_stage("初中", single=0, multiple=0, true_false=1, open_ended=0)
    assert stage_generation.origin(stage_task.task_id) == StageOrigin("初中")
    assert generation.origin(task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")

    objectives.edit_statement("objective-1", "改后的目标")
    objectives.delete("objective-1")
    assert [question.prompt for question in tasks.get(task.task_id).questions] == ["单选乙", "单选甲", "多选题", "判断题", "综合题"]
    assert generation.origin(task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")
    tasks.update(task.task_id, (single("教师改过"),))
    tasks.publish(task.task_id)
    assert generation.origin(task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")
    assert base.get_lesson("人教版", "必修一", "信息系统的组成") is stored_lesson

    listed = tasks.student_tasks()
    assert len(listed) == 1
    assert not hasattr(listed[0], "origin")
    decision = RecordingDecision()
    Session(tasks, tasks.start(task.task_id), decision, ScriptedScaffoldAgent())
    assert decision.records[0].questions == tasks.get(task.task_id).questions
    assert not hasattr(decision.records[0], "origin")
