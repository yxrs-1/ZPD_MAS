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
        if not isinstance(item, dict):
            raise Rejected("text task reply is not acceptable")
        dimension = item.get("维度")
        statement = item.get("表述")
        if type(dimension) is not str or dimension not in _DIMENSIONS:
            raise Rejected("text task reply is not acceptable")
        if type(statement) is not str or statement.strip() == "":
            raise Rejected("text task reply is not acceptable")


def _questions(questions):
    if not isinstance(questions, dict):
        raise Rejected("text task reply is not acceptable")
    return {
        "单选": _choices(questions.get("单选", []), SelectionMode.SINGLE),
        "多选": _choices(questions.get("多选", []), SelectionMode.MULTIPLE),
        "判断": _judged(questions.get("判断", [])),
        "综合": _opened(questions.get("综合", [])),
    }


def _text(item, key):
    value = item.get(key, "")
    if type(value) is not str:
        return None
    return value


def _string_list(value):
    if type(value) is str:
        value = [value]
    if not isinstance(value, list) or any(type(item) is not str for item in value):
        return None
    return tuple(value)


def _choices(value, selection):
    if not isinstance(value, list):
        return ()
    questions = []
    for item in value:
        if not isinstance(item, dict):
            continue
        prompt = _text(item, "题目")
        explanation = _text(item, "解析")
        options = _string_list(item.get("选项"))
        answers = _string_list(item.get("参考答案"))
        if prompt is None or explanation is None or options is None or answers is None:
            continue
        try:
            questions.append(ChoiceQuestion(prompt, selection, options, answers, explanation))
        except ValueError:
            continue
    return tuple(questions)


def _judged(value):
    if not isinstance(value, list):
        return ()
    questions = []
    for item in value:
        if not isinstance(item, dict):
            continue
        prompt = _text(item, "题目")
        answer = item.get("参考答案")
        explanation = _text(item, "解析")
        if type(answer) is not str or prompt is None or explanation is None:
            continue
        try:
            questions.append(TrueFalseQuestion(prompt, answer, explanation))
        except ValueError:
            continue
    return tuple(questions)


def _opened(value):
    if not isinstance(value, list):
        return ()
    questions = []
    for item in value:
        if not isinstance(item, dict):
            continue
        prompt = _text(item, "题目")
        requirements = _text(item, "作答要求")
        answer = item.get("参考答案", "")
        explanation = item.get("解析", "")
        if prompt is None or requirements is None or type(answer) is not str or type(explanation) is not str:
            continue
        try:
            questions.append(OpenQuestion(prompt, requirements, answer, explanation))
        except ValueError:
            continue
    return tuple(questions)
