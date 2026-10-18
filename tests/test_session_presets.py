from scaffolding.records import TaskRecord, TaskStatement
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.session import Session


def test_before_help_the_page_shows_presets_and_no_scaffold():
    decision = ScriptedDecisionAgent(presets=("这一步要判断什么？", "作品还缺哪一部分？"))
    session = Session(
        record=TaskRecord(statement=TaskStatement(prompt="完成作品并判断说法")),
        decision=decision,
        scaffold_agent=ScriptedScaffoldAgent(),
    )

    view = session.view()

    assert view.presets == ("这一步要判断什么？", "作品还缺哪一部分？")
    assert view.scaffold is None
    assert decision.choose_calls == []
