from scaffolding.records import TrueFalseQuestion
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage


def test_the_teacher_prefix_is_written_on_list_and_task_links():
    catalog = TaskCatalog()
    task = catalog.create((TrueFalseQuestion("判断说法", "正确", "题目里有依据"),))
    catalog.publish(task.task_id)
    catalog.start(task.task_id)
    page = TeacherPage(catalog, prefix="/teacher")

    listed = page.list_tasks()
    opened = page.open_task(task.task_id)

    assert 'href="/teacher/tasks/task-1"' in listed
    assert 'href="/teacher/tasks/new"' in listed
    assert 'action="/teacher/tasks/task-1"' in opened
    assert 'action="/tasks"' not in listed
    assert 'action="/tasks/task-1"' not in opened
