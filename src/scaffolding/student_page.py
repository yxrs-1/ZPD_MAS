from dataclasses import dataclass
from html import escape
from urllib.parse import parse_qs, quote, unquote, urlsplit

from scaffolding.records import ChoiceQuestion, HelpSource, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.session import Session
from scaffolding.tasks import display_status


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

    def open_task(self, task_id: str, now: float) -> str:
        if not _published(self, task_id):
            return _missing()
        session = self._ensure_session(task_id)
        if session is None:
            return _render_work(self, task_id)
        self._note_shown(session, task_id, now)
        return _render_session(session)

    def edit_answer(self, task_id: str, index: int, *, text: str | None = None, selected: tuple[str, ...] | None = None, now: float) -> str:
        if not _published(self, task_id):
            return _missing()
        session = self._ensure_session(task_id)
        if session is None:
            return _render_work(self, task_id)
        self._note_shown(session, task_id, now)
        try:
            session.edit_answer(index, text=text, selected=selected)
        except Exception:
            pass
        return _render_session(session)

    def ask(self, task_id: str, question: str, source: str, now: float) -> str:
        if not _published(self, task_id):
            return _missing()
        session = self._ensure_session(task_id)
        if session is None:
            return _render_work(self, task_id)
        self._note_shown(session, task_id, now)
        if source in (HelpSource.PRESET.value, HelpSource.OWN.value):
            try:
                session.ask(question, HelpSource(source))
            except Exception:
                pass
        return _render_session(session)

    def submit(self, task_id: str, now: float) -> str:
        if not _published(self, task_id):
            return _missing()
        session = self._ensure_session(task_id)
        if session is None:
            return _render_work(self, task_id)
        self._note_shown(session, task_id, now)
        try:
            session.submit()
        except Exception:
            pass
        return _render_session(session)

    def asset(self, task_id: str, filename: str) -> tuple[str, bytes] | None:
        session = self.sessions.get(task_id)
        if session is None:
            return None
        scaffold = session.view().scaffold
        if scaffold is None:
            return None
        for asset in scaffold.assets:
            if asset.filename == filename:
                return asset.filename, asset.content
        return None

    def _ensure_session(self, task_id: str):
        if task_id in self.sessions:
            return self.sessions[task_id]
        task = self.catalog.get(task_id)
        if not task.started:
            self.catalog.start(task_id)
        try:
            session = Session(self.catalog, self.catalog.work(task_id), self.decision, self.scaffold_agent)
        except Exception:
            return None
        self.sessions[task_id] = session
        return session

    def _note_shown(self, session, task_id: str, now: float) -> None:
        if task_id not in self.shown_at:
            self.shown_at[task_id] = now


def _document(body: str) -> str:
    return "<!DOCTYPE html><html lang=\"zh\"><body>" + body + "</body></html>"


def _missing() -> str:
    return _document("<h1>任务不存在</h1>")


def _html_response(text: str, status: int = 200) -> PageResponse:
    return PageResponse(status, "text/html; charset=utf-8", text.encode())


def _published(page: StudentPage, task_id: str) -> bool:
    try:
        task = page.catalog.get(task_id)
    except KeyError:
        return False
    return task.published


def _render_work(page: StudentPage, task_id: str) -> str:
    task = page.catalog.get(task_id)
    work = page.catalog.work(task_id)
    return _page(
        task_id,
        display_status(task),
        work.questions,
        work.answers,
        (),
        dialogue=work.dialogue,
    )


def _render_session(session: Session) -> str:
    view = session.view()
    return _page(
        session.work.task_id,
        view.status,
        session.work.questions,
        session.work.answers,
        view.presets,
        scaffold=view.scaffold,
        dialogue=view.dialogue,
    )


def _page(task_id, status, questions, answers, presets, scaffold=None, dialogue=()) -> str:
    parts = ["<h1>" + escape(task_id) + "</h1><p>" + escape(status) + "</p>"]
    action = "/tasks/" + quote(task_id, safe="") + "/answers"
    parts.append("<form method=\"post\" action=\"" + action + "\">")
    for index, question in enumerate(questions):
        parts.append(_question(index, question, answers[index], locked=False))
    parts.append("<button type=\"submit\">保存作答</button></form>")
    if presets:
        parts.append("<h2>预设提问</h2><ul>")
        for preset in presets:
            parts.append("<li>" + _ask_form(task_id, preset, HelpSource.PRESET.value) + "</li>")
        parts.append("</ul>")
    parts.append(_ask_form(task_id, "", HelpSource.OWN.value, own=True))
    submit_action = "/tasks/" + quote(task_id, safe="") + "/submit"
    parts.append(
        "<form method=\"post\" action=\"" + submit_action + "\">"
        + "<button type=\"submit\">提交</button></form>"
    )
    if scaffold is not None:
        parts.append("<h2>支架</h2>" + _scaffold_body(task_id, scaffold))
    if dialogue:
        parts.append("<h2>对话</h2>")
        for turn in dialogue:
            parts.append(_turn(task_id, turn))
    return _document("".join(parts))


def _scaffold_body(task_id: str, scaffold) -> str:
    parts = ["<p>" + escape(scaffold.text) + "</p>"]
    for asset in scaffold.assets:
        address = "/tasks/" + quote(task_id, safe="") + "/assets/" + quote(asset.filename, safe="")
        parts.append(
            "<figure><figcaption>" + escape(asset.kind.value) + " " + escape(asset.filename)
            + "</figcaption><img src=\"" + escape(address) + "\" alt=\"" + escape(asset.filename)
            + "\"><a href=\"" + escape(address) + "\" download=\"" + escape(asset.filename)
            + "\">保存</a></figure>"
        )
    return "".join(parts)


def _turn(task_id: str, turn) -> str:
    body = "<h3>" + escape(turn.question) + "</h3>"
    if turn.scaffold is not None:
        body += "<div class=\"turn-scaffold\">" + _scaffold_body(task_id, turn.scaffold) + "</div>"
    return "<article>" + body + "</article>"


def _question(index: int, question, answer, locked: bool) -> str:
    if isinstance(question, ChoiceQuestion):
        kind = question.selection.value
        choices = question.choices
        requirements = ""
        input_type = "radio" if question.selection == SelectionMode.SINGLE else "checkbox"
    elif isinstance(question, TrueFalseQuestion):
        kind = "判断"
        choices = ("正确", "错误")
        requirements = ""
        input_type = "radio"
    elif isinstance(question, OpenQuestion):
        kind = "综合"
        choices = ()
        requirements = question.requirements
        input_type = ""
    else:
        raise TypeError("unknown question")
    disabled = " disabled" if locked else ""
    body = (
        "<section><h2>题目" + str(index + 1) + "</h2><p>" + escape(kind)
        + "</p><p>" + escape(question.prompt) + "</p>"
    )
    if requirements:
        body += "<p>" + escape(requirements) + "</p>"
    if choices:
        for choice in choices:
            checked = " checked" if choice in answer.selected else ""
            body += (
                "<label><input type=\"" + input_type + "\" name=\"selected-" + str(index)
                + "\" value=\"" + escape(choice) + "\"" + checked + disabled + ">"
                + escape(choice) + "</label>"
            )
    else:
        body += (
            "<textarea name=\"text-" + str(index) + "\"" + disabled + ">"
            + escape(answer.text) + "</textarea>"
        )
    return body + "</section>"


def _ask_form(task_id: str, question: str, source: str, own: bool = False) -> str:
    action = "/tasks/" + quote(task_id, safe="") + "/ask"
    if own:
        control = "<input type=\"text\" name=\"question\" value=\"\">"
        label = "<button type=\"submit\">提问</button>"
    else:
        control = "<input type=\"hidden\" name=\"question\" value=\"" + escape(question) + "\">"
        label = "<button type=\"submit\">" + escape(question) + "</button>"
    return (
        "<form method=\"post\" action=\"" + action + "\">" + control
        + "<input type=\"hidden\" name=\"source\" value=\"" + escape(source) + "\">"
        + label + "</form>"
    )


def response_for(page: StudentPage, method: str, path: str, body: str, now: float) -> PageResponse:
    parts = [unquote(part) for part in urlsplit(path).path.split("/") if part]
    fields = parse_qs(body, keep_blank_values=True)
    if method == "GET" and parts == []:
        return _html_response(page.todo())
    if len(parts) >= 2 and parts[0] == "tasks":
        task_id = parts[1]
        if method == "GET" and len(parts) == 2:
            if not _published(page, task_id):
                return _html_response(_missing(), 404)
            return _html_response(page.open_task(task_id, now))
        if method == "POST" and parts[2:] == ["answers"]:
            if not _published(page, task_id):
                return _html_response(_missing(), 404)
            return _html_response(_post_answers(page, task_id, fields, now))
        if method == "POST" and parts[2:] == ["ask"]:
            if not _published(page, task_id):
                return _html_response(_missing(), 404)
            question = fields.get("question", [""])[-1]
            source = fields.get("source", [""])[-1]
            return _html_response(page.ask(task_id, question, source, now))
        if method == "GET" and len(parts) == 4 and parts[2] == "assets":
            found = page.asset(task_id, parts[3])
            if found is None:
                return PageResponse(404, "application/octet-stream", b"")
            filename, content = found
            return PageResponse(200, "application/octet-stream", content, filename)
    return _html_response(_missing(), 404)


def _post_answers(page: StudentPage, task_id: str, fields: dict, now: float) -> str:
    indexes = []
    for key in fields:
        if key.startswith("selected-") or key.startswith("text-"):
            suffix = key.split("-", 1)[1]
            if suffix.isdigit():
                indexes.append(int(suffix))
    html = None
    for index in sorted(set(indexes)):
        text_key = "text-" + str(index)
        selected_key = "selected-" + str(index)
        if text_key in fields:
            html = page.edit_answer(task_id, index, text=fields[text_key][-1], now=now)
        if selected_key in fields:
            html = page.edit_answer(task_id, index, selected=tuple(fields[selected_key]), now=now)
    if html is None:
        return page.open_task(task_id, now)
    return html
