from pathlib import Path

from scaffolding.agents import ScaffoldDraft
from scaffolding.model_decision import ModelDecisionAgent
from scaffolding.model_scaffold import ModelScaffoldAgent
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage, production_page, response_for
from scaffolding.tasks import TaskCatalog
from tests.student_page_helpers import body_text, true_false_catalog


def test_student_page_spec_is_in_the_workspace():
    spec = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "specs" / "2026-10-21-student-page-design.md"
    assert spec.is_file()


def test_a_student_can_open_ask_save_one_asset_and_submit():
    catalog, task_id = true_false_catalog()
    draft = ScaffoldDraft(
        text="先看人员和硬件是否都写到了。",
        html='<asset kind="思维导图" name="组成.svg">人员—硬件</asset>',
    )
    page = StudentPage(
        catalog,
        ScriptedDecisionAgent(presets=("先看题目",), scaffold_type="提示"),
        ScriptedScaffoldAgent(draft),
    )

    todo = response_for(page, "GET", "/", "", 0)
    assert task_id in body_text(todo)
    assert catalog.get(task_id).started is False

    opened = response_for(page, "GET", "/tasks/" + task_id, "", 0)
    assert "判断说法" in body_text(opened)
    assert "先看题目" in body_text(opened)
    assert "题目里有依据" not in body_text(opened)

    asked = response_for(page, "POST", "/tasks/" + task_id + "/ask", "question=先看题目&source=预设提问", 1)
    assert "先看人员和硬件是否都写到了。" in body_text(asked)
    assert "<asset" not in body_text(asked)
    asset = response_for(page, "GET", "/tasks/" + task_id + "/assets/组成.svg", "", 1)
    assert asset.body == "人员—硬件".encode()

    submitted = response_for(page, "POST", "/tasks/" + task_id + "/submit", "", 2)
    assert "已完成" in body_text(submitted)
    assert "参考答案：正确" in body_text(submitted)
    assert "解析：题目里有依据" in body_text(submitted)

    fresh = StudentPage(TaskCatalog(), ScriptedDecisionAgent(), ScriptedScaffoldAgent())
    assert task_id not in fresh.todo()
    assert fresh.sessions == {}


def test_production_page_uses_the_model_agents_without_a_network_call():
    def post(url, headers, payload):
        raise AssertionError("network")

    page = production_page(TaskCatalog(), post=post, api_key="secret")

    assert isinstance(page.decision, ModelDecisionAgent)
    assert isinstance(page.scaffold_agent, ModelScaffoldAgent)
