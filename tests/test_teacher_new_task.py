from scaffolding.teacher_page import TeacherPage, response_for
from tests.teacher_objectives_helpers import text


def test_new_task_offers_manual_and_agent_choices():
    page = TeacherPage()
    listed = text(response_for(page, "GET", "/", ""))
    choice = text(response_for(page, "GET", "/tasks/new", ""))

    assert 'href="/tasks/new"' in listed
    assert ">目标<" not in listed
    assert "<h1>新建任务</h1>" in choice
    assert "手动添加" in choice
    assert 'href="/objectives"' in choice
    assert "智能体生成" in choice
    assert page.catalog._tasks == {}

    created = text(response_for(page, "POST", "/tasks", ""))
    assert "task-1" in created
    assert "未发布" in created
