from dataclasses import dataclass, replace
from html import escape
from urllib.parse import parse_qs, quote, unquote, urlsplit

from scaffolding.generation import LessonOrigin, StageOrigin
from scaffolding.knowledge import KnowledgeBase, LessonRetrieval, LessonSource
from scaffolding.objectives import ObjectiveCatalog, Rejected as ObjectiveRejected
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


class _EmptyExtractor:
    def extract(self, retrieval):
        return ()


class TeacherPage:
    def __init__(self, catalog, prefix: str = "", *, knowledge=None, objectives=None, generation=None) -> None:
        self.catalog = catalog
        self.drafts = {}
        self.prefix = prefix
        self.knowledge = knowledge if knowledge is not None else KnowledgeBase()
        self.objectives = (
            objectives if objectives is not None else ObjectiveCatalog(self.knowledge, _EmptyExtractor())
        )
        self.generation = generation

    def list_tasks(self) -> str:
        items = []
        for task in self.catalog._tasks.values():
            href = _with_prefix(self.prefix, "/tasks/" + quote(task.task_id, safe=""))
            items.append(
                "<li><a href=\"" + href + "\">" + escape(task.task_id)
                + "</a> " + escape(_fact(task)) + "</li>"
            )
        body = (
            "<h1>任务列表</h1><form method=\"post\" action=\""
            + _with_prefix(self.prefix, "/tasks") + "\">"
            + "<button type=\"submit\">新建</button></form>"
            + "<a href=\"" + _with_prefix(self.prefix, "/objectives") + "\">目标</a><ul>"
            + "".join(items) + "</ul>"
        )
        return _document(body)

    def open_objectives(self, message: str = "") -> str:
        return _render_objectives(self, None, message)

    def apply_objectives(self, fields, action: str) -> str:
        if action not in ("查看", "提炼", "修改", "删除"):
            return self.open_objectives()
        query = _objective_query(fields)
        if query is None:
            return self.open_objectives("先填完整再查询")
        if action == "提炼":
            return _extract_objectives(self, query)
        if action == "修改":
            return _edit_objective(self, query, fields)
        if action == "删除":
            return _delete_objective(self, query, fields)
        return _render_objectives(self, query, "")

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
            return self.list_tasks()
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


def _filled(value: str) -> bool:
    return value.strip() != ""


def _objective_query(fields):
    mode = fields.get("mode", [""])[-1]
    if mode == "课时":
        version = fields.get("version", [""])[-1]
        volume = fields.get("volume", [""])[-1]
        lesson = fields.get("lesson", [""])[-1]
        if not all(_filled(value) for value in (version, volume, lesson)):
            return None
        return ("课时", version, volume, lesson)
    if mode == "学段":
        stage = fields.get("stage", [""])[-1]
        if not _filled(stage):
            return None
        return ("学段", stage)
    return None


def _retrieve(page, query):
    if query[0] == "课时":
        return page.knowledge.retrieve_lesson(query[1], query[2], query[3])
    return page.knowledge.retrieve_stage(query[1])


def _saved(page, query):
    if query[0] == "课时":
        return page.objectives.lesson_objectives(query[1], query[2], query[3])
    return page.objectives.stage_objectives(query[1])


def _source_text(source) -> str:
    if isinstance(source, LessonSource):
        return (
            "版本：" + source.version
            + " 册次：" + source.volume
            + " 课时：" + source.lesson
            + " 学段：" + source.stage
            + " 页码：" + source.pages
        )
    return (
        "名称：" + source.name
        + " 学段：" + source.stage
        + " 条款号：" + source.clauses
        + " 现行"
    )


def _query_fields(query):
    version = volume = lesson = stage = ""
    mode = "" if query is None else query[0]
    if query is not None and query[0] == "课时":
        version, volume, lesson = query[1], query[2], query[3]
    if query is not None and query[0] == "学段":
        stage = query[1]
    checked_lesson = " checked" if mode == "课时" else ""
    checked_stage = " checked" if mode == "学段" else ""
    return mode, version, volume, lesson, stage, checked_lesson, checked_stage


def _query_form(page, query, offer_extract: bool) -> str:
    _mode, version, volume, lesson, stage, checked_lesson, checked_stage = _query_fields(query)
    action = _with_prefix(page.prefix, "/objectives")
    body = (
        "<form method=\"post\" action=\"" + action + "\">"
        + "<label><input type=\"radio\" name=\"mode\" value=\"课时\"" + checked_lesson + ">课时</label>"
        + "<label><input type=\"radio\" name=\"mode\" value=\"学段\"" + checked_stage + ">学段</label>"
        + "<input name=\"version\" value=\"" + escape(version) + "\">"
        + "<input name=\"volume\" value=\"" + escape(volume) + "\">"
        + "<input name=\"lesson\" value=\"" + escape(lesson) + "\">"
        + "<input name=\"stage\" value=\"" + escape(stage) + "\">"
        + "<button type=\"submit\" name=\"action\" value=\"查看\">查看</button>"
    )
    if offer_extract:
        body += "<button type=\"submit\" name=\"action\" value=\"提炼\">提炼</button>"
    return (
        body
        + "</form><a href=\""
        + _with_prefix(page.prefix, "/generation")
        + "\">生成</a>"
    )


def _retrieval_html(retrieval) -> str:
    if isinstance(retrieval, LessonRetrieval):
        return (
            "<section><h2>课时原文</h2><p>" + escape(retrieval.lesson_text) + "</p>"
            + "<p>教材来源：" + escape(_source_text(retrieval.lesson_source)) + "</p>"
            + "<h2>课标全文</h2><p>" + escape(retrieval.standard_text) + "</p>"
            + "<p>课标来源：" + escape(_source_text(retrieval.standard_source)) + "</p></section>"
        )
    if retrieval is None:
        return ""
    return (
        "<section><h2>课标全文</h2><p>" + escape(retrieval.standard_text) + "</p>"
        + "<p>课标来源：" + escape(_source_text(retrieval.standard_source)) + "</p></section>"
    )


def _render_objectives(page, query, message: str) -> str:
    retrieval = None if query is None else _retrieve(page, query)
    objectives = () if query is None else _saved(page, query)
    if retrieval is None and query is not None and message == "":
        message = "没有检索到资料"
    parts = ["<h1>目标</h1>"]
    if message:
        parts.append("<p>" + escape(message) + "</p>")
    parts.append(_query_form(page, query, offer_extract=query is not None and objectives == ()))
    parts.append(_retrieval_html(retrieval))
    action = _with_prefix(page.prefix, "/objectives")
    for item in objectives:
        hidden = "" if query is None else _hidden_query(query)
        parts.append(
            "<article><p>" + escape(item.objective_id) + "</p><p>"
            + escape(item.dimension) + "</p><p>" + escape(item.statement) + "</p><p>"
            + escape(_source_text(item.source)) + "</p>"
            + "<form method=\"post\" action=\"" + action + "\">" + hidden
            + "<input type=\"hidden\" name=\"objective\" value=\"" + escape(item.objective_id) + "\">"
            + "<input name=\"statement\" value=\"" + escape(item.statement) + "\">"
            + "<button type=\"submit\" name=\"action\" value=\"修改\">修改表述</button></form>"
            + "<form method=\"post\" action=\"" + action + "\">" + hidden
            + "<input type=\"hidden\" name=\"objective\" value=\"" + escape(item.objective_id) + "\">"
            + "<button type=\"submit\" name=\"action\" value=\"删除\">删除</button></form></article>"
        )
    parts.append(_task_links(page, query))
    return _document("".join(parts))


def _hidden_query(query) -> str:
    mode, version, volume, lesson, stage, _checked_lesson, _checked_stage = _query_fields(query)
    return (
        "<input type=\"hidden\" name=\"mode\" value=\"" + escape(mode) + "\">"
        + "<input type=\"hidden\" name=\"version\" value=\"" + escape(version) + "\">"
        + "<input type=\"hidden\" name=\"volume\" value=\"" + escape(volume) + "\">"
        + "<input type=\"hidden\" name=\"lesson\" value=\"" + escape(lesson) + "\">"
        + "<input type=\"hidden\" name=\"stage\" value=\"" + escape(stage) + "\">"
    )


def _edit_objective(page, query, fields) -> str:
    objective_id = fields.get("objective", [""])[-1]
    statement = fields.get("statement", [""])[-1]
    current = _saved(page, query)
    if objective_id not in {item.objective_id for item in current}:
        return _render_objectives(page, query, "目标不存在")
    if not _filled(statement):
        return _render_objectives(page, query, "表述不能为空")
    try:
        page.objectives.edit_statement(objective_id, statement)
    except ObjectiveRejected:
        return _render_objectives(page, query, "目标不存在")
    return _render_objectives(page, query, "")


def _delete_objective(page, query, fields) -> str:
    objective_id = fields.get("objective", [""])[-1]
    current = _saved(page, query)
    if objective_id not in {item.objective_id for item in current}:
        return _render_objectives(page, query, "目标不存在")
    try:
        page.objectives.delete(objective_id)
    except ObjectiveRejected:
        return _render_objectives(page, query, "目标不存在")
    return _render_objectives(page, query, "")


def _extract_objectives(page, query) -> str:
    if _saved(page, query) != ():
        return _render_objectives(page, query, "已有目标，不能再次提炼")
    if _retrieve(page, query) is None:
        return _render_objectives(page, query, "没有检索到资料")
    try:
        if query[0] == "课时":
            saved = page.objectives.extract_lesson(query[1], query[2], query[3])
        else:
            saved = page.objectives.extract_stage(query[1])
    except ObjectiveRejected:
        if _saved(page, query) != ():
            return _render_objectives(page, query, "已有目标，不能再次提炼")
        return _render_objectives(page, query, "提炼失败，没有保存目标")
    except Exception:
        return _render_objectives(page, query, "提炼失败，没有保存目标")
    if saved == ():
        return _render_objectives(page, query, "没有留下可保存的目标")
    return _render_objectives(page, query, "")


def _task_links(page, query) -> str:
    if page.generation is None or query is None:
        return ""
    items = []
    for task in page.catalog._tasks.values():
        origin = page.generation.origin(task.task_id)
        matched = False
        if query[0] == "课时":
            matched = origin == LessonOrigin(query[1], query[2], query[3])
        elif query[0] == "学段":
            matched = origin == StageOrigin(query[1])
        if not matched:
            continue
        href = _with_prefix(page.prefix, "/tasks/" + quote(task.task_id, safe=""))
        items.append("<li><a href=\"" + href + "\">" + escape(task.task_id) + "</a></li>")
    if items == []:
        return ""
    return "<ul>" + "".join(items) + "</ul>"


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
        if method == "POST":
            fields = parse_qs(body, keep_blank_values=True)
            action = fields.get("action", [""])[-1]
            return _html(page.apply(task_id, fields, action))
    if parts == ["objectives"] and method == "GET":
        return _html(page.open_objectives())
    if parts == ["objectives"] and method == "POST":
        fields = parse_qs(body, keep_blank_values=True)
        action = fields.get("action", [""])[-1]
        return _html(page.apply_objectives(fields, action))
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
