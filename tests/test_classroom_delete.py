import pytest

from scaffolding.classroom import response_for
from tests.classroom_helpers import form, room, student_cookie, teacher_cookie, text


def _started(page):
    response_for(page, "POST", "/teacher/tasks", "", 0, teacher_cookie(page))
    response_for(page, "POST", "/teacher/tasks/task-1", form(**{
        "kind-0": "综合",
        "prompt-0": "完成作品",
        "requirements-0": "写明人员",
        "answer-0": "",
        "explanation-0": "",
        "action": "save",
    }), 0, teacher_cookie(page))
    response_for(page, "POST", "/teacher/tasks/task-1", form(action="publish"), 0, teacher_cookie(page))
    cookie = student_cookie(page)
    page.classwork.assign(page.catalog, "task-1", (page.roster.authenticate_student("s1", "secret").class_id,))
    response_for(page, "GET", "/student/tasks/task-1", "", 3, cookie)
    response_for(page, "POST", "/student/tasks/task-1/answers", form(**{"text-0": "学生写下的答案"}), 4, cookie)


def test_delete_removes_the_student_session_and_later_requests_do_not_rebuild_it():
    page = room()
    _started(page)

    response_for(page, "POST", "/teacher/tasks/task-1", form(action="delete"), 5, teacher_cookie(page))
    opened = response_for(page, "GET", "/student/tasks/task-1", "", 6, student_cookie(page))
    asset = response_for(page, "GET", "/student/tasks/task-1/assets/a.png", "", 6, student_cookie(page))
    teacher = text(response_for(page, "GET", "/teacher", "", 6, teacher_cookie(page)))
    student = text(response_for(page, "GET", "/student", "", 6, student_cookie(page)))

    assert "task-1" not in teacher
    assert "task-1" not in student
    assert "task-1" not in page.teacher.drafts
    assert "task-1" not in page.student.sessions
    assert "task-1" not in page.student.shown_at
    assert opened.status == 404
    assert "任务不存在" in text(opened)
    assert "任务不存在" in text(asset)
    assert page.student.sessions == {}
    assert page.student.shown_at == {}
    with pytest.raises(KeyError):
        page.catalog.get("task-1")
    with pytest.raises(KeyError):
        page.catalog.work("task-1")
    assert page.classwork.assigned("task-1") == ()
    assert page.classwork.any_started("task-1") is False


def test_submit_leaves_the_teacher_page_without_the_student_answer():
    page = room()
    _started(page)

    response_for(page, "POST", "/student/tasks/task-1/submit", "", 8, student_cookie(page))
    teacher = text(response_for(page, "GET", "/teacher/tasks/task-1", "", 9, teacher_cookie(page)))

    assert "已开始" in teacher
    assert "学生写下的答案" not in teacher
    assert "待办" not in teacher
    assert "已完成" not in teacher
