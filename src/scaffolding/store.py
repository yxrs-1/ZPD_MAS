import base64
import json
import os
import tempfile

from scaffolding.generation import LessonOrigin, StageOrigin
from scaffolding.knowledge import CurriculumStandard, LessonSource, StandardSource, TextbookLesson
from scaffolding.objectives import Objective
from scaffolding.records import (
    Asset,
    AssetKind,
    Behavior,
    ChoiceQuestion,
    HelpEvent,
    HelpSource,
    ItemAnswer,
    OpenQuestion,
    SelectionMode,
    TrueFalseQuestion,
)
from scaffolding.roster import ClassRecord, StudentRecord
from scaffolding.session import DialogueTurn, Scaffold
from scaffolding.tasks import StudentWork, Task
from scaffolding.teacher_page import DraftQuestion


def save_classroom(path, room) -> None:
    destination = os.fspath(path)
    directory = os.path.dirname(destination) or "."
    temporary = None
    replaced = False
    try:
        descriptor, temporary = tempfile.mkstemp(prefix="classroom-", suffix=".tmp", dir=directory)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(classroom_state(room), handle, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        replaced = True
    finally:
        if temporary is not None and not replaced:
            try:
                os.remove(temporary)
            except OSError:
                pass
    room.saved_sessions = _live_sessions(room)


def load_classroom(path, room) -> None:
    with open(path, encoding="utf-8") as handle:
        _apply(room, json.load(handle))


def classroom_state(room) -> dict:
    return {
        "teacher_password": room.roster.teacher_password,
        "next_class": room.roster._next_class,
        "classes": [
            {"class_id": item.class_id, "name": item.name}
            for item in room.roster.classes()
        ],
        "students": [
            {
                "account": student.account,
                "password": student.password,
                "name": student.name,
                "class_id": student.class_id,
            }
            for item in room.roster.classes()
            for student in room.roster.students(item.class_id)
        ],
        "next_task": room.catalog._next_id,
        "tasks": [_task_data(task) for task in room.catalog._tasks.values()],
        "drafts": {
            task_id: [_draft_data(item) for item in draft]
            for task_id, draft in room.teacher.drafts.items()
        },
        "assignments": {
            task_id: list(class_ids)
            for task_id, class_ids in room.classwork._assigned.items()
        },
        "works": [
            _work_data(room, account, task_id, work)
            for (account, task_id), work in room.classwork._works.items()
        ],
        "lessons": [_lesson_data(lesson) for lesson in room.knowledge._lessons.values()],
        "standards": [_standard_data(standard) for standard in room.knowledge._standards.values()],
        "objectives": _objective_state(room),
        "origins": _origin_state(room),
    }


def _apply(room, data: dict) -> None:
    _apply_roster(room, data)
    _apply_tasks(room, data)
    room.teacher.drafts.clear()
    for task_id, items in data["drafts"].items():
        room.teacher.drafts[task_id] = tuple(_draft(item) for item in items)
    _apply_classwork(room, data)
    _apply_knowledge(room, data)
    _apply_objectives(room, data)
    _apply_origins(room, data)
    room.student_pages.clear()
    room.student.sessions.clear()
    room.student.shown_at.clear()


def _apply_roster(room, data: dict) -> None:
    roster = room.roster
    roster.teacher_password = data["teacher_password"]
    roster._classes = {}
    roster._order = []
    roster._students = {}
    roster._members = {}
    for item in data["classes"]:
        record = ClassRecord(item["class_id"], item["name"])
        roster._classes[record.class_id] = record
        roster._order.append(record.class_id)
        roster._members[record.class_id] = []
    for item in data["students"]:
        student = StudentRecord(item["account"], item["password"], item["name"], item["class_id"])
        roster._students[student.account] = student
        roster._members[student.class_id].append(student.account)
    roster._next_class = data.get("next_class", _next_number("class-", roster._order))


def _apply_tasks(room, data: dict) -> None:
    catalog = room.catalog
    catalog._tasks = {}
    catalog._works = {}
    for item in data["tasks"]:
        catalog._tasks[item["task_id"]] = Task(
            item["task_id"],
            tuple(_question(question) for question in item["questions"]),
            published=item["published"],
            started=item["started"],
            submitted=item["submitted"],
        )
    catalog._next_id = data.get("next_task", _next_number("task-", catalog._tasks))


def _apply_classwork(room, data: dict) -> None:
    classwork = room.classwork
    classwork._catalog = room.catalog
    classwork._assigned = {
        task_id: tuple(class_ids) for task_id, class_ids in data["assignments"].items()
    }
    classwork._works = {}
    saved = {}
    for item in data["works"]:
        work = StudentWork(item["task_id"], tuple(_question(question) for question in item["questions"]))
        work.submitted = item["submitted"]
        work.answers = tuple(_answer(answer) for answer in item["answers"])
        work.behavior = _behavior(item["behavior"])
        work.dialogue = tuple(_turn(turn) for turn in item["dialogue"])
        classwork._works[(item["account"], item["task_id"])] = work
        if item["presets"] is not None:
            saved.setdefault(item["account"], {})[item["task_id"]] = {
                "presets": tuple(item["presets"]),
                "scaffold": _scaffold(item["scaffold"]),
            }
    room.saved_sessions = saved


def _apply_knowledge(room, data: dict) -> None:
    lessons = {}
    for item in data["lessons"]:
        lesson = TextbookLesson(
            item["version"], item["volume"], item["lesson"], item["stage"], item["pages"], item["text"]
        )
        lessons[(lesson.version, lesson.volume, lesson.lesson)] = lesson
    standards = {}
    for item in data["standards"]:
        standard = CurriculumStandard(item["name"], item["stage"], item["clauses"], item["text"])
        standards[standard.stage] = standard
    room.knowledge._lessons = lessons
    room.knowledge._standards = standards


def _apply_objectives(room, data: dict) -> None:
    catalog = room.objectives
    catalog._lessons = {}
    for group in data["objectives"]["lessons"]:
        key = (group["version"], group["volume"], group["lesson"])
        catalog._lessons[key] = tuple(_objective(item) for item in group["items"])
    catalog._stages = {}
    for group in data["objectives"]["stages"]:
        catalog._stages[group["stage"]] = tuple(_objective(item) for item in group["items"])
    catalog._next_id = data["objectives"].get("next_id", _next_objective(data["objectives"]))


def _apply_origins(room, data: dict) -> None:
    if room.generation is None:
        return
    room.generation._origins.clear()
    for task_id, item in data["origins"].items():
        room.generation._origins[task_id] = _origin(item)


def _live_sessions(room) -> dict:
    saved = {}
    for account, page in room.student_pages.items():
        tasks = {}
        for task_id, session in page.sessions.items():
            tasks[task_id] = {"presets": tuple(session._presets), "scaffold": session._scaffold}
        if tasks:
            saved[account] = tasks
    return saved


def _objective_state(room) -> dict:
    return {
        "lessons": [
            {
                "version": key[0],
                "volume": key[1],
                "lesson": key[2],
                "items": [_objective_data(item) for item in objectives],
            }
            for key, objectives in room.objectives._lessons.items()
        ],
        "stages": [
            {
                "stage": stage,
                "items": [_objective_data(item) for item in objectives],
            }
            for stage, objectives in room.objectives._stages.items()
        ],
        "next_id": room.objectives._next_id,
    }


def _origin_state(room) -> dict:
    if room.generation is None:
        return {}
    return {task_id: _origin_data(origin) for task_id, origin in room.generation._origins.items()}


def _task_data(task: Task) -> dict:
    return {
        "task_id": task.task_id,
        "published": task.published,
        "started": task.started,
        "submitted": task.submitted,
        "questions": [_question_data(question) for question in task.questions],
    }


def _work_data(room, account: str, task_id: str, work: StudentWork) -> dict:
    session = _session_for(room, account, task_id)
    return {
        "account": account,
        "task_id": task_id,
        "submitted": work.submitted,
        "questions": [_question_data(question) for question in work.questions],
        "answers": [_answer_data(answer) for answer in work.answers],
        "behavior": _behavior_data(work.behavior),
        "dialogue": [_turn_data(turn) for turn in work.dialogue],
        "presets": None if session is None else list(session._presets),
        "scaffold": None if session is None else _scaffold_data(session._scaffold),
    }


def _session_for(room, account: str, task_id: str):
    page = room.student_pages.get(account)
    if page is None:
        return None
    return page.sessions.get(task_id)


def _question_data(question) -> dict:
    if isinstance(question, ChoiceQuestion):
        return {
            "kind": question.selection.value,
            "prompt": question.prompt,
            "choices": list(question.choices),
            "answer": list(question.answer),
            "explanation": question.explanation,
        }
    if isinstance(question, TrueFalseQuestion):
        return {
            "kind": "判断",
            "prompt": question.prompt,
            "answer": question.answer,
            "explanation": question.explanation,
        }
    if isinstance(question, OpenQuestion):
        return {
            "kind": "综合",
            "prompt": question.prompt,
            "requirements": question.requirements,
            "answer": question.answer,
            "explanation": question.explanation,
        }
    raise TypeError("unknown question")


def _question(data: dict):
    kind = data["kind"]
    if kind == "单选":
        return ChoiceQuestion(
            data["prompt"], SelectionMode.SINGLE, tuple(data["choices"]), tuple(data["answer"]), data["explanation"]
        )
    if kind == "多选":
        return ChoiceQuestion(
            data["prompt"], SelectionMode.MULTIPLE, tuple(data["choices"]), tuple(data["answer"]), data["explanation"]
        )
    if kind == "判断":
        return TrueFalseQuestion(data["prompt"], data["answer"], data["explanation"])
    if kind == "综合":
        return OpenQuestion(data["prompt"], data["requirements"], data["answer"], data["explanation"])
    raise ValueError("unknown question")


def _draft_data(item: DraftQuestion) -> dict:
    return {
        "kind": item.kind,
        "prompt": item.prompt,
        "options": list(item.options),
        "requirements": item.requirements,
        "selected": list(item.selected),
        "answer": item.answer,
        "explanation": item.explanation,
    }


def _draft(data: dict) -> DraftQuestion:
    return DraftQuestion(
        data["kind"],
        data["prompt"],
        tuple(data["options"]),
        data["requirements"],
        tuple(data["selected"]),
        data["answer"],
        data["explanation"],
    )


def _answer_data(answer: ItemAnswer) -> dict:
    return {
        "text": answer.text,
        "selected": list(answer.selected),
        "text_revisions": list(answer.text_revisions),
        "selected_revisions": [list(item) for item in answer.selected_revisions],
    }


def _answer(data: dict) -> ItemAnswer:
    return ItemAnswer(
        data["text"],
        tuple(data["selected"]),
        tuple(data["text_revisions"]),
        tuple(tuple(item) for item in data["selected_revisions"]),
    )


def _behavior_data(behavior: Behavior) -> dict:
    return {
        "dwell_seconds": behavior.dwell_seconds,
        "helps": [{"text": event.text, "source": event.source.value} for event in behavior.helps],
    }


def _behavior(data: dict) -> Behavior:
    return Behavior(
        float(data["dwell_seconds"]),
        tuple(HelpEvent(event["text"], HelpSource(event["source"])) for event in data["helps"]),
    )


def _turn_data(turn: DialogueTurn) -> dict:
    return {
        "question": turn.question,
        "source": turn.source.value,
        "scaffold": _scaffold_data(turn.scaffold),
    }


def _turn(data: dict) -> DialogueTurn:
    return DialogueTurn(data["question"], HelpSource(data["source"]), _scaffold(data["scaffold"]))


def _scaffold_data(scaffold: Scaffold | None):
    if scaffold is None:
        return None
    return {"text": scaffold.text, "assets": [_asset_data(asset) for asset in scaffold.assets]}


def _scaffold(data) -> Scaffold | None:
    if data is None:
        return None
    return Scaffold(data["text"], tuple(_asset(asset) for asset in data["assets"]))


def _asset_data(asset: Asset) -> dict:
    return {
        "kind": asset.kind.value,
        "filename": asset.filename,
        "content": base64.b64encode(asset.content).decode("ascii"),
    }


def _asset(data: dict) -> Asset:
    return Asset(AssetKind(data["kind"]), data["filename"], base64.b64decode(data["content"]))


def _lesson_data(lesson: TextbookLesson) -> dict:
    return {
        "version": lesson.version,
        "volume": lesson.volume,
        "lesson": lesson.lesson,
        "stage": lesson.stage,
        "pages": lesson.pages,
        "text": lesson.text,
    }


def _standard_data(standard: CurriculumStandard) -> dict:
    return {
        "name": standard.name,
        "stage": standard.stage,
        "clauses": standard.clauses,
        "text": standard.text,
    }


def _objective_data(objective: Objective) -> dict:
    return {
        "objective_id": objective.objective_id,
        "dimension": objective.dimension,
        "statement": objective.statement,
        "source": _source_data(objective.source),
    }


def _objective(data: dict) -> Objective:
    return Objective(data["objective_id"], data["dimension"], data["statement"], _source(data["source"]))


def _source_data(source) -> dict:
    if isinstance(source, LessonSource):
        return {
            "kind": "lesson",
            "version": source.version,
            "volume": source.volume,
            "lesson": source.lesson,
            "stage": source.stage,
            "pages": source.pages,
        }
    return {
        "kind": "standard",
        "name": source.name,
        "stage": source.stage,
        "clauses": source.clauses,
        "current": source.current,
    }


def _source(data: dict):
    if data["kind"] == "lesson":
        return LessonSource(data["version"], data["volume"], data["lesson"], data["stage"], data["pages"])
    return StandardSource(data["name"], data["stage"], data["clauses"], current=data.get("current", True))


def _origin_data(origin) -> dict:
    if isinstance(origin, LessonOrigin):
        return {"kind": "lesson", "version": origin.version, "volume": origin.volume, "lesson": origin.lesson}
    return {"kind": "stage", "stage": origin.stage}


def _origin(data: dict):
    if data["kind"] == "lesson":
        return LessonOrigin(data["version"], data["volume"], data["lesson"])
    return StageOrigin(data["stage"])


def _next_objective(data: dict) -> int:
    identifiers = []
    for group in data["lessons"] + data["stages"]:
        for item in group["items"]:
            identifiers.append(item["objective_id"])
    return _next_number("objective-", identifiers)


def _next_number(prefix: str, identifiers) -> int:
    highest = 0
    for identifier in identifiers:
        if str(identifier).startswith(prefix):
            tail = str(identifier)[len(prefix):]
            if tail.isdecimal():
                highest = max(highest, int(tail))
    return highest + 1
