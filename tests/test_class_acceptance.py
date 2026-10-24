from pathlib import Path

from scaffolding.classroom import production_classroom, response_for, serve
from scaffolding.model_text import ModelTextGenerator
from scaffolding.records import ChoiceQuestion, SelectionMode
from tests.classroom_helpers import form, text
from tests.test_sheet import _xlsx

ROOT = Path(__file__).resolve().parents[1]


def test_the_classroom_entry_has_no_tasks(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    room = production_classroom(post=lambda _request: (_ for _ in ()).throw(AssertionError("network")))

    home = text(response_for(room, "GET", "/", "", 0))

    assert "<h1>登录</h1>" in home
    assert "task-" not in home
    assert isinstance(room.generation._text_generator, ModelTextGenerator)
    monkeypatch.chdir(ROOT)
    assert Path("docs/superpowers/specs/2026-10-23-teacher-classes-design.md").is_file()
    assert callable(serve)
    assert callable(production_classroom)


def test_a_logged_in_student_only_sees_an_assigned_task(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    room = production_classroom(post=lambda _request: (_ for _ in ()).throw(AssertionError("network")))
    teacher = response_for(room, "POST", "/teacher/login", form(account="643590872", password="643590872"), 0)
    headers = teacher.set_cookie.split(";", 1)[0]
    response_for(room, "POST", "/teacher/classes", form(action="创建", name="一班"), 0, headers)
    task = room.catalog.create((
        ChoiceQuestion("题干", SelectionMode.SINGLE, ("甲", "乙"), ("甲",), "因为甲"),
    ))
    room.catalog.publish(task.task_id)
    response_for(
        room, "POST", "/teacher/tasks/" + task.task_id,
        form(action="布置", class_id="class-1"), 0, headers,
    )
    response_for(
        room, "POST", "/teacher/classes/class-1", form(action="导入"), 0, headers,
        uploads={"file": _xlsx((("账号", "密码", "姓名"), ("s1", "secret", "甲")))},
    )
    student = response_for(room, "POST", "/student/login", form(account="s1", password="secret"), 0)
    todo = text(response_for(room, "GET", "/student", "", 0, student.set_cookie.split(";", 1)[0]))
    hidden = response_for(room, "GET", "/student/tasks/task-2", "", 0, student.set_cookie.split(";", 1)[0])

    assert "task-1" in todo
    assert hidden.status == 404
    assert "任务不存在" in text(hidden)
