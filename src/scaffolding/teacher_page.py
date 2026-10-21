from dataclasses import dataclass, replace
from html import escape
from urllib.parse import quote, unquote, urlsplit

from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion


KINDS = ("单选", "多选", "判断", "综合")


@dataclass(frozen=True)
class DraftQuestion:
    kind: str
    prompt: str = ""
    options: tuple[str, ...] = ()
    requirements: str = ""
    selected: tuple[str, ...] = ()
    answer: str = ""
    explanation: str = ""


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
        return _render(self, task.task_id)

    def open_task(self, task_id: str) -> str:
        if task_id not in self.catalog._tasks:
            return _missing()
        return _render(self, task_id)


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


def _render(page: TeacherPage, task_id: str, message: str = "") -> str:
    task = page.catalog.get(task_id)
    parts = ["<h1>" + escape(task_id) + "</h1><p>" + escape(_fact(task)) + "</p>"]
    if message:
        parts.append("<p>" + escape(message) + "</p>")
    if task.started:
        for question in task.questions:
            parts.append(_read_only(question))
        action = "/tasks/" + quote(task_id, safe="")
        parts.append(
            "<form method=\"post\" action=\"" + action + "\">"
            + "<button type=\"submit\" name=\"action\" value=\"delete\">删除</button></form>"
        )
        return _document("".join(parts))
    questions, has_draft = _shown(page, task_id)
    action = "/tasks/" + quote(task_id, safe="")
    parts.append("<form method=\"post\" action=\"" + action + "\">")
    for index, item in enumerate(questions):
        parts.append(_editor(index, item, len(questions)))
    for kind in KINDS:
        parts.append(
            "<button type=\"submit\" name=\"action\" value=\"add:" + kind
            + "\">增加" + kind + "</button>"
        )
    parts.append("<button type=\"submit\" name=\"action\" value=\"save\">保存</button>")
    if has_draft:
        parts.append("<button type=\"submit\" name=\"action\" value=\"abandon\">放弃草稿</button>")
    elif task.questions != ():
        parts.append("<button type=\"submit\" name=\"action\" value=\"publish\">发布</button>")
    parts.append("<button type=\"submit\" name=\"action\" value=\"delete\">删除</button></form>")
    return _document("".join(parts))


def _shown(page: TeacherPage, task_id: str):
    if task_id in page.drafts:
        return page.drafts[task_id], True
    task = page.catalog.get(task_id)
    return tuple(_from_question(question) for question in task.questions), False


def _from_question(question) -> DraftQuestion:
    if isinstance(question, ChoiceQuestion):
        kind = "单选" if question.selection == SelectionMode.SINGLE else "多选"
        return DraftQuestion(kind, question.prompt, question.choices, "", question.answer, "", question.explanation)
    if isinstance(question, TrueFalseQuestion):
        return DraftQuestion("判断", question.prompt, (), "", (question.answer,), "", question.explanation)
    if isinstance(question, OpenQuestion):
        return DraftQuestion("综合", question.prompt, (), question.requirements, (), question.answer, question.explanation)
    raise TypeError("unknown question")


def _editor(index: int, item: DraftQuestion, count: int) -> str:
    name = str(index)
    body = "<section><p>" + escape(item.kind) + "</p>"
    body += "<input type=\"hidden\" name=\"kind-" + name + "\" value=\"" + escape(item.kind) + "\">"
    body += "<input type=\"text\" name=\"prompt-" + name + "\" value=\"" + escape(item.prompt) + "\">"
    if item.kind in ("单选", "多选"):
        input_type = "radio" if item.kind == "单选" else "checkbox"
        for option_index, option in enumerate(item.options):
            checked = " checked" if option in item.selected else ""
            option_name = name + ":" + str(option_index)
            body += (
                "<input type=\"text\" name=\"option-" + name + "-" + str(option_index)
                + "\" value=\"" + escape(option) + "\">"
            )
            body += (
                "<input type=\"" + input_type + "\" name=\"selected-" + name
                + "\" value=\"" + escape(option) + "\"" + checked + ">"
            )
            if option_index > 0:
                body += (
                    "<button type=\"submit\" name=\"action\" value=\"up-option:"
                    + option_name + "\">上移选项</button>"
                )
            if option_index < len(item.options) - 1:
                body += (
                    "<button type=\"submit\" name=\"action\" value=\"down-option:"
                    + option_name + "\">下移选项</button>"
                )
            body += (
                "<button type=\"submit\" name=\"action\" value=\"delete-option:"
                + option_name + "\">删除选项</button>"
            )
        body += "<button type=\"submit\" name=\"action\" value=\"add-option:" + name + "\">增加选项</button>"
    elif item.kind == "判断":
        for choice in ("正确", "错误"):
            checked = " checked" if choice in item.selected else ""
            body += (
                "<input type=\"radio\" name=\"selected-" + name + "\" value=\""
                + choice + "\"" + checked + ">" + choice
            )
    else:
        body += (
            "<input type=\"text\" name=\"requirements-" + name + "\" value=\""
            + escape(item.requirements) + "\">"
        )
        body += "<input type=\"text\" name=\"answer-" + name + "\" value=\"" + escape(item.answer) + "\">"
    body += "<input type=\"text\" name=\"explanation-" + name + "\" value=\"" + escape(item.explanation) + "\">"
    body += "<button type=\"submit\" name=\"action\" value=\"delete:" + name + "\">删除题目</button>"
    if index > 0:
        body += "<button type=\"submit\" name=\"action\" value=\"up:" + name + "\">上移</button>"
    if index < count - 1:
        body += "<button type=\"submit\" name=\"action\" value=\"down:" + name + "\">下移</button>"
    return body + "</section>"


def _read_only(question) -> str:
    if isinstance(question, ChoiceQuestion):
        kind = question.selection.value
        prompt = question.prompt
        options = question.choices
        requirements = ""
        answer = "、".join(question.answer)
        explanation = question.explanation
    elif isinstance(question, TrueFalseQuestion):
        kind = "判断"
        prompt = question.prompt
        options = ("正确", "错误")
        requirements = ""
        answer = question.answer
        explanation = question.explanation
    elif isinstance(question, OpenQuestion):
        kind = "综合"
        prompt = question.prompt
        options = ()
        requirements = question.requirements
        answer = question.answer
        explanation = question.explanation
    else:
        raise TypeError("unknown question")
    body = "<section><p>" + escape(kind) + "</p><p>" + escape(prompt) + "</p>"
    if kind == "综合":
        body += "<p>" + escape(requirements) + "</p>"
    for option in options:
        body += "<p>" + escape(option) + "</p>"
    return body + "<p>参考答案：" + escape(answer) + "</p><p>解析：" + escape(explanation) + "</p></section>"


def response_for(page: TeacherPage, method: str, path: str, body: str) -> PageResponse:
    parts = [unquote(part) for part in urlsplit(path).path.split("/") if part]
    if method == "GET" and parts == []:
        return _html(page.list_tasks())
    if method == "POST" and parts == ["tasks"]:
        return _html(page.create_task())
    if len(parts) == 2 and parts[0] == "tasks":
        task_id = parts[1]
        if task_id not in page.catalog._tasks:
            return _html(_missing(), 404)
        if method == "GET":
            return _html(page.open_task(task_id))
    return _html(_missing(), 404)
