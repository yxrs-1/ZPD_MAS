import asyncio

from fastapi.testclient import TestClient

from scaffolding.agents import ScaffoldDraft
from scaffolding.classroom import Classroom
from scaffolding.records import Asset, AssetKind
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.tasks import TaskCatalog
from zpd_api.main import app


class RunningLoopDecision:
    def suggest(self, record):
        return ()

    def choose_type(self, record, question):
        asyncio.run(asyncio.sleep(0))
        self.last_reason = "看过作答"
        return "提示"


def test_pages_use_the_classroom_api(monkeypatch):
    room = Classroom(
        TaskCatalog(),
        ScriptedDecisionAgent(presets=("先看题目",), scaffold_type="提示"),
        ScriptedScaffoldAgent(draft=ScaffoldDraft(text="先看已经写出的部分")),
    )
    monkeypatch.setattr("zpd_api.classroom_api.get_room", lambda: room)
    teacher = TestClient(app)
    logged = teacher.post("/api/login", json={"role": "教师", "account": "643590872", "password": "643590872"})
    assert logged.json()["role"] == "教师"
    created = teacher.post("/api/teacher/classes", json={"name": "一班"})
    assert created.json()["class_id"] == "class-1"
    task = teacher.post("/api/teacher/tasks")
    assert task.json()["task_id"] == "task-1"
    saved = teacher.post("/api/teacher/tasks/task-1", json={
        "action": "save",
        "questions": [{
            "kind": "判断",
            "prompt": "判断说法",
            "selected": ["正确"],
            "explanation": "题目里有依据",
        }],
    })
    assert saved.json()["message"] == ""
    assert saved.json()["questions"][0]["prompt"] == "判断说法"
    published = teacher.post("/api/teacher/tasks/task-1", json={"action": "publish"})
    assert published.json()["status"] == "已发布"
    assigned = teacher.post("/api/teacher/tasks/task-1", json={"action": "布置", "class_ids": ["class-1"]})
    assert assigned.json()["classes"][0]["assigned"] is True

    student = TestClient(app)
    registered = student.post("/api/register", json={
        "account": "s1",
        "password": "secret",
        "name": "甲",
        "class_id": "class-1",
    })
    assert registered.json()["ok"] is True
    listed = student.get("/api/student/tasks")
    assert listed.json()["tasks"][0]["task_id"] == "task-1"
    opened = student.get("/api/student/tasks/task-1")
    assert opened.json()["questions"][0]["prompt"] == "判断说法"
    answered = student.post("/api/student/tasks/task-1/answers", json={"answers": [{"selected": ["错误"]}]})
    assert answered.json()["questions"][0]["selected"] == ["错误"]
    asked = student.post("/api/student/tasks/task-1/ask", json={"question": "这题怎么看", "source": "自己写的"})
    assert asked.json()["scaffold"]["text"] == "先看已经写出的部分"
    assert asked.json()["dialogue"][0]["question"] == "这题怎么看"

    accounts = teacher.get("/api/teacher/accounts")
    assert accounts.json()["students"][0]["name"] == "甲"
    documents = teacher.get("/api/teacher/documents")
    assert documents.json()["documents"] == []


def test_help_decides_the_type_from_the_request_thread(monkeypatch):
    room = Classroom(
        TaskCatalog(),
        RunningLoopDecision(),
        ScriptedScaffoldAgent(draft=ScaffoldDraft(text="先看已经写出的部分")),
    )
    monkeypatch.setattr("zpd_api.classroom_api.get_room", lambda: room)
    teacher = TestClient(app)
    teacher.post("/api/login", json={"role": "教师", "account": "643590872", "password": "643590872"})
    teacher.post("/api/teacher/classes", json={"name": "一班"})
    teacher.post("/api/teacher/tasks")
    teacher.post("/api/teacher/tasks/task-1", json={
        "action": "save",
        "questions": [{"kind": "判断", "prompt": "判断说法", "selected": ["正确"], "explanation": ""}],
    })
    teacher.post("/api/teacher/tasks/task-1", json={"action": "publish"})
    teacher.post("/api/teacher/tasks/task-1", json={"action": "布置", "class_ids": ["class-1"]})
    student = TestClient(app)
    student.post("/api/register", json={"account": "s1", "password": "secret", "name": "甲", "class_id": "class-1"})
    asked = student.post("/api/student/tasks/task-1/ask", json={"question": "这题怎么看", "source": "自己写的"})
    assert asked.json()["scaffold"]["text"] == "先看已经写出的部分"


def test_student_can_read_scaffold_assets(monkeypatch):
    picture = Asset(AssetKind.IMAGE, "hint.png", b"\x89PNG-hint")
    room = Classroom(
        TaskCatalog(),
        ScriptedDecisionAgent(presets=("先看题目",), scaffold_type="提示"),
        ScriptedScaffoldAgent(draft=ScaffoldDraft(text="看这张图", assets=(picture,))),
    )
    monkeypatch.setattr("zpd_api.classroom_api.get_room", lambda: room)
    teacher = TestClient(app)
    teacher.post("/api/login", json={"role": "教师", "account": "643590872", "password": "643590872"})
    teacher.post("/api/teacher/classes", json={"name": "一班"})
    teacher.post("/api/teacher/tasks")
    teacher.post("/api/teacher/tasks/task-1", json={
        "action": "save",
        "questions": [{"kind": "判断", "prompt": "判断说法", "selected": ["正确"], "explanation": ""}],
    })
    teacher.post("/api/teacher/tasks/task-1", json={"action": "publish"})
    teacher.post("/api/teacher/tasks/task-1", json={"action": "布置", "class_ids": ["class-1"]})
    student = TestClient(app)
    student.post("/api/register", json={"account": "s1", "password": "secret", "name": "甲", "class_id": "class-1"})
    student.post("/api/student/tasks/task-1/ask", json={"question": "这题怎么看", "source": "自己写的"})

    current = student.get("/api/student/tasks/task-1/assets/hint.png")
    assert current.status_code == 200
    assert current.content == b"\x89PNG-hint"
    assert "hint.png" in current.headers["content-disposition"]
    turn = student.get("/api/student/tasks/task-1/turns/0/assets/hint.png")
    assert turn.status_code == 200
    assert turn.content == b"\x89PNG-hint"
    missing = student.get("/api/student/tasks/task-1/assets/missing.png")
    assert missing.status_code == 404
    assert missing.content == b""
    stranger = TestClient(app)
    denied = stranger.get("/api/student/tasks/task-1/assets/hint.png")
    assert denied.status_code == 401
    denied_turn = stranger.get("/api/student/tasks/task-1/turns/0/assets/hint.png")
    assert denied_turn.status_code == 401


def test_ask_streams_the_kind_before_the_finished_task(monkeypatch):
    room = Classroom(
        TaskCatalog(),
        ScriptedDecisionAgent(presets=("先看题目",), scaffold_type="提示"),
        ScriptedScaffoldAgent(draft=ScaffoldDraft(text="先看已经写出的部分")),
    )
    monkeypatch.setattr("zpd_api.classroom_api.get_room", lambda: room)
    teacher = TestClient(app)
    teacher.post("/api/login", json={"role": "教师", "account": "643590872", "password": "643590872"})
    teacher.post("/api/teacher/classes", json={"name": "一班"})
    teacher.post("/api/teacher/tasks")
    teacher.post("/api/teacher/tasks/task-1", json={
        "action": "save",
        "questions": [{"kind": "判断", "prompt": "判断说法", "selected": ["正确"], "explanation": ""}],
    })
    teacher.post("/api/teacher/tasks/task-1", json={"action": "publish"})
    teacher.post("/api/teacher/tasks/task-1", json={"action": "布置", "class_ids": ["class-1"]})
    student = TestClient(app)
    student.post("/api/register", json={"account": "s1", "password": "secret", "name": "甲", "class_id": "class-1"})

    with student.stream(
        "POST",
        "/api/student/tasks/task-1/ask",
        json={"question": "这题怎么看", "source": "自己写的"},
        headers={"Accept": "text/event-stream"},
    ) as response:
        raw = response.read().decode()

    assert "event: kind\ndata: \"思维导图\"" in raw
    assert raw.index("event: kind") < raw.index("event: task")
    assert "先看已经写出的部分" in raw
