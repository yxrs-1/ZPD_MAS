from dataclasses import dataclass
from html import escape
from urllib.parse import quote, unquote, urlsplit

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
    return _page(task_id, display_status(task), work.questions, work.answers, ())


def _render_session(session: Session) -> str:
    view = session.view()
    return _page(
        session.work.task_id,
        view.status,
        session.work.questions,
        session.work.answers,
        view.presets,
    )


def _page(task_id, status, questions, answers, presets) -> str:
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
    return _document("".join(parts))


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
    if method == "GET" and parts == []:
        return _html_response(page.todo())
    if method == "GET" and len(parts) == 2 and parts[0] == "tasks":
        if not _published(page, parts[1]):
            return _html_response(_missing(), 404)
        return _html_response(page.open_task(parts[1], now))
    return _html_response(_missing(), 404)
