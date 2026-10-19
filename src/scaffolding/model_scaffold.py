import json

from scaffolding.agents import ScaffoldDraft


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
