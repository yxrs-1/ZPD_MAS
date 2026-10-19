from scaffolding.knowledge import CurriculumStandard
from scaffolding.model_extractor import build_messages
from tests.objective_helpers import sample_base


def test_a_lesson_prompt_contains_both_texts_and_both_sources():
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")

    system, user = build_messages(retrieval)

    assert system == {
        "role": "system",
        "content": (
            "你是高中信息科技教师。只回一份 JSON 对象，不要代码块，不要其他文字。\n"
            "JSON 有且只有一个键：目标。它的值是数组。数组可以是空的。\n"
            "每条目标都有且只有这些键：维度、表述、来源。三个值都是字符串。\n"
            "维度只能是信息意识、计算思维、数字化学习与创新、信息社会责任。\n"
            "来源写成「教材」或「课标」，并且必须是这次交回的来源。\n"
            "表述不能为空白。空白不算已填写。"
        ),
    }
    assert user == {
        "role": "user",
        "content": (
            "教材原文：\n"
            "课时原文\n"
            "\n"
            "教材来源：版本 人教版，册次 必修一，课时 信息系统的组成，学段 高中，页码 12-15\n"
            "\n"
            "课标原文：\n"
            "课标全文\n"
            "\n"
            "课标来源：名称 普通高中信息科技课程标准，学段 高中，条款号 1.1.2，现行课标"
        ),
    }
    assert base.get_lesson("人教版", "必修一", "信息系统的组成").text == "课时原文"


def test_a_stage_prompt_contains_only_the_standard():
    base = sample_base()
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    retrieval = base.retrieve_stage("初中")

    system, user = build_messages(retrieval)

    assert system["role"] == "system"
    assert "来源只能写成「课标」，并且必须是这次交回的课标来源。" in system["content"]
    assert "来源写成「教材」或「课标」" not in system["content"]
    assert user == {
        "role": "user",
        "content": (
            "课标原文：\n"
            "初中课标全文\n"
            "\n"
            "课标来源：名称 义务教育信息科技课程标准，学段 初中，条款号 2.1，现行课标"
        ),
    }
    assert "教材原文" not in user["content"]
    assert "课时原文" not in user["content"]
