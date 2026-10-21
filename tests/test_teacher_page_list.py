from scaffolding.records import ChoiceQuestion, SelectionMode
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage, response_for
from tests.teacher_page_helpers import body_text


def test_an_empty_catalog_lists_no_tasks_and_create_enters_an_unpublished_task():
    page = TeacherPage(TaskCatalog())

    empty = response_for(page, "GET", "/", "", )
    created = response_for(page, "POST", "/tasks", "")
    listed = response_for(page, "GET", "/", "")

    assert "<li>" not in body_text(empty)
    assert "新建" in body_text(empty)
    assert "task-1" in body_text(created)
    assert "未发布" in body_text(created)
    assert "待办" not in body_text(created)
    assert "已完成" not in body_text(created)
    task = page.catalog.get("task-1")
    assert task.questions == ()
    assert task.published is False
    assert 'href="/tasks/task-1"' in body_text(listed)


def test_the_list_is_in_creation_order_and_hides_question_text():
    catalog = TaskCatalog()
    catalog.create((
        ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "硬件"), ("人员",), "选择依据"),
    ))
    page = TeacherPage(catalog)
    page.create_task()

    listed = body_text(response_for(page, "GET", "/", ""))

    assert listed.index("task-1") < listed.index("task-2")
    assert "未发布" in listed
    assert "选出人员" not in listed
    assert "选择依据" not in listed
    assert "参考答案" not in listed
