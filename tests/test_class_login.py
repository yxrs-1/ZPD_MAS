from scaffolding.classroom import response_for
from tests.classroom_helpers import form, room, text


def test_teacher_and_student_pages_require_login():
    page = room()

    teacher = response_for(page, "GET", "/teacher", "", 0)
    student = response_for(page, "GET", "/student", "", 0)
    home = text(response_for(page, "GET", "/", "", 0))

    assert teacher.status == 200
    assert "<h1>登录</h1>" in text(teacher)
    assert "任务列表" not in text(teacher)
    assert "<h1>登录</h1>" in text(student)
    assert "待办" not in text(student)
    assert "<h1>登录</h1>" in home and 'href="/student/register"' in home


def test_the_preset_teacher_logs_in_changes_password_and_logs_out():
    page = room()

    wrong = response_for(page, "POST", "/teacher/login", form(account="s1", password="secret"), 0)
    opened = response_for(page, "POST", "/teacher/login", form(account="643590872", password="643590872"), 0)
    listed = response_for(page, "GET", "/teacher", "", 0, opened.set_cookie.split(";", 1)[0])
    changed = response_for(
        page, "POST", "/teacher", form(action="修改密码", old_password="643590872", password="next"), 0,
        opened.set_cookie.split(";", 1)[0],
    )
    again = response_for(page, "POST", "/teacher/login", form(account="643590872", password="next"), 0)
    left = response_for(page, "POST", "/teacher", form(action="退出"), 0, again.set_cookie.split(";", 1)[0])

    assert wrong.status == 200
    assert "账号或密码不正确" in text(wrong)
    assert wrong.set_cookie == ""
    assert opened.set_cookie.startswith("teacher=")
    assert "Path=/teacher" in opened.set_cookie
    assert "<h1>任务列表</h1>" in text(opened)
    assert 'href="/teacher/classes"' in text(listed)
    assert "密码已修改" in text(changed)
    assert again.set_cookie.startswith("teacher=")
    assert left.set_cookie.startswith("teacher=;")
    assert "<h1>登录</h1>" in text(left)


def test_a_student_cookie_does_not_open_the_teacher_page():
    page = room()
    created = page.roster.create_class("一班")
    page.roster.import_rows(created.class_id, ((2, "s1", "secret", "甲"),))

    opened = response_for(page, "POST", "/student/login", form(account="s1", password="secret"), 0)
    teacher = response_for(page, "GET", "/teacher", "", 0, opened.set_cookie.split(";", 1)[0])

    assert opened.set_cookie.startswith("student=")
    assert "<h1>待办</h1>" in text(opened)
    assert "<h1>登录</h1>" in text(teacher)
