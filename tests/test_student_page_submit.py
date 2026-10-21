from scaffolding.agents import ScaffoldDraft
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage, response_for
from scaffolding.tasks import TaskCatalog
from tests.student_page_helpers import body_text


def test_submit_locks_the_page_and_reveals_keys():
    catalog = TaskCatalog()
    task = catalog.create((
        ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "硬件"), ("人员",), "选择依据"),
        TrueFalseQuestion("判断说法", "正确", "题目里有依据"),
        OpenQuestion("完成作品", "写明人员"),
    ))
    catalog.publish(task.task_id)
    decision = ScriptedDecisionAgent(presets=("先看题目",))
    draft = ScaffoldDraft(text="先看人员和硬件是否都写到了。", html="")
    page = StudentPage(catalog, decision, ScriptedScaffoldAgent(draft))
    page.open_task(task.task_id, 0)
    page.edit_answer(task.task_id, 0, selected=("人员",), now=1)
    page.ask(task.task_id, "旧求助原文", "自己写的", 2)

    response = response_for(page, "POST", "/tasks/" + task.task_id + "/submit", "", 3)
    html = body_text(response)

    assert response.status == 200
    assert "已完成" in html
    assert "disabled" in html
    assert "<button type=\"submit\">保存作答</button>" not in html
    assert "<button type=\"submit\">提问</button>" not in html
    assert "<button type=\"submit\">提交</button>" not in html
    assert "先看题目" not in html
    assert "旧求助原文" in html
    assert "先看人员和硬件是否都写到了。" in html
    assert "参考答案：人员" in html
    assert "解析：选择依据" in html
    assert "参考答案：正确" in html
    assert "解析：题目里有依据" in html
    sections = html.split("<section>")
    assert "<p>参考答案：</p><p>解析：</p>" in sections[3]
    assert "已完成" in page.todo()

    again = page.edit_answer(task.task_id, 0, selected=("硬件",), now=4)
    asked = page.ask(task.task_id, "再问一次", "自己写的", 5)

    assert catalog.work(task.task_id).answers[0].selected == ("人员",)
    assert 'value="硬件" checked' not in again
    assert "再问一次" not in asked
    assert len(catalog.work(task.task_id).dialogue) == 1
