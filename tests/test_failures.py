import pytest

from scaffolding.agents import ScaffoldDraft
from scaffolding.records import HelpSource, TaskRecord, TaskStatement
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.session import Session


def _session(decision: ScriptedDecisionAgent, scaffold_agent: ScriptedScaffoldAgent) -> Session:
    return Session(
        TaskRecord(statement=TaskStatement(prompt="判断说法")),
        decision,
        scaffold_agent,
    )


def test_blank_question_does_not_call_either_agent():
    decision = ScriptedDecisionAgent(presets=("先看题目",))
    scaffold_agent = ScriptedScaffoldAgent(ScaffoldDraft(text="不该出现"))
    session = _session(decision, scaffold_agent)

    view = session.ask("   ", HelpSource.OWN)

    assert view.presets == ("先看题目",)
    assert view.scaffold is None
    assert decision.choose_calls == []
    assert scaffold_agent.calls == []


@pytest.mark.parametrize("scaffold_type", ["", "第4级", "answer"])
def test_type_outside_the_six_shows_no_scaffold(scaffold_type: str):
    decision = ScriptedDecisionAgent(presets=("先看题目",), scaffold_type=scaffold_type)
    scaffold_agent = ScriptedScaffoldAgent(ScaffoldDraft(text="不该出现"))
    session = _session(decision, scaffold_agent)

    view = session.ask("这题怎么做？", HelpSource.OWN)

    assert view.scaffold is None
    assert view.presets == ("先看题目",)
    assert scaffold_agent.calls == []


def test_decision_failure_keeps_the_presets():
    decision = ScriptedDecisionAgent(presets=("先看题目",), error=RuntimeError("down"))
    session = _session(decision, ScriptedScaffoldAgent(ScaffoldDraft(text="不该出现")))

    view = session.ask("这题怎么做？", HelpSource.PRESET)

    assert view.scaffold is None
    assert view.presets == ("先看题目",)


def test_empty_scaffold_is_not_shown():
    decision = ScriptedDecisionAgent(presets=("先看题目",), scaffold_type="反馈")
    session = _session(decision, ScriptedScaffoldAgent(ScaffoldDraft(text="  ", html="<p>说明</p>")))

    view = session.ask("这题怎么做？", HelpSource.OWN)

    assert view.scaffold is None
    assert view.presets == ("先看题目",)


def test_scaffold_failure_keeps_the_presets():
    decision = ScriptedDecisionAgent(presets=("先看题目",), scaffold_type="提问")
    session = _session(decision, ScriptedScaffoldAgent(error=RuntimeError("down")))

    view = session.ask("这题怎么做？", HelpSource.OWN)

    assert view.scaffold is None
    assert view.presets == ("先看题目",)


def test_empty_answer_can_still_receive_a_scaffold():
    decision = ScriptedDecisionAgent(presets=("题目要求是什么？",), scaffold_type="解释")
    scaffold_agent = ScriptedScaffoldAgent(ScaffoldDraft(text="解释：题目要求是什么？"))
    session = _session(decision, scaffold_agent)

    view = session.ask("题目要求是什么？", HelpSource.PRESET)

    assert session.record.answer.content == ""
    assert view.scaffold is not None
    assert view.scaffold.text == "解释：题目要求是什么？"


def test_later_ask_failures_keep_the_existing_scaffold():
    class SequenceDecision:
        def __init__(self) -> None:
            self._calls = 0

        def suggest(self, record: TaskRecord) -> tuple[str, ...]:
            return ("先看题目",)

        def choose_type(self, record: TaskRecord, question: str) -> str:
            self._calls += 1
            if self._calls == 1:
                return "提示"
            if self._calls == 2:
                return "第4级"
            if self._calls == 3:
                raise RuntimeError("down")
            return "反馈"

    class SequenceScaffold:
        def __init__(self) -> None:
            self._calls = 0

        def produce(self, scaffold_type: str, question: str, statement: object, answer: object) -> ScaffoldDraft:
            self._calls += 1
            if self._calls == 1:
                return ScaffoldDraft(text="先看这句提示")
            return ScaffoldDraft()

    session = _session(SequenceDecision(), SequenceScaffold())
    first = session.ask("这题怎么做？", HelpSource.OWN)
    assert first.scaffold is not None
    assert first.scaffold.text == "先看这句提示"
    assert first.presets == ("先看题目",)

    later_type = session.ask("第4级会怎样？", HelpSource.OWN)
    assert later_type.scaffold is not None
    assert later_type.scaffold.text == "先看这句提示"
    assert later_type.presets == ("先看题目",)
    assert session.record.behavior.helps[-1].text == "第4级会怎样？"

    later_error = session.ask("决策失败会怎样？", HelpSource.PRESET)
    assert later_error.scaffold is not None
    assert later_error.scaffold.text == "先看这句提示"
    assert later_error.presets == ("先看题目",)
    assert session.record.behavior.helps[-1].text == "决策失败会怎样？"

    later_empty = session.ask("空支架会怎样？", HelpSource.OWN)
    assert later_empty.scaffold is not None
    assert later_empty.scaffold.text == "先看这句提示"
    assert later_empty.presets == ("先看题目",)
    assert [event.text for event in session.record.behavior.helps] == [
        "这题怎么做？",
        "第4级会怎样？",
        "决策失败会怎样？",
        "空支架会怎样？",
    ]
