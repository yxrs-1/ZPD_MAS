from urllib.parse import urlencode

from scaffolding.knowledge import KnowledgeBase
from scaffolding.objectives import ObjectiveCatalog
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage
from tests.objective_helpers import ScriptedExtractor


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


def make_page(base=None, extractor=None, catalog=None, generation=None, prefix=""):
    if base is None:
        base = KnowledgeBase()
    if extractor is None:
        extractor = ScriptedExtractor()
    objectives = ObjectiveCatalog(base, extractor)
    if catalog is None:
        catalog = TaskCatalog()
    page = TeacherPage(
        catalog,
        prefix=prefix,
        knowledge=base,
        objectives=objectives,
        generation=generation,
    )
    return page, objectives
