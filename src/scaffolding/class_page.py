from html import escape
from urllib.parse import quote, unquote, urlsplit

from scaffolding.classwork import StudentView
from scaffolding.records import ChoiceQuestion, OpenQuestion, TrueFalseQuestion
from scaffolding.roster import RosterError
from scaffolding.sheet import SheetError, read_student_rows
from scaffolding.teacher_page import teacher_shell


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
    if len(parts) >= 4 and parts[2] == "students":
        account = parts[3]
        try:
            page.roster.student(class_id, account)
        except RosterError:
            return ""
        if len(parts) == 4:
            if method == "POST" and action == "修改姓名":
                return _rename(page, class_id, account, fields)
            if method == "POST" and action == "重置密码":
                return _reset(page, class_id, account, fields)
            if method == "POST" and action == "移除":
                page.roster.remove_student(class_id, account)
                return _class_page(page, class_id)
            return _student_page(page, class_id, account)
        if len(parts) >= 6 and parts[4] == "tasks":
            return _task_response(page, class_id, account, parts)
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


def _document(page, body: str, current: str = "班级") -> str:
    wrapped = teacher_shell(body, "/teacher", current, page.roster.teacher_account)
    return (
        "<!DOCTYPE html><html lang=\"zh\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<link rel=\"stylesheet\" href=\"/static/classroom.css?v=8\"></head><body>"
        + wrapped
        + "<script src=\"/static/teacher.js\"></script></body></html>"
    )


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
    return _document(page, body)


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
    return _document(page, body)


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
        + "<ul>" + "".join(_task_items(page, class_id, account)) + "</ul>"
    )
    return _document(page, body)


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


def missing_task_page(page) -> str:
    return _document(page, "<h1>任务不存在</h1>")


def class_asset(page, path: str) -> tuple[str, bytes] | None:
    parts = [unquote(part) for part in urlsplit(path).path.split("/") if part]
    if parts[:1] != ["classes"] or len(parts) < 8 or parts[2] != "students" or parts[4] != "tasks":
        return None
    class_id = parts[1]
    account = parts[3]
    task_id = parts[5]
    try:
        page.roster.student(class_id, account)
    except RosterError:
        return None
    found = _assigned(page, class_id, account, task_id)
    if found is None or found[1] is None:
        return None
    work = found[1]
    if len(parts) == 8 and parts[6] == "assets":
        return _named_asset(_current_scaffold(work), parts[7])
    if len(parts) == 10 and parts[6] == "turns" and parts[8] == "assets" and parts[7].isdigit():
        index = int(parts[7])
        if index >= len(work.dialogue):
            return None
        return _named_asset(work.dialogue[index].scaffold, parts[9])
    return None


def _task_response(page, class_id: str, account: str, parts: list[str]) -> str:
    if len(parts) != 6:
        return ""
    found = _assigned(page, class_id, account, parts[5])
    if found is None:
        return missing_task_page(page)
    task, work = found
    return _task_detail(page, class_id, account, task, work)


def _task_items(page, class_id: str, account: str) -> list[str]:
    view = _view(page, class_id, account)
    action = _student_href(class_id, account)
    items = []
    for listed in view.student_tasks():
        try:
            work = view.work(listed.task_id)
        except KeyError:
            work = None
        href = action + "/tasks/" + quote(listed.task_id, safe="")
        items.append(
            "<li><a href=\"" + href + "\">" + escape(listed.task_id)
            + "</a> " + escape(_status(work)) + "</li>"
        )
    return items


def _task_detail(page, class_id: str, account: str, task, work) -> str:
    questions = task.questions if work is None else work.questions
    parts = ["<h1>" + escape(task.task_id) + "</h1><p>" + escape(_status(work)) + "</p>"]
    for index, question in enumerate(questions):
        answer = None if work is None else work.answers[index]
        parts.append(_read_question(question, answer))
    if work is None:
        return _document(page, "".join(parts))
    parts.append("<p>停留" + str(int(work.behavior.dwell_seconds)) + "</p>")
    if work.behavior.helps:
        parts.append("<h2>求助</h2><ul>")
        for event in work.behavior.helps:
            parts.append("<li>" + escape(event.text) + "</li>")
        parts.append("</ul>")
    base = _student_href(class_id, account) + "/tasks/" + quote(task.task_id, safe="")
    current = _current_scaffold(work)
    if current is not None:
        parts.append("<h2>支架</h2>" + _scaffold_body(current, base + "/assets/"))
    if work.dialogue:
        parts.append("<h2>对话</h2>")
        for index, turn in enumerate(work.dialogue):
            parts.append(_turn(base, index, turn))
    return _document(page, "".join(parts))


def _read_question(question, answer) -> str:
    if isinstance(question, OpenQuestion):
        given = "" if answer is None else answer.text
        requirements = question.requirements
    elif isinstance(question, (ChoiceQuestion, TrueFalseQuestion)):
        given = "" if answer is None else "、".join(answer.selected)
        requirements = ""
    else:
        raise TypeError("unknown question")
    reference = question.answer if isinstance(question.answer, str) else "、".join(question.answer)
    body = "<section><p>" + escape(question.prompt) + "</p>"
    if requirements:
        body += "<p>" + escape(requirements) + "</p>"
    body += (
        "<p>作答：" + escape(given) + "</p>"
        + "<p>参考答案：" + escape(reference) + "</p>"
        + "<p>解析：" + escape(question.explanation) + "</p></section>"
    )
    return body


def _scaffold_body(scaffold, address_prefix: str) -> str:
    parts = ["<p>" + escape(scaffold.text) + "</p>"]
    for asset in scaffold.assets:
        address = address_prefix + quote(asset.filename, safe="")
        parts.append(
            "<figure><figcaption>" + escape(asset.kind.value) + " " + escape(asset.filename)
            + "</figcaption><img src=\"" + escape(address) + "\" alt=\"" + escape(asset.filename)
            + "\"><a href=\"" + escape(address) + "\" download=\"" + escape(asset.filename)
            + "\">保存</a></figure>"
        )
    return "".join(parts)


def _turn(base: str, index: int, turn) -> str:
    body = "<h3>" + escape(turn.question) + "</h3>"
    if turn.scaffold is not None:
        address = base + "/turns/" + str(index) + "/assets/"
        body += "<div class=\"turn-scaffold\">" + _scaffold_body(turn.scaffold, address) + "</div>"
    return "<article>" + body + "</article>"


def _assigned(page, class_id: str, account: str, task_id: str):
    view = _view(page, class_id, account)
    try:
        task = view.get(task_id)
    except KeyError:
        return None
    try:
        work = view.work(task_id)
    except KeyError:
        work = None
    return task, work


def _view(page, class_id: str, account: str) -> StudentView:
    return StudentView(page.catalog, page.classwork, account, class_id)


def _student_href(class_id: str, account: str) -> str:
    return (
        _prefix() + "/classes/" + quote(class_id, safe="")
        + "/students/" + quote(account, safe="")
    )


def _status(work) -> str:
    if work is None:
        return "还没作答"
    if work.submitted:
        return "已完成"
    return "待办"


def _current_scaffold(work):
    found = None
    for turn in work.dialogue:
        if turn.scaffold is not None:
            found = turn.scaffold
    return found


def _named_asset(scaffold, filename: str) -> tuple[str, bytes] | None:
    if scaffold is None:
        return None
    for asset in scaffold.assets:
        if asset.filename == filename:
            return asset.filename, asset.content
    return None
