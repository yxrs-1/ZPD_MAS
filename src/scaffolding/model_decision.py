import json

from scaffolding.records import ChoiceQuestion, ItemAnswer, OpenQuestion, TaskRecord, TrueFalseQuestion


class Rejected(Exception):
    pass


_SCAFFOLD_TYPES = frozenset({"反馈", "提示", "指导", "解释", "示范", "提问"})


def parse_presets(text: str) -> tuple[str, ...]:
    items = _object(text, "预设提问")
    if not isinstance(items, list):
        raise Rejected("model reply is not the decision JSON")
    kept = []
    for item in items:
        if type(item) is not str:
            raise Rejected("model reply is not the decision JSON")
        if item.strip() == "":
            continue
        kept.append(item)
    return tuple(kept)


def parse_scaffold_type(text: str) -> str:
    value = _object(text, "类型")
    if type(value) is not str or value not in _SCAFFOLD_TYPES:
        raise Rejected("model reply is not the decision JSON")
    return value


def _object(text: str, key: str):
    if type(text) is not str:
        raise Rejected("model reply is not the decision JSON")
    try:
        body = json.loads(text.strip())
    except json.JSONDecodeError as error:
        raise Rejected("model reply is not the decision JSON") from error
    if not isinstance(body, dict) or set(body) != {key}:
        raise Rejected("model reply is not the decision JSON")
    return body[key]


_PRESET_SYSTEM = (
    "只回一份 JSON 对象，不要代码块，不要其他文字。\n"
    "顶层只有「预设提问」。它的值是字符串数组，数组可以是空的。\n"
    "每一条都不能为空白。空白不算已填写。\n"
    "不要写出学情。"
)

_TYPE_SYSTEM = (
    "只回一份 JSON 对象，不要代码块，不要其他文字。\n"
    "顶层只有「类型」。它的值是字符串，并且正好是反馈、提示、指导、解释、示范、提问之一。\n"
    "不要写出学情。"
)


def build_preset_messages(record: TaskRecord) -> tuple[dict[str, str], dict[str, str]]:
    return ({"role": "system", "content": _PRESET_SYSTEM}, {"role": "user", "content": _record_text(record)})


def build_type_messages(record: TaskRecord, question: str) -> tuple[dict[str, str], dict[str, str]]:
    content = _record_text(record) + "\n\n这次提问：" + question
    return ({"role": "system", "content": _TYPE_SYSTEM}, {"role": "user", "content": content})


def _record_text(record: TaskRecord) -> str:
    blocks = [
        _block(number, question, answer)
        for number, (question, answer) in enumerate(zip(record.questions, record.answers, strict=True), start=1)
    ]
    helps = "\n".join(event.source.value + "：" + event.text for event in record.behavior.helps)
    return "\n\n".join(blocks) + "\n\n停留时间：" + str(float(record.behavior.dwell_seconds)) + "\n求助：\n" + helps


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
