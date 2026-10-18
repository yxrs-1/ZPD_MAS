from scaffolding.records import (
    ASSET_KIND_VALUES,
    SCAFFOLD_TYPE_VALUES,
    AnswerState,
    Behavior,
    HelpEvent,
    HelpSource,
    TaskRecord,
    TaskStatement,
)


def test_record_keeps_the_whole_task_and_an_empty_answer():
    record = TaskRecord(
        statement=TaskStatement(
            prompt="完成作品并判断说法",
            choices=("正确", "错误"),
            requirements="写出组成说明",
        )
    )

    assert record.answer == AnswerState()
    assert record.behavior == Behavior()
    assert record.statement.choices == ("正确", "错误")


def test_help_event_records_the_verbatim_question_and_its_source():
    event = HelpEvent(text="这一步怎么判断？", source=HelpSource.OWN)

    assert event.text == "这一步怎么判断？"
    assert event.source == HelpSource.PRESET or event.source == HelpSource.OWN
    assert {HelpSource.PRESET, HelpSource.OWN} == {HelpSource("预设提问"), HelpSource("自己写的")}


def test_type_and_asset_vocabularies_are_fixed():
    assert SCAFFOLD_TYPE_VALUES == frozenset({"反馈", "提示", "指导", "解释", "示范", "提问"})
    assert ASSET_KIND_VALUES == frozenset({"图片素材", "思维导图", "结构图", "微格动画"})
