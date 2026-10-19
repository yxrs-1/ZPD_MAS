import json

from scaffolding.agents import ScaffoldDraft
from scaffolding.records import ChoiceQuestion, ItemAnswer, OpenQuestion, TrueFalseQuestion


class Rejected(Exception):
    pass


_KEYS = {"文字", "HTML"}


def parse_scaffold(text: str) -> ScaffoldDraft:
    if type(text) is not str:
        raise Rejected("model reply is not the scaffold JSON")
    try:
        body = json.loads(text.strip())
    except json.JSONDecodeError as error:
        raise Rejected("model reply is not the scaffold JSON") from error
    if not isinstance(body, dict) or set(body) != _KEYS:
        raise Rejected("model reply is not the scaffold JSON")
    if type(body["文字"]) is not str or type(body["HTML"]) is not str:
        raise Rejected("model reply is not the scaffold JSON")
    return ScaffoldDraft(text=body["文字"], html=body["HTML"])


_SYSTEM = (
    "只回一份 JSON 对象，不要代码块，不要其他文字。\n"
    "顶层只有「文字」和「HTML」。两个值都是字符串，可以是空字符串。\n"
    "HTML 里只放四类素材，写成 <asset kind=\"…\" name=\"…\">…</asset>。\n"
    "kind 是图片素材、思维导图、结构图、微格动画之一，name 是文件名。\n"
    "支架的文字和 HTML 不要写出参考答案，也不要写出学情。"
)


def build_messages(scaffold_type: str, question: str, questions: tuple, answers: tuple) -> tuple[dict[str, str], dict[str, str]]:
    blocks = [
        _block(number, item, answer)
        for number, (item, answer) in enumerate(zip(questions, answers, strict=True), start=1)
    ]
    content = "\n\n".join(blocks) + "\n\n支架类型：" + scaffold_type + "\n这次提问：" + question
    return ({"role": "system", "content": _SYSTEM}, {"role": "user", "content": content})


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

    def produce(self, scaffold_type: str, question: str, questions: tuple, answers: tuple) -> ScaffoldDraft:
        return parse_scaffold(self._complete(build_messages(scaffold_type, question, questions, answers)))
