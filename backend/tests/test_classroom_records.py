import os
from urllib.parse import urlencode

from sqlalchemy import create_engine, text

from scaffolding.agents import ScaffoldDraft
from scaffolding.classroom import Classroom, response_for
from scaffolding.documents import StoredDocument
from scaffolding.generation import LessonOrigin, TaskGeneration
from scaffolding.knowledge import KnowledgeBase
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft
from scaffolding.records import Asset, AssetKind
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.store import classroom_state
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import DraftQuestion
from zpd_api.classroom_records import PostgresRecords


def test_restart_restores_classroom_from_postgres(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine = _engine()
    first = _room(PostgresRecords(engine))
    teacher = _teacher_cookie(first)
    response_for(first, "POST", "/teacher/classes", _form(action="创建", name="一班"), 0, teacher)
    student = response_for(
        first,
        "POST",
        "/student/register",
        _form(account="s1", password="secret", name="甲", class_id="class-1"),
        0,
    )
    student_cookie = student.set_cookie.split(";", 1)[0]
    response_for(first, "POST", "/teacher/tasks", "", 0, teacher)
    response_for(first, "POST", "/teacher/tasks/task-1", _form(**{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "selected-0": "正确",
        "explanation-0": "题目里有依据",
        "action": "save",
    }), 0, teacher)
    response_for(first, "POST", "/teacher/tasks/task-1", _form(action="publish"), 0, teacher)
    response_for(first, "POST", "/teacher/tasks/task-1", _form(action="布置", class_id="class-1"), 0, teacher)
    response_for(first, "GET", "/student/tasks/task-1", "", 10, student_cookie)
    response_for(first, "GET", "/student/tasks/task-1", "", 40, student_cookie)
    response_for(first, "POST", "/student/tasks/task-1/answers", _form(**{"selected-0": "正确"}), 40, student_cookie)
    response_for(first, "POST", "/student/tasks/task-1/answers", _form(**{"selected-0": "错误"}), 40, student_cookie)
    response_for(first, "POST", "/student/tasks/task-1/ask", _form(question="这题怎么看", source="自己写的"), 40, student_cookie)
    first.teacher.drafts["task-1"] = (
        DraftQuestion("判断", "草稿题", (), "", ("正确",), "正确", "因为"),
    )
    first.generation._origins["task-1"] = LessonOrigin("2019", "必修1", "数据")
    first.roster.teacher_account = "teacher-9"
    first.documents.load((StoredDocument("doc-1", "教材.docx", ("第一段",)),), 2)
    response_for(
        first,
        "POST",
        "/teacher",
        _form(action="修改密码", old_password="643590872", password="new-secret"),
        0,
        teacher,
    )

    assert list(tmp_path.iterdir()) == []
    restored = _room(PostgresRecords(engine))
    assert restored.roster.teacher_account == "teacher-9"
    assert restored.roster.teacher_password == "new-secret"
    assert classroom_state(restored) == classroom_state(first)
    with engine.connect() as connection:
        classes = connection.execute(text("SELECT name FROM classroom_test.classes")).scalars().all()
        accounts = connection.execute(text("SELECT account, name FROM classroom_test.students")).all()
        answers = connection.execute(text(
            "SELECT text, selected, text_revisions, selected_revisions FROM classroom_test.answers"
        )).mappings().all()
        helps = connection.execute(text("SELECT text, source FROM classroom_test.helps")).mappings().all()
        turns = connection.execute(text("SELECT question, scaffold FROM classroom_test.scaffold_turns")).mappings().all()
        origins = connection.execute(text("SELECT kind, lesson FROM classroom_test.generation_origins")).mappings().all()
        dwell = connection.execute(text("SELECT dwell_seconds FROM classroom_test.student_works")).scalars().all()
    assert classes == ["一班"]
    assert accounts == [("s1", "甲")]
    assert answers[0]["selected"] == ["错误"]
    assert answers[0]["selected_revisions"] == [[], ["正确"]]
    assert helps == [{"text": "这题怎么看", "source": "自己写的"}]
    assert turns[0]["question"] == "这题怎么看"
    assert turns[0]["scaffold"]["text"] == "先看人员和硬件"
    assert origins == [{"kind": "lesson", "lesson": "数据"}]
    assert dwell == [30]
    engine.dispose()


class _Extractor:
    def extract(self, retrieval):
        return (ObjectiveDraft("计算思维", "能分辨系统和要素", retrieval.lesson_source),)


class _Generator:
    def generate(self, counts, objectives):
        raise AssertionError("model")


def _room(records):
    knowledge = KnowledgeBase()
    catalog = TaskCatalog()
    return Classroom(
        catalog,
        ScriptedDecisionAgent(presets=("先看题目",)),
        ScriptedScaffoldAgent(draft=ScaffoldDraft(text="先看人员和硬件", assets=(Asset(AssetKind.IMAGE, "figure.png", b"png"),))),
        knowledge,
        ObjectiveCatalog(knowledge, _Extractor()),
        TaskGeneration(ObjectiveCatalog(knowledge, _Extractor()), catalog, _Generator()),
        records=records,
    )


def _engine():
    raw = os.environ.get("DATABASE_URL", "postgresql+asyncpg://zpd:zpd@127.0.0.1:5432/zpd")
    url = raw.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS classroom_test CASCADE"))
        connection.execute(text("CREATE SCHEMA classroom_test"))
    admin.dispose()
    return create_engine(url, execution_options={"schema_translate_map": {None: "classroom_test"}})


def _form(**fields) -> str:
    return urlencode(fields)


def _teacher_cookie(room) -> str:
    response = response_for(room, "POST", "/teacher/login", _form(account="643590872", password="643590872"), 0)
    return response.set_cookie.split(";", 1)[0]
