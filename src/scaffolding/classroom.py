import secrets
import time
from dataclasses import replace
from html import escape
from urllib.parse import parse_qs, quote, urlsplit

from scaffolding.generation import TaskGeneration
from scaffolding.knowledge import KnowledgeBase
from scaffolding.model_decision import ModelDecisionAgent
from scaffolding.model_extractor import ModelObjectiveExtractor
from scaffolding.model_generator import ModelQuestionGenerator, deepseek_complete
from scaffolding.model_text import ModelTextGenerator
from scaffolding.model_scaffold import ModelScaffoldAgent
from scaffolding.objectives import ObjectiveCatalog
from scaffolding.roster import Roster, RosterError
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
    ) -> None:
        self.catalog = catalog
        self.knowledge = knowledge if knowledge is not None else KnowledgeBase()
        self.objectives = (
            objectives
            if objectives is not None
            else ObjectiveCatalog(self.knowledge, _EmptyExtractor())
        )
        self.generation = generation
        self.roster = Roster()
        self.teacher_tokens = set()
        self.student_tokens = {}
        self.student_pages = {}
        self.teacher = TeacherPage(
            catalog,
            prefix="/teacher",
            roster=self.roster,
            knowledge=self.knowledge,
            objectives=self.objectives,
            generation=generation,
        )
        self.student = StudentPage(catalog, decision, scaffold_agent, prefix="/student")


def response_for(room: Classroom, method: str, path: str, body: str, now: float, headers: str = ""):
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
        return _teacher_response(room, method, parts, rest, body, headers)
    return _student_response(room, method, parts, rest, body, now, headers)


def _student_visible(room: Classroom, task_id: str) -> bool:
    try:
        task = room.catalog.get(task_id)
    except KeyError:
        return False
    return task.published


def _document(body: str) -> str:
    return "<!DOCTYPE html><html lang=\"zh\"><body>" + body + "</body></html>"


def _html(text: str, status: int = 200, set_cookie: str = "") -> PageResponse:
    return PageResponse(status, "text/html; charset=utf-8", text.encode(), set_cookie)


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


def _student_page(room: Classroom, account: str) -> StudentPage:
    if account not in room.student_pages:
        page = StudentPage(
            room.catalog,
            room.student.decision,
            room.student.scaffold_agent,
            prefix="/student",
            show_logout=True,
        )
        room.student_pages[account] = page
    room.student = room.student_pages[account]
    return room.student_pages[account]


def _student_login(room: Classroom, body: str, now: float):
    fields = parse_qs(body, keep_blank_values=True)
    account = fields.get("account", [""])[-1]
    password = fields.get("password", [""])[-1]
    student = room.roster.authenticate_student(account, password)
    if student is None:
        return _html(_login_page("/student/login", "账号或密码不正确"))
    token = secrets.token_hex(16)
    room.student_tokens[token] = student.account
    page = _student_page(room, student.account)
    response = student_response_for(page, "GET", "/", "", now)
    return replace(response, set_cookie=_set_cookie("student", token, "/student"))


def _teacher_response(room: Classroom, method: str, parts: list, rest: str, body: str, headers: str):
    if len(parts) >= 2 and parts[1] == "login" and method == "POST":
        return _teacher_login(room, body)
    token = _cookie_value(headers, "teacher")
    if token not in room.teacher_tokens:
        return _html(_login_page("/teacher/login"))
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
    response = teacher_response_for(room.teacher, method, rest, body)
    if method == "POST" and len(parts) == 3 and parts[1] == "tasks":
        action = parse_qs(body, keep_blank_values=True).get("action", [""])[-1]
        task_id = parts[2]
        if action == "delete" and task_id not in room.catalog._tasks:
            room.student.sessions.pop(task_id, None)
            room.student.shown_at.pop(task_id, None)
            for student_page in room.student_pages.values():
                student_page.sessions.pop(task_id, None)
                student_page.shown_at.pop(task_id, None)
    return response


def _student_response(room: Classroom, method: str, parts: list, rest: str, body: str, now: float, headers: str):
    if len(parts) >= 2 and parts[1] == "login" and method == "POST":
        return _student_login(room, body, now)
    token = _cookie_value(headers, "student")
    account = room.student_tokens.get(token)
    if account is None:
        return _html(_login_page("/student/login"))
    student_page = _student_page(room, account)
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
            raw = self.rfile.read(length).decode("utf-8")
            headers = self.headers.get("Cookie", "")
            response = response_for(room, self.command, self.path, raw, time.monotonic(), headers)
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
