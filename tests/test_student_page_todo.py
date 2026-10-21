from scaffolding.records import TrueFalseQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage, response_for
from scaffolding.tasks import TaskCatalog
from tests.student_page_helpers import body_text, true_false_catalog


def _page(catalog):
    return StudentPage(catalog, ScriptedDecisionAgent(), ScriptedScaffoldAgent())


def test_empty_catalog_has_an_empty_todo():
    page = _page(TaskCatalog())

    assert "<h1>待办</h1><ul></ul>" in page.todo()
    assert page.sessions == {}


def test_todo_lists_only_published_tasks_and_does_not_start_them():
    catalog, task_id = true_false_catalog()
    hidden = catalog.create((TrueFalseQuestion("未发布题目", "错误", "未发布解析"),))
    page = _page(catalog)

    html = page.todo()

    assert task_id in html
    assert "待办" in html
    assert "未发布题目" not in html
    assert "题目里有依据" not in html
    assert "未发布解析" not in html
    assert catalog.get(task_id).started is False
    assert page.sessions == {}
    response = response_for(page, "GET", "/", "", 0)
    assert response.status == 200
    assert body_text(response) == html


def test_submitted_task_is_listed_as_finished_without_a_session():
    catalog, task_id = true_false_catalog()
    catalog.start(task_id)
    catalog.mark_submitted(task_id)
    page = _page(catalog)

    assert task_id in page.todo()
    assert "已完成" in page.todo()
    assert page.sessions == {}
