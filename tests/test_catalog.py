import pytest

from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.tasks import ListedQuestion, TaskCatalog


def _questions():
    return (
        ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "天气"), ("人员",), "人员是组成"),
        TrueFalseQuestion("网络负责传送", "正确", "网络是通道"),
        OpenQuestion("写出组成", "覆盖五类组成"),
    )


def test_student_sees_only_published_tasks_as_todo_without_keys():
    catalog = TaskCatalog()
    draft = catalog.create(_questions())
    visible = catalog.create(_questions())
    catalog.publish(visible.task_id)

    assert catalog.student_tasks() == (
        catalog.student_tasks()[0],
    )
    listed = catalog.student_tasks()[0]
    assert listed.task_id == visible.task_id
    assert listed.status == "待办"
    assert listed.questions[0] == ListedQuestion("选出人员", ("人员", "天气"), selection="单选")
    assert listed.questions[1] == ListedQuestion("网络负责传送", ("正确", "错误"))
    assert listed.questions[2] == ListedQuestion("写出组成", requirements="覆盖五类组成")
    assert "人员是组成" not in repr(listed)
    assert draft.task_id not in [item.task_id for item in catalog.student_tasks()]


def test_teacher_can_edit_before_a_student_starts_and_can_delete():
    catalog = TaskCatalog()
    task = catalog.create(_questions())
    catalog.publish(task.task_id)
    revised = (OpenQuestion("改后的综合题", "只写网络"),)
    updated = catalog.update(task.task_id, revised)

    assert updated.published is True
    assert updated.questions == revised
    catalog.delete(task.task_id)
    assert catalog.student_tasks() == ()


def test_started_task_cannot_be_edited_and_delete_removes_it():
    catalog = TaskCatalog()
    task = catalog.create(_questions())
    catalog.publish(task.task_id)
    catalog.start(task.task_id)

    with pytest.raises(Exception):
        catalog.update(task.task_id, (OpenQuestion("不能改", "不能改"),))
    assert catalog.get(task.task_id).questions[0].prompt == "选出人员"
    catalog.delete(task.task_id)
    with pytest.raises(KeyError):
        catalog.get(task.task_id)


def test_empty_task_cannot_be_published_or_started():
    catalog = TaskCatalog()
    task = catalog.create(())

    with pytest.raises(Exception):
        catalog.publish(task.task_id)
    with pytest.raises(Exception):
        catalog.start(task.task_id)
