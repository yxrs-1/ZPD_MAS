import time
from dataclasses import dataclass
from html import escape
from urllib.parse import parse_qs, quote, unquote, urlsplit

from scaffolding.model_decision import ModelDecisionAgent
from scaffolding.model_generator import deepseek_complete
from scaffolding.model_scaffold import ModelScaffoldAgent
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
    def __init__(self, catalog, decision, scaffold_agent, prefix: str = "") -> None:
        self.catalog = catalog
        self.decision = decision
        self.scaffold_agent = scaffold_agent
        self.sessions = {}
        self.shown_at = {}
        self.prefix = prefix

    def todo(self) -> str:
        items = []
        for listed in self.catalog.student_tasks():
            href = _with_prefix(self.prefix, "/tasks/" + quote(listed.task_id, safe=""))
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
        return _render_session(session, self.prefix)

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
        return _render_session(session, self.prefix)

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
        return _render_session(session, self.prefix)

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
        return _render_session(session, self.prefix)

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

    def turn_asset(self, task_id: str, index: int, filename: str) -> tuple[str, bytes] | None:
        session = self.sessions.get(task_id)
        if session is None:
            return None
        dialogue = session.view().dialogue
        if index < 0 or index >= len(dialogue):
            return None
        scaffold = dialogue[index].scaffold
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
        shown = self.shown_at.get(task_id)
        if shown is None:
            self.shown_at[task_id] = now
            return
        elapsed = now - shown
        if elapsed > 0:
            session.note_dwell(session.work.behavior.dwell_seconds + elapsed)
            self.shown_at[task_id] = now


def _document(body: str) -> str:
    return "<!DOCTYPE html><html lang=\"zh\"><body>" + body + "</body></html>"


def _missing() -> str:
    return _document("<h1>任务不存在</h1>")


def _html_response(text: str, status: int = 200) -> PageResponse:
    return PageResponse(status, "text/html; charset=utf-8", text.encode())


def _asset_response(found: tuple[str, bytes] | None) -> PageResponse:
    if found is None:
        return PageResponse(404, "application/octet-stream", b"")
    filename, content = found
    return PageResponse(200, "application/octet-stream", content, filename)


def _published(page: StudentPage, task_id: str) -> bool:
    try:
        task = page.catalog.get(task_id)
    except KeyError:
        return False
    return task.published


def _with_prefix(prefix: str, path: str) -> str:
    return prefix + path


def _render_work(page: StudentPage, task_id: str) -> str:
    task = page.catalog.get(task_id)
    work = page.catalog.work(task_id)
    return _page(
        task_id,
        page.prefix,
        display_status(task),
        work.questions,
        work.answers,
        (),
        dialogue=work.dialogue,
    )


def _render_session(session: Session, prefix: str) -> str:
    view = session.view()
    return _page(
        session.work.task_id,
        prefix,
        view.status,
        session.work.questions,
        session.work.answers,
        view.presets,
        locked=view.answers_locked,
        revealed=view.revealed,
        scaffold=view.scaffold,
        dialogue=view.dialogue,
        send_closed=view.send_closed,
    )


def _page(
    task_id,
    prefix,
    status,
    questions,
    answers,
    presets,
    locked=False,
    revealed=(),
    scaffold=None,
    dialogue=(),
    send_closed=False,
) -> str:
    parts = ["<h1>" + escape(task_id) + "</h1><p>" + escape(status) + "</p>"]
    action = _with_prefix(prefix, "/tasks/" + quote(task_id, safe="") + "/answers")
    parts.append("<form method=\"post\" action=\"" + action + "\">")
    for index, question in enumerate(questions):
        item = revealed[index] if revealed else None
        parts.append(_question(index, question, answers[index], locked, item))
    if not locked:
        parts.append("<button type=\"submit\">保存作答</button>")
    parts.append("</form>")
    if not send_closed:
        if presets:
            parts.append("<h2>预设提问</h2><ul>")
            for preset in presets:
                parts.append("<li>" + _ask_form(task_id, preset, HelpSource.PRESET.value, prefix) + "</li>")
            parts.append("</ul>")
        parts.append(_ask_form(task_id, "", HelpSource.OWN.value, prefix, own=True))
        submit_action = _with_prefix(prefix, "/tasks/" + quote(task_id, safe="") + "/submit")
        parts.append(
            "<form method=\"post\" action=\"" + submit_action + "\">"
            + "<button type=\"submit\">提交</button></form>"
        )
    if scaffold is not None:
        current = _with_prefix(prefix, "/tasks/" + quote(task_id, safe="") + "/assets/")
        parts.append("<h2>支架</h2>" + _scaffold_body(scaffold, current))
    if dialogue:
        parts.append("<h2>对话</h2>")
        for index, turn in enumerate(dialogue):
            parts.append(_turn(task_id, index, turn, prefix))
    return _document("".join(parts))


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


def _turn(task_id: str, index: int, turn, prefix: str) -> str:
    body = "<h3>" + escape(turn.question) + "</h3>"
    if turn.scaffold is not None:
        address = _with_prefix(prefix, "/tasks/" + quote(task_id, safe="") + "/turns/" + str(index) + "/assets/")
        body += "<div class=\"turn-scaffold\">" + _scaffold_body(turn.scaffold, address) + "</div>"
    return "<article>" + body + "</article>"


def _question(index: int, question, answer, locked: bool, revealed=None) -> str:
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
    if revealed is not None:
        shown = revealed.answer if isinstance(revealed.answer, str) else "、".join(revealed.answer)
        body += "<p>参考答案：" + escape(shown) + "</p><p>解析：" + escape(revealed.explanation) + "</p>"
    return body + "</section>"


def _ask_form(task_id: str, question: str, source: str, prefix: str, own: bool = False) -> str:
    action = _with_prefix(prefix, "/tasks/" + quote(task_id, safe="") + "/ask")
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
        if method == "POST" and parts[2:] == ["submit"]:
            if not _published(page, task_id):
                return _html_response(_missing(), 404)
            return _html_response(page.submit(task_id, now))
        if method == "GET" and len(parts) == 4 and parts[2] == "assets":
            found = page.asset(task_id, parts[3])
            return _asset_response(found)
        if method == "GET" and len(parts) == 6 and parts[2] == "turns" and parts[4] == "assets":
            index = int(parts[3]) if parts[3].isdigit() else -1
            found = page.turn_asset(task_id, index, parts[5])
            return _asset_response(found)
    return _html_response(_missing(), 404)


def _current_selected(page: StudentPage, task_id: str, index: int) -> tuple[str, ...]:
    session = page.sessions.get(task_id)
    if session is not None:
        return session.work.answers[index].selected
    if not page.catalog.get(task_id).started:
        return ()
    return page.catalog.work(task_id).answers[index].selected


def _post_answers(page: StudentPage, task_id: str, fields: dict, now: float) -> str:
    html = None
    for index, question in enumerate(page.catalog.get(task_id).questions):
        text_key = "text-" + str(index)
        selected_key = "selected-" + str(index)
        if isinstance(question, (ChoiceQuestion, TrueFalseQuestion)) and selected_key not in fields:
            if _current_selected(page, task_id, index) != ():
                html = page.edit_answer(task_id, index, selected=(), now=now)
        if text_key in fields:
            html = page.edit_answer(task_id, index, text=fields[text_key][-1], now=now)
        if selected_key in fields:
            html = page.edit_answer(task_id, index, selected=tuple(fields[selected_key]), now=now)
    if html is None:
        return page.open_task(task_id, now)
    return html


def production_page(catalog, *, post, api_key=None) -> StudentPage:
    def complete(messages):
        return deepseek_complete(messages, post=post, api_key=api_key)
    return StudentPage(catalog, ModelDecisionAgent(complete), ModelScaffoldAgent(complete))


def serve(page: StudentPage, port: int) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._respond()

        def do_POST(self) -> None:
            self._respond()

        def _respond(self) -> None:
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length).decode("utf-8")
            response = response_for(page, self.command, self.path, raw, time.monotonic())
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            if response.filename:
                encoded = quote(response.filename, safe="")
                self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + encoded)
            self.send_header("Content-Length", str(len(response.body)))
            self.end_headers()
            self.wfile.write(response.body)

        def log_message(self, *args) -> None:
            return

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
