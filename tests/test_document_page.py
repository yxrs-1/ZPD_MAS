import json

from scaffolding.generation import TaskGeneration
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage, response_for
from tests.teacher_objectives_helpers import form, text
from tests.test_documents import _docx


_OBJECTIVE = json.dumps({"目标": [{"维度": "信息意识", "表述": "能识别信息"}]}, ensure_ascii=False)
_TASK = json.dumps({
    "读法": {"单选": 1, "多选": "未指定", "判断": "未指定", "综合": "未指定"},
    "目标": [{"维度": "信息意识", "表述": "模型另写的目标"}],
    "题目": {
        "单选": [{
            "题目": "哪一项是数据",
            "选项": ["数据", "电线"],
            "参考答案": ["数据"],
            "解析": "题干已说明",
        }],
        "多选": [],
        "判断": [],
        "综合": [],
    },
}, ensure_ascii=False)


class _Text:
    def generate(self, message: str) -> str:
        return _TASK


def _page(calls):
    catalog = TaskCatalog()

    def complete(messages):
        calls.append(messages[1]["content"])
        if len(calls) == 1:
            return json.dumps({"检索": "数据"}, ensure_ascii=False)
        return _OBJECTIVE

    return TeacherPage(catalog, generation=TaskGeneration(None, catalog, None, _Text()), complete=complete), catalog


def test_get_lists_upload_and_does_not_call_the_model():
    calls = []
    page, _catalog = _page(calls)

    opened = text(response_for(page, "GET", "/objectives/?ready=1", ""))
    library = text(response_for(page, "GET", "/documents", ""))

    assert 'name="text"' in opened
    assert "生成目标" in opened
    assert 'name="file"' not in opened
    assert 'href="/generation"' not in opened
    assert 'name="objectives"' not in opened
    assert 'name="file"' in library
    assert calls == []


def test_upload_delete_and_a_bad_extension():
    calls = []
    page, _catalog = _page(calls)
    content = _docx((("第一章 数据", ""), ("片段秘密", "")))

    uploaded = text(response_for(
        page, "POST", "/documents", form(action="上传"),
        {"file": content}, {"file": "a<b.docx"},
    ))
    missing = text(response_for(page, "POST", "/documents", form(action="删除", doc_id="doc-9"), None, None))
    rejected = text(response_for(
        page, "POST", "/documents", form(action="上传"),
        {"file": b"notes"}, {"file": "笔记.txt"},
    ))

    assert page.library.documents()[0].doc_id == "doc-1"
    assert "&lt;" in uploaded
    assert "文档不存在" in missing
    assert "只接受 docx 或 pdf" in rejected
    assert len(page.library.documents()) == 1
    assert calls == []
    removed = text(response_for(page, "POST", "/documents", form(action="删除", doc_id="doc-1"), None, None))
    assert "a&lt;b.docx" not in removed
    assert page.library.documents() == ()


def test_draft_shows_editable_objectives_without_the_passage():
    calls = []
    page, _catalog = _page(calls)
    content = _docx((("第一章 数据", ""), ("片段秘密", "")))
    response_for(page, "POST", "/documents", form(action="上传"), {"file": content}, {"file": "教材.docx"})

    drafted = text(response_for(page, "POST", "/objectives", form(action="生成目标", text="  识别数据  ")))
    blank = text(response_for(page, "POST", "/objectives", form(action="生成目标", text="  ")))

    assert calls[0] == "识别数据"
    assert "文件名：教材.docx" in calls[1]
    assert "片段秘密" in calls[1]
    assert 'name="objectives"' in drafted
    assert "确认" in drafted
    assert "识别数据" in drafted
    assert "匹配片段" not in drafted
    assert "片段秘密" not in drafted
    assert "先填写需求" in blank
    assert 'name="objectives"' not in blank


def test_confirm_creates_an_unpublished_task_and_a_bad_edit_stays():
    calls = []
    page, catalog = _page(calls)
    confirmed = text(response_for(page, "POST", "/objectives", form(
        action="确认", text="做一道单选", objectives="维度：信息意识\n表述：能识别信息",
    )))
    rejected = text(response_for(page, "POST", "/objectives", form(
        action="确认", text="做一道单选", objectives="维度：其他\n表述：能识别信息",
    )))
    unknown = text(response_for(page, "POST", "/objectives", form(action="发布")))

    assert "task-1" in confirmed
    assert "未发布" in confirmed
    assert page.generation.origin("task-1") is None
    assert page.objectives.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
    assert len(catalog._tasks) == 1
    assert "目标格式不正确" in rejected
    assert "维度：其他" in rejected
    assert "做一道单选" in rejected
    assert len(catalog._tasks) == 1
    assert "生成目标" in unknown
    assert "失败" not in unknown
