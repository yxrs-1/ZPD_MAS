import asyncio

from httpx import ASGITransport, AsyncClient

from scaffolding.records import ScaffoldType
from scaffolding.scaffold_decision import PreviousScaffold, ScaffoldDecision
from zpd_api.main import app
from zpd_api.routes import get_repo
import zpd_api.routes as routes


def test_model_choice_is_kept_and_retrieval_happens_after_it(monkeypatch):
    order = []
    saved = {}

    class Repo:
        async def previous(self, student_id, task_id):
            order.append("previous")
            assert student_id == "s1"
            assert task_id == "t1"
            return [PreviousScaffold(scaffold_type=ScaffoldType.FEEDBACK, content="先看条件")]

        async def save_decision(self, **kwargs):
            order.append("save")
            saved.update(kwargs)

    async def decide(student_state, student_answer, previous, client=None):
        order.append("decide")
        assert student_state == "首次求助"
        assert student_answer == "我选了 A"
        assert previous[0].content == "先看条件"
        return ScaffoldDecision(scaffold_type=ScaffoldType.MODELING, reason="需要一个同类例子")

    def retrieve(query):
        order.append("retrieve")
        assert query == "示范\n我选了 A"
        return ["教材里的同类例子"]

    async def repo_dependency():
        yield Repo()

    monkeypatch.setattr(routes, "decide_scaffold_type", decide)
    monkeypatch.setattr(routes, "retrieve_passages", retrieve)
    monkeypatch.setattr(routes, "deepseek_client", lambda: None)
    app.dependency_overrides[get_repo] = repo_dependency

    async def request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/api/scaffold-decisions",
                json={
                    "student_id": "s1",
                    "task_id": "t1",
                    "student_state": "首次求助",
                    "student_answer": "我选了 A",
                },
            )

    response = asyncio.run(request())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "scaffold_type": "示范",
        "reason": "需要一个同类例子",
        "passages": ["教材里的同类例子"],
    }
    assert order == ["previous", "decide", "retrieve", "save"]
    assert saved["scaffold_type"] == "示范"
    assert saved["content"] == "需要一个同类例子"


def test_upload_returns_queued_without_embedding(monkeypatch):
    queued = []

    class Repo:
        async def add_material(self, name, content):
            assert name == "lesson.pdf"
            assert content == b"pdf-bytes"
            return 7

    async def repo_dependency():
        yield Repo()

    monkeypatch.setattr(routes, "enqueue_ingest", lambda material_id: queued.append(material_id))
    app.dependency_overrides[get_repo] = repo_dependency

    async def request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/api/documents",
                files={"file": ("lesson.pdf", b"pdf-bytes", "application/pdf")},
            )

    response = asyncio.run(request())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"id": 7, "status": "queued"}
    assert queued == [7]
