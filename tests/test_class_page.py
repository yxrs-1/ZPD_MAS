from scaffolding.classroom import files_from_body, response_for
from tests.classroom_helpers import form, room, teacher_cookie, text
from tests.test_sheet import _xlsx


def _headers(page):
    return teacher_cookie(page)


def test_the_teacher_creates_a_class_and_imports_a_sheet():
    page = room()
    headers = _headers(page)
    data = _xlsx((
        ("账号", "密码", "姓名"),
        ("s1", "secret", "<甲"),
        ("s1", "other", "乙"),
    ))

    created = response_for(page, "POST", "/teacher/classes", form(action="创建", name="一班"), 0, headers)
    imported = response_for(
        page, "POST", "/teacher/classes/class-1", form(action="导入"), 0, headers, uploads={"file": data}
    )
    missing = response_for(page, "GET", "/teacher/classes/missing", "", 0, headers)

    assert 'enctype="multipart/form-data"' in text(created)
    assert 'name="file"' in text(created)
    assert "一班" in text(created)
    assert "&lt;甲" in text(imported)
    assert "账号在这份表里重复" in text(imported)
    assert "<甲" not in text(imported).replace("&lt;甲", "")
    assert missing.status == 404
    assert "班级不存在" in text(missing)


def test_rename_reset_remove_and_delete_class():
    page = room()
    headers = _headers(page)
    response_for(page, "POST", "/teacher/classes", form(action="创建", name="一班"), 0, headers)
    response_for(
        page, "POST", "/teacher/classes/class-1", form(action="导入"), 0, headers,
        uploads={"file": _xlsx((("账号", "密码", "姓名"), ("s1", "secret", "甲")))},
    )

    renamed = response_for(
        page, "POST", "/teacher/classes/class-1/students/s1",
        form(action="修改姓名", name="甲一"), 0, headers,
    )
    reset = response_for(
        page, "POST", "/teacher/classes/class-1/students/s1",
        form(action="重置密码", password="next"), 0, headers,
    )
    removed = response_for(
        page, "POST", "/teacher/classes/class-1/students/s1",
        form(action="移除"), 0, headers,
    )
    response_for(page, "POST", "/teacher/classes", form(action="创建", name="二班"), 0, headers)
    deleted = response_for(page, "POST", "/teacher/classes/class-2", form(action="删除班级"), 0, headers)

    assert "甲一" in text(renamed)
    assert "密码已重置" in text(reset)
    assert "value=\"next\"" not in text(reset)
    assert "s1" not in text(removed)
    assert page.roster.authenticate_student("s1", "next") is None
    assert "二班" not in text(deleted)


def test_files_from_body_reads_the_uploaded_bytes():
    body = (
        b"--line\r\n"
        b"Content-Disposition: form-data; name=\"file\"; filename=\"students.xlsx\"\r\n"
        b"\r\n"
        b"PK\x03\x04sheet\r\n"
        b"--line--\r\n"
    )

    assert files_from_body("multipart/form-data; boundary=line", body)["file"] == b"PK\x03\x04sheet"
