from scaffolding.agents import ScaffoldDraft
from scaffolding.records import HelpSource, OpenQuestion, TaskRecord
from scaffolding.scripted import ScriptedScaffoldAgent
from scaffolding.session import Session
from scaffolding.tasks import TaskCatalog


class _ChangingDecision:
    def __init__(self) -> None:
        self.records = []

    def suggest(self, record: TaskRecord) -> tuple[str, ...]:
        self.records.append(record)
        if record.answers[0].text == "":
            return ("先看题目要求",)
        return ("对照你改过的作品",)

    def choose_type(self, record: TaskRecord, question: str) -> str:
        return "反馈"


def _open_session(decision: _ChangingDecision, scaffold_agent: ScriptedScaffoldAgent) -> Session:
    catalog = TaskCatalog()
    task = catalog.create((OpenQuestion("完成作品", "写出组成"),))
    catalog.publish(task.task_id)
    return Session(catalog, catalog.start(task.task_id), decision, scaffold_agent)


def test_editing_the_answer_refreshes_presets_and_keeps_the_statement():
    decision = _ChangingDecision()
    session = _open_session(decision, ScriptedScaffoldAgent())

    view = session.edit_answer(0, text="第一次写了人员")

    assert view.presets == ("对照你改过的作品",)
    assert view.scaffold is None
    assert session.work.questions[0].prompt == "完成作品"
    assert session.work.answers[0].text == "第一次写了人员"
    assert session.work.answers[0].text_revisions == ("",)
    assert len(decision.records) == 2


def test_a_scaffold_already_on_the_page_stays_after_an_edit():
    decision = _ChangingDecision()
    session = _open_session(
        decision,
        ScriptedScaffoldAgent(ScaffoldDraft(text="反馈：先看题目要求")),
    )
    session.ask("先看题目要求", HelpSource.PRESET)

    view = session.edit_answer(0, text="补上硬件")

    assert view.presets == ("对照你改过的作品",)
    assert view.scaffold is not None
    assert view.scaffold.text == "反馈：先看题目要求"


def test_dwell_is_stored_without_refreshing_presets():
    session = _open_session(_ChangingDecision(), ScriptedScaffoldAgent())

    session.note_dwell(15)

    assert session.record.behavior.dwell_seconds == 15
    assert session.view().presets == ("先看题目要求",)
    assert session.view().scaffold is None
