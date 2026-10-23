import json
from pathlib import Path

from scaffolding.classroom import (
    Classroom,
    files_from_body,
    filenames_from_body,
    production_classroom,
    response_for,
)
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


def test_quoted_utf8_and_ascii_filenames_stay_as_uploaded():
    docx = _docx((("第一章 数据", ""), ("正文", "")))
    notes = _pdf(("笔记",))
    body = (
        b"--line\r\n"
        b"Content-Disposition: form-data; name=\"file\"; filename=\""
        + "教材.docx".encode("utf-8")
        + b"\"\r\n"
        b"\r\n"
        + docx
        + b"\r\n"
        b"--line\r\n"
        b"Content-Disposition: form-data; name=\"notes\"; filename=\"notes.pdf\"\r\n"
        b"\r\n"
        + notes
        + b"\r\n"
        b"--line--\r\n"
    )
    content_type = "multipart/form-data; boundary=line"

    names = filenames_from_body(content_type, body)
    files = files_from_body(content_type, body)

    assert names["file"] == "教材.docx"
    assert names["notes"] == "notes.pdf"
    assert files["file"] == docx
    assert files["notes"] == notes


def test_filename_star_alone_is_the_utf8_name():
    body = (
        b"--line\r\n"
        b"Content-Disposition: form-data; name=\"file\"; "
        b"filename*=UTF-8''%E6%95%99%E6%9D%90.docx\r\n"
        b"\r\n"
        b"PK\x03\x04sheet\r\n"
        b"--line--\r\n"
    )

    names = filenames_from_body("multipart/form-data; boundary=line", body)

    assert names["file"] == "教材.docx"


def test_filename_star_wins_over_the_ascii_filename():
    body = (
        b"--line\r\n"
        b"Content-Disposition: form-data; name=\"file\"; filename=\"book.docx\"; "
        b"filename*=UTF-8''%E6%95%99%E6%9D%90.docx\r\n"
        b"\r\n"
        b"PK\x03\x04sheet\r\n"
        b"--line--\r\n"
    )

    names = filenames_from_body("multipart/form-data; boundary=line", body)

    assert names["file"] == "教材.docx"
