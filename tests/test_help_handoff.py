from scaffolding.agents import ScaffoldDraft
from scaffolding.records import AnswerState, Asset, AssetKind, Behavior, HelpEvent, HelpSource, TaskRecord, TaskStatement
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.session import Session


def _session(scaffold_agent: ScriptedScaffoldAgent) -> tuple[Session, ScriptedDecisionAgent]:
    decision = ScriptedDecisionAgent(presets=("这一步要判断什么？",), scaffold_type="示范")
    record = TaskRecord(
        statement=TaskStatement(prompt="完成作品并判断说法", requirements="写出组成说明"),
        answer=AnswerState(content="人员已经写了", revisions=("空",)),
        behavior=Behavior(dwell_seconds=42, helps=(HelpEvent(text="更早的问题", source=HelpSource.OWN),)),
    )
    return Session(record, decision, scaffold_agent), decision


def test_clicking_a_preset_passes_that_sentence_and_one_type():
    scaffold_agent = ScriptedScaffoldAgent(ScaffoldDraft(text="示范：这一步要判断什么？"))
    session, decision = _session(scaffold_agent)

    view = session.ask("这一步要判断什么？", HelpSource.PRESET)

    assert decision.choose_calls[0][1] == "这一步要判断什么？"
    call = scaffold_agent.calls[0]
    assert call["scaffold_type"] == "示范"
    assert call["question"] == "这一步要判断什么？"
    assert set(call) == {"scaffold_type", "question", "statement", "answer"}
    assert call["answer"] == AnswerState(content="人员已经写了", revisions=("空",))
    assert view.scaffold is not None
    assert view.scaffold.text == "示范：这一步要判断什么？"


def test_an_owned_question_is_passed_verbatim():
    scaffold_agent = ScriptedScaffoldAgent(ScaffoldDraft(text="提示：我自己的问题"))
    session, _decision = _session(scaffold_agent)

    session.ask("我自己的问题", HelpSource.OWN)

    assert scaffold_agent.calls[0]["question"] == "我自己的问题"
    assert session.record.behavior.helps[-1].source == HelpSource.OWN


def test_behavior_is_not_given_to_the_scaffold_agent():
    scaffold_agent = ScriptedScaffoldAgent(
        ScaffoldDraft(assets=(Asset(AssetKind.IMAGE, "figure.png", b"png"),))
    )
    session, _decision = _session(scaffold_agent)

    session.ask("我自己的问题", HelpSource.OWN)

    call = scaffold_agent.calls[0]
    assert not hasattr(call["statement"], "dwell_seconds")
    assert "42" not in repr(call["answer"])
    assert "更早的问题" not in repr(call)
