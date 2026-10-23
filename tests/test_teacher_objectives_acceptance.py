from pathlib import Path

from scaffolding.classroom import Classroom, production_classroom, response_for, serve
from scaffolding.knowledge import KnowledgeBase
from scaffolding.model_extractor import ModelObjectiveExtractor
from scaffolding.model_generator import ModelQuestionGenerator
from scaffolding.objectives import ObjectiveCatalog
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.tasks import TaskCatalog
from tests.classroom_helpers import student_cookie, teacher_cookie, text
from tests.objective_helpers import ScriptedExtractor, sample_base


def test_the_classroom_prefixes_objectives_and_hides_them_from_the_student():
    base = sample_base()
    objectives = ObjectiveCatalog(base, ScriptedExtractor())
    catalog = TaskCatalog()
    room = Classroom(
        catalog,
        ScriptedDecisionAgent(),
        ScriptedScaffoldAgent(),
        base,
        objectives,
        None,
    )

    home = text(response_for(room, "GET", "/", "", 0))
    listed = text(response_for(room, "GET", "/teacher", "", 0, teacher_cookie(room)))
    opened = text(response_for(room, "GET", "/teacher/objectives/?ready=1", "", 0, teacher_cookie(room)))
    student = response_for(room, "GET", "/student/objectives", "", 1, student_cookie(room))

    assert "目标" not in home
    assert 'href="/teacher/objectives"' in listed
    assert "生成目标" in opened
    assert 'name="file"' in opened
    assert student.status == 404
    assert "任务不存在" in text(student)
    assert "课时原文" not in text(student)
    assert "能描述组成" not in text(student)


def test_a_new_classroom_does_not_see_another_knowledge_base_or_objectives():
    base = sample_base()
    objectives = ObjectiveCatalog(base, ScriptedExtractor())
    first = Classroom(
        TaskCatalog(),
        ScriptedDecisionAgent(),
        ScriptedScaffoldAgent(),
        base,
        objectives,
        None,
    )
    second = Classroom(TaskCatalog(), ScriptedDecisionAgent(), ScriptedScaffoldAgent())

    assert second.knowledge.lesson_count() == 0
    assert second.objectives.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
    assert first.knowledge is not second.knowledge
    assert first.objectives is not second.objectives
    assert first.teacher.knowledge is first.knowledge
    assert second.teacher.objectives is second.objectives


def test_production_prepares_the_model_records_without_calling_them(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def post(_request):
        raise AssertionError("network")

    room = production_classroom(post=post)

    assert isinstance(room.objectives._extractor, ModelObjectiveExtractor)
    assert isinstance(room.generation._generator, ModelQuestionGenerator)
    assert room.teacher.knowledge is room.knowledge
    assert room.teacher.objectives is room.objectives
    assert room.teacher.generation is room.generation
    assert room.generation._tasks is room.catalog
    assert room.generation._objectives is room.objectives


def test_the_spec_is_present_and_the_listener_is_not_started():
    assert Path("docs/superpowers/specs/2026-10-21-teacher-objectives-design.md").is_file()
    assert callable(serve)
    assert callable(production_classroom)
