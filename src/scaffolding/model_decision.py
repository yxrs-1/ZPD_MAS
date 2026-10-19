import json


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
