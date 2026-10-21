from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage, response_for
from tests.teacher_page_helpers import body_text, form


def _post(page, task_id, **fields):
    return response_for(page, "POST", "/tasks/" + task_id, form(**fields))


def test_adding_a_question_keeps_a_draft_and_shows_only_that_kinds_fields():
    page = TeacherPage(TaskCatalog())
    page.create_task()

    single = _post(page, "task-1", action="add:单选")
    assert 'value="单选"' in body_text(single)
    assert 'value="add-option:0"' in body_text(single)
    assert 'name="requirements-0"' not in body_text(single)
    assert 'value="up:0"' not in body_text(single)
    assert 'value="down:0"' not in body_text(single)
    assert page.catalog.get("task-1").questions == ()

    multiple = _post(page, "task-1", **{"kind-0": "单选", "prompt-0": "第一", "action": "add:多选"})
    assert 'type="checkbox"' in body_text(multiple)
    assert 'value="第一"' in body_text(multiple)

    judgement = _post(page, "task-1", **{
        "kind-0": "单选", "prompt-0": "第一", "kind-1": "多选", "action": "add:判断",
    })
    assert "正确" in body_text(judgement)
    assert "错误" in body_text(judgement)
    assert 'value="add-option:2"' not in body_text(judgement)

    opened = _post(page, "task-1", **{
        "kind-0": "单选", "prompt-0": "第一",
        "kind-1": "多选",
        "kind-2": "判断",
        "action": "add:综合",
    })
    html = body_text(opened)
    assert 'name="requirements-3"' in html
    assert 'name="answer-3"' in html
    assert 'value="add-option:3"' not in html
    again = body_text(response_for(page, "GET", "/tasks/task-1", ""))
    assert 'value="第一"' in again
    assert page.catalog.get("task-1").questions == ()


def test_an_unknown_kind_does_not_add_a_question():
    page = TeacherPage(TaskCatalog())
    page.create_task()

    html = body_text(_post(page, "task-1", action="add:课外"))

    assert "课外" not in html
    assert page.catalog.get("task-1").questions == ()


def test_options_and_questions_move_only_inside_their_ends():
    page = TeacherPage(TaskCatalog())
    page.create_task()
    _post(page, "task-1", action="add:单选")
    added = _post(page, "task-1", **{
        "kind-0": "单选",
        "prompt-0": "选出<人员>",
        "action": "add-option:0",
    })
    assert "选出&lt;人员&gt;" in body_text(added)
    assert "<人员>" not in body_text(added)
    assert 'name="option-0-0"' in body_text(added)
    _post(page, "task-1", **{
        "kind-0": "单选",
        "prompt-0": "选出<人员>",
        "option-0-0": "人员",
        "action": "add-option:0",
    })
    moved = _post(page, "task-1", **{
        "kind-0": "单选",
        "prompt-0": "选出<人员>",
        "option-0-0": "人员",
        "option-0-1": "硬件",
        "action": "up-option:0:1",
    })
    text = body_text(moved)
    assert text.index('value="硬件"') < text.index('value="人员"')
    assert 'value="up-option:0:0"' not in text
    assert 'value="down-option:0:1"' not in text
    stayed = _post(page, "task-1", **{
        "kind-0": "单选",
        "prompt-0": "选出<人员>",
        "option-0-0": "硬件",
        "option-0-1": "人员",
        "action": "up-option:0:0",
    })
    stayed_text = body_text(stayed)
    assert stayed_text.index('value="硬件"') < stayed_text.index('value="人员"')

    _post(page, "task-1", **{
        "kind-0": "单选", "prompt-0": "第一", "action": "add:判断",
    })
    swapped = _post(page, "task-1", **{
        "kind-0": "单选", "prompt-0": "第一",
        "kind-1": "判断", "prompt-1": "第二",
        "action": "down:0",
    })
    order = body_text(swapped)
    assert order.index('value="第二"') < order.index('value="第一"')
    untouched = _post(page, "task-1", **{
        "kind-0": "判断", "prompt-0": "第二",
        "kind-1": "单选", "prompt-1": "第一",
        "action": "up:0",
    })
    assert body_text(untouched).index('value="第二"') < body_text(untouched).index('value="第一"')
    assert page.catalog.get("task-1").questions == ()


def test_option_actions_on_a_true_false_question_do_not_add_options():
    page = TeacherPage(TaskCatalog())
    page.create_task()
    _post(page, "task-1", action="add:判断")

    html = body_text(_post(page, "task-1", **{"kind-0": "判断", "prompt-0": "判断说法", "action": "add-option:0"}))

    assert 'name="option-0-0"' not in html
    assert page.catalog.get("task-1").questions == ()
