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


def test_an_earlier_scaffold_file_stays_available_after_a_later_scaffold():
    catalog, task_id = true_false_catalog()
    agent = ScriptedScaffoldAgent(draft=ScaffoldDraft(
        text="第一支架",
        html='<asset kind="图片素材" name="a.png">AAAA</asset>',
    ))
    page = StudentPage(catalog, ScriptedDecisionAgent(presets=("先看题目",)), agent)
    page.open_task(task_id, 0)
    page.ask(task_id, "先看题目", "预设提问", 1)
    agent.draft = ScaffoldDraft(
        text="第二支架",
        html=(
            '<asset kind="图片素材" name="a.png">CCCC</asset>'
            '<asset kind="思维导图" name="b.svg">BBBB</asset>'
        ),
    )

    html = page.ask(task_id, "再看一层", "自己写的", 2)
    article = html.split("<article>")[1]
    first = "/tasks/" + task_id + "/turns/0/assets/" + quote("a.png", safe="")
    earlier = response_for(page, "GET", first, "", 3)
    current_old = response_for(page, "GET", "/tasks/" + task_id + "/assets/" + quote("a.png", safe=""), "", 3)
    current_new = response_for(page, "GET", "/tasks/" + task_id + "/assets/" + quote("b.svg", safe=""), "", 3)
    wrong_turn = response_for(page, "GET", "/tasks/" + task_id + "/turns/0/assets/" + quote("b.svg", safe=""), "", 3)

    assert first in article
    assert earlier.status == 200
    assert earlier.filename == "a.png"
    assert earlier.body == "AAAA".encode()
    assert current_old.status == 200
    assert current_old.body == "CCCC".encode()
    assert current_new.status == 200
    assert current_new.body == "BBBB".encode()
    assert wrong_turn.status == 404
    assert wrong_turn.body == b""


def test_a_page_without_assets_does_not_offer_export():
    catalog, task_id = true_false_catalog()
    page = StudentPage(catalog, ScriptedDecisionAgent(presets=("先看题目",)), ScriptedScaffoldAgent())
    html = page.open_task(task_id, 0)

    assert ">保存</a>" not in html
    assert page.asset(task_id, "组成.svg") is None
