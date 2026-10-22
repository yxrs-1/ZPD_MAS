import pytest

from scaffolding.classroom import response_for
from tests.classroom_helpers import form, room, student_cookie, teacher_cookie, text


def _save(page):
    response_for(page, "POST", "/teacher/tasks", "", 0, teacher_cookie(page))
    response_for(page, "POST", "/teacher/tasks/task-1", form(**{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "selected-0": "正确",
        "explanation-0": "题目里有依据",
        "action": "save",
    }), 0, teacher_cookie(page))


def test_an_unpublished_task_is_hidden_and_does_not_start():
    page = room()
    _save(page)

    student = text(response_for(page, "GET", "/student", "", 0, student_cookie(page)))
    opened = response_for(page, "GET", "/student/tasks/task-1", "", 1, student_cookie(page))
    asset = response_for(page, "GET", "/student/tasks/task-1/assets/a.png", "", 1, student_cookie(page))

    assert "task-1" not in student
    assert opened.status == 404
    assert "任务不存在" in text(opened)
    assert asset.status == 404
    assert "任务不存在" in text(asset)
    assert page.catalog.get("task-1").started is False
    assert page.student.sessions == {}


def test_publishing_shows_the_task_and_opening_starts_it():
    page = room()
    _save(page)
    response_for(page, "POST", "/teacher/tasks/task-1", form(action="publish"), 0, teacher_cookie(page))
    student_cookie(page)
    page.classwork.assign(page.catalog, "task-1", (page.roster.authenticate_student("s1", "secret").class_id,))

    student = text(response_for(page, "GET", "/student", "", 0, student_cookie(page)))
    opened = text(response_for(page, "GET", "/student/tasks/task-1", "", 10, student_cookie(page)))
    teacher = text(response_for(page, "GET", "/teacher", "", 11, teacher_cookie(page)))
    missing = response_for(page, "GET", "/student/tasks/task-1/assets/没有.svg", "", 12, student_cookie(page))

    assert "task-1" in student
    assert "待办" in student
    assert 'href="/student/tasks/task-1"' in student
    assert "判断说法" in opened
    assert "参考答案" not in opened
    assert "解析" not in opened
    assert page.student.shown_at["task-1"] == 10
    assert page.student.catalog.work("task-1").behavior.dwell_seconds == 0
    with pytest.raises(KeyError):
        page.catalog.work("task-1")
    assert "已开始" in teacher
    assert missing.status == 404
    assert missing.body == b""
    assert missing.content_type == "application/octet-stream"
    locked = text(response_for(page, "POST", "/teacher/tasks/task-1", form(**{
        "kind-0": "判断",
        "prompt-0": "不该写入",
        "selected-0": "错误",
        "explanation-0": "题目里有依据",
        "action": "save",
    }), 13, teacher_cookie(page)))
    assert "学生已开始，只能删除" in locked
    assert page.catalog.get("task-1").questions[0].prompt == "判断说法"


def test_a_teacher_draft_is_not_visible_to_the_student():
    page = room()
    _save(page)
    response_for(page, "POST", "/teacher/tasks/task-1", form(action="publish"), 0, teacher_cookie(page))
    response_for(page, "POST", "/teacher/tasks/task-1", form(**{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "action": "add:单选",
    }), 0, teacher_cookie(page))
    response_for(page, "POST", "/teacher/tasks/task-1", form(**{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "kind-1": "单选",
        "prompt-1": "草稿里的新题干",
        "action": "add-option:1",
    }), 0, teacher_cookie(page))
    cookie = student_cookie(page)
    page.classwork.assign(page.catalog, "task-1", (page.roster.authenticate_student("s1", "secret").class_id,))

    opened = text(response_for(page, "GET", "/student/tasks/task-1", "", 5, cookie))

    assert "判断说法" in opened
    assert "草稿里的新题干" not in opened
