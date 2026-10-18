from pathlib import Path

import pytest

from scaffolding.agents import ScaffoldDraft
from scaffolding.records import ChoiceQuestion, HelpSource, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.session import Session
from scaffolding.tasks import TaskCatalog


def test_task_publishing_spec_is_in_the_workspace():
    spec = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "specs" / "2026-10-18-task-publishing-design.md"
    assert spec.is_file()


def test_published_task_matches_the_spec():
    catalog = TaskCatalog()
    task = catalog.create(
        (
            ChoiceQuestion("选出人员", SelectionMode.MULTIPLE, ("人员", "硬件", "天气"), ("人员", "硬件"), "天气不是组成"),
            TrueFalseQuestion("网络负责传送", "正确", "网络是通道"),
            OpenQuestion("写出组成", "覆盖五类组成"),
        )
    )
    assert catalog.student_tasks() == ()
    catalog.publish(task.task_id)
    assert catalog.student_tasks()[0].status == "待办"

    decision = ScriptedDecisionAgent(presets=("还缺哪一类？",), scaffold_type="提示")
    scaffold_agent = ScriptedScaffoldAgent(ScaffoldDraft(text="提示：还缺哪一类？"))
    session = Session(catalog, catalog.start(task.task_id), decision, scaffold_agent)
    with pytest.raises(Exception):
        catalog.update(task.task_id, (OpenQuestion("开始后不能改", "开始后不能改"),))

    session.edit_answer(0, selected=("人员",))
    asked = session.ask("还缺哪一类？", HelpSource.PRESET)
    assert asked.revealed == ()
    assert asked.scaffold is not None
    assert scaffold_agent.calls[0]["questions"][0].explanation == "天气不是组成"
    assert "behavior" not in scaffold_agent.calls[0]

    blank = session.ask("   ", HelpSource.OWN)
    assert blank.scaffold.text == "提示：还缺哪一类？"
    assert len(scaffold_agent.calls) == 1

    done = session.submit()
    assert done.answers_locked is True
    assert done.send_closed is True
    assert done.dialogue[0].question == "还缺哪一类？"
    assert done.revealed[2].answer == ""
    assert catalog.get(task.task_id).submitted is True

    catalog.delete(task.task_id)
    assert catalog.student_tasks() == ()
