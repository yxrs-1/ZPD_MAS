from scaffolding.records import TrueFalseQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage, response_for
from scaffolding.tasks import TaskCatalog
from tests.student_page_helpers import body_text, true_false_catalog


class FailOnce:
    def __init__(self) -> None:
        self.calls = 0

    def suggest(self, record):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("down")
        return ("先看题目",)

    def choose_type(self, record, question):
        return "提示"


class AlwaysFail:
    def suggest(self, record):
        raise RuntimeError("down")

    def choose_type(self, record, question):
        return "提示"


def test_missing_and_unpublished_tasks_show_nothing():
    catalog, task_id = true_false_catalog("判断说法")
    hidden = catalog.create((TrueFalseQuestion("未发布题目", "错误", "未发布解析"),))
    page = StudentPage(catalog, ScriptedDecisionAgent(), ScriptedScaffoldAgent())

    missing = page.open_task("task-missing", 0)
    unpublished = page.open_task(hidden.task_id, 0)
    response = response_for(page, "GET", "/tasks/" + hidden.task_id, "", 0)

    assert "判断说法" not in missing
    assert "未发布题目" not in unpublished
    assert "未发布解析" not in unpublished
    assert "参考答案" not in unpublished
    assert response.status == 404
    assert "未发布题目" not in body_text(response)
    assert task_id not in page.sessions


def test_failed_session_shows_questions_and_the_next_open_retries():
    catalog, task_id = true_false_catalog()
    decision = FailOnce()
    page = StudentPage(catalog, decision, ScriptedScaffoldAgent())

    first = page.open_task(task_id, 0)

    assert "判断说法" in first
    assert "先看题目" not in first
    assert "<h2>支架</h2>" not in first
    assert task_id not in page.sessions
    assert task_id not in page.shown_at
    assert catalog.get(task_id).started is True

    second = page.open_task(task_id, 5)

    assert "先看题目" in second
    assert task_id in page.sessions


def test_actions_do_nothing_while_the_session_cannot_be_created():
    catalog, task_id = true_false_catalog()
    page = StudentPage(catalog, AlwaysFail(), ScriptedScaffoldAgent())
    page.open_task(task_id, 0)

    edited = page.edit_answer(task_id, 0, selected=("错误",), now=1)
    asked = page.ask(task_id, "旧求助原文", "自己写的", 2)
    submitted = page.submit(task_id, 3)

    assert catalog.work(task_id).answers[0].selected == ()
    assert catalog.work(task_id).dialogue == ()
    assert catalog.get(task_id).submitted is False
    assert "旧求助原文" not in asked
    assert "参考答案" not in submitted
    assert task_id not in page.sessions
    assert "判断说法" in edited
