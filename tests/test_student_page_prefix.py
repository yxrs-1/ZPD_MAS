from scaffolding.agents import ScaffoldDraft
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.student_page import StudentPage, response_for
from tests.student_page_helpers import body_text, true_false_catalog


def test_the_student_prefix_is_written_on_forms_and_assets():
    catalog, task_id = true_false_catalog()
    draft = ScaffoldDraft(
        text="先看。",
        html='<asset kind="图片素材" name="a.png">AAAA</asset>',
    )
    page = StudentPage(
        catalog,
        ScriptedDecisionAgent(presets=("先看题目",)),
        ScriptedScaffoldAgent(draft),
        prefix="/student",
    )

    opened = body_text(response_for(page, "GET", "/tasks/" + task_id, "", 0))
    asked = body_text(response_for(page, "POST", "/tasks/" + task_id + "/ask", "question=先看题目&source=预设提问", 1))
    listed = body_text(response_for(page, "GET", "/", "", 2))

    assert 'href="/student/tasks/' + task_id + '"' in listed
    assert 'action="/student/tasks/' + task_id + '/answers"' in opened
    assert 'action="/student/tasks/' + task_id + '/ask"' in opened
    assert 'action="/student/tasks/' + task_id + '/submit"' in opened
    assert 'src="/student/tasks/' + task_id + '/assets/a.png"' in asked
    assert 'src="/student/tasks/' + task_id + '/turns/0/assets/a.png"' in asked
    assert 'action="/tasks/' not in opened
