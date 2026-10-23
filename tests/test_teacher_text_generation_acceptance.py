from pathlib import Path

from scaffolding.classroom import production_classroom, response_for, serve
from scaffolding.model_text import ModelTextGenerator
from tests.classroom_helpers import student_cookie, teacher_cookie, text


def test_the_classroom_links_generation_from_objectives_only():
    from scaffolding.classroom import Classroom
    from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
    from scaffolding.tasks import TaskCatalog

    room = Classroom(TaskCatalog(), ScriptedDecisionAgent(), ScriptedScaffoldAgent())

    home = text(response_for(room, "GET", "/", "", 0))
    listed = text(response_for(room, "GET", "/teacher", "", 0, teacher_cookie(room)))
    objectives = text(response_for(room, "GET", "/teacher/objectives/", "", 0, teacher_cookie(room)))
    opened = text(response_for(room, "GET", "/teacher/generation?ready=1", "", 0, teacher_cookie(room)))
    student = response_for(room, "GET", "/student/generation", "", 1, student_cookie(room))

    assert 'href="/teacher/generation"' not in home
    assert 'href="/teacher/generation"' not in listed
    assert 'href="/teacher/objectives"' in listed
    assert 'href="/teacher/generation">生成</a>' in objectives
    assert "<textarea name=\"text\"></textarea>" in opened
    assert "查看" not in opened
    assert student.status == 404
    assert "任务不存在" in text(student)


def test_production_prepares_the_text_generator_without_calling_it(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def post(_request):
        raise AssertionError("network")

    room = production_classroom(post=post)

    assert isinstance(room.generation._text_generator, ModelTextGenerator)
    assert room.teacher.generation is room.generation
    assert room.generation._tasks is room.catalog


def test_the_spec_is_present_and_the_listener_is_not_started():
    assert Path("docs/superpowers/specs/2026-10-22-teacher-text-generation-design.md").is_file()
    assert callable(serve)
    assert callable(production_classroom)
