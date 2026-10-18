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
