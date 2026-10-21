import time
from urllib.parse import parse_qs, quote, urlsplit

from scaffolding.model_decision import ModelDecisionAgent
from scaffolding.model_generator import deepseek_complete
from scaffolding.model_scaffold import ModelScaffoldAgent
from scaffolding.student_page import StudentPage
from scaffolding.tasks import TaskCatalog
from scaffolding.student_page import response_for as student_response_for
from scaffolding.teacher_page import PageResponse
from scaffolding.teacher_page import TeacherPage
from scaffolding.teacher_page import response_for as teacher_response_for


class Classroom:
    def __init__(self, catalog, decision, scaffold_agent) -> None:
        self.catalog = catalog
        self.teacher = TeacherPage(catalog, prefix="/teacher")
        self.student = StudentPage(catalog, decision, scaffold_agent, prefix="/student")


def response_for(room: Classroom, method: str, path: str, body: str, now: float):
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
        response = teacher_response_for(room.teacher, method, rest, body)
        if method == "POST" and len(parts) == 3 and parts[1] == "tasks":
            action = parse_qs(body, keep_blank_values=True).get("action", [""])[-1]
            task_id = parts[2]
            if action == "delete" and task_id not in room.catalog._tasks:
                room.student.sessions.pop(task_id, None)
                room.student.shown_at.pop(task_id, None)
        return response
    if len(parts) >= 3 and parts[1] == "tasks" and not _student_visible(room, parts[2]):
        return _html(_document("<h1>任务不存在</h1>"), 404)
    return student_response_for(room.student, method, rest, body, now)


def _student_visible(room: Classroom, task_id: str) -> bool:
    try:
        task = room.catalog.get(task_id)
    except KeyError:
        return False
    return task.published


def _document(body: str) -> str:
    return "<!DOCTYPE html><html lang=\"zh\"><body>" + body + "</body></html>"


def _html(text: str, status: int = 200) -> PageResponse:
    return PageResponse(status, "text/html; charset=utf-8", text.encode())


def production_classroom(*, post, api_key=None) -> Classroom:
    catalog = TaskCatalog()

    def complete(messages):
        return deepseek_complete(messages, post=post, api_key=api_key)

    return Classroom(catalog, ModelDecisionAgent(complete), ModelScaffoldAgent(complete))


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
            response = response_for(room, self.command, self.path, raw, time.monotonic())
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            filename = getattr(response, "filename", "")
            if filename:
                encoded = quote(filename, safe="")
                self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + encoded)
            self.send_header("Content-Length", str(len(response.body)))
            self.end_headers()
            self.wfile.write(response.body)

        def log_message(self, *args) -> None:
            return

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
