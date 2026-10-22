import json

import pytest

from scaffolding.generation import Rejected
from scaffolding.text_generation import parse_text_task
from tests.text_generation_helpers import body, choice, dumped, judged, opened


def test_parse_orders_specified_and_unspecified_questions():
    questions = parse_text_task(dumped(
        reading={"单选": 2, "多选": "未指定", "判断": 0, "综合": "未指定"},
        questions={
            "单选": [choice("第一"), choice("第二")],
            "多选": [],
            "判断": [],
            "综合": [opened("综合题")],
        },
    ))

    assert [item.prompt for item in questions] == ["第一", "第二", "综合题"]


def test_parse_rejects_an_unacceptable_reply():
    readings = [
        {"多选": "未指定", "判断": 0, "综合": "未指定"},
        {"单选": 1, "多选": "未指定", "判断": 0, "综合": "未指定", "填空": 1},
        {"单选": "1", "多选": "未指定", "判断": 0, "综合": "未指定"},
        {"单选": 1.0, "多选": "未指定", "判断": 0, "综合": "未指定"},
        {"单选": True, "多选": "未指定", "判断": 0, "综合": "未指定"},
        {"单选": -1, "多选": "未指定", "判断": 0, "综合": "未指定"},
    ]
    objectives = [
        [],
        [{"维度": "超纲", "表述": "能识别信息"}],
        [{"维度": "信息意识", "表述": "   "}],
        [{"维度": "信息意识", "表述": "能识别信息", "来源": "教材"}],
    ]
    questions = [
        {"单选": [choice("第一")], "多选": [], "判断": [judged()], "综合": []},
        {"单选": [], "多选": [], "判断": [], "综合": []},
        {"单选": [choice("第一", answers=("甲", "乙"))], "多选": [], "判断": [], "综合": []},
        {"单选": [choice("第一")], "多选": [], "判断": [], "综合": [opened()], "填空": []},
    ]
    samples = [json.dumps({**body(), "读法": item}) for item in readings]
    one_option = {"题目": "单选题", "选项": ["甲"], "参考答案": ["甲"], "解析": "解析"}
    questions.append({"单选": [one_option], "多选": [], "判断": [], "综合": [opened()]})
    samples += [json.dumps({"读法": body()["读法"], "目标": item, "题目": body()["题目"]}) for item in objectives]
    samples += [json.dumps({"读法": body()["读法"], "目标": body()["目标"], "题目": item}) for item in questions]
    samples.append(json.dumps({
        **body(),
        "读法": {"单选": 2, "多选": "未指定", "判断": 0, "综合": "未指定"},
        "题目": {
            "单选": [choice("只有一道")],
            "多选": [],
            "判断": [],
            "综合": [opened()],
        },
    }))
    samples.append("```")

    for sample in samples:
        with pytest.raises(Rejected):
            parse_text_task(sample)
