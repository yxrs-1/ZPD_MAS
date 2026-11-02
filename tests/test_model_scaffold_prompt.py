from scaffolding.model_scaffold import build_messages
from scaffolding.records import (
    ChoiceQuestion,
    ItemAnswer,
    OpenQuestion,
    SelectionMode,
    TrueFalseQuestion,
)


def _questions():
    return (
        ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "天气"), ("人员",), "人员是组成"),
        ChoiceQuestion("选出组成", SelectionMode.MULTIPLE, ("人员", "硬件", "天气"), ("人员", "硬件"), "天气不是组成"),
        TrueFalseQuestion("判断说法", "正确", "题目里有依据"),
        OpenQuestion("完成作品", "写出组成"),
    )


def _answers():
    return (
        ItemAnswer(selected=("人员",), selected_revisions=(("天气",),)),
        ItemAnswer(selected=("人员", "硬件"), selected_revisions=(("人员",), ("硬件", "天气"))),
        ItemAnswer(),
        ItemAnswer(text="第二稿", text_revisions=("第一稿",)),
    )


def test_the_prompt_lists_the_task_and_this_question():
    system, user = build_messages("提示", "还缺{什么}？", _questions(), _answers())

    assert system == {
        "role": "system",
        "content": (
            "只回一份 JSON 对象，不要代码块，不要其他文字。\n"
            "顶层只有「文字」和「源码」。两个值都是字符串，可以是空字符串。\n"
            "不要写 HTML，不要写文件名。\n"
            "文字写两三句，不要引用题干原句。\n"
            "读者是正在做这道题的学生。用「你」直接对这个人说。\n"
            "文字里不出现：学生、教师、引导、让学生、请学生、学情。\n"
            "支架的文字和源码不要写出参考答案，也不要写出学情。"
        ),
    }
    assert user == {
        "role": "user",
        "content": (
            "题目1\n"
            "题型：单选\n"
            "题干：选出人员\n"
            "选项：人员、天气\n"
            "参考答案：人员\n"
            "解析：人员是组成\n"
            "当前作答：人员\n"
            "修改痕迹：\n"
            "天气\n"
            "\n"
            "题目2\n"
            "题型：多选\n"
            "题干：选出组成\n"
            "选项：人员、硬件、天气\n"
            "参考答案：人员、硬件\n"
            "解析：天气不是组成\n"
            "当前作答：人员、硬件\n"
            "修改痕迹：\n"
            "人员\n"
            "硬件、天气\n"
            "\n"
            "题目3\n"
            "题型：判断\n"
            "题干：判断说法\n"
            "选项：正确、错误\n"
            "参考答案：正确\n"
            "解析：题目里有依据\n"
            "当前作答：\n"
            "修改痕迹：\n"
            "\n"
            "题目4\n"
            "题型：综合\n"
            "题干：完成作品\n"
            "作答要求：写出组成\n"
            "参考答案：\n"
            "解析：\n"
            "当前作答：第二稿\n"
            "修改痕迹：\n"
            "第一稿\n"
            "\n"
            "素材：思维导图\n"
            "源码是缩进大纲。第一行是根，下一层多两个空格。\n"
            "例如：\n"
            "网络\n"
            "  带宽\n"
            "  延迟\n"
            "文字的第一句是：先看下面这张图。\n"
            "支架类型：提示\n"
            "这次提问：还缺{什么}？"
        ),
    }
    assert "停留时间" not in user["content"]
    assert "求助：" not in user["content"]


def test_an_empty_selection_trace_is_a_blank_line():
    _, user = build_messages(
        "提示",
        "还缺什么？",
        (TrueFalseQuestion("判断说法", "正确", "题目里有依据"),),
        (ItemAnswer(selected=("正确",), selected_revisions=((),)),),
    )

    assert user["content"].endswith(
        "修改痕迹：\n\n\n素材：思维导图\n源码是缩进大纲。第一行是根，下一层多两个空格。\n例如：\n网络\n  带宽\n  延迟\n文字的第一句是：先看下面这张图。\n支架类型：提示\n这次提问：还缺什么？"
    )


def test_a_demonstration_prompt_uses_the_shot_list():
    _system, user = build_messages("示范", "循环怎么走？", _questions(), _answers())

    assert "帧：带宽" not in user["content"]
    assert "停留写成「拍：节点：秒数：说明」。" in user["content"]
    assert "移动写成「拍：起点 -> 终点：秒数：说明」。" in user["content"]
    assert "终点比起点更早出现的箭头是回头边，每一条回头边都要走一次。" in user["content"]
    assert "例子只示范写法。节点、箭头和说明对着这次提问写。" in user["content"]
    assert "拍：执行循环体 -> 判断条件：2：执行完回到判断" in user["content"]
    assert "文字的第一句是：先看下面这张图。" in user["content"]

