from dataclasses import dataclass
from html import escape
from urllib.parse import quote, unquote, urlsplit


@dataclass(frozen=True)
class PageResponse:
    status: int
    content_type: str
    body: bytes


class TeacherPage:
    def __init__(self, catalog) -> None:
        self.catalog = catalog
        self.drafts = {}

    def list_tasks(self) -> str:
        items = []
        for task in self.catalog._tasks.values():
            href = "/tasks/" + quote(task.task_id, safe="")
            items.append(
                "<li><a href=\"" + href + "\">" + escape(task.task_id)
                + "</a> " + escape(_fact(task)) + "</li>"
            )
        body = (
            "<h1>任务列表</h1><form method=\"post\" action=\"/tasks\">"
            + "<button type=\"submit\">新建</button></form><ul>"
            + "".join(items) + "</ul>"
        )
        return _document(body)

    def create_task(self) -> str:
        task = self.catalog.create(())
        return _document("<h1>" + escape(task.task_id) + "</h1><p>" + escape(_fact(task)) + "</p>")


def _fact(task) -> str:
    if task.started:
        return "已开始"
    if task.published:
        return "已发布"
    return "未发布"


def _document(body: str) -> str:
    return "<!DOCTYPE html><html lang=\"zh\"><body>" + body + "</body></html>"


def _missing() -> str:
    return _document("<h1>任务不存在</h1>")


def _html(text: str, status: int = 200) -> PageResponse:
    return PageResponse(status, "text/html; charset=utf-8", text.encode())


def response_for(page: TeacherPage, method: str, path: str, body: str) -> PageResponse:
    parts = [unquote(part) for part in urlsplit(path).path.split("/") if part]
    if method == "GET" and parts == []:
        return _html(page.list_tasks())
    if method == "POST" and parts == ["tasks"]:
        return _html(page.create_task())
    return _html(_missing(), 404)
