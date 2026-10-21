from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage, response_for
from tests.teacher_page_helpers import body_text


def _page():
    catalog = TaskCatalog()
    task = catalog.create((
        ChoiceQuestion("选出<人员>", SelectionMode.SINGLE, ("人员", "<硬件>"), ("人员",), "选择依据"),
        ChoiceQuestion("选出组成", SelectionMode.MULTIPLE, ("人员", "硬件"), ("人员", "硬件"), "多选依据"),
        TrueFalseQuestion("判断说法", "正确", "题目里有依据"),
        OpenQuestion("完成作品", "写明人员", "", ""),
    ))
    catalog.publish(task.task_id)
    return TeacherPage(catalog), task.task_id


def test_opening_a_task_shows_its_fact_and_only_each_questions_fields():
    page, task_id = _page()

    html = body_text(response_for(page, "GET", "/tasks/" + task_id, ""))

    assert "已发布" in html
    assert "待办" not in html
    assert "选出&lt;人员&gt;" in html
    assert "<人员>" not in html
    assert "&lt;硬件&gt;" in html
    assert "<硬件>" not in html
    assert 'type="radio"' in html
    assert 'type="checkbox"' in html
    assert "判断说法" in html
    assert "正确" in html
    assert "错误" in html
    assert "完成作品" in html
    assert 'name="requirements-3"' in html
    assert 'name="answer-3" value=""' in html
    assert 'value="publish"' in html
    assert 'value="save"' in html
    assert 'value="delete"' in html
    assert 'value="abandon"' not in html
    assert 'value="add:单选"' in html
    assert 'value="add:多选"' in html
    assert 'value="add:判断"' in html
    assert 'value="add:综合"' in html
    assert page.drafts == {}


def test_a_missing_task_shows_no_questions():
    page = TeacherPage(TaskCatalog())

    opened = response_for(page, "GET", "/tasks/missing", "")
    posted = response_for(page, "POST", "/tasks/missing", "action=save")

    assert opened.status == 404
    assert "任务不存在" in body_text(opened)
    assert "选出" not in body_text(opened)
    assert "参考答案" not in body_text(opened)
    assert posted.status == 404
    assert "任务不存在" in body_text(posted)
