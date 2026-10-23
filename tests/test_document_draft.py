import json

import pytest

from scaffolding.documents import DraftError, StoredDocument, draft_objectives, format_objectives


def _reply(body: dict) -> str:
    return json.dumps(body, ensure_ascii=False)


def test_a_match_is_shown_to_the_second_call_and_formatted():
    calls = []

    def complete(messages):
        calls.append(messages[1]["content"])
        if len(calls) == 1:
            return _reply({"检索": "信息，数据"})
        return _reply({"目标": [
            {"维度": "信息意识", "表述": "能识别信息"},
            {"维度": "信息意识", "表述": "能保护数据"},
        ]})

    documents = (StoredDocument("doc-1", "a.docx", ("信息与数据",)),)
    drafted = draft_objectives(complete, documents, "  数据怎么识别  ")

    assert calls[0] == "数据怎么识别"
    assert "教师需求：\n数据怎么识别\n\n匹配片段：\n文件名：a.docx\n信息与数据" == calls[1]
    assert format_objectives(drafted) == "维度：信息意识\n表述：能识别信息\n\n维度：信息意识\n表述：能保护数据"
    assert len(calls) == 2


def test_an_empty_match_uses_the_demand_and_does_not_search_again():
    calls = []

    def complete(messages):
        calls.append(messages[1]["content"])
        if len(calls) == 1:
            return _reply({"检索": "没有的词"})
        return _reply({"检索": "再找一次"})

    with pytest.raises(DraftError, match="没有写出目标"):
        draft_objectives(complete, (StoredDocument("doc-1", "a.docx", ("其他",)),), "教师需求原文")

    assert calls[1].endswith("没有匹配内容")
    assert "教师需求原文" in calls[1]
    assert len(calls) == 2


def test_blank_demand_does_not_call_the_model():
    def complete(messages):
        raise AssertionError("called")

    with pytest.raises(DraftError, match="先填写需求"):
        draft_objectives(complete, (), "  ")
