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
