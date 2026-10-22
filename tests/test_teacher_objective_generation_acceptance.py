from pathlib import Path

from scaffolding.classroom import Classroom, production_classroom, response_for, serve
from scaffolding.generation import TaskGeneration
from scaffolding.model_text import ModelTextGenerator
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.tasks import TaskCatalog
from tests.classroom_helpers import student_cookie, teacher_cookie, text
from tests.generation_helpers import ScriptedGenerator
from tests.objective_helpers import ScriptedExtractor, sample_base
from tests.teacher_objectives_helpers import form
from tests.test_text_generation_record import ScriptedTextGenerator


def test_the_classroom_hides_objective_generation_until_objectives_exist():
    room = Classroom(TaskCatalog(), ScriptedDecisionAgent(), ScriptedScaffoldAgent())

    home = text(response_for(room, "GET", "/", "", 0))
    listed = text(response_for(room, "GET", "/teacher", "", 0, teacher_cookie(room)))
    objectives = text(response_for(room, "GET", "/teacher/objectives/", "", 0, teacher_cookie(room)))
    student = response_for(room, "GET", "/student/objectives", "", 1, student_cookie(room))

    assert "按目标生成" not in home
    assert "按目标生成" not in listed
    assert 'href="/teacher/objectives"' in listed
    assert 'href="/teacher/generation">生成</a>' in objectives
    assert "按目标生成" not in objectives
    assert student.status == 404
    assert "任务不存在" in text(student)


def test_the_classroom_generates_from_saved_objectives():
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (
        ObjectiveDraft("信息意识", "能识别信息", retrieval.lesson_source),
    )
    catalog = TaskCatalog()
    objectives = ObjectiveCatalog(base, extractor)
    objectives.extract_lesson("人教版", "必修一", "信息系统的组成")
    generation = TaskGeneration(
        objectives, catalog, ScriptedGenerator(), ScriptedTextGenerator()
    )
    room = Classroom(
        catalog,
        ScriptedDecisionAgent(),
        ScriptedScaffoldAgent(),
        base,
        objectives,
        generation,
    )

    opened = text(response_for(room, "POST", "/teacher/objectives", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        action="按目标生成",
    ), 0, teacher_cookie(room)))
    viewed = text(response_for(room, "POST", "/teacher/objectives?ready=1", form(
        mode="课时",
        version="人教版",
        volume="必修一",
        lesson="信息系统的组成",
        action="查看",
    ), 0, teacher_cookie(room)))

    assert "未发布" in opened
    assert "task-1" in viewed
    assert 'action="/teacher/objectives"' in viewed
    assert 'value="按目标生成"' in viewed


def test_production_still_prepares_the_text_generator_without_calling_it(tmp_path, monkeypatch):
    repo = Path.cwd()
    monkeypatch.chdir(tmp_path)

    def post(_request):
        raise AssertionError("network")

    room = production_classroom(post=post)
    monkeypatch.chdir(repo)

    assert isinstance(room.generation._text_generator, ModelTextGenerator)
    assert room.teacher.generation is room.generation
    assert Path("docs/superpowers/specs/2026-10-22-teacher-objective-generation-design.md").is_file()
    assert callable(serve)
    assert callable(production_classroom)
