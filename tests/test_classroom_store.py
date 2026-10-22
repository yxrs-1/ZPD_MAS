import base64
import json
import os

from scaffolding.agents import ScaffoldDraft
from scaffolding.classroom import Classroom, production_classroom, response_for
from scaffolding.generation import LessonOrigin, TaskGeneration
from scaffolding.knowledge import CurriculumStandard, KnowledgeBase, TextbookLesson
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft
from scaffolding.records import Asset, AssetKind, TrueFalseQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.session import Scaffold, Session
from scaffolding.tasks import TaskCatalog
from tests.classroom_helpers import form, teacher_cookie, text
from tests.test_sheet import _xlsx


_RAW = b"\x89PNG\r\n\x1a\n"
_KEYS = (
    "teacher_password",
    "classes",
    "students",
    "tasks",
    "drafts",
    "assignments",
    "works",
    "lessons",
    "standards",
    "objectives",
    "origins",
)


class _Extractor:
    def extract(self, retrieval):
        return (ObjectiveDraft("计算思维", "能分辨系统和要素", retrieval.lesson_source),)


class _Generator:
    def generate(self, counts, objectives):
        raise AssertionError("model")


class _RaisingDecision:
    def suggest(self, record):
        raise AssertionError("suggest")

    def choose_type(self, record, question):
        raise AssertionError("choose")


class _CountingDecision:
    def __init__(self):
        self.suggest_calls = 0

    def suggest(self, record):
        self.suggest_calls += 1
        raise AssertionError("suggest")

    def choose_type(self, record, question):
        raise AssertionError("choose")


def _cookie(response) -> str:
    return response.set_cookie.split(";", 1)[0]


def _room(path, decision=None, scaffold=None):
    decision = decision or ScriptedDecisionAgent(presets=("先看题目", "作品还缺哪一部分？"))
    scaffold = scaffold or ScriptedScaffoldAgent(
        draft=ScaffoldDraft(text="先看人员和硬件", assets=(Asset(AssetKind.IMAGE, "figure.png", _RAW),))
    )
    knowledge = KnowledgeBase()
    objectives = ObjectiveCatalog(knowledge, _Extractor())
    catalog = TaskCatalog()
    generation = TaskGeneration(objectives, catalog, _Generator())
    return Classroom(catalog, decision, scaffold, knowledge, objectives, generation, path=path)


def _assigned_student(tmp_path):
    path = tmp_path / "classroom.json"
    page = _room(path)
    headers = teacher_cookie(page)
    response_for(page, "POST", "/teacher/classes", form(action="创建", name="一班"), 0, headers)
    response_for(
        page, "POST", "/teacher/classes/class-1", form(action="导入"), 0, headers,
        uploads={"file": _xlsx((("账号", "密码", "姓名"), ("s1", "secret", "甲")))},
    )
    response_for(page, "POST", "/teacher/tasks", "", 0, headers)
    response_for(page, "POST", "/teacher/tasks/task-1", form(**{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "selected-0": "正确",
        "explanation-0": "题目里有依据",
        "action": "save",
    }), 0, headers)
    response_for(page, "POST", "/teacher/tasks/task-1", form(action="publish"), 0, headers)
    response_for(page, "POST", "/teacher/tasks/task-1", form(action="布置", class_id="class-1"), 0, headers)
    student = response_for(page, "POST", "/student/login", form(account="s1", password="secret"), 0)
    return page, path, _cookie(student)


def _two_scaffolded_students(tmp_path):
    path = tmp_path / "classroom.json"
    page = _room(path)
    headers = teacher_cookie(page)
    response_for(page, "POST", "/teacher/classes", form(action="创建", name="一班"), 0, headers)
    response_for(
        page, "POST", "/teacher/classes/class-1", form(action="导入"), 0, headers,
        uploads={"file": _xlsx((("账号", "密码", "姓名"), ("s1", "secret", "甲"), ("s2", "secret", "乙")))},
    )
    response_for(page, "POST", "/teacher/tasks", "", 0, headers)
    response_for(page, "POST", "/teacher/tasks/task-1", form(**{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "selected-0": "正确",
        "explanation-0": "题目里有依据",
        "action": "save",
    }), 0, headers)
    response_for(page, "POST", "/teacher/tasks/task-1", form(action="publish"), 0, headers)
    response_for(page, "POST", "/teacher/tasks/task-1", form(action="布置", class_id="class-1"), 0, headers)
    for account in ("s1", "s2"):
        student = response_for(page, "POST", "/student/login", form(account=account, password="secret"), 0)
        cookie = _cookie(student)
        response_for(page, "GET", "/student/tasks/task-1", "", 0, cookie)
        response_for(
            page, "POST", "/student/tasks/task-1/answers",
            form(**{"selected-0": "正确"}), 0, cookie,
        )
        response_for(
            page, "POST", "/student/tasks/task-1/ask",
            form(question="先看题目", source="预设提问"), 0, cookie,
        )
    return path


def _assert_restored(room, account, decision):
    assert decision.suggest_calls == 0
    session = room.student_pages[account].sessions["task-1"]
    assert session.view().presets == ("先看题目", "作品还缺哪一部分？")
    assert session.view().scaffold is not None
    assert session.view().scaffold.text == "先看人员和硬件"
    assert session.view().scaffold.assets[0].content == _RAW


def _fail_saves(monkeypatch):
    def fail(target, room):
        raise OSError("disk full")

    import scaffolding.store as store
    monkeypatch.setattr(store, "save_classroom", fail)


def test_restore_does_not_ask_the_decision_agent():
    catalog = TaskCatalog()
    task = catalog.create((TrueFalseQuestion("判断说法", "正确", "题目里有依据"),))
    catalog.publish(task.task_id)
    work = catalog.start(task.task_id)
    scaffold = Scaffold(text="先看人员和硬件", assets=(Asset(AssetKind.IMAGE, "figure.png", _RAW),))

    session = Session.restore(catalog, work, _RaisingDecision(), ScriptedScaffoldAgent(), ("保存的预设",), scaffold)

    assert session.view().presets == ("保存的预设",)
    assert session.view().scaffold is not None
    assert session.view().scaffold.assets[0].content == _RAW


def test_a_classroom_without_a_path_stays_in_memory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    page = Classroom(TaskCatalog(), ScriptedDecisionAgent(), ScriptedScaffoldAgent())

    response_for(page, "POST", "/teacher/classes", form(action="创建", name="一班"), 0, teacher_cookie(page))

    assert page.roster.classes()[0].name == "一班"
    assert list(tmp_path.iterdir()) == []


def test_the_saved_classroom_reloads_without_login_or_the_model(tmp_path):
    path = tmp_path / "classroom.json"
    page = _room(path)
    initial = json.loads(path.read_text(encoding="utf-8"))
    assert initial["teacher_password"] == "643590872"
    assert initial["classes"] == []
    headers = teacher_cookie(page)
    response_for(page, "POST", "/teacher/classes", form(action="创建", name="一班"), 0, headers)
    response_for(
        page, "POST", "/teacher/classes/class-1", form(action="导入"), 0, headers,
        uploads={"file": _xlsx((("账号", "密码", "姓名"), ("s1", "secret", "甲")))},
    )
    response_for(
        page, "POST", "/teacher/classes/class-1/students/s1",
        form(action="修改姓名", name="甲一"), 0, headers,
    )
    response_for(
        page, "POST", "/teacher/classes/class-1/students/s1",
        form(action="重置密码", password="fresh-pass"), 0, headers,
    )
    response_for(page, "POST", "/teacher/tasks", "", 0, headers)
    response_for(page, "POST", "/teacher/tasks/task-1", form(**{
        "kind-0": "判断",
        "prompt-0": "判断说法",
        "selected-0": "正确",
        "explanation-0": "题目里有依据",
        "action": "save",
    }), 0, headers)
    response_for(page, "POST", "/teacher/tasks/task-1", form(action="publish"), 0, headers)
    response_for(page, "POST", "/teacher/tasks/task-1", form(action="布置", class_id="class-1"), 0, headers)
    response_for(page, "POST", "/teacher/tasks", "", 0, headers)
    response_for(page, "POST", "/teacher/tasks/task-2", form(**{
        "kind-0": "综合",
        "prompt-0": "还没保存的题干",
        "requirements-0": "写出组成",
        "action": "edit",
    }), 0, headers)
    page.knowledge.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "课时原文"))
    page.knowledge.add_standard(CurriculumStandard("普通高中信息科技课程标准", "高中", "1.1.2", "课标全文"))
    page.objectives.extract_lesson("人教版", "必修一", "信息系统的组成")
    page.generation._origins["task-1"] = LessonOrigin("人教版", "必修一", "信息系统的组成")
    student = response_for(page, "POST", "/student/login", form(account="s1", password="fresh-pass"), 0)
    student_header = _cookie(student)
    response_for(page, "GET", "/student/tasks/task-1", "", 0, student_header)
    response_for(page, "POST", "/student/tasks/task-1/answers", form(**{"selected-0": "正确"}), 0, student_header)
    response_for(
        page, "POST", "/student/tasks/task-1/ask",
        form(question="先看题目", source="预设提问"), 0, student_header,
    )

    saved_text = path.read_text(encoding="utf-8")
    saved = json.loads(saved_text)
    assert set(_KEYS) <= set(saved)
    assert base64.b64encode(_RAW).decode("ascii") in saved_text
    assert _RAW not in path.read_bytes()
    decision = ScriptedDecisionAgent(presets=("不该出现",))
    scaffold = ScriptedScaffoldAgent(draft=ScaffoldDraft(text="不该生成"))
    second = _room(path, decision, scaffold)

    assert second.teacher_tokens == set()
    assert second.student_tokens == {}
    assert [item.name for item in second.roster.classes()] == ["一班"]
    assert second.roster.authenticate_student("s1", "secret") is None
    student_record = second.roster.authenticate_student("s1", "fresh-pass")
    assert student_record is not None
    assert student_record.name == "甲一"
    assert second.catalog.get("task-1").published is True
    assert second.catalog.get("task-1").questions[0].prompt == "判断说法"
    assert second.teacher.drafts["task-2"][0].prompt == "还没保存的题干"
    assert second.classwork.assigned("task-1") == ("class-1",)
    assert second.knowledge.get_lesson("人教版", "必修一", "信息系统的组成").text == "课时原文"
    assert second.knowledge.get_standard("高中").name == "普通高中信息科技课程标准"
    found = second.objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")
    assert found[0].statement == "能分辨系统和要素"
    assert second.generation.origin("task-1") == LessonOrigin("人教版", "必修一", "信息系统的组成")
    work = second.classwork._works[("s1", "task-1")]
    assert work.answers[0].selected == ("正确",)
    assert work.dialogue[0].scaffold.assets[0].content == _RAW
    assert "<h1>登录</h1>" in text(response_for(second, "GET", "/teacher", "", 0, headers))
    assert "<h1>登录</h1>" in text(response_for(second, "GET", "/student", "", 0, student_header))
    rejected = response_for(second, "POST", "/student/login", form(account="s1", password="secret"), 0)
    assert "账号或密码不正确" in text(rejected)
    logged = response_for(second, "POST", "/student/login", form(account="s1", password="fresh-pass"), 0)
    opened = text(response_for(second, "GET", "/student/tasks/task-1", "", 0, _cookie(logged)))
    asset = response_for(second, "GET", "/student/tasks/task-1/assets/figure.png", "", 0, _cookie(logged))

    assert "作品还缺哪一部分？" in opened
    assert "不该出现" not in opened
    assert "不该生成" not in opened
    assert "先看人员和硬件" in opened
    assert decision.choose_calls == []
    assert scaffold.calls == []
    assert asset.status == 200
    assert asset.body == _RAW


def test_one_students_login_keeps_the_other_restored_session(tmp_path):
    path = _two_scaffolded_students(tmp_path)
    decision = _CountingDecision()
    second = _room(path, decision)

    response_for(second, "POST", "/student/login", form(account="s1", password="secret"), 0)
    logged = response_for(second, "POST", "/student/login", form(account="s2", password="secret"), 0)
    response_for(second, "GET", "/student/tasks/task-1", "", 0, _cookie(logged))

    _assert_restored(second, "s2", decision)


def test_a_teacher_save_keeps_both_students_for_session_restore(tmp_path):
    path = _two_scaffolded_students(tmp_path)
    decision = _CountingDecision()
    second = _room(path, decision)
    headers = teacher_cookie(second)
    response_for(second, "POST", "/teacher/classes", form(action="创建", name="二班"), 0, headers)

    for account in ("s1", "s2"):
        logged = response_for(second, "POST", "/student/login", form(account=account, password="secret"), 0)
        response_for(second, "GET", "/student/tasks/task-1", "", 0, _cookie(logged))
        _assert_restored(second, account, decision)


def test_removed_students_and_deleted_classes_stay_gone(tmp_path):
    path = tmp_path / "classroom.json"
    page = _room(path)
    headers = teacher_cookie(page)
    response_for(page, "POST", "/teacher/classes", form(action="创建", name="一班"), 0, headers)
    response_for(
        page, "POST", "/teacher/classes/class-1", form(action="导入"), 0, headers,
        uploads={"file": _xlsx((("账号", "密码", "姓名"), ("s1", "secret", "甲"), ("s2", "secret", "乙")))},
    )
    response_for(page, "POST", "/teacher/classes/class-1/students/s1", form(action="移除"), 0, headers)
    response_for(page, "POST", "/teacher/classes", form(action="创建", name="二班"), 0, headers)
    response_for(page, "POST", "/teacher/classes/class-2", form(action="删除班级"), 0, headers)

    second = _room(path)

    assert [item.name for item in second.roster.classes()] == ["一班"]
    assert [item.account for item in second.roster.students("class-1")] == ["s2"]
    assert second.roster.authenticate_student("s1", "secret") is None


def test_a_failed_write_keeps_the_previous_classroom(tmp_path, monkeypatch):
    path = tmp_path / "classroom.json"
    page = _room(path)
    headers = teacher_cookie(page)
    response_for(page, "POST", "/teacher/classes", form(action="创建", name="一班"), 0, headers)

    def fail(target, room):
        raise OSError("disk full")

    import scaffolding.store as store
    monkeypatch.setattr(store, "save_classroom", fail)
    failed = response_for(page, "POST", "/teacher/classes", form(action="创建", name="二班"), 0, headers)

    assert "没有写入文件" in text(failed)
    assert [item.name for item in page.roster.classes()] == ["一班"]
    saved = json.loads(path.read_text(encoding="utf-8"))
    blob = json.dumps(saved, ensure_ascii=False)
    assert "一班" in blob
    assert "二班" not in blob
    assert {item.name for item in path.parent.iterdir()} == {"classroom.json"}


def test_a_failed_student_answer_redraws_from_the_restored_room(tmp_path, monkeypatch):
    page, path, student_header = _assigned_student(tmp_path)
    response_for(page, "GET", "/student/tasks/task-1", "", 0, student_header)
    _fail_saves(monkeypatch)

    failed = response_for(
        page, "POST", "/student/tasks/task-1/answers",
        form(**{"selected-0": "正确"}), 0, student_header,
    )
    body = text(failed)
    second = _room(path)

    assert "没有写入文件" in body
    assert 'value="正确" checked' not in body
    assert second.classwork._works[("s1", "task-1")].answers[0].selected == ()


def test_a_failed_student_help_redraws_from_the_restored_room(tmp_path, monkeypatch):
    page, path, student_header = _assigned_student(tmp_path)
    response_for(page, "GET", "/student/tasks/task-1", "", 0, student_header)
    _fail_saves(monkeypatch)

    failed = response_for(
        page, "POST", "/student/tasks/task-1/ask",
        form(question="先看题目", source="预设提问"), 0, student_header,
    )
    body = text(failed)
    second = _room(path)

    assert "没有写入文件" in body
    assert "先看人员和硬件" not in body
    assert second.classwork._works[("s1", "task-1")].dialogue == ()


def test_a_failed_student_submit_redraws_from_the_restored_room(tmp_path, monkeypatch):
    page, path, student_header = _assigned_student(tmp_path)
    response_for(page, "GET", "/student/tasks/task-1", "", 0, student_header)
    _fail_saves(monkeypatch)

    failed = response_for(page, "POST", "/student/tasks/task-1/submit", "", 0, student_header)
    body = text(failed)
    second = _room(path)

    assert "没有写入文件" in body
    assert "已完成" not in body
    assert "参考答案" not in body
    assert second.classwork._works[("s1", "task-1")].submitted is False


def test_a_failed_student_open_redraws_from_the_restored_room(tmp_path, monkeypatch):
    page, path, student_header = _assigned_student(tmp_path)
    _fail_saves(monkeypatch)

    failed = response_for(page, "GET", "/student/tasks/task-1", "", 0, student_header)
    body = text(failed)
    second = _room(path)

    assert "没有写入文件" in body
    assert "判断说法" not in body
    assert ("s1", "task-1") not in second.classwork._works


def test_a_failed_student_save_keeps_the_request_time_for_dwell(tmp_path, monkeypatch):
    page, path, student_header = _assigned_student(tmp_path)
    response_for(page, "GET", "/student/tasks/task-1", "", 0, student_header)

    import scaffolding.store as store
    original = store.save_classroom
    failed_once = {"done": False}

    def fail_once(target, room):
        if not failed_once["done"]:
            failed_once["done"] = True
            raise OSError("disk full")
        return original(target, room)

    monkeypatch.setattr(store, "save_classroom", fail_once)

    failed = response_for(
        page, "POST", "/student/tasks/task-1/answers",
        form(**{"selected-0": "正确"}), 50, student_header,
    )
    body = text(failed)

    assert "没有写入文件" in body
    assert 'value="正确" checked' not in body
    assert page.classwork._works[("s1", "task-1")].answers[0].selected == ()

    response_for(
        page, "POST", "/student/tasks/task-1/answers",
        form(**{"selected-0": "正确"}), 55, student_header,
    )

    dwell = page.classwork._works[("s1", "task-1")].behavior.dwell_seconds
    assert dwell == 5
    saved = json.loads(path.read_text(encoding="utf-8"))
    work = next(item for item in saved["works"] if item["account"] == "s1")
    assert work["behavior"]["dwell_seconds"] == 5


def test_a_failed_replace_leaves_the_previous_file(tmp_path, monkeypatch):
    path = tmp_path / "classroom.json"
    page = _room(path)
    headers = teacher_cookie(page)
    response_for(page, "POST", "/teacher/classes", form(action="创建", name="一班"), 0, headers)

    def fail(source, target):
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", fail)
    failed = response_for(page, "POST", "/teacher/classes", form(action="创建", name="二班"), 0, headers)

    assert "没有写入文件" in text(failed)
    assert [item.name for item in page.roster.classes()] == ["一班"]
    saved = json.loads(path.read_text(encoding="utf-8"))
    blob = json.dumps(saved, ensure_ascii=False)
    assert "一班" in blob
    assert "二班" not in blob
    assert {item.name for item in tmp_path.iterdir()} == {"classroom.json"}


def test_production_classroom_writes_the_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def post(*_args, **_kwargs):
        raise AssertionError("network")

    production_classroom(post=post)

    saved = json.loads((tmp_path / "classroom.json").read_text(encoding="utf-8"))
    assert saved["teacher_password"] == "643590872"
    assert saved["classes"] == []
