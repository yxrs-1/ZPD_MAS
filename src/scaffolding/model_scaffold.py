import json
from contextvars import ContextVar

from scaffolding.agents import ScaffoldDraft
from scaffolding.model_trace import remember_model_result, tracing_model_call
from scaffolding.records import ChoiceQuestion, ItemAnswer, OpenQuestion, TrueFalseQuestion
from scaffolding.scaffold_figures import kind_for


class Rejected(Exception):
    pass


_KEYS = {"文字", "源码"}


class _ScaffoldProgress:
    def __init__(self, on_text) -> None:
        self.on_text = on_text
        self.shown = ""


_progress: ContextVar[_ScaffoldProgress | None] = ContextVar("scaffold_progress", default=None)


def begin_scaffold_progress(on_text):
    return _progress.set(_ScaffoldProgress(on_text))


def end_scaffold_progress(token) -> None:
    _progress.reset(token)


def clear_scaffold_progress() -> None:
    progress = _progress.get()
    if progress is None:
        return
    progress.shown = ""


def scaffold_listening() -> bool:
    return _progress.get() is not None


def partial_scaffold_text(raw: str) -> str:
    key = '"文字"'
    at = raw.find(key)
    if at < 0:
        return ""
    index = at + len(key)
    while index < len(raw) and raw[index] in " \n\r\t":
        index += 1
    if index >= len(raw) or raw[index] != ":":
        return ""
    index += 1
    while index < len(raw) and raw[index] in " \n\r\t":
        index += 1
    if index >= len(raw) or raw[index] != '"':
        return ""
    index += 1
    out = []
    while index < len(raw):
        char = raw[index]
        if char == '"':
            break
        if char == "\\":
            if index + 1 >= len(raw):
                break
            nxt = raw[index + 1]
            mapped = {'"': '"', "\\": "\\", "/": "/", "n": "\n", "r": "\r", "t": "\t"}
            if nxt in mapped:
                out.append(mapped[nxt])
                index += 2
                continue
            if nxt == "u" and index + 6 <= len(raw):
                try:
                    out.append(chr(int(raw[index + 2:index + 6], 16)))
                except ValueError:
                    break
                index += 6
                continue
            break
        out.append(char)
        index += 1
    return "".join(out)


def feed_scaffold_stream(raw: str) -> None:
    progress = _progress.get()
    if progress is None or progress.on_text is None:
        return
    text = partial_scaffold_text(raw)
    if text == progress.shown:
        return
    progress.shown = text
    progress.on_text(text)


def parse_scaffold(text: str) -> ScaffoldDraft:
    if type(text) is not str:
        raise Rejected("model reply is not the scaffold JSON")
    try:
        body = json.loads(text.strip())
    except json.JSONDecodeError as error:
        raise Rejected("model reply is not the scaffold JSON") from error
    if not isinstance(body, dict) or set(body) != _KEYS:
        raise Rejected("model reply is not the scaffold JSON")
    if type(body["文字"]) is not str or type(body["源码"]) is not str:
        raise Rejected("model reply is not the scaffold JSON")
    return ScaffoldDraft(text=body["文字"], source=body["源码"])


_FORBIDDEN = ("学生", "教师", "引导", "让学生", "请学生", "学情")


def _teacher_voice(text: str) -> bool:
    return any(word in text for word in _FORBIDDEN)


_SYSTEM = (
    "只回一份 JSON 对象，不要代码块，不要其他文字。\n"
    "顶层只有「文字」和「源码」。两个值都是字符串，可以是空字符串。\n"
    "不要写 HTML，不要写文件名。\n"
    "文字写两三句，不要引用题干原句。\n"
    "读者是正在做这道题的学生。用「你」直接对这个人说。\n"
    "文字里不出现：学生、教师、引导、让学生、请学生、学情。\n"
    "支架的文字和源码不要写出参考答案，也不要写出学情。"
)

_FORMAT = {
    "思维导图": "源码是缩进大纲。第一行是根，下一层多两个空格。\n例如：\n网络\n  带宽\n  延迟",
    "结构图": "源码每行是「节点：名称」或「箭头：起点 -> 终点：标签」。\n例如：\n节点：带宽\n节点：延迟\n箭头：带宽 -> 延迟：不同",
    "微格动画": "源码先写结构图，再写「帧：节点名」，至少一帧。\n例如：\n节点：带宽\n节点：延迟\n箭头：带宽 -> 延迟：不同\n帧：带宽\n帧：延迟",
}


def build_messages(
    scaffold_type: str,
    question: str,
    questions: tuple,
    answers: tuple,
    passages: tuple[tuple[str, str], ...] = (),
    example_source: str = "",
) -> tuple[dict[str, str], dict[str, str]]:
    blocks = [
        _block(number, item, answer)
        for number, (item, answer) in enumerate(zip(questions, answers, strict=True), start=1)
    ]
    content = "\n\n".join(blocks) + "\n\n" + _figure_note(scaffold_type, example_source)
    content += "支架类型：" + scaffold_type + "\n这次提问：" + question
    if passages:
        lines = ["匹配片段："]
        for name, chunk in passages:
            lines.append("文件名：" + name)
            lines.append(chunk)
        content += "\n\n" + "\n".join(lines)
    return ({"role": "system", "content": _SYSTEM}, {"role": "user", "content": content})


def _figure_note(scaffold_type: str, example_source: str) -> str:
    kind = kind_for(scaffold_type)
    if kind is None:
        return "素材：无\n源码留空。\n"
    note = "素材：" + kind + "\n" + _FORMAT[kind] + "\n文字的第一句是：先看下面这张图。\n"
    if example_source.strip() != "":
        note += "示例源码：\n" + example_source.rstrip() + "\n"
    return note


def _block(number: int, question, answer: ItemAnswer) -> str:
    if isinstance(question, ChoiceQuestion):
        return _lines(
            number,
            question.selection.value,
            (
                "题干：" + question.prompt,
                "选项：" + "、".join(question.choices),
                "参考答案：" + "、".join(question.answer),
                "解析：" + question.explanation,
                "当前作答：" + "、".join(answer.selected),
                _selected_traces(answer),
            ),
        )
    if isinstance(question, TrueFalseQuestion):
        return _lines(
            number,
            "判断",
            (
                "题干：" + question.prompt,
                "选项：正确、错误",
                "参考答案：" + question.answer,
                "解析：" + question.explanation,
                "当前作答：" + "、".join(answer.selected),
                _selected_traces(answer),
            ),
        )
    if isinstance(question, OpenQuestion):
        return _lines(
            number,
            "综合",
            (
                "题干：" + question.prompt,
                "作答要求：" + question.requirements,
                "参考答案：" + question.answer,
                "解析：" + question.explanation,
                "当前作答：" + answer.text,
                _text_traces(answer),
            ),
        )
    raise TypeError("unknown question")


def _lines(number: int, kind: str, rows: tuple[str, ...]) -> str:
    return "题目" + str(number) + "\n题型：" + kind + "\n" + "\n".join(rows)


def _selected_traces(answer: ItemAnswer) -> str:
    if not answer.selected_revisions:
        return "修改痕迹："
    return "修改痕迹：\n" + "\n".join("、".join(item) for item in answer.selected_revisions)


def _text_traces(answer: ItemAnswer) -> str:
    if not answer.text_revisions:
        return "修改痕迹："
    return "修改痕迹：\n" + "\n".join(answer.text_revisions)


class ModelScaffoldAgent:
    def __init__(self, complete) -> None:
        self._complete = complete

    def produce(
        self,
        scaffold_type: str,
        question: str,
        questions: tuple,
        answers: tuple,
        passages: tuple[tuple[str, str], ...] = (),
        example_source: str = "",
    ) -> ScaffoldDraft:
        messages = build_messages(
            scaffold_type,
            question,
            questions,
            answers,
            passages,
            example_source=example_source,
        )
        with tracing_model_call("支架", 支架类型=scaffold_type) as meta:
            text = self._complete(messages)
            if isinstance(text, str):
                remember_model_result(messages, text)
            draft = parse_scaffold(text)
            if _teacher_voice(draft.text):
                clear_scaffold_progress()
                follow = (
                    messages[0],
                    messages[1],
                    {
                        "role": "user",
                        "content": "上一稿是在对教师说话，按规则改成直接对学生说的话。\n上一稿："
                        + draft.text,
                    },
                )
                text = self._complete(follow)
                if isinstance(text, str):
                    remember_model_result(follow, text)
                draft = parse_scaffold(text)
            meta["支架正文"] = draft.text
            return draft
