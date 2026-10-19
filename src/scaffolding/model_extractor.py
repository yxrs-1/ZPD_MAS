import json

from scaffolding.knowledge import LessonRetrieval, LessonSource, StageRetrieval
from scaffolding.objectives import ObjectiveDraft, Rejected


_ITEM_KEYS = {"维度", "表述", "来源"}


def parse_objectives(text: str, retrieval: LessonRetrieval | StageRetrieval) -> tuple[ObjectiveDraft, ...]:
    if not isinstance(text, str):
        raise Rejected("model reply is not the objective JSON")
    try:
        body = json.loads(text.strip())
    except json.JSONDecodeError as error:
        raise Rejected("model reply is not the objective JSON") from error
    if not isinstance(body, dict) or set(body) != {"目标"} or not isinstance(body["目标"], list):
        raise Rejected("model reply is not the objective JSON")
    drafts = []
    for item in body["目标"]:
        if not isinstance(item, dict) or set(item) != _ITEM_KEYS:
            raise Rejected("model reply is not the objective JSON")
        if any(type(item[key]) is not str for key in _ITEM_KEYS):
            raise Rejected("model reply is not the objective JSON")
        drafts.append(ObjectiveDraft(item["维度"], item["表述"], _source(item["来源"], retrieval)))
    return tuple(drafts)


def _source(label: str, retrieval: LessonRetrieval | StageRetrieval):
    if label == "教材" and isinstance(retrieval, LessonRetrieval):
        return retrieval.lesson_source
    if label == "课标":
        return retrieval.standard_source
    return LessonSource(label, label, label, label, label)


_LESSON_SYSTEM = (
    "你是高中信息科技教师。只回一份 JSON 对象，不要代码块，不要其他文字。\n"
    "JSON 有且只有一个键：目标。它的值是数组。数组可以是空的。\n"
    "每条目标都有且只有这些键：维度、表述、来源。三个值都是字符串。\n"
    "维度只能是信息意识、计算思维、数字化学习与创新、信息社会责任。\n"
    "来源写成「教材」或「课标」，并且必须是这次交回的来源。\n"
    "表述不能为空白。空白不算已填写。"
)

_STAGE_SYSTEM = (
    "你是高中信息科技教师。只回一份 JSON 对象，不要代码块，不要其他文字。\n"
    "JSON 有且只有一个键：目标。它的值是数组。数组可以是空的。\n"
    "每条目标都有且只有这些键：维度、表述、来源。三个值都是字符串。\n"
    "维度只能是信息意识、计算思维、数字化学习与创新、信息社会责任。\n"
    "来源只能写成「课标」，并且必须是这次交回的课标来源。\n"
    "表述不能为空白。空白不算已填写。"
)


def build_messages(retrieval: LessonRetrieval | StageRetrieval) -> tuple[dict[str, str], dict[str, str]]:
    if isinstance(retrieval, LessonRetrieval):
        lesson = retrieval.lesson_source
        standard = retrieval.standard_source
        content = (
            "教材原文：\n"
            + retrieval.lesson_text
            + "\n\n教材来源：版本 "
            + lesson.version
            + "，册次 "
            + lesson.volume
            + "，课时 "
            + lesson.lesson
            + "，学段 "
            + lesson.stage
            + "，页码 "
            + lesson.pages
            + "\n\n课标原文：\n"
            + retrieval.standard_text
            + "\n\n课标来源：名称 "
            + standard.name
            + "，学段 "
            + standard.stage
            + "，条款号 "
            + standard.clauses
            + "，现行课标"
        )
        return ({"role": "system", "content": _LESSON_SYSTEM}, {"role": "user", "content": content})
    standard = retrieval.standard_source
    content = (
        "课标原文：\n"
        + retrieval.standard_text
        + "\n\n课标来源：名称 "
        + standard.name
        + "，学段 "
        + standard.stage
        + "，条款号 "
        + standard.clauses
        + "，现行课标"
    )
    return ({"role": "system", "content": _STAGE_SYSTEM}, {"role": "user", "content": content})
