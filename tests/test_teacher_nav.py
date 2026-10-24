from scaffolding.classroom import response_for
from tests.classroom_helpers import form, room, student_cookie, teacher_cookie, text


def test_logged_in_teacher_pages_share_the_nav():
    page = room()
    cookie = teacher_cookie(page)
    listed = text(response_for(page, "GET", "/teacher", "", 0, cookie))
    library = text(response_for(page, "GET", "/teacher/documents", "", 0, cookie))
    accounts = text(response_for(page, "GET", "/teacher/accounts", "", 0, cookie))

    for html, current in ((listed, "任务"), (library, "资料库"), (accounts, "账号管理")):
        assert 'href="/teacher/"' in html or 'href="/teacher"' in html
        assert 'href="/teacher/classes"' in html
        assert 'href="/teacher/documents"' in html
        assert 'href="/teacher/accounts"' in html
        assert 'src="/static/logo.png"' in html
        assert 'name="old_password"' in html and 'name="password"' in html
        assert "修改密码" in html and "退出" in html
        assert ">目标<" not in html
    assert 'class="current"' in listed
    assert "old_password" not in listed.split("<nav", 1)[-1].split("</nav>", 1)[-1]

    classes = text(response_for(page, "GET", "/teacher/classes", "", 0, cookie))
    assert (
        '<button type="button" class="account">'
        + page.roster.teacher_account
        + "</button>"
    ) in classes
    assert '<a class="current" href="/teacher/classes">' in classes

    guest = text(response_for(page, "GET", "/teacher", "", 0))
    assert "<nav" not in guest
    assert "<h1>登录</h1>" in guest
    for path in ("/student/documents", "/student/accounts", "/student/tasks/new"):
        missing = response_for(page, "GET", path, "", 0, student_cookie(page))
        assert missing.status == 404
        assert "任务不存在" in text(missing)
