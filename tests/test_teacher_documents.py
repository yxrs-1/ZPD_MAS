from scaffolding.teacher_page import TeacherPage, response_for
from tests.teacher_objectives_helpers import form, text
from tests.test_documents import _docx


def test_documents_list_upload_and_delete_without_objectives():
    page = TeacherPage(complete=lambda _messages: "")
    content = _docx((("第一章 数据", ""), ("片段", "")))

    opened = text(response_for(page, "GET", "/documents", ""))
    assert "<h1>资料库</h1>" in opened
    assert 'name="file"' in opened
    assert "上传" in opened
    assert 'name="text"' not in opened
    assert "生成目标" not in opened

    uploaded = text(response_for(
        page, "POST", "/documents", form(action="上传"),
        {"file": content}, {"file": "a<b.docx"},
    ))
    assert page.library.documents()[0].doc_id == "doc-1"
    assert "a&lt;b.docx" in uploaded
    rejected = text(response_for(
        page, "POST", "/documents", form(action="上传"),
        {"file": b"notes"}, {"file": "笔记.txt"},
    ))
    assert "只接受 docx 或 pdf" in rejected
    missing = text(response_for(page, "POST", "/documents", form(action="删除", doc_id="doc-9")))
    assert "文档不存在" in missing
    removed = text(response_for(page, "POST", "/documents", form(action="删除", doc_id="doc-1")))
    assert page.library.documents() == ()
    assert "a&lt;b.docx" not in removed


def test_objectives_upload_does_not_change_the_library():
    page = TeacherPage(complete=lambda _messages: "")
    content = _docx((("第一章 数据", ""), ("片段", "")))
    response_for(page, "POST", "/documents", form(action="上传"), {"file": content}, {"file": "教材.docx"})

    ignored = text(response_for(
        page, "POST", "/objectives", form(action="上传"),
        {"file": content}, {"file": "另一份.docx"},
    ))
    assert len(page.library.documents()) == 1
    assert 'name="file"' not in ignored
    assert 'name="text"' in ignored
    assert "生成目标" in ignored
    assert 'href="/generation"' not in ignored
