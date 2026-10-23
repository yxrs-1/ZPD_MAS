from dataclasses import dataclass, replace
from html import escape
from urllib.parse import parse_qs, quote, unquote, urlsplit

from scaffolding.documents import (
    DocumentError,
    DocumentLibrary,
    DraftError,
    draft_objectives,
    format_objectives,
    parse_objective_text,
)
from scaffolding.knowledge import KnowledgeBase
from scaffolding.objectives import ObjectiveCatalog
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.roster import RosterError


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
    set_cookie: str = ""


class _EmptyExtractor:
    def extract(self, retrieval):
        return ()


class TeacherPage:
    def __init__(
        self,
        catalog,
        prefix: str = "",
        roster=None,
        *,
        knowledge=None,
        objectives=None,
        generation=None,
        classwork=None,
        library=None,
        complete=None,
    ) -> None:
        self.catalog = catalog
        self.drafts = {}
        self.prefix = prefix
        self.roster = roster
        self.classwork = classwork
        self.knowledge = knowledge if knowledge is not None else KnowledgeBase()
        self.objectives = (
            objectives if objectives is not None else ObjectiveCatalog(self.knowledge, _EmptyExtractor())
        )
        self.generation = generation
        self.library = library if library is not None else DocumentLibrary()
        self.complete = complete

    def list_tasks(self, message: str = "") -> str:
        return _render_list(self, message)

    def open_objectives(self, message: str = "", text: str = "", objectives: str = "") -> str:
        return _render_library(self, message, text, objectives)

    def apply_objectives(self, fields, action: str, uploads=None, filenames=None) -> str:
        if action == "上传":
            return _upload_document(self, uploads or {}, filenames or {})
        if action == "删除":
            return _delete_document(self, fields.get("doc_id", [""])[-1])
        if action == "生成目标":
            return _draft_on_page(self, fields.get("text", [""])[-1])
        if action == "确认":
            return _confirm_on_page(self, fields.get("text", [""])[-1], fields.get("objectives", [""])[-1])
        return self.open_objectives()

    def create_task(self) -> str:
        task = self.catalog.create(())
        return _render(self, task.task_id)

    def open_task(self, task_id: str) -> str:
        if task_id not in self.catalog._tasks:
            return _missing()
        return _render(self, task_id)

    def open_generation(self, message: str = "", text: str = "") -> str:
        action = _with_prefix(self.prefix, "/generation")
        body = "<h1>生成</h1>"
        if message:
            body += "<p>" + escape(message) + "</p>"
        body += (
            "<form method=\"post\" action=\"" + action + "\">"
            + "<textarea name=\"text\">" + escape(text) + "</textarea>"
            + "<button type=\"submit\">生成</button></form>"
        )
        return _document(body)

    def apply_generation(self, text: str) -> str:
        if text.strip() == "" or self.generation is None:
            return self.open_generation("生成失败，没有创建任务", text)
        try:
            task = self.generation.generate_from_text(text)
        except Exception:
            return self.open_generation("生成失败，没有创建任务", text)
        return _render(self, task.task_id)

    def apply(self, task_id: str, fields: dict, action: str) -> str:
        if task_id not in self.catalog._tasks:
            return _missing()
        task = self.catalog.get(task_id)
        if action == "delete":
            self.drafts.pop(task_id, None)
            self.catalog.delete(task_id)
            if self.classwork is not None:
                self.classwork.drop_task(task_id)
            return self.list_tasks()
        if action == "布置" and self.classwork is not None:
            class_ids = tuple(fields.get("class_id", ()))
            try:
                self.classwork.assign(self.catalog, task_id, class_ids)
            except RosterError as error:
                return _render(self, task_id, str(error))
            return _render(self, task_id)
        if task.started:
            return _render(self, task_id, "学生已开始，只能删除")
        if action == "abandon":
            self.drafts.pop(task_id, None)
            return _render(self, task_id)
        if action == "publish":
            if task_id in self.drafts:
                return _render(self, task_id, "先保存再发布")
            if task.questions == ():
                return _render(self, task_id, "没有题目，不能发布")
            self.catalog.publish(task_id)
            return _render(self, task_id)
        self.drafts[task_id] = _apply_action(_draft_from_fields(fields), action)
        if action == "save":
            return _save(self, task_id)
        return _render(self, task_id)


def _with_prefix(prefix: str, path: str) -> str:
    return prefix + path


def _render_list(page: TeacherPage, message: str = "") -> str:
    items = []
    for task in page.catalog._tasks.values():
        href = _with_prefix(page.prefix, "/tasks/" + quote(task.task_id, safe=""))
        items.append(
            "<li><a href=\"" + href + "\">" + escape(task.task_id)
            + "</a> " + escape(_fact(task)) + "</li>"
        )
    extra = ""
    if page.roster is not None:
        action = page.prefix if page.prefix else "/"
        extra = (
            "<a href=\"" + _with_prefix(page.prefix, "/classes") + "\">班级</a>"
            + "<form method=\"post\" action=\"" + action + "\">"
            + "<input name=\"old_password\">"
            + "<input name=\"password\">"
            + "<button type=\"submit\" name=\"action\" value=\"修改密码\">修改密码</button></form>"
            + "<form method=\"post\" action=\"" + action + "\">"
            + "<button type=\"submit\" name=\"action\" value=\"退出\">退出</button></form>"
        )
    notice = ""
    if message:
        notice = "<p>" + escape(message) + "</p>"
    body = (
        "<h1>任务列表</h1>" + notice
        + "<form method=\"post\" action=\""
        + _with_prefix(page.prefix, "/tasks") + "\">"
        + "<button type=\"submit\">新建</button></form>"
        + "<a href=\"" + _with_prefix(page.prefix, "/objectives") + "\">目标</a>"
        + extra
        + "<ul>" + "".join(items) + "</ul>"
    )
    return _document(body)


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
        parts.append(_assignment(page, task_id))
        action = _with_prefix(page.prefix, "/tasks/" + quote(task_id, safe=""))
        parts.append(
            "<form method=\"post\" action=\"" + action + "\">"
            + "<button type=\"submit\" name=\"action\" value=\"delete\">删除</button></form>"
        )
        return _document("".join(parts))
    questions, has_draft = _shown(page, task_id)
    action = _with_prefix(page.prefix, "/tasks/" + quote(task_id, safe=""))
    parts.append("<form method=\"post\" action=\"" + action + "\">")
    parts.append("<button type=\"submit\" name=\"action\" value=\"save\" hidden>保存</button>")
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
    parts.append(_assignment(page, task_id))
    return _document("".join(parts))


def _assignment(page: TeacherPage, task_id: str) -> str:
    if page.classwork is None or page.roster is None:
        return ""
    task = page.catalog.get(task_id)
    if not task.published:
        return ""
    selected = set(page.classwork.assigned(task_id))
    action = _with_prefix(page.prefix, "/tasks/" + quote(task_id, safe=""))
    parts = ["<form method=\"post\" action=\"" + action + "\">"]
    for item in page.roster.classes():
        checked = " checked" if item.class_id in selected else ""
        parts.append(
            "<label><input type=\"checkbox\" name=\"class_id\" value=\""
            + escape(item.class_id) + "\"" + checked + ">"
            + escape(item.name) + "</label>"
        )
    parts.append("<button type=\"submit\" name=\"action\" value=\"布置\">布置</button></form>")
    return "".join(parts)


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
                + "\" value=\"" + str(option_index) + "\"" + checked + ">"
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
        for text in item.selected:
            if text not in item.options:
                body += (
                    "<input type=\"" + input_type + "\" name=\"selected-" + name
                    + "\" value=\"s:" + escape(text) + "\" checked>" + escape(text)
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


def _is_ascii_decimal(token: str) -> bool:
    return token.isascii() and token.isdecimal()


def _choice_token(token: str, options: tuple[str, ...]) -> str:
    if token.startswith("s:"):
        return token[2:]
    if _is_ascii_decimal(token):
        index = int(token)
        if index < len(options):
            return options[index]
    return token


def _draft_from_fields(fields: dict) -> tuple:
    indexes = []
    for key in fields:
        if key.startswith("kind-") and _is_ascii_decimal(key[5:]):
            indexes.append(int(key[5:]))
    items = []
    for index in sorted(set(indexes)):
        kind = fields["kind-" + str(index)][-1]
        if kind not in KINDS:
            continue
        prefix = "option-" + str(index) + "-"
        option_ids = []
        for key in fields:
            if key.startswith(prefix) and _is_ascii_decimal(key[len(prefix):]):
                option_ids.append(int(key[len(prefix):]))
        options = tuple(
            fields["option-" + str(index) + "-" + str(option_id)][-1]
            for option_id in sorted(set(option_ids))
        )
        selected = tuple(fields.get("selected-" + str(index), ()))
        if kind in ("单选", "多选"):
            selected = tuple(_choice_token(token, options) for token in selected)
        items.append(DraftQuestion(
            kind,
            fields.get("prompt-" + str(index), [""])[-1],
            options,
            fields.get("requirements-" + str(index), [""])[-1],
            selected,
            fields.get("answer-" + str(index), [""])[-1],
            fields.get("explanation-" + str(index), [""])[-1],
        ))
    return tuple(items)


def _apply_action(draft: tuple, action: str) -> tuple:
    parts = action.split(":")
    head = parts[0]
    if head == "add" and len(parts) == 2 and parts[1] in KINDS:
        kind = parts[1]
        return draft + (DraftQuestion(kind),)
    if head == "delete" and len(parts) == 2 and parts[1].isdigit():
        index = int(parts[1])
        if 0 <= index < len(draft):
            return draft[:index] + draft[index + 1:]
        return draft
    if head == "up" and len(parts) == 2 and parts[1].isdigit():
        index = int(parts[1])
        if 1 <= index < len(draft):
            items = list(draft)
            items[index - 1], items[index] = items[index], items[index - 1]
            return tuple(items)
        return draft
    if head == "down" and len(parts) == 2 and parts[1].isdigit():
        index = int(parts[1])
        if 0 <= index < len(draft) - 1:
            items = list(draft)
            items[index + 1], items[index] = items[index], items[index + 1]
            return tuple(items)
        return draft
    if head == "add-option" and len(parts) == 2 and parts[1].isdigit():
        return _map_choice(draft, int(parts[1]), lambda question: replace(question, options=question.options + ("",)))
    if head == "delete-option" and len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
        option_index = int(parts[2])

        def remove(question):
            if not 0 <= option_index < len(question.options):
                return question
            return replace(
                question,
                options=question.options[:option_index] + question.options[option_index + 1:],
            )

        return _map_choice(draft, int(parts[1]), remove)
    if head == "up-option" and len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
        option_index = int(parts[2])

        def move_up(question):
            if not 1 <= option_index < len(question.options):
                return question
            items = list(question.options)
            items[option_index - 1], items[option_index] = items[option_index], items[option_index - 1]
            return replace(question, options=tuple(items))

        return _map_choice(draft, int(parts[1]), move_up)
    if head == "down-option" and len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
        option_index = int(parts[2])

        def move_down(question):
            if not 0 <= option_index < len(question.options) - 1:
                return question
            items = list(question.options)
            items[option_index + 1], items[option_index] = items[option_index], items[option_index + 1]
            return replace(question, options=tuple(items))

        return _map_choice(draft, int(parts[1]), move_down)
    return draft


def _save(page: TeacherPage, task_id: str) -> str:
    draft = page.drafts[task_id]
    task = page.catalog.get(task_id)
    if task.published and draft == ():
        return _render(page, task_id, "已发布的任务至少留一题")
    try:
        questions = tuple(_to_question(item) for item in draft)
    except ValueError:
        return _render(page, task_id, "题目不合格，原任务保持不变")
    page.catalog.update(task_id, questions)
    del page.drafts[task_id]
    return _render(page, task_id)


def _to_question(item: DraftQuestion):
    if item.kind == "单选":
        return ChoiceQuestion(item.prompt, SelectionMode.SINGLE, item.options, item.selected, item.explanation)
    if item.kind == "多选":
        return ChoiceQuestion(item.prompt, SelectionMode.MULTIPLE, item.options, item.selected, item.explanation)
    if item.kind == "判断":
        if len(item.selected) != 1:
            raise ValueError("true/false answer")
        return TrueFalseQuestion(item.prompt, item.selected[0], item.explanation)
    if item.kind == "综合":
        return OpenQuestion(item.prompt, item.requirements, item.answer, item.explanation)
    raise ValueError("unknown kind")


def _map_choice(draft: tuple, index: int, change) -> tuple:
    if not 0 <= index < len(draft) or draft[index].kind not in ("单选", "多选"):
        return draft
    items = list(draft)
    items[index] = change(draft[index])
    return tuple(items)


def _render_library(page, message: str, text: str, objectives: str) -> str:
    action = _with_prefix(page.prefix, "/objectives")
    parts = ["<h1>目标</h1>"]
    if message:
        parts.append("<p>" + escape(message) + "</p>")
    if page.library.documents():
        items = []
        for item in page.library.documents():
            items.append(
                "<li>" + escape(item.name)
                + "<form method=\"post\" action=\"" + action + "\">"
                + "<input type=\"hidden\" name=\"action\" value=\"删除\">"
                + "<input type=\"hidden\" name=\"doc_id\" value=\"" + escape(item.doc_id) + "\">"
                + "<button type=\"submit\">删除</button></form></li>"
            )
        parts.append("<ul>" + "".join(items) + "</ul>")
    parts.append(
        "<form method=\"post\" action=\"" + action + "\" enctype=\"multipart/form-data\">"
        + "<input type=\"hidden\" name=\"action\" value=\"上传\">"
        + "<input type=\"file\" name=\"file\">"
        + "<button type=\"submit\">上传</button></form>"
    )
    parts.append(
        "<form method=\"post\" action=\"" + action + "\">"
        + "<textarea name=\"text\">" + escape(text) + "</textarea>"
        + "<button type=\"submit\" name=\"action\" value=\"生成目标\">生成目标</button>"
        + "<a href=\"" + _with_prefix(page.prefix, "/generation") + "\">生成</a></form>"
    )
    if objectives:
        parts.append(
            "<form method=\"post\" action=\"" + action + "\">"
            + "<input type=\"hidden\" name=\"action\" value=\"确认\">"
            + "<input type=\"hidden\" name=\"text\" value=\"" + escape(text) + "\">"
            + "<textarea name=\"objectives\">" + escape(objectives) + "</textarea>"
            + "<button type=\"submit\">确认</button></form>"
        )
    return _document("".join(parts))


def _upload_document(page, uploads: dict, filenames: dict) -> str:
    name = filenames.get("file", "")
    content = uploads.get("file")
    if content is None:
        return page.open_objectives("只接受 docx 或 pdf")
    try:
        page.library.add(name, content)
    except DocumentError as error:
        return page.open_objectives(error.message)
    return page.open_objectives()


def _delete_document(page, doc_id: str) -> str:
    try:
        page.library.delete(doc_id)
    except DocumentError as error:
        return page.open_objectives(error.message)
    return page.open_objectives()


def _draft_on_page(page, text: str) -> str:
    if text.strip() == "":
        return page.open_objectives("先填写需求", text)
    if page.complete is None:
        return page.open_objectives("没有写出目标", text)
    try:
        drafted = draft_objectives(page.complete, page.library.documents(), text)
    except DraftError as error:
        return page.open_objectives(error.message, text)
    return page.open_objectives("", text, format_objectives(drafted))


def _confirm_on_page(page, text: str, objectives: str) -> str:
    if text.strip() == "":
        return page.open_objectives("先填写需求", text, objectives)
    try:
        parsed = parse_objective_text(objectives)
    except DraftError as error:
        return page.open_objectives(error.message, text, objectives)
    if page.generation is None:
        return page.open_objectives("生成失败，没有创建任务", text, objectives)
    try:
        task = page.generation.generate_from_confirmed(text, parsed)
    except Exception:
        return page.open_objectives("生成失败，没有创建任务", text, objectives)
    return _render(page, task.task_id)


def response_for(page: TeacherPage, method: str, path: str, body: str, uploads=None, filenames=None) -> PageResponse:
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
        if method == "POST":
            fields = parse_qs(body, keep_blank_values=True)
            action = fields.get("action", [""])[-1]
            return _html(page.apply(task_id, fields, action))
    if parts == ["objectives"] and method == "GET":
        return _html(page.open_objectives())
    if parts == ["objectives"] and method == "POST":
        fields = parse_qs(body, keep_blank_values=True)
        action = fields.get("action", [""])[-1]
        return _html(page.apply_objectives(fields, action, uploads, filenames))
    if parts == ["generation"] and method == "GET":
        return _html(page.open_generation())
    if parts == ["generation"] and method == "POST":
        fields = parse_qs(body, keep_blank_values=True)
        text = fields.get("text", [""])[-1]
        return _html(page.apply_generation(text))
    return _html(_missing(), 404)


def serve(page: TeacherPage, port: int) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._respond()

        def do_POST(self) -> None:
            self._respond()

        def _respond(self) -> None:
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length).decode("utf-8")
            response = response_for(page, self.command, self.path, raw)
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            self.send_header("Content-Length", str(len(response.body)))
            self.end_headers()
            self.wfile.write(response.body)

        def log_message(self, *args) -> None:
            return

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
