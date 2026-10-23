import email
import os
import sys
import secrets
import threading
import time
from dataclasses import dataclass, replace
from html import escape
from urllib.parse import parse_qs, quote, unquote, urlencode, urlsplit

import scaffolding.store as store
from scaffolding.class_page import class_asset, class_response, missing_task_page
from scaffolding.classwork import Classwork, StudentView
from scaffolding.documents import DocumentLibrary
from scaffolding.generation import TaskGeneration
from scaffolding.knowledge import KnowledgeBase
from scaffolding.model_decision import ModelDecisionAgent
from scaffolding.model_extractor import ModelObjectiveExtractor
from scaffolding.model_generator import ModelQuestionGenerator, deepseek_complete, post_json
from scaffolding.model_text import ModelTextGenerator
from scaffolding.model_scaffold import ModelScaffoldAgent
from scaffolding.objectives import ObjectiveCatalog
from scaffolding.roster import Roster, RosterError
from scaffolding.session import Session
from scaffolding.student_page import StudentPage
from scaffolding.tasks import TaskCatalog
from scaffolding.student_page import response_for as student_response_for
from scaffolding.teacher_page import PageResponse
from scaffolding.teacher_page import TeacherPage
from scaffolding.teacher_page import response_for as teacher_response_for


class _EmptyExtractor:
    def extract(self, retrieval):
        return ()


class Classroom:
    def __init__(
        self,
        catalog,
        decision,
        scaffold_agent,
        knowledge=None,
        objectives=None,
        generation=None,
        *,
        path=None,
        complete=None,
    ) -> None:
        self._lock = threading.RLock()
        self.catalog = catalog
        self.knowledge = knowledge if knowledge is not None else KnowledgeBase()
        self.objectives = (
            objectives
            if objectives is not None
            else ObjectiveCatalog(self.knowledge, _EmptyExtractor())
        )
        self.generation = generation
        self.roster = Roster()
        self.classwork = Classwork(self.roster)
        self.teacher_tokens = set()
        self.student_tokens = {}
        self.student_pages = {}
        self.documents = DocumentLibrary()
        self.teacher = TeacherPage(
            catalog,
            prefix="/teacher",
            roster=self.roster,
            knowledge=self.knowledge,
            objectives=self.objectives,
            generation=generation,
            classwork=self.classwork,
            library=self.documents,
            complete=complete,
        )
        self.student = StudentPage(catalog, decision, scaffold_agent, prefix="/student")
        self.path = None if path is None else os.fspath(path)
        self.saved_sessions = {}
        if self.path is not None:
            if os.path.isfile(self.path):
                store.load_classroom(self.path, self)
            else:
                store.save_classroom(self.path, self)


def response_for(
    room: Classroom,
    method: str,
    path: str,
    body: str,
    now: float,
    headers: str = "",
    uploads=None,
    filenames=None,
):
    with room._lock:
        tracking = room.path is not None
        before = store.classroom_state(room) if tracking else None
        response = _dispatch_response(room, method, path, body, now, headers, uploads, filenames)
        if before is not None and store.classroom_state(room) != before:
            return _commit(room, response, path, headers, now)
        return response


def _dispatch_response(
    room: Classroom,
    method: str,
    path: str,
    body: str,
    now: float,
    headers: str = "",
    uploads=None,
    filenames=None,
):
    raw_path = urlsplit(path).path
    parts = [part for part in raw_path.split("/") if part]
    if parts == []:
        return _html(_document("<h1>课堂</h1><a href=\"/teacher\">教师</a><a href=\"/student\">学生</a>"))
    if parts[0] not in ("teacher", "student"):
        return _html(_document("<h1>页面不存在</h1>"), 404)
    rest = raw_path[len("/" + parts[0]):] or "/"
    if not rest.startswith("/"):
        rest = "/" + rest
    if parts[0] == "teacher":
        return _teacher_response(room, method, parts, rest, body, headers, uploads, filenames)
    return _student_response(room, method, parts, rest, body, now, headers)


def _student_visible(room: Classroom, task_id: str) -> bool:
    try:
        task = room.catalog.get(task_id)
    except KeyError:
        return False
    return task.published


def _document(body: str) -> str:
    return "<!DOCTYPE html><html lang=\"zh\"><body>" + body + "</body></html>"


@dataclass(frozen=True)
class _Download:
    status: int
    content_type: str
    body: bytes
    set_cookie: str = ""
    filename: str = ""


def _html(text: str, status: int = 200, set_cookie: str = "") -> PageResponse:
    return PageResponse(status, "text/html; charset=utf-8", text.encode(), set_cookie)


def _download(content: bytes, status: int = 200, filename: str = "") -> _Download:
    return _Download(status, "application/octet-stream", content, filename=filename)


def _login_page(action: str, message: str = "") -> str:
    body = "<h1>登录</h1>"
    if message:
        body += "<p>" + escape(message) + "</p>"
    body += (
        "<form method=\"post\" action=\"" + action + "\">"
        + "<input name=\"account\">"
        + "<input name=\"password\">"
        + "<button type=\"submit\">登录</button></form>"
    )
    return _document(body)


def _cookie_value(headers: str, name: str) -> str:
    for part in headers.split(";"):
        item = part.strip()
        if item.lower().startswith("cookie:"):
            item = item[7:].strip()
        if item.startswith(name + "="):
            return item[len(name) + 1:]
    return ""


def _set_cookie(name: str, token: str, path: str) -> str:
    return name + "=" + token + "; HttpOnly; Path=" + path


def _clear_cookie(name: str, path: str) -> str:
    return name + "=; Max-Age=0; Path=" + path


def _teacher_login(room: Classroom, body: str):
    fields = parse_qs(body, keep_blank_values=True)
    account = fields.get("account", [""])[-1]
    password = fields.get("password", [""])[-1]
    if not room.roster.authenticate_teacher(account, password):
        return _html(_login_page("/teacher/login", "账号或密码不正确"))
    token = secrets.token_hex(16)
    room.teacher_tokens.add(token)
    response = teacher_response_for(room.teacher, "GET", "/", "")
    return replace(response, set_cookie=_set_cookie("teacher", token, "/teacher"))


def _class_of(room: Classroom, account: str) -> str:
    for item in room.roster.classes():
        for student in room.roster.students(item.class_id):
            if student.account == account:
                return item.class_id
    return ""


def _student_page(room: Classroom, account: str, class_id: str) -> StudentPage:
    page = room.student_pages.get(account)
    if page is None or page.catalog._class_id != class_id:
        page = StudentPage(
            StudentView(room.catalog, room.classwork, account, class_id),
            room.student.decision,
            room.student.scaffold_agent,
            prefix="/student",
            show_logout=True,
        )
        _restore_saved_sessions(room, page, account)
        room.student_pages[account] = page
    room.student = page
    return page


def _restore_saved_sessions(room: Classroom, page, account: str) -> None:
    for task_id, item in room.saved_sessions.get(account, {}).items():
        try:
            work = page.catalog.work(task_id)
        except KeyError:
            continue
        page.sessions[task_id] = Session.restore(
            page.catalog,
            work,
            page.decision,
            page.scaffold_agent,
            item["presets"],
            item["scaffold"],
        )


def _commit(room: Classroom, response, path: str, headers: str, now: float):
    try:
        store.save_classroom(room.path, room)
    except OSError:
        store.load_classroom(room.path, room)
        fresh = _rerender_teacher(room, path, headers)
        if fresh is None:
            fresh = _rerender_student(room, path, headers, now)
        return _inject_failure(fresh if fresh is not None else response)
    return response


def _rerender_teacher(room: Classroom, path: str, headers: str):
    raw_path = urlsplit(path).path
    parts = [part for part in raw_path.split("/") if part]
    if not parts or parts[0] != "teacher" or (len(parts) >= 2 and parts[1] == "login"):
        return None
    token = _cookie_value(headers, "teacher")
    if token not in room.teacher_tokens:
        return _html(_login_page("/teacher/login"))
    rest = raw_path[len("/teacher"):] or "/"
    if not rest.startswith("/"):
        rest = "/" + rest
    if len(parts) >= 2 and parts[1] == "classes":
        html = class_response(room, "GET", rest, {}, {})
        if html == "":
            title = "学生不存在" if len(parts) >= 4 and parts[3] == "students" else "班级不存在"
            return _html(_document("<h1>" + title + "</h1>"), 404)
        return _html(html)
    return teacher_response_for(room.teacher, "GET", rest, "")


def _rerender_student(room: Classroom, path: str, headers: str, now: float):
    raw_path = urlsplit(path).path
    parts = [part for part in raw_path.split("/") if part]
    if not parts or parts[0] != "student" or (len(parts) >= 2 and parts[1] == "login"):
        return None
    token = _cookie_value(headers, "student")
    account = room.student_tokens.get(token)
    if account is None:
        return _html(_login_page("/student/login"))
    student_page = _student_page(room, account, _class_of(room, account))
    if len(parts) >= 3 and parts[1] == "tasks":
        task_id = unquote(parts[2])
        if not _student_visible(room, task_id):
            return _html(_document("<h1>任务不存在</h1>"), 404)
        try:
            student_page.catalog.work(task_id)
        except KeyError:
            return student_response_for(student_page, "GET", "/", "", now)
        return student_response_for(student_page, "GET", "/tasks/" + task_id, "", now)
    rest = raw_path[len("/student"):] or "/"
    if not rest.startswith("/"):
        rest = "/" + rest
    return student_response_for(student_page, "GET", rest, "", now)


def _inject_failure(response):
    try:
        body = response.body.decode("utf-8")
    except UnicodeDecodeError:
        return response
    if "没有写入文件" in body:
        return response
    if "</body>" in body:
        body = body.replace("</body>", "<p>没有写入文件</p></body>", 1)
    else:
        body += "没有写入文件"
    return replace(response, body=body.encode("utf-8"))


def _clear_pages(room: Classroom, accounts) -> None:
    for account in accounts:
        room.student_pages.pop(account, None)


def _release_unassigned_sessions(room: Classroom, task_id: str) -> None:
    assigned = set(room.classwork.assigned(task_id))
    for account, student_page in room.student_pages.items():
        if _class_of(room, account) not in assigned:
            student_page.sessions.pop(task_id, None)
            student_page.shown_at.pop(task_id, None)


def _student_login(room: Classroom, body: str, now: float):
    fields = parse_qs(body, keep_blank_values=True)
    account = fields.get("account", [""])[-1]
    password = fields.get("password", [""])[-1]
    student = room.roster.authenticate_student(account, password)
    if student is None:
        return _html(_login_page("/student/login", "账号或密码不正确"))
    token = secrets.token_hex(16)
    room.student_tokens[token] = student.account
    page = _student_page(room, student.account, student.class_id)
    response = student_response_for(page, "GET", "/", "", now)
    return replace(response, set_cookie=_set_cookie("student", token, "/student"))


def files_from_body(content_type: str, body: bytes) -> dict[str, bytes]:
    files = {}
    for part in _multipart_parts(content_type, body):
        name = _part_name(part)
        if name == "" or part.get_filename() is None:
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        files[name] = payload
    return files


def filenames_from_body(content_type: str, body: bytes) -> dict[str, str]:
    names = {}
    for headers in _raw_part_headers(content_type, body):
        name, filename = _disposition_name_and_filename(headers)
        if name and filename:
            names[name] = filename
    return names


def _raw_part_headers(content_type: str, body: bytes):
    boundary = _multipart_boundary(content_type)
    if boundary == b"":
        return
    for chunk in body.split(b"--" + boundary):
        if chunk.startswith(b"--"):
            continue
        if chunk.startswith(b"\r\n"):
            chunk = chunk[2:]
        elif chunk.startswith(b"\n"):
            chunk = chunk[1:]
        if chunk == b"":
            continue
        separator = b"\r\n\r\n"
        index = chunk.find(separator)
        if index < 0:
            index = chunk.find(b"\n\n")
        if index < 0:
            continue
        yield chunk[:index]


def _multipart_boundary(content_type: str) -> bytes:
    lower = content_type.lower()
    marker = "boundary="
    start = lower.find(marker)
    if start < 0:
        return b""
    value = content_type[start + len(marker):].strip()
    if ";" in value:
        value = value.split(";", 1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    return value.encode("utf-8")


def _disposition_name_and_filename(headers: bytes) -> tuple[str, str]:
    params = _header_params(_header_value(headers, b"content-disposition"))
    name = params.get(b"name", b"").decode("utf-8")
    starred = params.get(b"filename*")
    if starred is not None:
        return name, _decode_filename_star(starred)
    quoted = params.get(b"filename")
    if quoted is None:
        return name, ""
    return name, quoted.decode("utf-8")


def _header_value(headers: bytes, name: bytes) -> bytes:
    prefix = name.lower() + b":"
    current = None
    for raw in headers.replace(b"\r\n", b"\n").split(b"\n"):
        if raw.startswith((b" ", b"\t")) and current is not None:
            current += b" " + raw.strip()
            continue
        if current is not None and current.lower().startswith(prefix):
            return current.split(b":", 1)[1].strip()
        current = raw
    if current is not None and current.lower().startswith(prefix):
        return current.split(b":", 1)[1].strip()
    return b""


def _header_params(header: bytes) -> dict[bytes, bytes]:
    params = {}
    rest = header
    while True:
        semicolon = rest.find(b";")
        if semicolon < 0:
            break
        rest = rest[semicolon + 1:].lstrip()
        equals = rest.find(b"=")
        if equals < 0:
            break
        key = rest[:equals].strip().lower()
        rest = rest[equals + 1:].lstrip()
        if rest.startswith(b'"'):
            value, rest = _quoted_bytes(rest)
        else:
            end = rest.find(b";")
            if end < 0:
                value, rest = rest, b""
            else:
                value, rest = rest[:end].rstrip(), rest[end:]
        params[key] = value
    return params


def _quoted_bytes(text: bytes) -> tuple[bytes, bytes]:
    out = bytearray()
    index = 1
    while index < len(text):
        char = text[index]
        if char == 92 and index + 1 < len(text):
            out.append(text[index + 1])
            index += 2
            continue
        if char == 34:
            return bytes(out), text[index + 1:]
        out.append(char)
        index += 1
    return bytes(out), b""


def _decode_filename_star(value: bytes) -> str:
    text = value.decode("ascii")
    marker = "utf-8''"
    if text.lower().startswith(marker):
        return unquote(text[len(marker):], encoding="utf-8")
    return unquote(text, encoding="utf-8")


def _multipart_parts(content_type: str, body: bytes):
    message = email.message_from_bytes(
        b"Content-Type: " + content_type.encode("utf-8") + b"\r\n\r\n" + body
    )
    payload = message.get_payload()
    if not isinstance(payload, list):
        return ()
    return payload


def _part_name(part) -> str:
    name = part.get_param("name", header="content-disposition")
    if name is None:
        return ""
    if isinstance(name, tuple):
        name = name[-1]
    return str(name)


def _fields_from_multipart(content_type: str, body: bytes) -> str:
    pairs = []
    for part in _multipart_parts(content_type, body):
        name = _part_name(part)
        if name == "" or part.get_filename() is not None:
            continue
        payload = part.get_payload(decode=True)
        value = payload.decode("utf-8") if payload else ""
        pairs.append((name, value))
    return urlencode(pairs)


def _teacher_response(
    room: Classroom,
    method: str,
    parts: list,
    rest: str,
    body: str,
    headers: str,
    uploads=None,
    filenames=None,
):
    if len(parts) >= 2 and parts[1] == "login" and method == "POST":
        return _teacher_login(room, body)
    token = _cookie_value(headers, "teacher")
    if token not in room.teacher_tokens:
        return _html(_login_page("/teacher/login"))
    if len(parts) >= 2 and parts[1] == "classes":
        if method == "GET" and _is_class_asset(parts):
            found = class_asset(room, rest)
            if found is None:
                return _download(b"", 404)
            filename, content = found
            return _download(content, 200, filename)
        fields = parse_qs(body, keep_blank_values=True)
        action = fields.get("action", [""])[-1]
        if method == "POST" and action == "删除班级" and len(parts) >= 3:
            class_id = unquote(parts[2])
            try:
                accounts = tuple(student.account for student in room.roster.students(class_id))
            except RosterError:
                accounts = None
            if accounts is not None:
                room.classwork.drop_class(class_id)
                _clear_pages(room, accounts)
        if method == "POST" and action == "移除" and len(parts) >= 5 and parts[3] == "students":
            class_id = unquote(parts[2])
            account = unquote(parts[4])
            try:
                room.roster.student(class_id, account)
            except RosterError:
                pass
            else:
                room.classwork.drop_student(account)
                _clear_pages(room, (account,))
        html = class_response(room, method, rest, fields, uploads or {})
        if html == "":
            title = "学生不存在" if len(parts) >= 4 and parts[3] == "students" else "班级不存在"
            return _html(_document("<h1>" + title + "</h1>"), 404)
        status = 404 if html == missing_task_page() else 200
        return _html(html, status)
    if method == "POST" and len(parts) == 1:
        fields = parse_qs(body, keep_blank_values=True)
        action = fields.get("action", [""])[-1]
        if action == "退出":
            room.teacher_tokens.discard(token)
            return _html(_login_page("/teacher/login"), set_cookie=_clear_cookie("teacher", "/teacher"))
        if action == "修改密码":
            old_password = fields.get("old_password", [""])[-1]
            password = fields.get("password", [""])[-1]
            try:
                room.roster.change_teacher_password(old_password, password)
                message = "密码已修改"
            except RosterError as error:
                message = str(error)
            return _html(room.teacher.list_tasks(message))
    response = teacher_response_for(room.teacher, method, rest, body, uploads, filenames)
    if method == "POST" and len(parts) == 3 and parts[1] == "tasks":
        action = parse_qs(body, keep_blank_values=True).get("action", [""])[-1]
        task_id = parts[2]
        if action == "delete" and task_id not in room.catalog._tasks:
            room.student.sessions.pop(task_id, None)
            room.student.shown_at.pop(task_id, None)
            for student_page in room.student_pages.values():
                student_page.sessions.pop(task_id, None)
                student_page.shown_at.pop(task_id, None)
        if action == "布置" and task_id in room.catalog._tasks:
            _release_unassigned_sessions(room, task_id)
    return response


def _is_class_asset(parts: list) -> bool:
    if parts[1] != "classes" or len(parts) < 8 or parts[3] != "students" or parts[5] != "tasks":
        return False
    if len(parts) == 9 and parts[7] == "assets":
        return True
    return len(parts) == 11 and parts[7] == "turns" and parts[9] == "assets"


def _student_response(room: Classroom, method: str, parts: list, rest: str, body: str, now: float, headers: str):
    if len(parts) >= 2 and parts[1] == "login" and method == "POST":
        return _student_login(room, body, now)
    token = _cookie_value(headers, "student")
    account = room.student_tokens.get(token)
    if account is None:
        return _html(_login_page("/student/login"))
    student_page = _student_page(room, account, _class_of(room, account))
    if method == "POST" and len(parts) == 1:
        fields = parse_qs(body, keep_blank_values=True)
        action = fields.get("action", [""])[-1]
        if action == "退出":
            room.student_tokens.pop(token, None)
            return _html(_login_page("/student/login"), set_cookie=_clear_cookie("student", "/student"))
    if len(parts) >= 3 and parts[1] == "tasks" and not _student_visible(room, parts[2]):
        return _html(_document("<h1>任务不存在</h1>"), 404)
    return student_response_for(student_page, method, rest, body, now)


def production_classroom(*, post, api_key=None) -> Classroom:
    catalog = TaskCatalog()
    knowledge = KnowledgeBase()

    def complete(messages):
        return deepseek_complete(messages, post=post, api_key=api_key)

    objectives = ObjectiveCatalog(knowledge, ModelObjectiveExtractor(complete))
    generation = TaskGeneration(
        objectives,
        catalog,
        ModelQuestionGenerator(complete),
        ModelTextGenerator(complete),
    )
    return Classroom(
        catalog,
        ModelDecisionAgent(complete),
        ModelScaffoldAgent(complete),
        knowledge,
        objectives,
        generation,
        path=os.path.abspath("classroom.json"),
        complete=complete,
    )


def serve(room: Classroom, port: int) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._respond()

        def do_POST(self) -> None:
            self._respond()

        def _respond(self) -> None:
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw_bytes = self.rfile.read(length)
            content_type = self.headers.get("Content-Type", "") or ""
            uploads = None
            filenames = None
            if "multipart/form-data" in content_type.lower():
                uploads = files_from_body(content_type, raw_bytes)
                filenames = filenames_from_body(content_type, raw_bytes)
                raw = _fields_from_multipart(content_type, raw_bytes)
            else:
                raw = raw_bytes.decode("utf-8")
            headers = self.headers.get("Cookie", "")
            response = response_for(
                room, self.command, self.path, raw, time.monotonic(), headers, uploads, filenames
            )
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            filename = getattr(response, "filename", "")
            if filename:
                encoded = quote(filename, safe="")
                self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + encoded)
            if response.set_cookie:
                self.send_header("Set-Cookie", response.set_cookie)
            self.send_header("Content-Length", str(len(response.body)))
            self.end_headers()
            self.wfile.write(response.body)

        def log_message(self, *args) -> None:
            return

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


def _port(argv: list[str]) -> int | None:
    if len(argv) == 0:
        return 8000
    if len(argv) != 1:
        return None
    text = argv[0].strip()
    if len(text) == 0 or not text.isascii() or not text.isdigit():
        return None
    value = int(text)
    if value < 1 or value > 65535:
        return None
    return value


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:]) if argv is None else argv
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key is None or key.strip() == "":
        print("没有配置 DEEPSEEK_API_KEY", file=sys.stderr)
        return 1
    port = _port(args)
    if port is None:
        print("端口不正确", file=sys.stderr)
        return 1
    print("http://127.0.0.1:" + str(port), flush=True)
    room = production_classroom(post=post_json)
    serve(room, port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
