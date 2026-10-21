from pathlib import Path

from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage, serve


def test_a_new_service_does_not_see_another_catalog_or_draft():
    first = TeacherPage(TaskCatalog())
    first.create_task()
    first.drafts["task-1"] = ()
    second = TeacherPage(TaskCatalog())

    assert "task-1" not in second.list_tasks()
    assert second.drafts == {}
    assert first.catalog is not second.catalog


def test_the_spec_is_present_and_the_listener_is_not_started():
    assert Path("docs/superpowers/specs/2026-10-21-teacher-page-design.md").is_file()
    assert callable(serve)
