import json
from pathlib import Path

from scaffolding.classroom import Classroom, production_classroom, response_for
from scaffolding.model_text import ModelTextGenerator
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.tasks import TaskCatalog
from tests.classroom_helpers import form, student_cookie, teacher_cookie, text
from tests.test_documents import _docx, _pdf


def test_the_spec_is_present_and_text_generation_is_wired(tmp_path, monkeypatch):
    spec = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "specs" / "2026-10-23-document-retrieval-design.md"
    calls = []

    def post(url, headers, payload):
        calls.append(url)
        raise AssertionError("network")

    monkeypatch.chdir(tmp_path)
    room = production_classroom(post=post)
    assert spec.is_file()
    assert isinstance(room.generation._text_generator, ModelTextGenerator)
    assert calls == []


def test_a_logged_in_teacher_uploads_and_the_student_does_not_read_documents(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    room = Classroom(TaskCatalog(), ScriptedDecisionAgent(), ScriptedScaffoldAgent(), path="classroom.json")
    headers = teacher_cookie(room)
    uploaded = response_for(
        room, "POST", "/teacher/objectives", form(action="上传"), 0, headers,
        {"file": _docx((("第一章 数据", ""), ("正文", "")))},
        {"file": "教材.docx"},
    )
    saved = json.loads(Path("classroom.json").read_text(encoding="utf-8"))
    student = response_for(room, "GET", "/student/objectives", "", 0, student_cookie(room))

    assert "教材.docx" in text(uploaded)
    assert saved["documents"][0]["doc_id"] == "doc-1"
    assert student.status == 404
    assert "任务不存在" in text(student)
    assert "教材.docx" not in text(student)
