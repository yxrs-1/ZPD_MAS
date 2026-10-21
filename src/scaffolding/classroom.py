from urllib.parse import urlsplit

from scaffolding.student_page import StudentPage
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
        return teacher_response_for(room.teacher, method, rest, body)
    return student_response_for(room.student, method, rest, body, now)


def _document(body: str) -> str:
    return "<!DOCTYPE html><html lang=\"zh\"><body>" + body + "</body></html>"


def _html(text: str, status: int = 200) -> PageResponse:
    return PageResponse(status, "text/html; charset=utf-8", text.encode())
