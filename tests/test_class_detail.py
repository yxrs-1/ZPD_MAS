from dataclasses import replace
from urllib.parse import quote

import pytest

from scaffolding.agents import ScaffoldDraft
from scaffolding.classwork import StudentView
from scaffolding.classroom import response_for
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from tests.classroom_helpers import form, room, student_cookie, teacher_cookie, text


class _CountingDecision(ScriptedDecisionAgent):
    def __init__(self, presets=()):
        super().__init__(presets=presets)
        self.suggest_calls = 0

    def suggest(self, record):
        self.suggest_calls += 1
        return super().suggest(record)


def _headers(page):
    return teacher_cookie(page)


def _prepared():
    page = room()
    headers = _headers(page)
    page.roster.create_class("一班")
    page.roster.create_class("二班")
    page.roster.import_rows("class-1", ((2, "s1", "secret", "甲"),))
    page.roster.import_rows("class-2", ((2, "s2", "secret", "乙"),))
    task = page.catalog.create((
        ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "硬件"), ("人员",), "选择依据"),
        ChoiceQuestion("选出组成", SelectionMode.MULTIPLE, ("人员", "硬件", "软件"), ("人员", "硬件"), "多选依据"),
        TrueFalseQuestion("判断说法", "正确", "题目里有依据"),
        OpenQuestion("完成<作品>", "写明人员", "标准<答案>", "解析<依据>"),
    ))
    page.catalog.publish(task.task_id)
    page.classwork.assign(page.catalog, task.task_id, ("class-1",))
    return page, headers, task


def _detail(page, headers, account, task_id):
    return response_for(
        page, "GET", "/teacher/classes/class-1/students/" + account + "/tasks/" + task_id, "", 0, headers
    )


def _student(page, headers, account):
    return response_for(
        page, "GET", "/teacher/classes/class-1/students/" + account, "", 0, headers
    )


def _assets(image: str) -> str:
    return (
        '<asset kind="图片素材" name="图.png">' + image + "</asset>"
        '<asset kind="思维导图" name="导图.svg">导图内容</asset>'
        '<asset kind="结构图" name="结构.svg">结构内容</asset>'
        '<asset kind="微格动画" name="动画.html">动画内容</asset>'
    )


def test_an_unopened_detail_shows_every_key_without_starting():
    page, headers, task = _prepared()

    listed = text(_student(page, headers, "s1"))
    detail = _detail(page, headers, "s1", task.task_id)
    html = text(detail)
    view = StudentView(page.catalog, page.classwork, "s1", "class-1")

    assert detail.status == 200
    assert 'href="/teacher/classes/class-1/students/s1/tasks/' + task.task_id + '"' in listed
    assert "还没作答" in listed
    assert "还没作答" in html
    assert "参考答案：人员" in html
    assert "解析：选择依据" in html
    assert "参考答案：人员、硬件" in html
    assert "解析：多选依据" in html
    assert "参考答案：正确" in html
    assert "解析：题目里有依据" in html
    assert "参考答案：标准&lt;答案&gt;" in html
    assert "解析：解析&lt;依据&gt;" in html
    assert "完成&lt;作品&gt;" in html
    assert "标准<答案>" not in html
    assert "解析<依据>" not in html
    assert "/answers" not in html
    assert "/ask" not in html
    assert "/submit" not in html
    assert page.catalog.get(task.task_id).started is False
    assert "s1" not in page.student_pages
    with pytest.raises(KeyError):
        view.work(task.task_id)


def test_opening_and_submitting_changes_the_detail_and_keeps_it_read_only():
    page, headers, task = _prepared()
    decision = _CountingDecision(("先看题目",))
    scaffold = ScriptedScaffoldAgent(ScaffoldDraft(text="先看<提示", html=_assets("AAAA")))
    page.student.decision = decision
    page.student.scaffold_agent = scaffold
    cookie = student_cookie(page, "s1", "secret", "甲")

    opened = response_for(page, "GET", "/student/tasks/" + task.task_id, "", 0, cookie)
    todo = text(_detail(page, headers, "s1", task.task_id))
    student_list = text(_student(page, headers, "s1"))

    assert "参考答案" not in text(opened)
    assert "待办" in todo
    assert "还没作答" not in todo
    assert "参考答案：标准&lt;答案&gt;" in todo
    assert "/answers" not in todo
    assert "/ask" not in todo
    assert "/submit" not in todo
    assert "待办" in student_list
    assert "还没作答" not in student_list

    response_for(
        page, "POST", "/student/tasks/" + task.task_id + "/answers",
        form(**{"text-3": "甲的<答案"}), 1, cookie,
    )
    response_for(
        page, "POST", "/student/tasks/" + task.task_id + "/ask",
        form(question="这题<怎么做", source="自己写的"), 2, cookie,
    )
    scaffold.draft = ScaffoldDraft(text="再看<一层", html=_assets("BBBB"))
    response_for(
        page, "POST", "/student/tasks/" + task.task_id + "/ask",
        form(question="再问<一次", source="自己写的"), 3, cookie,
    )
    response_for(page, "POST", "/student/tasks/" + task.task_id + "/submit", "", 4, cookie)
    view = StudentView(page.catalog, page.classwork, "s1", "class-1")
    work = view.work(task.task_id)
    work.behavior = replace(work.behavior, dwell_seconds=12.9)
    before = (decision.suggest_calls, len(decision.choose_calls), len(scaffold.calls))

    done = response_for(
        page, "GET", "/teacher/classes/class-1/students/s1/tasks/" + task.task_id, "", 5, headers
    )
    html = text(done)
    image = quote("图.png", safe="")
    current = (
        "/teacher/classes/class-1/students/s1/tasks/" + task.task_id + "/assets/" + image
    )
    earlier = (
        "/teacher/classes/class-1/students/s1/tasks/" + task.task_id + "/turns/0/assets/" + image
    )
    current_bytes = response_for(page, "GET", current, "", 5, headers)
    earlier_bytes = response_for(page, "GET", earlier, "", 5, headers)
    missing_bytes = response_for(
        page, "GET", "/teacher/classes/class-1/students/s1/tasks/" + task.task_id + "/assets/没有.svg",
        "", 5, headers,
    )

    assert done.status == 200
    assert "已完成" in html
    assert "待办" not in html
    assert "还没作答" not in html
    assert "甲的&lt;答案" in html
    assert "这题&lt;怎么做" in html
    assert "再问&lt;一次" in html
    assert "先看&lt;提示" in html
    assert "再看&lt;一层" in html
    assert "图片素材" in html
    assert "思维导图" in html
    assert "结构图" in html
    assert "微格动画" in html
    assert "导图.svg" in html
    assert "结构.svg" in html
    assert "动画.html" in html
    assert current in html
    assert earlier in html
    assert "AAAA" not in html
    assert "BBBB" not in html
    assert "停留12" in html
    assert "停留12.9" not in html
    assert "/answers" not in html
    assert "/ask" not in html
    assert "/submit" not in html
    assert "已完成" in text(_student(page, headers, "s1"))
    assert current_bytes.status == 200
    assert current_bytes.body == b"BBBB"
    assert current_bytes.filename == "图.png"
    assert current_bytes.content_type == "application/octet-stream"
    assert earlier_bytes.status == 200
    assert earlier_bytes.body == b"AAAA"
    assert earlier_bytes.filename == "图.png"
    assert missing_bytes.status == 404
    assert missing_bytes.body == b""
    assert view.work(task.task_id).answers[3].text == "甲的<答案"
    assert view.work(task.task_id).submitted is True
    assert (decision.suggest_calls, len(decision.choose_calls), len(scaffold.calls)) == before


def test_an_unassigned_task_and_a_foreign_account_are_missing():
    page, headers, task = _prepared()
    secret = page.catalog.create((OpenQuestion("另一题", "另一要求", "秘密答案", "秘密解析"),))
    page.catalog.publish(secret.task_id)
    page.classwork.assign(page.catalog, secret.task_id, ("class-2",))
    draft = page.catalog.create((OpenQuestion("草稿题", "草稿要求", "草稿答案", "草稿解析"),))

    missing = _detail(page, headers, "s1", secret.task_id)
    unpublished = _detail(page, headers, "s1", draft.task_id)
    unknown = _detail(page, headers, "s1", "task-missing")
    foreign = _detail(page, headers, "s2", task.task_id)
    absent = _student(page, headers, "nobody")

    assert missing.status == 404
    assert "任务不存在" in text(missing)
    assert "秘密答案" not in text(missing)
    assert "秘密解析" not in text(missing)
    assert "参考答案" not in text(missing)
    assert unpublished.status == 404
    assert "任务不存在" in text(unpublished)
    assert "草稿答案" not in text(unpublished)
    assert unknown.status == 404
    assert "任务不存在" in text(unknown)
    assert foreign.status == 404
    assert "学生不存在" in text(foreign)
    assert "任务不存在" not in text(foreign)
    assert "参考答案" not in text(foreign)
    assert "选择依据" not in text(foreign)
    assert absent.status == 404
    assert "学生不存在" in text(absent)
    assert page.catalog.get(task.task_id).started is False
    assert page.catalog.get(secret.task_id).started is False
