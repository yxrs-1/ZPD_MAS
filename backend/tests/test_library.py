from pathlib import Path

from urllib.parse import urlencode

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scaffolding.documents import StoredDocument, draft_objectives
from scaffolding.model_scaffold import build_messages
from scaffolding.records import OpenQuestion, ItemAnswer
from scaffolding.teacher_page import TeacherPage, _confirm_on_page, response_for
from zpd_api.library import QueuedLibrary
from zpd_api.models import Base
from zpd_api.scaffold_bridge import PassageScaffoldAgent


def test_upload_shows_queued_and_delete_removes_file_record_and_vectors(tmp_path):
    queued = []
    removed = []
    library, factory = _library(tmp_path, queued, removed)
    page = TeacherPage(library=library)

    uploaded = text(response_for(
        page, "POST", "/documents", form(action="上传"),
        {"file": b"not-a-real-docx"}, {"file": "教材.docx"},
    ))
    assert "排队中" in uploaded
    assert "教材.docx" in uploaded
    assert queued == [1]
    assert library.documents()[0].chunks == ()
    stored_path = _stored_path(factory)
    assert Path(stored_path).is_file()

    _set_status(factory, "ready", "")
    assert "可用" in text(response_for(page, "GET", "/documents", ""))
    _set_status(factory, "failed", "不能读取这份文件")
    failed = text(response_for(page, "GET", "/documents", ""))
    assert "失败" in failed
    assert "不能读取这份文件" in failed

    removed_page = text(response_for(page, "POST", "/documents", form(action="删除", doc_id="1")))
    assert "教材.docx" not in removed_page
    assert removed == [1]
    assert library.documents() == ()
    assert not Path(stored_path).exists()


def test_rejected_upload_does_not_queue(tmp_path):
    queued = []
    page = TeacherPage(library=_library(tmp_path, queued, [])[0])
    rejected = text(response_for(
        page, "POST", "/documents", form(action="上传"),
        {"file": b"notes"}, {"file": "笔记.txt"},
    ))
    assert "只接受 docx 或 pdf" in rejected
    assert queued == []


def test_objectives_and_questions_use_chroma_passages_not_saved_chunks():
    calls = []

    def complete(messages):
        calls.append(messages[-1]["content"])
        if len(calls) == 1:
            return '{"检索":"数据"}'
        return '{"目标":[{"维度":"计算思维","表述":"能分辨数据"}]}'

    def retrieve(query):
        assert query == "数据"
        return [("教材.docx", "向量里的片段")]

    drafted = draft_objectives(
        complete,
        (StoredDocument("doc-1", "old.docx", ("旧切块里的数据",)),),
        "数据怎么识别",
        retrieve=retrieve,
    )
    assert drafted[0].statement == "能分辨数据"
    assert "向量里的片段" in calls[1]
    assert "旧切块" not in calls[1]

    seen = {}

    class Generation:
        def generate_from_confirmed(self, demand, objectives, passages=()):
            seen["passages"] = passages
            raise RuntimeError("stop")

    page = TeacherPage(complete=complete, generation=Generation(), retrieve=lambda _query: [("教材.docx", "出题片段")])
    page.open_objectives = lambda *args: "生成失败"
    _confirm_on_page(page, "做一道单选", "维度：计算思维\n表述：能分辨数据")
    assert seen["passages"] == (("教材.docx", "出题片段"),)


def test_help_retrieves_after_the_chosen_type_and_puts_passages_in_the_prompt():
    questions = (OpenQuestion("题干", "写出过程"),)
    answers = (ItemAnswer(text="一半"),)
    plain = build_messages("提示", "怎么做", questions, answers)[1]["content"]
    with_passage = build_messages(
        "提示", "怎么做", questions, answers, passages=(("教材.docx", "向量片段"),)
    )[1]["content"]
    assert plain.endswith("这次提问：怎么做")
    assert "向量片段" not in plain
    assert "向量片段" in with_passage

    seen = {}

    class Agent:
        def produce(self, scaffold_type, question, questions, answers, passages=(), example_source=""):
            seen["type"] = scaffold_type
            seen["passages"] = passages
            from scaffolding.agents import ScaffoldDraft
            return ScaffoldDraft(text="支架")

    def retrieve(query):
        seen["query"] = query
        return [("教材.docx", "向量片段")]

    PassageScaffoldAgent(Agent(), retrieve).produce("提示", "怎么做", questions, answers)
    assert seen["query"] == "提示\n怎么做"
    assert seen["passages"] == (("教材.docx", "向量片段"),)


def text(response) -> str:
    return response.body.decode()


def form(**fields) -> str:
    return urlencode(fields)


def _library(directory: Path, queued: list, removed: list):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    library = QueuedLibrary(
        session_factory=factory,
        enqueue=queued.append,
        delete_vectors=removed.append,
        upload_dir=directory,
    )
    return library, factory


def _stored_path(factory) -> str:
    from zpd_api.models import Material

    with factory() as session:
        return session.get(Material, 1).stored_path


def _set_status(factory, status: str, detail: str) -> None:
    from zpd_api.models import Material

    with factory() as session:
        row = session.get(Material, 1)
        row.status = status
        row.detail = detail
        session.commit()
