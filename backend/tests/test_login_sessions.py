import os
from urllib.parse import urlencode

import redis
from sqlalchemy import create_engine, text

from scaffolding.agents import ScaffoldDraft
from scaffolding.classroom import Classroom, response_for
from scaffolding.knowledge import KnowledgeBase
from scaffolding.objectives import ObjectiveCatalog
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.tasks import TaskCatalog
from zpd_api.classroom_records import PostgresRecords
from zpd_api.login_sessions import RedisSessions


def test_login_still_works_after_restart():
    engine = _engine()
    client, prefix = _redis()
    first = _room(PostgresRecords(engine), RedisSessions(client, prefix))
    teacher = _cookie(response_for(
        first, "POST", "/teacher/login", _form(account="643590872", password="643590872"), 0
    ))
    response_for(first, "POST", "/teacher/classes", _form(action="创建", name="一班"), 0, teacher)
    student = _cookie(response_for(
        first,
        "POST",
        "/student/register",
        _form(account="s1", password="secret", name="甲", class_id="class-1"),
        0,
    ))

    restarted = _room(PostgresRecords(engine), RedisSessions(client, prefix))
    teacher_page = response_for(restarted, "GET", "/teacher", "", 0, teacher).body.decode()
    student_page = response_for(restarted, "GET", "/student", "", 0, student).body.decode()
    assert "任务列表" in teacher_page
    assert "待办" in student_page

    response_for(restarted, "POST", "/teacher", _form(action="退出"), 0, teacher)
    response_for(restarted, "POST", "/student", _form(action="退出"), 0, student)
    signed_out = _room(PostgresRecords(engine), RedisSessions(client, prefix))
    assert "登录" in response_for(signed_out, "GET", "/teacher", "", 0, teacher).body.decode()
    assert "登录" in response_for(signed_out, "GET", "/student", "", 0, student).body.decode()
    engine.dispose()


def _room(records, sessions):
    catalog = TaskCatalog()
    knowledge = KnowledgeBase()
    return Classroom(
        catalog,
        ScriptedDecisionAgent(),
        ScriptedScaffoldAgent(draft=ScaffoldDraft(text="提示")),
        knowledge,
        ObjectiveCatalog(knowledge, _Extractor()),
        records=records,
        sessions=sessions,
    )


class _Extractor:
    def extract(self, retrieval):
        return ()


def _engine():
    raw = os.environ.get("DATABASE_URL", "postgresql+asyncpg://zpd:zpd@127.0.0.1:5432/zpd")
    url = raw.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS login_test CASCADE"))
        connection.execute(text("CREATE SCHEMA login_test"))
    admin.dispose()
    return create_engine(url, execution_options={"schema_translate_map": {None: "login_test"}})


def _redis():
    url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
    client = redis.Redis.from_url(url, decode_responses=True)
    prefix = "zpd:test-session:"
    for key in client.scan_iter(prefix + "*"):
        client.delete(key)
    return client, prefix


def _form(**fields) -> str:
    return urlencode(fields)


def _cookie(response) -> str:
    return response.set_cookie.split(";", 1)[0]
