import pytest

from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.tasks import TaskCatalog


def test_each_question_starts_blank_and_keeps_its_own_revision():
    catalog = TaskCatalog()
    task = catalog.create(
        (
            ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "天气"), ("人员",), "人员是组成"),
            ChoiceQuestion("选出组成", SelectionMode.MULTIPLE, ("人员", "硬件"), ("人员", "硬件"), "两项都是"),
            TrueFalseQuestion("网络负责传送", "错误", "网络是通道"),
            OpenQuestion("写出组成", "覆盖五类组成"),
        )
    )
    catalog.publish(task.task_id)
    work = catalog.start(task.task_id)

    assert all(answer.text == "" and answer.selected == () for answer in work.answers)
    work.edit(0, selected=("人员",))
    work.edit(0, selected=("天气",))
    work.edit(1, selected=("硬件", "人员"))
    work.edit(2, selected=("正确",))
    work.edit(3, text="只写了人员")

    assert work.answers[0].selected == ("天气",)
    assert work.answers[0].selected_revisions == ((), ("人员",))
    assert work.answers[1].selected == ("硬件", "人员")
    assert work.answers[2].selected == ("正确",)
    assert work.answers[3].text == "只写了人员"
    assert work.answers[3].text_revisions == ("",)


@pytest.mark.parametrize(
    ("index", "kwargs"),
    [
        (0, {"selected": ("人员", "天气")}),
        (0, {"selected": ("教室",)}),
        (1, {"selected": ("教室",)}),
        (2, {"selected": ("也许",)}),
        (2, {"text": "一段文字"}),
        (3, {"selected": ("人员",)}),
    ],
)
def test_invalid_answers_leave_the_previous_answer(index: int, kwargs: dict):
    catalog = TaskCatalog()
    task = catalog.create(
        (
            ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "天气"), ("人员",), "人员是组成"),
            ChoiceQuestion("选出组成", SelectionMode.MULTIPLE, ("人员", "硬件"), ("人员", "硬件"), "两项都是"),
            TrueFalseQuestion("网络负责传送", "正确", "网络是通道"),
            OpenQuestion("写出组成", "覆盖五类组成"),
        )
    )
    catalog.publish(task.task_id)
    work = catalog.start(task.task_id)
    before = work.answers[index]

    with pytest.raises(Exception):
        work.edit(index, **kwargs)

    assert work.answers[index] == before


def test_delete_removes_the_student_work():
    catalog = TaskCatalog()
    task = catalog.create((OpenQuestion("写出组成", "覆盖五类组成"),))
    catalog.publish(task.task_id)
    catalog.start(task.task_id)

    catalog.delete(task.task_id)

    with pytest.raises(KeyError):
        catalog.work(task.task_id)
