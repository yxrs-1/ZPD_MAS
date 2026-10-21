from urllib.parse import quote

from scaffolding.agents import ScaffoldDraft
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage, response_for
from tests.student_page_helpers import true_false_catalog


def test_one_asset_is_returned_and_unknown_names_are_empty():
    catalog, task_id = true_false_catalog()
    draft = ScaffoldDraft(
        text="先看。",
        html=(
            '<asset kind="思维导图" name="组成.svg">第一</asset>'
            '<asset kind="结构图" name="组成.svg">第二</asset>'
        ),
    )
    page = StudentPage(catalog, ScriptedDecisionAgent(presets=("先看题目",)), ScriptedScaffoldAgent(draft))
    page.open_task(task_id, 0)
    page.ask(task_id, "先看题目", "预设提问", 1)
    path = "/tasks/" + task_id + "/assets/" + quote("组成.svg", safe="")

    found = response_for(page, "GET", path, "", 2)
    missing = response_for(page, "GET", "/tasks/" + task_id + "/assets/没有.svg", "", 2)

    assert found.status == 200
    assert found.filename == "组成.svg"
    assert found.body == "第一".encode()
    assert found.content_type == "application/octet-stream"
    assert missing.status == 404
    assert missing.body == b""


def test_a_page_without_assets_does_not_offer_export():
    catalog, task_id = true_false_catalog()
    page = StudentPage(catalog, ScriptedDecisionAgent(presets=("先看题目",)), ScriptedScaffoldAgent())
    html = page.open_task(task_id, 0)

    assert ">保存</a>" not in html
    assert page.asset(task_id, "组成.svg") is None
