import json

from scaffolding.generation import QuestionCounts, Rejected
from scaffolding.knowledge import LessonSource
from scaffolding.objectives import Objective
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


SYSTEM_MESSAGE = (
    "你是高中信息科技教师。只回一份 JSON 对象，不要代码块，不要其他文字。\n"
    "JSON 有且只有四个键：单选、多选、判断、综合。每个键的值都是数组。某一类数量是 0 时，那个数组是空的。\n"
    "单选和多选的每一项都有且只有这些键：题目、选项、参考答案、解析。"
    "选项正好四个，互不相同，且都不能为空白。选项和参考答案是字符串数组。"
    "单选的参考答案是其中一个选项。多选的参考答案至少包含一个选项，且每一项都在选项里、互不相同。"
    "题目和解析都不能为空白。\n"
    "判断的每一项都有且只有这些键：题目、参考答案、解析。参考答案是「正确」或「错误」。题目和解析都不能为空白。\n"
    "综合的每一项都有且只有这些键：题目、作答要求、参考答案、解析。题目和作答要求都不能为空白。参考答案和解析可以空着。\n"
    "空白不算已填写。"
)


def build_messages(counts: QuestionCounts, objectives: tuple[Objective, ...]) -> tuple[dict[str, str], dict[str, str]]:
    lines = [
        f"单选：{counts.single}",
        f"多选：{counts.multiple}",
        f"判断：{counts.true_false}",
        f"综合：{counts.open_ended}",
        "",
        "目标：",
    ]
    for number, objective in enumerate(objectives, start=1):
        lines.append(f"{number}. 维度：{objective.dimension}")
        lines.append(f"表述：{objective.statement}")
        lines.append(f"来源：{_source_text(objective.source)}")
    return (
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": "\n".join(lines)},
    )


def _source_text(source: object) -> str:
    if isinstance(source, LessonSource):
        return f"版本 {source.version}，册次 {source.volume}，课时 {source.lesson}，学段 {source.stage}，页码 {source.pages}"
    return f"名称 {source.name}，学段 {source.stage}，条款号 {source.clauses}，现行课标"
