import pytest

from scaffolding.agents import ScaffoldDraft
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.session import Session
from scaffolding.tasks import TaskCatalog
from scaffolding.records import HelpSource


def _session():
    catalog = TaskCatalog()
    secret = catalog.create((OpenQuestion("其他任务", "不要读到机密解析", explanation="机密解析"),))
    catalog.publish(secret.task_id)
    task = catalog.create(
        (
            ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "天气"), ("人员",), "人员是组成"),
            OpenQuestion("写出组成", "覆盖五类组成"),
        )
    )
    catalog.publish(task.task_id)
    decision = ScriptedDecisionAgent(presets=("还缺什么？",), scaffold_type="提示")
    scaffold_agent = ScriptedScaffoldAgent(ScaffoldDraft(text="提示：还缺什么？"))
    session = Session(catalog, catalog.start(task.task_id), decision, scaffold_agent)
    return catalog, session, secret


def test_keys_stay_hidden_until_submit_and_then_the_page_locks():
    catalog, session, _secret = _session()
    session.edit_answer(1, text="只写了人员")
    session.ask("还缺什么？", HelpSource.PRESET)
    before = session.view()

    assert before.revealed == ()
    assert before.answers_locked is False
    assert "人员是组成" not in repr(catalog.student_tasks())

    after = session.submit()

    assert after.answers_locked is True
    assert after.send_closed is True
    assert after.status == "已完成"
    assert after.presets == ()
    assert after.revealed[0].answer == ("人员",)
    assert after.revealed[0].explanation == "人员是组成"
    assert after.revealed[1].answer == ""
    assert after.dialogue[-1].question == "还缺什么？"
    assert after.scaffold is not None
    assert catalog.get(session.work.task_id).submitted
    assert next(item for item in catalog.student_tasks() if item.task_id == session.work.task_id).status == "已完成"
    with pytest.raises(Exception):
        session.edit_answer(1, text="提交后再改")
    with pytest.raises(Exception):
        session.ask("还能问吗？", HelpSource.OWN)
    assert session.work.answers[1].text == "只写了人员"


def test_agents_do_not_receive_another_task():
    _catalog, session, secret = _session()
    decision = session._decision
    session.ask("还缺什么？", HelpSource.PRESET)

    assert "机密解析" not in repr(decision.choose_calls)
    assert "其他任务" not in repr(session._scaffold_agent.calls)


def test_empty_answers_can_be_submitted():
    catalog = TaskCatalog()
    task = catalog.create((OpenQuestion("写出组成", "覆盖五类组成"),))
    catalog.publish(task.task_id)
    session = Session(catalog, catalog.start(task.task_id), ScriptedDecisionAgent(), ScriptedScaffoldAgent())

    view = session.submit()

    assert session.work.answers[0].text == ""
    assert view.answers_locked is True
    assert view.revealed[0].answer == ""


def test_submit_does_not_let_the_teacher_edit():
    catalog, session, secret = _session()
    session.submit()

    with pytest.raises(Exception):
        catalog.update(session.work.task_id, (OpenQuestion("提交后改题", "不允许"),))
    catalog.delete(session.work.task_id)
    assert [item.task_id for item in catalog.student_tasks()] == [secret.task_id]
