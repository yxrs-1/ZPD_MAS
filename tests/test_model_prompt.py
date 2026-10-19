from scaffolding.generation import QuestionCounts
from scaffolding.knowledge import StandardSource
from scaffolding.model_generator import build_messages
from scaffolding.objectives import Objective
from tests.generation_helpers import prepared_objectives


def test_messages_carry_rules_counts_and_only_this_records_objectives():
    base, catalog = prepared_objectives()
    lesson = catalog.lesson_objectives("人教版", "必修一", "信息系统的组成")[0]
    standard = Objective(
        "objective-2",
        "信息社会责任",
        "遵守规范",
        StandardSource("普通高中信息科技课程标准", "高中", "1.1.2"),
    )

    system, user = build_messages(QuestionCounts(2, 0, 1, 1), (lesson, standard))

    assert system == {
        "role": "system",
        "content": (
            "你是高中信息科技教师。只回一份 JSON 对象，不要代码块，不要其他文字。\n"
            "JSON 有且只有四个键：单选、多选、判断、综合。每个键的值都是数组。某一类数量是 0 时，那个数组是空的。\n"
            "单选和多选的每一项都有且只有这些键：题目、选项、参考答案、解析。"
            "选项正好四个，互不相同，且都不能为空白。选项和参考答案是字符串数组。"
            "单选的参考答案是其中一个选项。多选的参考答案至少包含一个选项，且每一项都在选项里、互不相同。"
            "题目和解析都不能为空白。\n"
            "判断的每一项都有且只有这些键：题目、参考答案、解析。参考答案是「正确」或「错误」。题目和解析都不能为空白。\n"
            "综合的每一项都有且只有这些键：题目、作答要求、参考答案、解析。题目和作答要求都不能为空白。参考答案和解析可以空着。\n"
            "空白不算已填写。"
        ),
    }
    assert user == {
        "role": "user",
        "content": (
            "单选：2\n"
            "多选：0\n"
            "判断：1\n"
            "综合：1\n"
            "\n"
            "目标：\n"
            "1. 维度：信息意识\n"
            "表述：能识别信息\n"
            "来源：版本 人教版，册次 必修一，课时 信息系统的组成，学段 高中，页码 12-15\n"
            "2. 维度：信息社会责任\n"
            "表述：遵守规范\n"
            "来源：名称 普通高中信息科技课程标准，学段 高中，条款号 1.1.2，现行课标"
        ),
    }
    assert "objective-1" not in user["content"]
    assert "objective-2" not in user["content"]
    assert "课时原文" not in user["content"]
    assert "课标全文" not in user["content"]
    assert base.get_lesson("人教版", "必修一", "信息系统的组成").text == "课时原文"
