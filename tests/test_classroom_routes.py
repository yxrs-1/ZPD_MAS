from scaffolding.classroom import response_for
from tests.classroom_helpers import room, student_cookie, teacher_cookie, text


def test_the_root_links_to_the_teacher_and_the_student():
    page = room()

    html = text(response_for(page, "GET", "/", "", 0))

    assert "<h1>课堂</h1>" in html
    assert html.index("教师") < html.index("学生")
    assert 'href="/teacher"' in html
    assert 'href="/student"' in html
    assert "task-" not in html


def test_prefixes_dispatch_and_a_trailing_slash_or_query_does_not_matter():
    page = room()

    teacher_login = text(response_for(page, "GET", "/teacher/?ready=1", "", 0))
    student_login = text(response_for(page, "GET", "/student", "", 0))
    missing = response_for(page, "GET", "/teachers", "", 0)
    teacher = text(response_for(page, "GET", "/teacher/?ready=1", "", 0, teacher_cookie(page)))
    student = text(response_for(page, "GET", "/student", "", 0, student_cookie(page)))

    assert "<h1>登录</h1>" in teacher_login
    assert "任务列表" not in teacher_login
    assert "<h1>登录</h1>" in student_login
    assert "待办" not in student_login
    assert "<h1>任务列表</h1>" in teacher
    assert "<h1>待办</h1>" in student
    assert missing.status == 404
    assert "页面不存在" in text(missing)
    assert "任务列表" not in text(missing)
    assert "待办" not in text(missing)
    assert 'href="/teacher"' not in text(missing)


def test_an_unknown_teacher_path_stays_a_missing_task():
    page = room()

    missing = response_for(page, "GET", "/teacher/missing", "", 0, teacher_cookie(page))

    assert missing.status == 404
    assert "任务不存在" in text(missing)
