from scaffolding.classroom import Classroom, response_for
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.tasks import TaskCatalog
from tests.classroom_helpers import form, room, text


def test_the_home_page_is_the_student_login():
    html = text(response_for(room(), "GET", "/", "", 0))

    assert "<h1>登录</h1>" in html
    assert "<h1>课堂</h1>" not in html
    assert 'name="role"' in html
    assert 'value="学生"' in html and 'value="教师"' in html
    assert 'name="account"' in html and 'name="password"' in html
    assert 'action="/login"' in html
    assert ">登录</button>" in html
    assert 'value="学生" selected' in html
    assert "<h1>登录</h1>" in text(response_for(room(), "GET", "/login", "", 0))
    assert 'href="/student/register"' in html
    assert "忘记密码" in html
    assert 'class="characters"' in html
    assert 'class="person purple"' in html
    assert 'class="person orange"' in html
    assert 'class="person black"' in html
    assert 'class="person yellow"' in html
    assert ">显示</button>" in html
    assert "/static/entrance.js" in html


def test_teacher_addresses_preselect_the_teacher_and_hide_student_links():
    html = text(response_for(room(), "GET", "/teacher/login", "", 0))

    assert 'value="教师" selected' in html
    assert "注册账号" not in html
    assert "忘记密码" not in html
    assert "请教师重置密码" not in html


def test_forgot_password_only_shows_the_teacher_reset_sentence():
    shown = text(response_for(room(), "GET", "/student/login?forgot=1", "", 0))
    hidden = text(response_for(room(), "GET", "/teacher/login?forgot=1", "", 0))

    assert "请教师重置密码" in shown
    assert 'name="password"' in shown
    assert "请教师重置密码" not in hidden


def test_login_follows_the_selected_role():
    page = room()
    created = page.roster.create_class("一班")
    teacher_account = page.roster.teacher_account
    teacher_password = page.roster.teacher_password
    page.roster.import_rows(created.class_id, ((2, teacher_account, "secret", "甲"),))

    teacher = response_for(page, "POST", "/login", form(role="教师", account=teacher_account, password=teacher_password), 0)
    student = response_for(page, "POST", "/login", form(role="学生", account=teacher_account, password="secret"), 0)
    wrong = response_for(page, "POST", "/login", form(role="教师", account=teacher_account, password="secret"), 0)
    missing = response_for(page, "POST", "/login", form(role="其他", account=teacher_account, password=teacher_password), 0)

    assert teacher.set_cookie.startswith("teacher=")
    assert "<h1>任务列表</h1>" in text(teacher)
    assert student.set_cookie.startswith("student=")
    assert "<h1>待办</h1>" in text(student)
    assert wrong.set_cookie == ""
    assert wrong.status == 200
    assert "账号或密码不正确" in text(wrong)
    assert 'value="教师" selected' in text(wrong)
    assert missing.set_cookie == ""
    assert "账号或密码不正确" in text(missing)


def _saved_room(path):
    return Classroom(
        TaskCatalog(), ScriptedDecisionAgent(), ScriptedScaffoldAgent(), path=str(path)
    )


def test_register_adds_a_student_and_opens_the_todo(tmp_path):
    path = tmp_path / "classroom.json"
    page = _saved_room(path)
    created = page.roster.create_class("一班")
    response_for(page, "GET", "/", "", 0)

    empty = response_for(page, "POST", "/student/register", form(
        account="s2", password="secret", name="乙", class_id="  ",
    ), 0)

    assert empty.status == 200
    assert "先选择班级" in text(empty)
    assert page.roster.authenticate_student("s2", "secret") is None
    registered = response_for(page, "POST", "/student/register", form(
        account=" s2 ", password=" secret ", name=" 乙 ", class_id=created.class_id,
    ), 0)
    again = _saved_room(path)
    assert registered.set_cookie.startswith("student=")
    assert "<h1>待办</h1>" in text(registered)
    assert again.roster.authenticate_student("s2", "secret").name == "乙"
    assert [item.account for item in again.roster.students(created.class_id)] == ["s2"]


def test_register_page_lists_classes_and_rejects_without_writing():
    bare = text(response_for(room(), "GET", "/student/register", "", 0))
    page = room()
    created = page.roster.create_class("一班")
    listed = text(response_for(page, "GET", "/student/register", "", 0))
    page.roster.import_rows(created.class_id, ((2, "s1", "secret", "甲"),))
    duplicate = response_for(page, "POST", "/student/register", form(
        account="s1", password="secret", name="乙", class_id=created.class_id,
    ), 0)
    missing = response_for(page, "POST", "/student/register", form(
        account="s9", password="secret", name="乙", class_id="class-9",
    ), 0)
    blank = response_for(page, "POST", "/student/register", form(
        account="  ", password="secret", name="乙", class_id=created.class_id,
    ), 0)
    unnamed = response_for(page, "POST", "/student/register", form(
        account="s9", password="secret", name="  ", class_id=created.class_id,
    ), 0)
    cookie = response_for(
        page, "POST", "/student/login", form(account="s1", password="secret"), 0
    ).set_cookie.split(";", 1)[0]
    opened = response_for(page, "GET", "/student/register", "", 0, cookie)

    assert "<h1>注册</h1>" in bare
    assert "先由教师创建班级" in bare
    assert 'class="characters"' in bare
    assert '<option value="">选择班级</option>' in listed
    assert '<option value="class-1">一班</option>' in listed
    assert duplicate.status == 200 and "账号已经存在" in text(duplicate) and duplicate.set_cookie == ""
    assert missing.status == 200 and "班级不存在" in text(missing)
    assert blank.status == 200 and "账号或密码为空" in text(blank)
    assert unnamed.status == 200 and "姓名为空" in text(unnamed)
    assert [item.account for item in page.roster.students(created.class_id)] == ["s1"]
    assert "<h1>待办</h1>" in text(opened)
