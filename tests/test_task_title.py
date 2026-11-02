from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import response_for
from tests.teacher_page_helpers import body_text, form


def _page():
    from scaffolding.teacher_page import TeacherPage

    page = TeacherPage(TaskCatalog())
    page.create_task()
    response_for(page, "POST", "/tasks/task-1", form(**{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "selected-0": "正确",
        "explanation-0": "题目里有依据",
        "action": "save",
    }))
    return page


def test_a_task_name_can_change_after_students_start():
    page = _page()
    page.catalog.publish("task-1")
    page.catalog.start("task-1")

    renamed = body_text(response_for(page, "POST", "/tasks/task-1", form(action="改名", title="  网络基础  ")))
    blank = body_text(response_for(page, "POST", "/tasks/task-1", form(action="改名", title="   ")))

    assert page.catalog.get("task-1").title == "网络基础"
    assert page.catalog.get("task-1").questions[0].prompt == "判断说法"
    assert "先填写任务名称" in blank
    assert page.catalog.get("task-1").title == "网络基础"
    assert "学生已开始，只能删除" not in renamed


def test_a_blank_name_does_not_replace_the_task_id():
    page = _page()

    blank = body_text(response_for(page, "POST", "/tasks/task-1", form(action="改名", title="")))

    assert "先填写任务名称" in blank
    assert page.catalog.get("task-1").title == ""
