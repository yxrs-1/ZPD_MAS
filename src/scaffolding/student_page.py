from dataclasses import dataclass
from html import escape
from urllib.parse import quote, unquote, urlsplit


@dataclass(frozen=True)
class PageResponse:
    status: int
    content_type: str
    body: bytes
    filename: str = ""


class StudentPage:
    def __init__(self, catalog, decision, scaffold_agent) -> None:
        self.catalog = catalog
        self.decision = decision
        self.scaffold_agent = scaffold_agent
        self.sessions = {}
        self.shown_at = {}

    def todo(self) -> str:
        items = []
        for listed in self.catalog.student_tasks():
            href = "/tasks/" + quote(listed.task_id, safe="")
            items.append(
                "<li><a href=\"" + href + "\">" + escape(listed.task_id)
                + "</a> " + escape(listed.status) + "</li>"
            )
        return _document("<h1>待办</h1><ul>" + "".join(items) + "</ul>")


def _document(body: str) -> str:
    return "<!DOCTYPE html><html lang=\"zh\"><body>" + body + "</body></html>"


def _missing() -> str:
    return _document("<h1>任务不存在</h1>")


def _html_response(text: str, status: int = 200) -> PageResponse:
    return PageResponse(status, "text/html; charset=utf-8", text.encode())


def response_for(page: StudentPage, method: str, path: str, body: str, now: float) -> PageResponse:
    parts = [unquote(part) for part in urlsplit(path).path.split("/") if part]
    if method == "GET" and parts == []:
        return _html_response(page.todo())
    return _html_response(_missing(), 404)
