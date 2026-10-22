from html import escape
from urllib.parse import quote, unquote, urlsplit

from scaffolding.roster import RosterError
from scaffolding.sheet import SheetError, read_student_rows


def class_response(page, method, path, fields, uploads) -> str:
    parts = [unquote(part) for part in urlsplit(path).path.split("/") if part]
    if parts == [] or parts[0] != "classes":
        return ""
    action = _value(fields, "action")
    if len(parts) == 1:
        if method == "POST" and action == "创建":
            return _create(page, fields)
        return _list(page)
    class_id = parts[1]
    if _record(page, class_id) is None:
        return ""
    if len(parts) == 2:
        if method == "POST" and action == "导入":
            return _import_students(page, class_id, uploads)
        if method == "POST" and action == "删除班级":
            page.roster.delete_class(class_id)
            return _list(page)
        return _class_page(page, class_id)
    if len(parts) == 4 and parts[2] == "students":
        account = parts[3]
        try:
            page.roster.student(class_id, account)
        except RosterError:
            return ""
        if method == "POST" and action == "修改姓名":
            return _rename(page, class_id, account, fields)
        if method == "POST" and action == "重置密码":
            return _reset(page, class_id, account, fields)
        if method == "POST" and action == "移除":
            page.roster.remove_student(class_id, account)
            return _class_page(page, class_id)
        return _student_page(page, class_id, account)
    return ""


def _value(fields, name: str) -> str:
    values = fields.get(name, [""])
    if not values:
        return ""
    return values[-1]


def _record(page, class_id: str):
    for item in page.roster.classes():
        if item.class_id == class_id:
            return item
    return None


def _prefix() -> str:
    return "/teacher"


def _document(body: str) -> str:
    return "<!DOCTYPE html><html lang=\"zh\"><body>" + body + "</body></html>"


def _create(page, fields) -> str:
    try:
        created = page.roster.create_class(_value(fields, "name"))
    except RosterError as error:
        return _list(page, str(error))
    return _class_page(page, created.class_id)


def _list(page, message: str = "") -> str:
    notice = ""
    if message:
        notice = "<p>" + escape(message) + "</p>"
    action = _prefix() + "/classes"
    items = []
    for item in page.roster.classes():
        href = action + "/" + quote(item.class_id, safe="")
        items.append("<li><a href=\"" + href + "\">" + escape(item.name) + "</a></li>")
    body = (
        "<h1>班级</h1>" + notice
        + "<form method=\"post\" action=\"" + action + "\">"
        + "<input name=\"name\">"
        + "<button type=\"submit\" name=\"action\" value=\"创建\">创建</button></form>"
        + "<ul>" + "".join(items) + "</ul>"
    )
    return _document(body)


def _class_page(page, class_id: str, message: str = "", failures=()) -> str:
    record = _record(page, class_id)
    action = _prefix() + "/classes/" + quote(class_id, safe="")
    notice = ""
    if message:
        notice = "<p>" + escape(message) + "</p>"
    fail_items = []
    for item in failures:
        fail_items.append("<li>第" + str(item.row) + "行：" + escape(item.reason) + "</li>")
    fail_html = ""
    if fail_items:
        fail_html = "<ul>" + "".join(fail_items) + "</ul>"
    students = []
    for student in page.roster.students(class_id):
        href = action + "/students/" + quote(student.account, safe="")
        students.append(
            "<li><a href=\"" + href + "\">" + escape(student.name)
            + "</a> " + escape(student.account) + "</li>"
        )
    body = (
        "<h1>" + escape(record.name) + "</h1>" + notice + fail_html
        + "<form method=\"post\" action=\"" + action + "\" enctype=\"multipart/form-data\">"
        + "<input type=\"file\" name=\"file\">"
        + "<button type=\"submit\" name=\"action\" value=\"导入\">导入</button></form>"
        + "<form method=\"post\" action=\"" + action + "\">"
        + "<button type=\"submit\" name=\"action\" value=\"删除班级\">删除班级</button></form>"
        + "<ul>" + "".join(students) + "</ul>"
    )
    return _document(body)


def _import_students(page, class_id: str, uploads) -> str:
    data = (uploads or {}).get("file")
    if not data:
        return _class_page(page, class_id, "不能读取这份表格")
    try:
        rows = read_student_rows(data)
    except SheetError as error:
        return _class_page(page, class_id, str(error))
    result = page.roster.import_rows(class_id, rows)
    return _class_page(page, class_id, failures=result.failures)


def _student_page(page, class_id: str, account: str, message: str = "") -> str:
    student = page.roster.student(class_id, account)
    action = (
        _prefix() + "/classes/" + quote(class_id, safe="")
        + "/students/" + quote(account, safe="")
    )
    notice = ""
    if message:
        notice = "<p>" + escape(message) + "</p>"
    body = (
        "<h1>" + escape(student.name) + "</h1>"
        + "<p>" + escape(student.account) + "</p>"
        + notice
        + "<form method=\"post\" action=\"" + action + "\">"
        + "<input name=\"name\">"
        + "<button type=\"submit\" name=\"action\" value=\"修改姓名\">修改姓名</button></form>"
        + "<form method=\"post\" action=\"" + action + "\">"
        + "<input name=\"password\">"
        + "<button type=\"submit\" name=\"action\" value=\"重置密码\">重置密码</button></form>"
        + "<form method=\"post\" action=\"" + action + "\">"
        + "<button type=\"submit\" name=\"action\" value=\"移除\">移除</button></form>"
    )
    return _document(body)


def _rename(page, class_id: str, account: str, fields) -> str:
    try:
        page.roster.rename_student(class_id, account, _value(fields, "name"))
        return _student_page(page, class_id, account)
    except RosterError as error:
        return _student_page(page, class_id, account, str(error))


def _reset(page, class_id: str, account: str, fields) -> str:
    try:
        page.roster.reset_password(class_id, account, _value(fields, "password"))
        return _student_page(page, class_id, account, "密码已重置")
    except RosterError as error:
        return _student_page(page, class_id, account, str(error))
