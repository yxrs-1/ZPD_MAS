from scaffolding.records import OpenQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.tasks import TaskCatalog
from scaffolding.session import Session


def test_before_help_the_page_shows_presets_and_no_scaffold():
    decision = ScriptedDecisionAgent(presets=("这一步要判断什么？", "作品还缺哪一部分？"))
    catalog = TaskCatalog()
    task = catalog.create((OpenQuestion("完成作品并判断说法", "写出组成"),))
    catalog.publish(task.task_id)
    session = Session(catalog, catalog.start(task.task_id), decision, ScriptedScaffoldAgent())

    view = session.view()

    assert view.presets == ("这一步要判断什么？", "作品还缺哪一部分？")
    assert view.scaffold is None
    assert view.status == "待办"
    assert decision.choose_calls == []
