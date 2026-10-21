from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage, response_for
from scaffolding.tasks import TaskCatalog
from tests.student_page_helpers import body_text


class FailSecondSuggest:
    def __init__(self) -> None:
        self.calls = 0

    def suggest(self, record):
        self.calls += 1
        if self.calls >= 2:
            raise RuntimeError("down")
        return ("先看题目",)

    def choose_type(self, record, question):
        return "提示"


def _catalog():
    catalog = TaskCatalog()
    task = catalog.create((
        ChoiceQuestion("选出人员", SelectionMode.SINGLE, ("人员", "硬件"), ("人员",), "选择依据"),
    ))
    catalog.publish(task.task_id)
    return catalog, task.task_id


def test_an_accepted_edit_refreshes_presets_and_a_rejected_edit_keeps_the_answer():
    catalog, task_id = _catalog()
    decision = ScriptedDecisionAgent(presets=("先看题目",))
    page = StudentPage(catalog, decision, ScriptedScaffoldAgent())
    page.open_task(task_id, 0)
    decision.presets = ("改后预设",)

    accepted = page.edit_answer(task_id, 0, selected=("人员",), now=1)

    assert 'value="人员" checked' in accepted
    assert "改后预设" in accepted
    assert catalog.work(task_id).answers[0].selected == ("人员",)
    decision.presets = ("不应出现",)

    rejected = page.edit_answer(task_id, 0, selected=("人员", "硬件"), now=2)

    assert 'value="人员" checked' in rejected
    assert "改后预设" in rejected
    assert "不应出现" not in rejected
    assert catalog.work(task_id).answers[0].selected == ("人员",)


def test_a_failed_preset_refresh_keeps_the_new_answer_and_the_old_presets():
    catalog, task_id = _catalog()
    page = StudentPage(catalog, FailSecondSuggest(), ScriptedScaffoldAgent())
    page.open_task(task_id, 0)

    html = page.edit_answer(task_id, 0, selected=("硬件",), now=1)

    assert 'value="硬件" checked' in html
    assert "先看题目" in html
    assert catalog.work(task_id).answers[0].selected == ("硬件",)


def test_posting_the_answer_form_updates_the_page():
    catalog, task_id = _catalog()
    decision = ScriptedDecisionAgent(presets=("先看题目",))
    page = StudentPage(catalog, decision, ScriptedScaffoldAgent())
    page.open_task(task_id, 0)
    decision.presets = ("改后预设",)

    response = response_for(page, "POST", "/tasks/" + task_id + "/answers", "selected-0=人员", 3)

    assert response.status == 200
    assert "改后预设" in body_text(response)
    assert catalog.work(task_id).answers[0].selected == ("人员",)


def test_saving_the_form_clears_an_unchecked_multiple_choice():
    catalog = TaskCatalog()
    task = catalog.create((
        ChoiceQuestion("选出组成", SelectionMode.MULTIPLE, ("人员", "硬件"), ("人员",), "多选依据"),
        OpenQuestion("完成作品", "写明人员"),
    ))
    catalog.publish(task.task_id)
    page = StudentPage(catalog, ScriptedDecisionAgent(presets=("先看题目",)), ScriptedScaffoldAgent())
    page.open_task(task.task_id, 0)
    page.edit_answer(task.task_id, 0, selected=("人员", "硬件"), now=1)

    response = response_for(page, "POST", "/tasks/" + task.task_id + "/answers", "text-1=essay", 2)

    assert response.status == 200
    text = body_text(response)
    assert catalog.work(task.task_id).answers[0].selected == ()
    assert catalog.work(task.task_id).answers[1].text == "essay"
    assert 'value="人员" checked' not in text
    assert 'value="硬件" checked' not in text
