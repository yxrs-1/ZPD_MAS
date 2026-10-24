from scaffolding import classroom
from scaffolding.records import TrueFalseQuestion
from scaffolding.tasks import StudentWork
from scaffolding.teacher_page import response_for
from tests.classroom_helpers import form, room, student_cookie, text


def test_accounts_lists_students_and_resets_a_password():
    page = room()
    first = page.roster.create_class("一班")
    page.roster.import_rows(first.class_id, ((2, "s1", "secret", "甲"),))

    opened = text(response_for(page.teacher, "GET", "/accounts", ""))
    assert "<h1>账号管理</h1>" in opened
    assert "甲" in opened and "s1" in opened and "一班" in opened

    empty = text(response_for(page.teacher, "POST", "/accounts", form(action="重置密码", account="s1", password="  ")))
    assert "密码不能为空" in empty
    assert page.roster.student(first.class_id, "s1").password == "secret"
    missing = text(response_for(page.teacher, "POST", "/accounts", form(action="重置密码", account="none", password="next")))
    assert "学生不存在" in missing
    changed = text(response_for(page.teacher, "POST", "/accounts", form(action="重置密码", account="s1", password="next")))
    assert "密码已重置" in changed
    assert page.roster.student(first.class_id, "s1").password == "next"


def test_moving_class_keeps_the_answer_and_follows_the_new_class():
    page = room()
    first = page.roster.create_class("一班")
    second = page.roster.create_class("二班")
    page.roster.import_rows(first.class_id, ((2, "s1", "secret", "甲"),))
    task = page.catalog.create((TrueFalseQuestion("判断说法", "正确", "依据"),))
    page.catalog.publish(task.task_id)
    page.classwork.assign(page.catalog, task.task_id, (first.class_id,))
    work = StudentWork(task.task_id, task.questions)
    work.edit(0, selected=("正确",))
    page.classwork._works[("s1", task.task_id)] = work

    same = text(response_for(page.teacher, "POST", "/accounts", form(action="换班", account="s1", class_id=first.class_id)))
    assert "学生不存在" not in same
    assert page.roster.student(first.class_id, "s1").class_id == first.class_id
    blank = text(response_for(page.teacher, "POST", "/accounts", form(action="换班", account="s1", class_id="  ")))
    assert "先选择班级" in blank
    unknown = text(response_for(page.teacher, "POST", "/accounts", form(action="换班", account="s1", class_id="class-9")))
    assert "班级不存在" in unknown
    moved = text(response_for(page.teacher, "POST", "/accounts", form(action="换班", account="s1", class_id=second.class_id)))
    assert "甲" in moved and "二班" in moved
    assert page.roster.students(first.class_id) == ()
    assert page.roster.students(second.class_id)[0].account == "s1"
    assert page.classwork._works[("s1", task.task_id)].answers[0].selected == ("正确",)
    todo = text(classroom.response_for(page, "GET", "/student", "", 0, student_cookie(page)))
    assert task.task_id not in todo
