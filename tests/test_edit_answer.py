from scaffolding.agents import ScaffoldDraft
from scaffolding.records import HelpSource, TaskRecord, TaskStatement
from scaffolding.scripted import ScriptedScaffoldAgent
from scaffolding.session import Session


class _ChangingDecision:
    def __init__(self) -> None:
        self.records = []

    def suggest(self, record: TaskRecord) -> tuple[str, ...]:
        self.records.append(record)
        if record.answer.content == "":
            return ("先看题目要求",)
        return ("对照你改过的作品",)

    def choose_type(self, record: TaskRecord, question: str) -> str:
        return "反馈"


def test_editing_the_answer_refreshes_presets_and_keeps_the_statement():
    decision = _ChangingDecision()
    statement = TaskStatement(prompt="完成作品", choices=("正确", "错误"), requirements="写出组成")
    session = Session(TaskRecord(statement=statement), decision, ScriptedScaffoldAgent())

    view = session.edit_answer("第一次写了人员")

    assert view.presets == ("对照你改过的作品",)
    assert view.scaffold is None
    assert session.record.statement is statement
    assert session.record.answer.content == "第一次写了人员"
    assert session.record.answer.revisions == ("",)
    assert len(decision.records) == 2


def test_a_scaffold_already_on_the_page_stays_after_an_edit():
    decision = _ChangingDecision()
    session = Session(
        TaskRecord(statement=TaskStatement(prompt="完成作品")),
        decision,
        ScriptedScaffoldAgent(ScaffoldDraft(text="反馈：先看题目要求")),
    )
    session.ask("先看题目要求", HelpSource.PRESET)

    view = session.edit_answer("补上硬件")

    assert view.presets == ("对照你改过的作品",)
    assert view.scaffold is not None
    assert view.scaffold.text == "反馈：先看题目要求"


def test_dwell_is_stored_without_refreshing_presets():
    session = Session(
        TaskRecord(statement=TaskStatement(prompt="完成作品")),
        _ChangingDecision(),
        ScriptedScaffoldAgent(),
    )

    session.note_dwell(15)

    assert session.record.behavior.dwell_seconds == 15
    assert session.view().presets == ("先看题目要求",)
    assert session.view().scaffold is None
