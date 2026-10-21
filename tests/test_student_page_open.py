from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage, response_for
from scaffolding.tasks import TaskCatalog
from tests.student_page_helpers import body_text


def _catalog():
    catalog = TaskCatalog()
    task = catalog.create((
        ChoiceQuestion("选出<人员>", SelectionMode.SINGLE, ("人员", "<硬件>"), ("人员",), "选择依据"),
        ChoiceQuestion("选出组成", SelectionMode.MULTIPLE, ("人员", "硬件", "软件"), ("人员", "硬件"), "多选依据"),
        TrueFalseQuestion("判断说法", "正确", "题目里有依据"),
        OpenQuestion("完成作品", "写明人员", "标准作品", "作品解析"),
    ))
    catalog.publish(task.task_id)
    return catalog, task.task_id


def test_opening_a_published_task_starts_it_and_shows_questions_without_keys():
    catalog, task_id = _catalog()
    decision = ScriptedDecisionAgent(presets=("先看题目",))
    page = StudentPage(catalog, decision, ScriptedScaffoldAgent())

    html = page.open_task(task_id, 0)

    assert catalog.get(task_id).started is True
    assert task_id in page.sessions
    assert page.shown_at[task_id] == 0
    assert "单选" in html
    assert "多选" in html
    assert 'type="checkbox"' in html
    assert "选出&lt;人员&gt;" in html
    assert "&lt;硬件&gt;" in html
    assert "<硬件>" not in html
    assert "判断" in html
    assert "判断说法" in html
    assert "综合" in html
    assert "完成作品" in html
    assert "写明人员" in html
    assert "先看题目" in html
    assert "选择依据" not in html
    assert "多选依据" not in html
    assert "题目里有依据" not in html
    assert "标准作品" not in html
    assert "作品解析" not in html
    assert "参考答案" not in html
    assert "解析" not in html
    assert "<h2>支架</h2>" not in html
    response = response_for(page, "GET", "/tasks/" + task_id, "", 1)
    assert response.status == 200
    assert task_id in body_text(response)


def test_opening_again_uses_the_same_session():
    catalog, task_id = _catalog()
    decision = ScriptedDecisionAgent(presets=("先看题目",))
    page = StudentPage(catalog, decision, ScriptedScaffoldAgent())
    page.open_task(task_id, 0)
    decision.presets = ("新的预设",)

    html = page.open_task(task_id, 1)

    assert "先看题目" in html
    assert "新的预设" not in html
    assert len(page.sessions) == 1
