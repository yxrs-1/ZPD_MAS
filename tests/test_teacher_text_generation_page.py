from scaffolding.generation import TaskGeneration
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import response_for
from tests.generation_helpers import ScriptedGenerator
from tests.teacher_objectives_helpers import form, make_page, text
from tests.test_text_generation_record import ScriptedTextGenerator


def _page(generator=None, prefix=""):
    catalog = TaskCatalog()
    page, _objectives = make_page(catalog=catalog, prefix=prefix)
    if generator is not None:
        page.generation = TaskGeneration(
            page.objectives, catalog, ScriptedGenerator(), generator
        )
    return page, generator


def test_the_objectives_form_links_to_a_blank_generation_page():
    page, _generator = _page(prefix="/teacher")

    opened = text(response_for(page, "GET", "/objectives", ""))
    generated = text(response_for(page, "GET", "/generation/?ready=1", ""))
    listed = text(response_for(page, "GET", "/", ""))

    assert 'href="/teacher/generation"' not in opened
    assert 'action="/teacher/objectives"' in opened
    assert 'name="text"' in opened
    assert "生成目标" in opened
    assert 'name="file"' not in opened
    assert "<textarea name=\"text\"></textarea>" in generated
    assert "生成失败，没有创建任务" not in generated
    assert 'action="/teacher/generation"' in generated
    assert 'href="/teacher/generation"' not in listed


def test_blank_text_and_a_missing_generator_do_not_call_the_model():
    generator = ScriptedTextGenerator()
    page, _generator = _page(generator)
    bare, _none = make_page()

    blank = response_for(page, "POST", "/generation/", form(text="   "))
    absent = response_for(page, "POST", "/generation", "")
    missing = response_for(bare, "POST", "/generation", form(text=["先", "<需求"]))

    assert blank.status == 200
    assert "生成失败，没有创建任务" in text(blank)
    assert "<textarea name=\"text\">   </textarea>" in text(blank)
    assert absent.status == 200
    assert "生成失败，没有创建任务" in text(absent)
    assert generator.calls == []
    assert missing.status == 200
    assert "生成失败，没有创建任务" in text(missing)
    assert "<textarea name=\"text\">&lt;需求</textarea>" in text(missing)
    assert "<需求" not in text(missing)
    assert bare.catalog._tasks == {}


def test_a_rejected_reply_keeps_the_text_and_the_existing_task():
    generator = ScriptedTextGenerator()
    generator.error = RuntimeError("boom")
    page, _generator = _page(generator)
    kept = page.catalog.create(())

    failed = response_for(page, "POST", "/generation", form(text="出题"))

    assert failed.status == 200
    assert "生成失败，没有创建任务" in text(failed)
    assert "<textarea name=\"text\">出题</textarea>" in text(failed)
    assert list(page.catalog._tasks) == [kept.task_id]
    assert generator.calls == ["出题"]
