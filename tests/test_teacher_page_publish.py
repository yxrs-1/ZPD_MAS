from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage, response_for
from tests.teacher_page_helpers import body_text, form


def _post(page, task_id, **fields):
    return response_for(page, "POST", "/tasks/" + task_id, form(**fields))


def test_an_empty_task_cannot_be_published_and_a_draft_must_be_saved_first():
    page = TeacherPage(TaskCatalog())
    page.create_task()

    empty = body_text(_post(page, "task-1", action="publish"))

    assert "没有题目，不能发布" in empty
    assert page.catalog.get("task-1").published is False
    _post(page, "task-1", action="add:判断")
    _post(page, "task-1", **{"kind-0": "判断", "prompt-0": "判断说法", "action": "add-option:0"})
    drafted = body_text(_post(page, "task-1", action="publish"))
    assert "先保存再发布" in drafted
    assert page.catalog.get("task-1").published is False
    assert page.drafts["task-1"][0].prompt == "判断说法"
    assert page.drafts["task-1"][0].options == ()


def test_publish_then_edit_then_publish_again():
    page = TeacherPage(TaskCatalog())
    page.create_task()
    _post(page, "task-1", **{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "selected-0": "正确",
        "explanation-0": "题目里有依据",
        "action": "save",
    })

    published = body_text(_post(page, "task-1", action="publish"))
    listed = body_text(response_for(page, "GET", "/", ""))

    assert "已发布" in published
    assert "没有题目，不能发布" not in published
    assert "已发布" in listed
    assert page.catalog.get("task-1").published is True
    edited = body_text(_post(page, "task-1", **{
        "kind-0": "判断",
        "prompt-0": "改后的说法",
        "selected-0": "错误",
        "explanation-0": "题目里有依据",
        "action": "save",
    }))
    assert "改后的说法" in edited
    assert page.catalog.get("task-1").published is True
    assert page.catalog.get("task-1").questions[0].prompt == "改后的说法"
    assert page.catalog.get("task-1").questions[0].answer == "错误"
    assert "task-1" not in page.drafts
    again = body_text(_post(page, "task-1", action="publish"))
    assert "已发布" in again
    assert "没有题目，不能发布" not in again
    assert "先保存再发布" not in again


def test_abandoning_a_draft_returns_the_saved_questions():
    page = TeacherPage(TaskCatalog())
    page.create_task()
    _post(page, "task-1", **{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "selected-0": "正确",
        "explanation-0": "题目里有依据",
        "action": "save",
    })
    _post(page, "task-1", **{"kind-0": "判断", "prompt-0": "判断说法", "action": "add:单选"})

    html = body_text(_post(page, "task-1", action="abandon"))

    assert "task-1" not in page.drafts
    assert 'value="判断说法"' in html
    assert 'value="publish"' in html
    assert 'value="abandon"' not in html
    assert page.catalog.get("task-1").questions[0].prompt == "判断说法"


def test_clearing_a_published_task_is_rejected_and_publish_still_sees_the_draft():
    page = TeacherPage(TaskCatalog())
    page.create_task()
    _post(page, "task-1", **{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "selected-0": "正确",
        "explanation-0": "题目里有依据",
        "action": "save",
    })
    _post(page, "task-1", action="publish")
    _post(page, "task-1", **{"kind-0": "判断", "prompt-0": "判断说法", "action": "delete:0"})

    saved = body_text(_post(page, "task-1", action="save"))
    published = body_text(_post(page, "task-1", action="publish"))

    assert page.catalog.get("task-1").questions[0].prompt == "判断说法"
    assert "已发布的任务至少留一题" in saved
    assert "task-1" in page.drafts
    assert "先保存再发布" in published
    assert page.catalog.get("task-1").published is True
