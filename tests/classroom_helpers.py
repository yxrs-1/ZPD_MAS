from urllib.parse import urlencode

from scaffolding.classroom import Classroom, response_for
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


def teacher_cookie(page) -> str:
    response = response_for(
        page, "POST", "/teacher/login", form(account="643590872", password="643590872"), 0
    )
    return response.set_cookie.split(";", 1)[0]


def student_cookie(page, account="s1", password="secret", name="甲") -> str:
    if page.roster.authenticate_student(account, password) is None:
        created = page.roster.create_class("一班")
        page.roster.import_rows(created.class_id, ((2, account, password, name),))
    response = response_for(
        page, "POST", "/student/login", form(account=account, password=password), 0
    )
    return response.set_cookie.split(";", 1)[0]
