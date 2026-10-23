import json

import pytest

from scaffolding.documents import DraftError, DraftedObjective, confirm_prompt, parse_objective_text
from scaffolding.generation import TaskGeneration
from scaffolding.tasks import TaskCatalog


_REPLY = json.dumps({
    "读法": {"单选": 1, "多选": "未指定", "判断": "未指定", "综合": "未指定"},
    "目标": [{"维度": "信息意识", "表述": "模型另写的目标"}],
    "题目": {
        "单选": [{
            "题目": "哪一项是数据",
            "选项": ["数据", "电线"],
            "参考答案": ["数据"],
            "解析": "题干已说明",
        }],
        "多选": [],
        "判断": [],
        "综合": [],
    },
}, ensure_ascii=False)


class _Text:
    def __init__(self) -> None:
        self.messages = []

    def generate(self, text: str) -> str:
        self.messages.append(text)
        return _REPLY


def test_edited_text_parses_and_the_prompt_has_no_fixed_count_line():
    parsed = parse_objective_text("维度：信息意识\n表述：能识别信息\n\n维度：计算思维\n表述：能分解问题")

    prompt = confirm_prompt("做一道单选", parsed)

    assert parsed[0] == DraftedObjective("信息意识", "能识别信息")
    assert "没有指定题型和数量。" not in prompt
    assert prompt.startswith("教师需求：\n做一道单选\n\n目标：\n维度：信息意识\n表述：能识别信息")
    with pytest.raises(DraftError, match="目标格式不正确"):
        parse_objective_text("维度：其他\n表述：能识别信息")


def test_confirmation_creates_an_unpublished_task_without_an_origin():
    catalog = TaskCatalog()
    text = _Text()
    generation = TaskGeneration(None, catalog, None, text)
    objectives = (DraftedObjective("信息意识", "能识别信息"),)

    task = generation.generate_from_confirmed("做一道单选", objectives)

    assert task.published is False
    assert task.questions[0].prompt == "哪一项是数据"
    assert generation.origin(task.task_id) is None
    assert text.messages[0] == confirm_prompt("做一道单选", objectives)
