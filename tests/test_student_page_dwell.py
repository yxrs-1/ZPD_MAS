from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage
from tests.student_page_helpers import true_false_catalog
from tests.test_student_page_failure import AlwaysFail


def _page():
    catalog, task_id = true_false_catalog()
    page = StudentPage(catalog, ScriptedDecisionAgent(presets=("先看题目",)), ScriptedScaffoldAgent())
    return catalog, task_id, page


def test_later_actions_add_positive_elapsed_seconds():
    catalog, task_id, page = _page()
    page.open_task(task_id, 10)
    assert catalog.work(task_id).behavior.dwell_seconds == 0

    page.open_task(task_id, 10)
    page.open_task(task_id, 9)
    assert catalog.work(task_id).behavior.dwell_seconds == 0

    page.open_task(task_id, 12)
    assert catalog.work(task_id).behavior.dwell_seconds == 2

    page.todo()
    assert catalog.work(task_id).behavior.dwell_seconds == 2

    page.edit_answer(task_id, 0, selected=("人员", "硬件"), now=15)
    assert catalog.work(task_id).behavior.dwell_seconds == 5
    assert catalog.work(task_id).answers[0].selected == ()

    page.ask(task_id, "   ", "自己写的", 16)
    assert catalog.work(task_id).behavior.dwell_seconds == 6

    page.submit(task_id, 20)
    assert catalog.work(task_id).behavior.dwell_seconds == 10

    page.asset(task_id, "组成.svg")
    assert catalog.work(task_id).behavior.dwell_seconds == 10


def test_a_missing_session_does_not_record_dwell():
    catalog, task_id = true_false_catalog()
    page = StudentPage(catalog, AlwaysFail(), ScriptedScaffoldAgent())
    page.open_task(task_id, 0)
    page.open_task(task_id, 5)
    page.edit_answer(task_id, 0, selected=("错误",), now=6)

    assert task_id not in page.shown_at
    assert catalog.work(task_id).behavior.dwell_seconds == 0
