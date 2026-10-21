from urllib.parse import quote

from scaffolding.agents import ScaffoldDraft
from scaffolding.records import TrueFalseQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage, response_for
from scaffolding.tasks import TaskCatalog
from tests.student_page_helpers import body_text


def _page(draft=None, scaffold_type="提示", error=None):
    catalog = TaskCatalog()
    task = catalog.create((TrueFalseQuestion("判断说法", "正确", "题目里有依据"),))
    catalog.publish(task.task_id)
    decision = ScriptedDecisionAgent(presets=("先看题目",), scaffold_type=scaffold_type)
    scaffold = ScriptedScaffoldAgent(draft=draft, error=error)
    page = StudentPage(catalog, decision, scaffold)
    return catalog, task.task_id, decision, scaffold, page


_HTML = (
    '<asset kind="图片素材" name="图.png">PNGDATA</asset>'
    '<asset kind="思维导图" name="导图.svg">导图内容</asset>'
    '<asset kind="结构图" name="结构.svg">结构内容</asset>'
    '<asset kind="微格动画" name="动画.html"><anim></asset>'
)


def test_preset_and_own_questions_show_text_and_four_assets():
    draft = ScaffoldDraft(text="先看人员和硬件是否都写到了。", html=_HTML)
    catalog, task_id, decision, scaffold, page = _page(draft)
    page.open_task(task_id, 0)

    clicked = page.ask(task_id, "先看题目", "预设提问", 1)

    assert scaffold.calls[0]["scaffold_type"] == "提示"
    assert scaffold.calls[0]["question"] == "先看题目"
    assert "先看人员和硬件是否都写到了。" in clicked
    assert "图片素材" in clicked and "图.png" in clicked
    assert "思维导图" in clicked and "导图.svg" in clicked
    assert "结构图" in clicked and "结构.svg" in clicked
    assert "微格动画" in clicked and "动画.html" in clicked
    assert quote("图.png", safe="") in clicked
    assert "<asset" not in clicked
    assert "<anim>" not in clicked
    assert "PNGDATA" not in clicked
    decision.presets = ("改后预设",)
    edited = page.edit_answer(task_id, 0, selected=("错误",), now=2)
    assert "先看人员和硬件是否都写到了。" in edited
    assert "改后预设" in edited

    own = response_for(page, "POST", "/tasks/" + task_id + "/ask", "question=还缺什么？&source=自己写的", 3)
    assert scaffold.calls[1]["question"] == "还缺什么？"
    assert "还缺什么？" in body_text(own)


def test_blank_question_does_not_call_the_agents():
    catalog, task_id, decision, scaffold, page = _page(ScaffoldDraft(text="有支架", html=_HTML))
    page.open_task(task_id, 0)

    html = page.ask(task_id, "   ", "自己写的", 1)

    assert decision.choose_calls == []
    assert scaffold.calls == []
    assert "<h2>支架</h2>" not in html


def test_failed_help_keeps_the_existing_scaffold_and_records_the_question():
    draft = ScaffoldDraft(text="先看人员和硬件是否都写到了。", html=_HTML)
    catalog, task_id, decision, scaffold, page = _page(draft)
    page.open_task(task_id, 0)
    page.ask(task_id, "先看题目", "预设提问", 1)
    decision.scaffold_type = "课外"

    illegal = page.ask(task_id, "课外提问", "自己写的", 2)
    article = illegal.split("<article>")[-1]
    assert "课外提问" in article
    assert "turn-scaffold" not in article
    assert "先看人员和硬件是否都写到了。" in illegal
    assert "先看题目" in illegal

    decision.scaffold_type = "提示"
    scaffold.error = RuntimeError("down")
    failed = page.ask(task_id, "调用失败", "自己写的", 3)
    assert "调用失败" in failed.split("<article>")[-1]
    assert "turn-scaffold" not in failed.split("<article>")[-1]
    assert "先看人员和硬件是否都写到了。" in failed

    scaffold.error = None
    scaffold.draft = ScaffoldDraft()
    empty = page.ask(task_id, "空支架", "自己写的", 4)
    assert "空支架" in empty.split("<article>")[-1]
    assert "turn-scaffold" not in empty.split("<article>")[-1]
    assert "先看人员和硬件是否都写到了。" in empty
