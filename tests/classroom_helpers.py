from urllib.parse import urlencode

from scaffolding.classroom import Classroom
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.tasks import TaskCatalog


def room():
    return Classroom(TaskCatalog(), ScriptedDecisionAgent(), ScriptedScaffoldAgent())


def text(response) -> str:
    return response.body.decode()


def form(**fields) -> str:
    pairs = []
    for key, value in fields.items():
        if isinstance(value, (list, tuple)):
            for item in value:
                pairs.append((key, item))
        else:
            pairs.append((key, value))
    return urlencode(pairs)
