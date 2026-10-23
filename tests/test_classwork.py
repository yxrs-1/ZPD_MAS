import pytest

from scaffolding.classwork import Classwork, StudentView
from scaffolding.classroom import response_for
from scaffolding.records import OpenQuestion
from scaffolding.roster import Roster, RosterError
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage
from scaffolding.student_page import response_for as student_response_for
from scaffolding.tasks import TaskCatalog
from tests.classroom_helpers import form, room, student_cookie, teacher_cookie, text


def _question():
    return (OpenQuestion("写出组成", "覆盖五类组成"),)


def _world():
    roster = Roster()
    first = roster.create_class("一班")
    second = roster.create_class("二班")
    roster.import_rows(first.class_id, ((2, "s1", "secret", "甲"),))
    roster.import_rows(second.class_id, ((2, "s2", "secret", "乙"),))
    catalog = TaskCatalog()
    task = catalog.create(_question())
    return roster, first, second, catalog, task, Classwork(roster)


def _views(catalog, classwork, first, second):
    view1 = StudentView(catalog, classwork, "s1", first.class_id)
    view2 = StudentView(catalog, classwork, "s2", second.class_id)
    page1 = StudentPage(view1, ScriptedDecisionAgent(), ScriptedScaffoldAgent())
    page2 = StudentPage(view2, ScriptedDecisionAgent(), ScriptedScaffoldAgent())
    return view1, view2, page1, page2


def _open(page, task_id, now):
    return student_response_for(page, "GET", "/tasks/" + task_id, "", now)


def _write(page, task_id, answer, now):
    return student_response_for(
        page, "POST", "/tasks/" + task_id + "/answers", form(**{"text-0": answer}), now
    )


def test_only_a_published_task_can_be_assigned_and_a_missing_class_is_rejected():
    _roster, first, second, catalog, task, classwork = _world()
    other = catalog.create(_question())

    with pytest.raises(RosterError, match="先发布再布置"):
        classwork.assign(catalog, task.task_id, (first.class_id,))
    assert classwork.assigned(task.task_id) == ()

    catalog.publish(task.task_id)
    classwork.assign(catalog, task.task_id, (first.class_id, second.class_id))
    view1, view2, page1, _page2 = _views(catalog, classwork, first, second)
    _open(page1, task.task_id, 1)
    _write(page1, task.task_id, "甲的答案", 2)

    with pytest.raises(RosterError, match="班级不存在"):
        classwork.assign(catalog, task.task_id, (first.class_id, "missing"))

    assert classwork.assigned(task.task_id) == (first.class_id, second.class_id)
    assert classwork.tasks_for_class(first.class_id) == (task.task_id,)
    assert view1.work(task.task_id).answers[0].text == "甲的答案"
    assert classwork.assigned(other.task_id) == ()
    with pytest.raises(RosterError, match="先发布再布置"):
        classwork.assign(catalog, other.task_id, (second.class_id,))


def test_two_students_answer_and_submit_without_sharing_work():
    _roster, first, second, catalog, task, classwork = _world()
    catalog.publish(task.task_id)
    classwork.assign(catalog, task.task_id, (first.class_id, second.class_id))
    view1, view2, page1, page2 = _views(catalog, classwork, first, second)

    assert view1.student_tasks()[0].task_id == task.task_id
    assert view1.student_tasks()[0].status == "待办"
    assert view2.student_tasks()[0].status == "待办"
    assert "覆盖五类组成" in repr(view1.student_tasks()[0])
    assert "参考" not in repr(view1.student_tasks()[0])

    opened = _open(page1, task.task_id, 1)
    assert opened.status == 200
    assert catalog.get(task.task_id).started is True
    assert catalog.get(task.task_id).submitted is False
    _write(page1, task.task_id, "甲的答案", 2)
    _open(page2, task.task_id, 3)
    _write(page2, task.task_id, "乙的答案", 4)
    submitted = student_response_for(page1, "POST", "/tasks/" + task.task_id + "/submit", "", 5)

    assert "已完成" in text(submitted)
    assert view1.student_tasks()[0].status == "已完成"
    assert view2.student_tasks()[0].status == "待办"
    assert view1.work(task.task_id).submitted is True
    assert view1.work(task.task_id).answers[0].text == "甲的答案"
    assert view2.work(task.task_id).submitted is False
    assert view2.work(task.task_id).answers[0].text == "乙的答案"
    assert catalog.get(task.task_id).submitted is False
    assert catalog.get(task.task_id).started is True
    with pytest.raises(KeyError):
        catalog.work(task.task_id)


def test_an_unassigned_task_stays_missing_and_does_not_start():
    page = room()
    headers = teacher_cookie(page)
    response_for(page, "POST", "/teacher/classes", form(action="创建", name="一班"), 0, headers)
    page.roster.import_rows("class-1", ((2, "s1", "secret", "甲"),))
    response_for(page, "POST", "/teacher/tasks", "", 0, headers)
    response_for(page, "POST", "/teacher/tasks", "", 0, headers)
    for task_id, prompt in (("task-1", "写出组成"), ("task-2", "另一题")):
        response_for(page, "POST", "/teacher/tasks/" + task_id, form(**{
            "kind-0": "综合",
            "prompt-0": prompt,
            "requirements-0": "覆盖五类组成",
            "answer-0": "",
            "explanation-0": "",
            "action": "save",
        }), 0, headers)
        response_for(page, "POST", "/teacher/tasks/" + task_id, form(action="publish"), 0, headers)
    page.classwork.assign(page.catalog, "task-1", ("class-1",))

    cookie = student_cookie(page, "s1", "secret", "甲")
    missing = response_for(page, "GET", "/student/tasks/task-2", "", 1, cookie)
    listed = text(response_for(page, "GET", "/student", "", 2, cookie))

    assert missing.status == 404
    assert "任务不存在" in text(missing)
    assert "task-2" not in listed
    assert "task-1" in listed
    assert page.catalog.get("task-2").started is False
    assert page.student.sessions == {}


def test_removing_one_class_hides_that_class_and_keeps_the_other_answer():
    _roster, first, second, catalog, task, classwork = _world()
    catalog.publish(task.task_id)
    classwork.assign(catalog, task.task_id, (first.class_id,))
    view1, view2, page1, page2 = _views(catalog, classwork, first, second)
    _open(page1, task.task_id, 1)
    _write(page1, task.task_id, "甲的答案", 2)
    assert catalog.get(task.task_id).started is True

    classwork.assign(catalog, task.task_id, (first.class_id, second.class_id))
    assert catalog.get(task.task_id).started is True
    _open(page2, task.task_id, 3)
    _write(page2, task.task_id, "乙的答案", 4)

    classwork.assign(catalog, task.task_id, (second.class_id,))
    missing = _open(page1, task.task_id, 5)

    assert missing.status == 404
    assert "任务不存在" in text(missing)
    assert view1.student_tasks() == ()
    with pytest.raises(KeyError):
        view1.work(task.task_id)
    assert view2.work(task.task_id).answers[0].text == "乙的答案"
    assert catalog.get(task.task_id).started is True


def test_an_empty_assignment_idles_the_task_once_answers_are_gone():
    _roster, first, second, catalog, task, classwork = _world()
    catalog.publish(task.task_id)
    classwork.assign(catalog, task.task_id, (first.class_id, second.class_id))
    view1, view2, page1, page2 = _views(catalog, classwork, first, second)
    _open(page1, task.task_id, 1)
    _write(page1, task.task_id, "甲的答案", 2)
    _open(page2, task.task_id, 3)

    classwork.drop_student("s1")
    with pytest.raises(KeyError):
        view1.work(task.task_id)
    assert view2.work(task.task_id).task_id == task.task_id
    assert catalog.get(task.task_id).started is True

    classwork.assign(catalog, task.task_id, ())

    assert classwork.assigned(task.task_id) == ()
    assert classwork.any_started(task.task_id) is False
    with pytest.raises(KeyError):
        view2.work(task.task_id)
    assert catalog.get(task.task_id).started is False


def test_drop_class_and_drop_task_remove_answers_and_assignment():
    _roster, first, second, catalog, task, classwork = _world()
    catalog.publish(task.task_id)
    classwork.assign(catalog, task.task_id, (first.class_id, second.class_id))
    view1, _view2, page1, _page2 = _views(catalog, classwork, first, second)
    _open(page1, task.task_id, 1)
    _write(page1, task.task_id, "甲的答案", 2)

    classwork.drop_class(first.class_id)

    assert first.class_id not in classwork.assigned(task.task_id)
    assert classwork.assigned(task.task_id) == (second.class_id,)
    with pytest.raises(KeyError):
        view1.work(task.task_id)
    assert catalog.get(task.task_id).started is False

    classwork.drop_task(task.task_id)
    assert classwork.assigned(task.task_id) == ()
    assert classwork.tasks_for_class(second.class_id) == ()
    assert classwork.any_started(task.task_id) is False


def test_the_teacher_page_assigns_the_selected_classes():
    page = room()
    headers = teacher_cookie(page)
    response_for(page, "POST", "/teacher/classes", form(action="创建", name="一班"), 0, headers)
    response_for(page, "POST", "/teacher/classes", form(action="创建", name="二班"), 0, headers)
    page.roster.import_rows("class-1", ((2, "s1", "secret", "甲"),))
    page.roster.import_rows("class-2", ((2, "s2", "secret", "乙"),))
    response_for(page, "POST", "/teacher/tasks", "", 0, headers)
    response_for(page, "POST", "/teacher/tasks/task-1", form(**{
        "kind-0": "综合",
        "prompt-0": "写出组成",
        "requirements-0": "覆盖五类组成",
        "answer-0": "参考",
        "explanation-0": "解析",
        "action": "save",
    }), 0, headers)

    draft = text(response_for(page, "GET", "/teacher/tasks/task-1", "", 0, headers))
    refused = text(response_for(
        page, "POST", "/teacher/tasks/task-1", form(action="布置", class_id="class-1"), 0, headers
    ))

    assert 'name="class_id"' not in draft
    assert "先发布再布置" in refused
    assert page.classwork.assigned("task-1") == ()

    response_for(page, "POST", "/teacher/tasks/task-1", form(action="publish"), 0, headers)
    opened = text(response_for(page, "GET", "/teacher/tasks/task-1", "", 0, headers))
    chosen = text(response_for(
        page, "POST", "/teacher/tasks/task-1", form(action="布置", class_id="class-1"), 0, headers
    ))

    assert opened.count('name="class_id"') == 2
    assert "一班" in opened and "二班" in opened
    assert page.classwork.assigned("task-1") == ("class-1",)
    assert 'value="class-1" checked' in chosen
    assert 'value="class-2" checked' not in chosen

    cookie = student_cookie(page, "s1", "secret", "甲")
    response_for(page, "GET", "/student/tasks/task-1", "", 1, cookie)
    response_for(page, "POST", "/student/tasks/task-1/answers", form(**{"text-0": "甲的答案"}), 2, cookie)
    assert page.catalog.get("task-1").started is True
    started = text(response_for(page, "GET", "/teacher/tasks/task-1", "", 3, headers))
    added = text(response_for(
        page, "POST", "/teacher/tasks/task-1", form(action="布置", class_id=("class-1", "class-2")), 4, headers
    ))
    locked = text(response_for(page, "POST", "/teacher/tasks/task-1", form(**{
        "kind-0": "综合",
        "prompt-0": "不该写入",
        "requirements-0": "覆盖五类组成",
        "answer-0": "参考",
        "explanation-0": "解析",
        "action": "save",
    }), 5, headers))

    assert "已开始" in started
    assert started.count('name="class_id"') == 2
    assert page.classwork.assigned("task-1") == ("class-1", "class-2")
    assert 'value="class-2" checked' in added
    assert "学生已开始，只能删除" in locked
    assert page.catalog.get("task-1").questions[0].prompt == "写出组成"
    other = student_cookie(page, "s2", "secret", "乙")
    second = text(response_for(page, "GET", "/student", "", 6, other))
    assert "task-1" in second
    assert "甲的答案" not in second

    rejected = text(response_for(
        page, "POST", "/teacher/tasks/task-1", form(action="布置", class_id=("class-2", "missing")), 7, headers
    ))
    assert "班级不存在" in rejected
    assert page.classwork.assigned("task-1") == ("class-1", "class-2")
    assert page.student_pages["s1"].catalog.work("task-1").answers[0].text == "甲的答案"

    cleared = text(response_for(page, "POST", "/teacher/tasks/task-1", form(action="布置"), 8, headers))
    assert page.classwork.assigned("task-1") == ()
    assert page.classwork.any_started("task-1") is False
    assert page.catalog.get("task-1").started is False
    assert "已发布" in cleared
    assert "已开始" not in cleared
    gone = response_for(page, "GET", "/student/tasks/task-1", "", 9, cookie)
    assert gone.status == 404
    assert page.catalog.get("task-1").started is False

    response_for(page, "POST", "/teacher/tasks/task-1", form(action="布置", class_id="class-1"), 10, headers)
    reopened = text(response_for(page, "GET", "/student/tasks/task-1", "", 11, cookie))
    assert "写出组成" in reopened
    assert "甲的答案" not in reopened
    assert page.catalog.get("task-1").started is True
    assert page.student_pages["s1"].catalog.work("task-1").answers[0].text == ""


def test_a_remove_posted_to_another_class_keeps_the_student_answer():
    page = room()
    headers = teacher_cookie(page)
    response_for(page, "POST", "/teacher/classes", form(action="创建", name="一班"), 0, headers)
    response_for(page, "POST", "/teacher/classes", form(action="创建", name="二班"), 0, headers)
    page.roster.import_rows("class-1", ((2, "s1", "secret", "甲"),))
    page.roster.import_rows("class-2", ((2, "s2", "secret", "乙"),))
    response_for(page, "POST", "/teacher/tasks", "", 0, headers)
    response_for(page, "POST", "/teacher/tasks/task-1", form(**{
        "kind-0": "综合",
        "prompt-0": "写出组成",
        "requirements-0": "覆盖五类组成",
        "answer-0": "",
        "explanation-0": "",
        "action": "save",
    }), 0, headers)
    response_for(page, "POST", "/teacher/tasks/task-1", form(action="publish"), 0, headers)
    page.classwork.assign(page.catalog, "task-1", ("class-1",))
    cookie = student_cookie(page, "s1", "secret", "甲")
    response_for(page, "GET", "/student/tasks/task-1", "", 1, cookie)
    response_for(page, "POST", "/student/tasks/task-1/answers", form(**{"text-0": "甲的答案"}), 2, cookie)

    missing = response_for(
        page, "POST", "/teacher/classes/class-2/students/s1", form(action="移除"), 3, headers
    )

    assert missing.status == 404
    assert "学生不存在" in text(missing)
    assert page.student_pages["s1"].catalog.work("task-1").answers[0].text == "甲的答案"
    assert page.roster.authenticate_student("s1", "secret") is not None


def test_a_student_moved_to_another_class_sees_that_class_task():
    page = room()
    headers = teacher_cookie(page)
    response_for(page, "POST", "/teacher/classes", form(action="创建", name="一班"), 0, headers)
    response_for(page, "POST", "/teacher/classes", form(action="创建", name="二班"), 0, headers)
    page.roster.import_rows("class-1", ((2, "s1", "secret", "甲"),))
    response_for(page, "POST", "/teacher/tasks", "", 0, headers)
    response_for(page, "POST", "/teacher/tasks", "", 0, headers)
    for task_id, prompt in (("task-1", "写出组成"), ("task-2", "另一题")):
        response_for(page, "POST", "/teacher/tasks/" + task_id, form(**{
            "kind-0": "综合",
            "prompt-0": prompt,
            "requirements-0": "覆盖五类组成",
            "answer-0": "",
            "explanation-0": "",
            "action": "save",
        }), 0, headers)
        response_for(page, "POST", "/teacher/tasks/" + task_id, form(action="publish"), 0, headers)
    page.classwork.assign(page.catalog, "task-1", ("class-1",))
    cookie = student_cookie(page, "s1", "secret", "甲")
    response_for(page, "GET", "/student/tasks/task-1", "", 1, cookie)

    response_for(
        page, "POST", "/teacher/classes/class-1/students/s1", form(action="移除"), 2, headers
    )
    page.roster.import_rows("class-2", ((2, "s1", "secret", "甲"),))
    page.classwork.assign(page.catalog, "task-2", ("class-2",))

    listed = text(response_for(page, "GET", "/student", "", 3, cookie))

    assert "task-2" in listed
    assert "待办" in listed
    assert "task-1" not in listed
