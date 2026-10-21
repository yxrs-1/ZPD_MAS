import pytest

from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import DraftQuestion, TeacherPage, response_for
from tests.teacher_page_helpers import body_text, form


def _started_page():
    page = TeacherPage(TaskCatalog())
    page.create_task()
    response_for(page, "POST", "/tasks/task-1", form(**{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "selected-0": "正确",
        "explanation-0": "题目里有依据",
        "action": "save",
    }))
    page.catalog.publish("task-1")
    page.catalog.start("task-1")
    page.drafts["task-1"] = (DraftQuestion("单选", prompt="隐藏草稿"),)
    return page


def test_a_started_task_is_read_only_and_a_mutation_does_not_touch_the_draft():
    page = _started_page()

    opened = body_text(response_for(page, "GET", "/tasks/task-1", ""))
    listed = body_text(response_for(page, "GET", "/", ""))
    posted = body_text(response_for(page, "POST", "/tasks/task-1", form(**{
        "kind-0": "判断",
        "prompt-0": "不该写入",
        "action": "save",
    })))

    assert "已开始" in opened
    assert "已开始" in listed
    assert "<input" not in opened
    assert 'value="save"' not in opened
    assert 'value="publish"' not in opened
    assert 'value="delete"' in opened
    assert "判断说法" in opened
    assert "参考答案：正确" in opened
    assert "解析：题目里有依据" in opened
    assert "隐藏草稿" not in opened
    assert "不该写入" not in posted
    assert "学生已开始，只能删除" in posted
    assert page.drafts["task-1"] == (DraftQuestion("单选", prompt="隐藏草稿"),)
    assert page.catalog.get("task-1").questions[0].prompt == "判断说法"


def test_delete_removes_the_task_its_work_and_its_draft():
    page = _started_page()

    deleted = body_text(response_for(page, "POST", "/tasks/task-1", form(action="delete")))
    missing = response_for(page, "GET", "/tasks/task-1", "")

    assert "task-1" not in deleted
    assert "新建" in deleted
    assert "task-1" not in page.drafts
    with pytest.raises(KeyError):
        page.catalog.get("task-1")
    with pytest.raises(KeyError):
        page.catalog.work("task-1")
    assert missing.status == 404
    assert "任务不存在" in body_text(missing)
    posted = response_for(page, "POST", "/tasks/task-1", form(action="delete"))
    assert posted.status == 404
    assert "任务不存在" in body_text(posted)
