from pathlib import Path

from scaffolding.classroom import production_classroom, response_for, serve
from tests.classroom_helpers import room, text


def test_a_new_classroom_does_not_see_another_catalog_draft_or_session():
    first = room()
    response_for(first, "POST", "/teacher/tasks", "", 0)
    first.teacher.drafts["task-1"] = ()
    first.student.shown_at["task-1"] = 1
    second = room()

    assert "task-1" not in text(response_for(second, "GET", "/teacher", "", 0))
    assert "task-1" not in text(response_for(second, "GET", "/student", "", 0))
    assert second.teacher.drafts == {}
    assert second.student.sessions == {}
    assert second.student.shown_at == {}
    assert first.catalog is not second.catalog


def test_the_spec_is_present_and_the_listener_is_not_started():
    assert Path("docs/superpowers/specs/2026-10-21-classroom-design.md").is_file()
    assert callable(serve)
    assert callable(production_classroom)
