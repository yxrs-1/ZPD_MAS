import os
from urllib.parse import urlencode

from sqlalchemy import create_engine, text

from scaffolding.agents import ScaffoldDraft
from scaffolding.classroom import Classroom, response_for
from scaffolding.records import ScaffoldType
from scaffolding.scaffold_decision import PreviousScaffold, ScaffoldDecision
from scaffolding.tasks import TaskCatalog
from zpd_api.scaffold_bridge import PassageScaffoldAgent, RecordedScaffoldDecision


def test_second_help_reads_saved_scaffolds_then_keeps_the_model_type(monkeypatch):
    seen = {"order": [], "previous": None, "state": "", "answer": "", "query": "", "passages": ()}

    async def decide(state, answer, previous, client=None):
        seen["order"].append("decide")
        if seen["previous"] is None:
            assert previous == []
            return ScaffoldDecision(scaffold_type=ScaffoldType.FEEDBACK, reason="学生写下了一半")
        seen["state"] = state
        seen["answer"] = answer
        seen["previous"] = list(previous)
        assert seen["query"] == ""
        return ScaffoldDecision(scaffold_type=ScaffoldType.MODELING, reason="需要一个同类例子")

    def retrieve(query):
        seen["order"].append("retrieve")
        if seen["previous"] is not None:
            seen["query"] = query
        return [("教材.docx", "教材里的同类例子")]

    class Body:
        def produce(self, scaffold_type, question, questions, answers, passages=(), example_source=""):
            seen["order"].append("produce")
            if seen["previous"] is None:
                return ScaffoldDraft(text="先看已经写出的部分")
            seen["passages"] = passages
            assert scaffold_type == "示范"
            return ScaffoldDraft(text="看一个同类例子")

    monkeypatch.setattr("zpd_api.scaffold_bridge.decide_scaffold_type", decide)
    engine = _engine()
    sessions = type("Sessions", (), {"teachers": set(), "students": {}})()
    decision = RecordedScaffoldDecision(type("Presets", (), {"suggest": lambda self, record: ("先看题目",)})())
    room = Classroom(
        TaskCatalog(),
        decision,
        PassageScaffoldAgent(Body(), retrieve),
        records=_records(engine),
        sessions=sessions,
    )
    teacher = _teacher_cookie(room)
    response_for(room, "POST", "/teacher/classes", _form(action="创建", name="一班"), 0, teacher)
    student = response_for(
        room,
        "POST",
        "/student/register",
        _form(account="s1", password="secret", name="甲", class_id="class-1"),
        0,
    )
    student_cookie = student.set_cookie.split(";", 1)[0]
    response_for(room, "POST", "/teacher/tasks", "", 0, teacher)
    response_for(room, "POST", "/teacher/tasks/task-1", _form(**{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "selected-0": "正确",
        "explanation-0": "题目里有依据",
        "action": "save",
    }), 0, teacher)
    response_for(room, "POST", "/teacher/tasks/task-1", _form(action="publish"), 0, teacher)
    response_for(room, "POST", "/teacher/tasks/task-1", _form(action="布置", class_id="class-1"), 0, teacher)
    response_for(room, "GET", "/student/tasks/task-1", "", 10, student_cookie)
    response_for(room, "GET", "/student/tasks/task-1", "", 40, student_cookie)
    response_for(room, "POST", "/student/tasks/task-1/answers", _form(**{"selected-0": "错误"}), 40, student_cookie)
    response_for(room, "POST", "/student/tasks/task-1/ask", _form(question="这题怎么看", source="自己写的"), 40, student_cookie)

    again = Classroom(
        TaskCatalog(),
        decision,
        PassageScaffoldAgent(Body(), retrieve),
        records=_records(engine),
        sessions=sessions,
    )
    seen["previous"] = []
    response_for(again, "POST", "/student/tasks/task-1/ask", _form(question="下一步怎么写", source="自己写的"), 40, student_cookie)

    assert "停留秒数：30" in seen["state"]
    assert "先看已经写出的部分" not in seen["state"]
    assert "错误" in seen["answer"]
    assert seen["previous"] == [PreviousScaffold(scaffold_type=ScaffoldType.FEEDBACK, content="先看已经写出的部分")]
    assert seen["query"] == "示范\n下一步怎么写"
    assert seen["passages"] == (("教材.docx", "教材里的同类例子"),)
    assert seen["order"] == ["decide", "retrieve", "produce", "decide", "retrieve", "produce"]
    with engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT scaffold_type, reason, scaffold->>'text' AS text FROM help_flow.scaffold_turns ORDER BY position"
        )).mappings().all()
    assert rows[0]["scaffold_type"] == "反馈"
    assert rows[0]["reason"] == "学生写下了一半"
    assert rows[0]["text"] == "先看已经写出的部分"
    assert rows[1]["scaffold_type"] == "示范"
    assert rows[1]["reason"] == "需要一个同类例子"
    assert rows[1]["text"] == "看一个同类例子"
    assert "正确" not in rows[1]["text"]
    engine.dispose()


def _records(engine):
    from zpd_api.classroom_records import PostgresRecords

    return PostgresRecords(engine)


def _engine():
    raw = os.environ.get("DATABASE_URL", "postgresql+asyncpg://zpd:zpd@127.0.0.1:5432/zpd")
    url = raw.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS help_flow CASCADE"))
        connection.execute(text("CREATE SCHEMA help_flow"))
    admin.dispose()
    return create_engine(url, execution_options={"schema_translate_map": {None: "help_flow"}})


def _form(**fields) -> str:
    return urlencode(fields)


def _teacher_cookie(room) -> str:
    response = response_for(room, "POST", "/teacher/login", _form(account="643590872", password="643590872"), 0)
    return response.set_cookie.split(";", 1)[0]
