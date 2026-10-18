from scaffolding.agents import ScaffoldDraft
from scaffolding.records import Asset, AssetKind, HelpSource, ItemAnswer, OpenQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.session import Session
from scaffolding.tasks import TaskCatalog


def _session(scaffold_agent: ScriptedScaffoldAgent):
    decision = ScriptedDecisionAgent(presets=("这一步要判断什么？",), scaffold_type="示范")
    catalog = TaskCatalog()
    task = catalog.create((OpenQuestion("完成作品并判断说法", "写出组成说明", answer="五类都要写", explanation="人员硬件软件数据和网络"),))
    catalog.publish(task.task_id)
    work = catalog.start(task.task_id)
    work.edit(0, text="人员已经写了")
    session = Session(catalog, work, decision, scaffold_agent)
    return session, decision


def test_clicking_a_preset_passes_that_sentence_type_and_keys():
    scaffold_agent = ScriptedScaffoldAgent(ScaffoldDraft(text="示范：这一步要判断什么？"))
    session, decision = _session(scaffold_agent)

    view = session.ask("这一步要判断什么？", HelpSource.PRESET)

    assert decision.choose_calls[0][1] == "这一步要判断什么？"
    call = scaffold_agent.calls[0]
    assert call["scaffold_type"] == "示范"
    assert call["question"] == "这一步要判断什么？"
    assert set(call) == {"scaffold_type", "question", "questions", "answers"}
    assert call["questions"][0].explanation == "人员硬件软件数据和网络"
    assert call["answers"] == (ItemAnswer(text="人员已经写了", text_revisions=("",)),)
    assert "dwell_seconds" not in call
    assert view.scaffold is not None
    assert view.scaffold.text == "示范：这一步要判断什么？"


def test_an_owned_question_is_passed_verbatim():
    scaffold_agent = ScriptedScaffoldAgent(ScaffoldDraft(text="提示：我自己的问题"))
    session, _decision = _session(scaffold_agent)

    session.ask("我自己的问题", HelpSource.OWN)

    assert scaffold_agent.calls[0]["question"] == "我自己的问题"
    assert session.record.behavior.helps[-1].source == HelpSource.OWN
    assert session.view().dialogue[-1].question == "我自己的问题"


def test_behavior_is_not_given_to_the_scaffold_agent():
    scaffold_agent = ScriptedScaffoldAgent(ScaffoldDraft(assets=(Asset(AssetKind.IMAGE, "figure.png", b"png"),)))
    session, _decision = _session(scaffold_agent)
    session.note_dwell(42)

    session.ask("我自己的问题", HelpSource.OWN)

    call = scaffold_agent.calls[0]
    assert "42" not in repr(call["answers"])
    assert "更早的问题" not in repr(call)
