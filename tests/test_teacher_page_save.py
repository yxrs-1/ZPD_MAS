from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage, response_for
from tests.teacher_page_helpers import body_text, form


def _post(page, task_id, **fields):
    return response_for(page, "POST", "/tasks/" + task_id, form(**fields))


def _valid_fields():
    return {
        "kind-0": "单选",
        "prompt-0": "选出<人员>",
        "option-0-0": "人员",
        "option-0-1": "<硬件>",
        "selected-0": "0",
        "explanation-0": "选择依据",
        "kind-1": "多选",
        "prompt-1": "选出组成",
        "option-1-0": "人员",
        "option-1-1": "硬件",
        "selected-1": ["0", "1"],
        "explanation-1": "多选依据",
        "kind-2": "判断",
        "prompt-2": "判断说法",
        "selected-2": "正确",
        "explanation-2": "题目里有依据",
        "kind-3": "综合",
        "prompt-3": "完成作品",
        "requirements-3": "写明人员",
        "answer-3": "",
        "explanation-3": "",
        "action": "save",
    }


def test_saving_a_valid_draft_updates_the_catalog_and_clears_the_draft():
    page = TeacherPage(TaskCatalog())
    page.create_task()

    html = body_text(_post(page, "task-1", **_valid_fields()))
    questions = page.catalog.get("task-1").questions

    assert "task-1" not in page.drafts
    assert 'value="publish"' in html
    assert 'value="abandon"' not in html
    assert "选出&lt;人员&gt;" in html
    assert "<人员>" not in html
    assert isinstance(questions[0], ChoiceQuestion)
    assert questions[0].selection == SelectionMode.SINGLE
    assert questions[0].choices == ("人员", "<硬件>")
    assert isinstance(questions[1], ChoiceQuestion)
    assert questions[1].selection == SelectionMode.MULTIPLE
    assert questions[1].answer == ("人员", "硬件")
    assert isinstance(questions[2], TrueFalseQuestion)
    assert questions[2].answer == "正确"
    assert isinstance(questions[3], OpenQuestion)
    assert questions[3].answer == ""
    assert questions[3].explanation == ""
    hidden_save = '<button type="submit" name="action" value="save" hidden>保存</button>'
    assert html.index(hidden_save) < html.index('value="down-option:')


def test_an_invalid_question_keeps_the_catalog_and_the_draft():
    page = TeacherPage(TaskCatalog())
    page.create_task()

    html = body_text(_post(page, "task-1", **{
        "kind-0": "单选",
        "prompt-0": "   ",
        "option-0-0": "人员",
        "option-0-1": "硬件",
        "selected-0": "0",
        "explanation-0": "选择依据",
        "action": "save",
    }))

    assert page.catalog.get("task-1").questions == ()
    assert "task-1" in page.drafts
    assert "题目不合格，原任务保持不变" in html
    assert 'value="publish"' not in html


def test_a_removed_option_that_is_still_selected_is_rejected():
    page = TeacherPage(TaskCatalog())
    page.create_task()

    html = body_text(_post(page, "task-1", **{
        "kind-0": "单选",
        "prompt-0": "选出人员",
        "option-0-0": "人员",
        "option-0-1": "硬件",
        "selected-0": "0",
        "explanation-0": "选择依据",
        "action": "delete-option:0:0",
    }))

    draft = page.drafts["task-1"][0]
    assert "人员" not in draft.options
    assert "人员" in draft.selected
    assert '<input type="radio" name="selected-0" value="s:人员" checked>人员' in html
    assert '<input type="hidden" name="selected-0"' not in html

    saved = body_text(_post(page, "task-1", **{
        "kind-0": "单选",
        "prompt-0": "选出人员",
        "option-0-0": "硬件",
        "selected-0": "s:人员",
        "explanation-0": "选择依据",
        "action": "save",
    }))

    assert "题目不合格，原任务保持不变" in saved
    assert page.catalog.get("task-1").questions == ()
    assert "task-1" in page.drafts
    assert page.drafts["task-1"][0].selected == ("人员",)


def test_replacing_a_deleted_choice_answer_saves_the_remaining_option():
    page = TeacherPage(TaskCatalog())
    page.create_task()
    _post(page, "task-1", **{
        "kind-0": "单选",
        "prompt-0": "选出人员",
        "option-0-0": "人员",
        "option-0-1": "硬件",
        "option-0-2": "软件",
        "selected-0": "0",
        "explanation-0": "选择依据",
        "action": "delete-option:0:0",
    })

    _post(page, "task-1", **{
        "kind-0": "单选",
        "prompt-0": "选出人员",
        "option-0-0": "硬件",
        "option-0-1": "软件",
        "selected-0": "0",
        "explanation-0": "选择依据",
        "action": "save",
    })

    question = page.catalog.get("task-1").questions[0]
    assert question.answer == ("硬件",)
    assert "task-1" not in page.drafts


def test_a_stale_numeric_selected_text_is_not_mapped_to_an_option_index():
    page = TeacherPage(TaskCatalog())
    page.create_task()

    html = body_text(_post(page, "task-1", **{
        "kind-0": "单选",
        "prompt-0": "选出编号",
        "option-0-0": "0",
        "option-0-1": "2",
        "selected-0": "s:1",
        "explanation-0": "选择依据",
        "action": "save",
    }))

    assert "题目不合格，原任务保持不变" in html
    assert page.catalog.get("task-1").questions == ()
    assert "task-1" in page.drafts
    assert page.drafts["task-1"][0].selected == ("1",)
    assert page.drafts["task-1"][0].options == ("0", "2")


def test_saving_maps_a_choice_index_to_the_edited_option_text():
    page = TeacherPage(TaskCatalog())
    page.create_task()

    html = body_text(_post(page, "task-1", **{
        "kind-0": "单选",
        "prompt-0": "选出人员",
        "option-0-0": "改后的选项",
        "option-0-1": "硬件",
        "selected-0": "0",
        "explanation-0": "选择依据",
        "action": "save",
    }))

    question = page.catalog.get("task-1").questions[0]
    assert question.answer == ("改后的选项",)
    assert 'type="radio" name="selected-0" value="0"' in html
    assert 'name="selected-0" value="改后的选项"' not in html


def test_an_unpublished_task_can_be_saved_with_no_questions():
    page = TeacherPage(TaskCatalog())
    page.create_task()
    _post(page, "task-1", action="add:单选")

    html = body_text(_post(page, "task-1", action="save"))

    assert page.catalog.get("task-1").questions == ()
    assert "task-1" not in page.drafts
    assert "题目不合格" not in html
