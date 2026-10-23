import pytest

from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion


def test_choice_question_stores_single_and_multiple_keys():
    single = ChoiceQuestion("信息系统包含哪些部分？", SelectionMode.SINGLE, ("人员", "只有硬件"), ("人员",), "人员是组成部分")
    multi = ChoiceQuestion("选出组成", SelectionMode.MULTIPLE, ("人员", "硬件", "天气"), ("人员", "硬件"), "天气不是组成")

    assert single.selection == SelectionMode.SINGLE
    assert single.answer == ("人员",)
    assert multi.answer == ("人员", "硬件")


def test_true_false_and_open_questions_keep_their_fields():
    judged = TrueFalseQuestion("网络属于信息系统", "正确", "网络负责传送")
    opened = OpenQuestion("完成组成说明", "写人员、硬件、软件、数据和网络")

    assert judged.answer == "正确"
    assert opened.answer == ""
    assert opened.explanation == ""


@pytest.mark.parametrize(
    "build",
    [
        lambda: ChoiceQuestion(" ", SelectionMode.SINGLE, ("人员", "硬件"), ("人员",), "解析"),
        lambda: ChoiceQuestion("题目", SelectionMode.SINGLE, ("人员",), ("人员",), "解析"),
        lambda: ChoiceQuestion("题目", SelectionMode.SINGLE, ("人员", "人员"), ("人员",), "解析"),
        lambda: ChoiceQuestion("题目", SelectionMode.SINGLE, ("人员", " "), ("人员",), "解析"),
        lambda: ChoiceQuestion("题目", SelectionMode.SINGLE, ("人员", "硬件"), ("天气",), "解析"),
        lambda: ChoiceQuestion("题目", SelectionMode.SINGLE, ("人员", "硬件"), ("人员", "硬件"), "解析"),
        lambda: ChoiceQuestion("题目", SelectionMode.MULTIPLE, ("人员", "硬件"), (), "解析"),
        lambda: TrueFalseQuestion(" ", "正确", "解析"),
        lambda: TrueFalseQuestion("题目", "对", "解析"),
        lambda: OpenQuestion(" ", "写出组成"),
        lambda: OpenQuestion("完成说明", " "),
    ],
)
def test_invalid_questions_are_rejected(build):
    with pytest.raises(ValueError):
        build()
