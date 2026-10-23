import json

from scaffolding.generation import Rejected
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion


_KINDS = ("单选", "多选", "判断", "综合")
_DIMENSIONS = frozenset({
    "信息意识",
    "计算思维",
    "数字化学习与创新",
    "信息社会责任",
})
_CHOICE_KEYS = {"题目", "选项", "参考答案", "解析"}
_JUDGED_KEYS = {"题目", "参考答案", "解析"}
_OPEN_KEYS = {"题目", "作答要求", "参考答案", "解析"}


def parse_text_task(reply: str) -> tuple:
    if not isinstance(reply, str):
        raise Rejected("text task reply is not acceptable")
    try:
        loaded = json.loads(reply.strip())
    except json.JSONDecodeError as error:
        raise Rejected("text task reply is not acceptable") from error
    if not isinstance(loaded, dict) or set(loaded) != {"读法", "目标", "题目"}:
        raise Rejected("text task reply is not acceptable")
    counts = _counts(loaded["读法"])
    _objectives(loaded["目标"])
    questions = _questions(loaded["题目"])
    if sum(len(items) for items in questions.values()) == 0:
        raise Rejected("text task reply is not acceptable")
    for kind in _KINDS:
        if counts[kind] is not None and len(questions[kind]) != counts[kind]:
            raise Rejected("text task reply is not acceptable")
    return questions["单选"] + questions["多选"] + questions["判断"] + questions["综合"]


def _counts(reading):
    if type(reading) is str and reading.strip() != "":
        return {kind: None for kind in _KINDS}
    if not isinstance(reading, dict) or set(reading) != set(_KINDS):
        raise Rejected("text task reply is not acceptable")
    counts = {}
    for kind in _KINDS:
        value = reading[kind]
        if type(value) is int and value >= 0:
            counts[kind] = value
        elif value == "未指定":
            counts[kind] = None
        else:
            raise Rejected("text task reply is not acceptable")
    return counts


def _objectives(objectives):
    if not isinstance(objectives, list) or objectives == []:
        raise Rejected("text task reply is not acceptable")
    for item in objectives:
        if not isinstance(item, dict) or set(item) != {"维度", "表述"}:
            raise Rejected("text task reply is not acceptable")
        if type(item["维度"]) is not str or item["维度"] not in _DIMENSIONS:
            raise Rejected("text task reply is not acceptable")
        if type(item["表述"]) is not str or item["表述"].strip() == "":
            raise Rejected("text task reply is not acceptable")


def _questions(questions):
    if not isinstance(questions, dict) or set(questions) != set(_KINDS):
        raise Rejected("text task reply is not acceptable")
    return {
        "单选": _choices(questions["单选"], SelectionMode.SINGLE),
        "多选": _choices(questions["多选"], SelectionMode.MULTIPLE),
        "判断": _judged(questions["判断"]),
        "综合": _opened(questions["综合"]),
    }


def _objects(value, keys):
    if not isinstance(value, list):
        raise Rejected("text task reply is not acceptable")
    items = []
    for item in value:
        if not isinstance(item, dict) or set(item) != keys:
            raise Rejected("text task reply is not acceptable")
        items.append(item)
    return items


def _strings(value):
    if not isinstance(value, list) or any(type(item) is not str for item in value):
        return None
    return tuple(value)


def _choices(value, selection):
    questions = []
    for item in _objects(value, _CHOICE_KEYS):
        options = _strings(item["选项"])
        answers = _strings(item["参考答案"])
        if options is None or answers is None or type(item["题目"]) is not str or type(item["解析"]) is not str:
            raise Rejected("text task reply is not acceptable")
        try:
            questions.append(ChoiceQuestion(
                item["题目"], selection, options, answers, item["解析"]
            ))
        except ValueError as error:
            raise Rejected("text task reply is not acceptable") from error
    return tuple(questions)


def _judged(value):
    questions = []
    for item in _objects(value, _JUDGED_KEYS):
        if any(type(item[key]) is not str for key in _JUDGED_KEYS):
            raise Rejected("text task reply is not acceptable")
        try:
            questions.append(TrueFalseQuestion(item["题目"], item["参考答案"], item["解析"]))
        except ValueError as error:
            raise Rejected("text task reply is not acceptable") from error
    return tuple(questions)


def _opened(value):
    questions = []
    for item in _objects(value, _OPEN_KEYS):
        if any(type(item[key]) is not str for key in _OPEN_KEYS):
            raise Rejected("text task reply is not acceptable")
        try:
            questions.append(OpenQuestion(
                item["题目"], item["作答要求"], item["参考答案"], item["解析"]
            ))
        except ValueError as error:
            raise Rejected("text task reply is not acceptable") from error
    return tuple(questions)
