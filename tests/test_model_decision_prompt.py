from scaffolding.model_decision import build_preset_messages, build_type_messages
from scaffolding.records import (
    Behavior,
    ChoiceQuestion,
    HelpEvent,
    HelpSource,
    ItemAnswer,
    OpenQuestion,
    SelectionMode,
    TaskRecord,
    TrueFalseQuestion,
)


def _record() -> TaskRecord:
    return TaskRecord(
        (
            ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "天气"), ("人员",), "人员是组成"),
            ChoiceQuestion("选出组成", SelectionMode.MULTIPLE, ("人员", "硬件", "天气"), ("人员", "硬件"), "天气不是组成"),
            TrueFalseQuestion("判断说法", "正确", "题目里有依据"),
            OpenQuestion("完成作品", "写出组成"),
        ),
        (
            ItemAnswer(selected=("人员",), selected_revisions=(("天气",),)),
            ItemAnswer(selected=("人员", "硬件"), selected_revisions=(("人员",), ("硬件", "天气"))),
            ItemAnswer(),
            ItemAnswer(text="第二稿", text_revisions=("第一稿",)),
        ),
        Behavior(
            dwell_seconds=3.5,
            helps=(
                HelpEvent("先看题目", HelpSource.PRESET),
                HelpEvent("这题怎么做？", HelpSource.OWN),
            ),
        ),
    )


def test_a_preset_prompt_lists_the_task_record():
    system, user = build_preset_messages(_record())

    assert system == {
        "role": "system",
        "content": (
            "只回一份 JSON 对象，不要代码块，不要其他文字。\n"
            "顶层只有「预设提问」。它的值是字符串数组，数组可以是空的。\n"
            "每一条都不能为空白。空白不算已填写。\n"
            "不要写出学情。"
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
            "停留时间：3.5\n"
            "求助：\n"
            "预设提问：先看题目\n"
            "自己写的：这题怎么做？"
        ),
    }


def test_a_type_prompt_appends_the_question_without_formatting():
    _, preset_user = build_preset_messages(_record())
    system, user = build_type_messages(_record(), "还缺{什么}？")

    assert system == {
        "role": "system",
        "content": (
            "只回一份 JSON 对象，不要代码块，不要其他文字。\n"
            "顶层只有「类型」。它的值是字符串，并且正好是反馈、提示、指导、解释、示范、提问之一。\n"
            "不要写出学情。"
        ),
    }
    assert "预设提问" not in system["content"]
    assert user["content"] == preset_user["content"] + "\n\n这次提问：还缺{什么}？"


def test_an_empty_selection_trace_is_a_blank_line():
    record = TaskRecord(
        (TrueFalseQuestion("判断说法", "正确", "题目里有依据"),),
        (ItemAnswer(selected=("正确",), selected_revisions=((),)),),
        Behavior(),
    )

    _, user = build_preset_messages(record)

    assert user["content"].endswith("修改痕迹：\n\n\n停留时间：0.0\n求助：\n")
