from scaffolding.records import Behavior, ItemAnswer, OpenQuestion, ScaffoldType, TaskRecord
from scaffolding.scaffold_decision import ScaffoldDecision
from zpd_api.scaffold_bridge import choose_scaffold_type


def test_help_uses_the_saved_answer(monkeypatch):
    seen = {}

    async def decide(state, answer, previous, client=None):
        seen["state"] = state
        seen["answer"] = answer
        seen["previous"] = previous
        return ScaffoldDecision(scaffold_type=ScaffoldType.EXPLANATION, reason="因为学生已经写了一步")

    monkeypatch.setattr("zpd_api.scaffold_bridge.decide_scaffold_type", decide)
    record = TaskRecord(
        (OpenQuestion("第一题", "写出过程"),),
        (ItemAnswer(text="我先算了一半"),),
        Behavior(),
    )
    assert choose_scaffold_type(record, "下一步怎么写") == "解释"
    assert "下一步怎么写" in seen["state"]
    assert "我先算了一半" in seen["answer"]
    assert seen["previous"] == []


def test_original_login_is_served_and_api_stays():
    from fastapi.testclient import TestClient
    from zpd_api.main import app

    client = TestClient(app)
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    page = client.get("/")
    assert page.status_code == 200
    assert "登录" in page.text
    assert "决定支架" not in page.text
