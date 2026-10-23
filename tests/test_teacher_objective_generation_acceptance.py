from pathlib import Path

from scaffolding.classroom import Classroom, production_classroom, response_for, serve
from scaffolding.model_text import ModelTextGenerator
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.tasks import TaskCatalog
from tests.classroom_helpers import student_cookie, teacher_cookie, text


def test_the_classroom_hides_objective_generation_until_objectives_exist():
    room = Classroom(TaskCatalog(), ScriptedDecisionAgent(), ScriptedScaffoldAgent())

    home = text(response_for(room, "GET", "/", "", 0))
    listed = text(response_for(room, "GET", "/teacher", "", 0, teacher_cookie(room)))
    objectives = text(response_for(room, "GET", "/teacher/objectives/", "", 0, teacher_cookie(room)))
    student = response_for(room, "GET", "/student/objectives", "", 1, student_cookie(room))

    assert "按目标生成" not in home
    assert "按目标生成" not in listed
    assert 'href="/teacher/objectives"' in listed
    assert 'href="/teacher/generation">生成</a>' in objectives
    assert "按目标生成" not in objectives
    assert student.status == 404
    assert "任务不存在" in text(student)


def test_production_still_prepares_the_text_generator_without_calling_it(tmp_path, monkeypatch):
    repo = Path.cwd()
    monkeypatch.chdir(tmp_path)

    def post(_request):
        raise AssertionError("network")

    room = production_classroom(post=post)
    monkeypatch.chdir(repo)

    assert isinstance(room.generation._text_generator, ModelTextGenerator)
    assert room.teacher.generation is room.generation
    assert Path("docs/superpowers/specs/2026-10-22-teacher-objective-generation-design.md").is_file()
    assert callable(serve)
    assert callable(production_classroom)
