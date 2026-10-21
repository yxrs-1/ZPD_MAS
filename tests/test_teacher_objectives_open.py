from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage, response_for
from tests.teacher_objectives_helpers import form, text


def test_the_list_links_to_objectives_outside_the_task_rows():
    page = TeacherPage(TaskCatalog())

    listed = text(response_for(page, "GET", "/", ""))

    assert 'href="/objectives"' in listed
    assert "<li>" not in listed


def test_get_objectives_shows_the_query_and_does_not_retrieve():
    page = TeacherPage(TaskCatalog())

    opened = response_for(page, "GET", "/objectives", "")
    slashed = text(response_for(page, "GET", "/objectives/?ready=1", ""))
    unknown = response_for(page, "POST", "/objectives", form(action="发布"))

    assert opened.status == 200
    assert "课时" in text(opened)
    assert "学段" in text(opened)
    assert "查看" in text(opened)
    assert "提炼" not in text(opened)
    assert "课时原文" not in text(opened)
    assert "查看" in slashed
    assert unknown.status == 200
    assert "任务不存在" not in text(unknown)
    assert "先填完整再查询" not in text(unknown)


def test_the_teacher_prefix_is_written_on_the_objectives_link():
    page = TeacherPage(TaskCatalog(), prefix="/teacher")

    listed = text(response_for(page, "GET", "/", ""))
    opened = text(response_for(page, "GET", "/objectives", ""))

    assert 'href="/teacher/objectives"' in listed
    assert 'action="/teacher/objectives"' in opened
