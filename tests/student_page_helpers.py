from scaffolding.records import TrueFalseQuestion
from scaffolding.tasks import TaskCatalog


def true_false_catalog(prompt="判断说法"):
    catalog = TaskCatalog()
    task = catalog.create((TrueFalseQuestion(prompt, "正确", "题目里有依据"),))
    catalog.publish(task.task_id)
    return catalog, task.task_id


def body_text(response) -> str:
    return response.body.decode()
