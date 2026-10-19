import json

from scaffolding.generation import Rejected
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion


_TOP_KEYS = ("单选", "多选", "判断", "综合")
_CHOICE_KEYS = {"题目", "选项", "参考答案", "解析"}
_JUDGED_KEYS = {"题目", "参考答案", "解析"}
_OPEN_KEYS = {"题目", "作答要求", "参考答案", "解析"}


def parse_questions(text: str) -> tuple:
    if not isinstance(text, str):
        raise Rejected("model reply is not the question JSON")
    try:
        body = json.loads(text.strip())
    except json.JSONDecodeError as error:
        raise Rejected("model reply is not the question JSON") from error
    if not isinstance(body, dict) or set(body) != set(_TOP_KEYS):
        raise Rejected("model reply is not the question JSON")
    return (
        *_choices(body["单选"], SelectionMode.SINGLE),
        *_choices(body["多选"], SelectionMode.MULTIPLE),
        *_judged(body["判断"]),
        *_opened(body["综合"]),
    )


def _items(value: object, keys: set[str]) -> list[dict]:
    if not isinstance(value, list):
        raise Rejected("model reply is not the question JSON")
    items = []
    for item in value:
        if not isinstance(item, dict) or set(item) != keys:
            raise Rejected("model reply is not the question JSON")
        items.append(item)
    return items


def _string_list(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, list) or any(type(item) is not str for item in value):
        return None
    return tuple(value)


def _choices(value: object, selection: SelectionMode) -> tuple[ChoiceQuestion, ...]:
    questions = []
    for item in _items(value, _CHOICE_KEYS):
        options = _string_list(item["选项"])
        answers = _string_list(item["参考答案"])
        if (
            options is None
            or answers is None
            or len(options) != 4
            or len(set(options)) != 4
            or any(option.strip() == "" for option in options)
            or type(item["题目"]) is not str
            or type(item["解析"]) is not str
        ):
            raise Rejected("model reply is not the question JSON")
        try:
            questions.append(ChoiceQuestion(item["题目"], selection, options, answers, item["解析"]))
        except ValueError as error:
            raise Rejected("model reply is not the question JSON") from error
    return tuple(questions)


def _judged(value: object) -> tuple[TrueFalseQuestion, ...]:
    questions = []
    for item in _items(value, _JUDGED_KEYS):
        if any(type(item[key]) is not str for key in _JUDGED_KEYS):
            raise Rejected("model reply is not the question JSON")
        try:
            questions.append(TrueFalseQuestion(item["题目"], item["参考答案"], item["解析"]))
        except ValueError as error:
            raise Rejected("model reply is not the question JSON") from error
    return tuple(questions)


def _opened(value: object) -> tuple[OpenQuestion, ...]:
    questions = []
    for item in _items(value, _OPEN_KEYS):
        if any(type(item[key]) is not str for key in _OPEN_KEYS):
            raise Rejected("model reply is not the question JSON")
        try:
            questions.append(OpenQuestion(item["题目"], item["作答要求"], item["参考答案"], item["解析"]))
        except ValueError as error:
            raise Rejected("model reply is not the question JSON") from error
    return tuple(questions)
