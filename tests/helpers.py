from scaffolding.records import OpenQuestion, TrueFalseQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.session import Session
from scaffolding.tasks import TaskCatalog


def open_session(decision=None, scaffold_agent=None, prompt="判断说法"):
    catalog = TaskCatalog()
    task = catalog.create((TrueFalseQuestion(prompt, "正确", "题目里有依据"),))
    catalog.publish(task.task_id)
    work = catalog.start(task.task_id)
    return Session(
        catalog,
        work,
        decision if decision is not None else ScriptedDecisionAgent(),
        scaffold_agent if scaffold_agent is not None else ScriptedScaffoldAgent(),
    )
