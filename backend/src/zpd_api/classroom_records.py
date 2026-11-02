from sqlalchemy import delete, inspect, text
from sqlalchemy.orm import Session

from scaffolding.store import _apply, _live_sessions, classroom_state
from zpd_api.db import sync_database_url
from zpd_api.models import (
    AnswerRow,
    AssignmentRow,
    Base,
    ClassroomProfile,
    DraftRow,
    GenerationOriginRow,
    HelpRow,
    LibraryDocumentRow,
    ScaffoldTurnRow,
    SchoolClass,
    StudentAccount,
    StudentWorkRow,
    TaskRow,
)


_TABLES = (
    AnswerRow,
    HelpRow,
    ScaffoldTurnRow,
    StudentWorkRow,
    DraftRow,
    AssignmentRow,
    GenerationOriginRow,
    LibraryDocumentRow,
    TaskRow,
    StudentAccount,
    SchoolClass,
    ClassroomProfile,
)


class PostgresRecords:
    def __init__(self, engine) -> None:
        self.engine = engine

    def open(self, room) -> None:
        Base.metadata.create_all(self.engine)
        _ensure_turn_columns(self.engine)
        _ensure_task_title(self.engine)
        with Session(self.engine) as session:
            exists = session.get(ClassroomProfile, 1) is not None
        if exists:
            self.load(room)
        else:
            self.save(room)

    def save(self, room) -> None:
        data = classroom_state(room)
        with Session(self.engine) as session:
            for model in _TABLES:
                session.execute(delete(model))
            session.add(ClassroomProfile(
                id=1,
                teacher_account=room.roster.teacher_account,
                teacher_password=data["teacher_password"],
                next_class=data["next_class"],
                next_task=data["next_task"],
                next_document=data["next_document"],
            ))
            for position, item in enumerate(data["classes"]):
                session.add(SchoolClass(position=position, class_id=item["class_id"], name=item["name"]))
            for position, item in enumerate(data["students"]):
                session.add(StudentAccount(
                    position=position,
                    account=item["account"],
                    password=item["password"],
                    name=item["name"],
                    class_id=item["class_id"],
                ))
            for position, item in enumerate(data["tasks"]):
                session.add(TaskRow(
                    position=position,
                    task_id=item["task_id"],
                    published=item["published"],
                    started=item["started"],
                    submitted=item["submitted"],
                    title=item.get("title", ""),
                    questions=item["questions"],
                ))
            for task_position, (task_id, items) in enumerate(data["drafts"].items()):
                for position, item in enumerate(items):
                    session.add(DraftRow(
                        task_position=task_position,
                        task_id=task_id,
                        position=position,
                        kind=item["kind"],
                        prompt=item["prompt"],
                        options=item["options"],
                        requirements=item["requirements"],
                        selected=item["selected"],
                        answer=item["answer"],
                        explanation=item["explanation"],
                    ))
            for task_position, (task_id, class_ids) in enumerate(data["assignments"].items()):
                for position, class_id in enumerate(class_ids):
                    session.add(AssignmentRow(
                        task_position=task_position,
                        task_id=task_id,
                        position=position,
                        class_id=class_id,
                    ))
            for position, item in enumerate(data["works"]):
                session.add(StudentWorkRow(
                    position=position,
                    account=item["account"],
                    task_id=item["task_id"],
                    submitted=item["submitted"],
                    questions=item["questions"],
                    presets=item["presets"],
                    scaffold=item["scaffold"],
                    dwell_seconds=item["behavior"]["dwell_seconds"],
                ))
                for answer_position, answer in enumerate(item["answers"]):
                    session.add(AnswerRow(
                        work_position=position,
                        position=answer_position,
                        text=answer["text"],
                        selected=answer["selected"],
                        text_revisions=answer["text_revisions"],
                        selected_revisions=answer["selected_revisions"],
                    ))
                for help_position, event in enumerate(item["behavior"]["helps"]):
                    session.add(HelpRow(
                        work_position=position,
                        position=help_position,
                        text=event["text"],
                        source=event["source"],
                    ))
                for turn_position, turn in enumerate(item["dialogue"]):
                    session.add(ScaffoldTurnRow(
                        work_position=position,
                        position=turn_position,
                        question=turn["question"],
                        source=turn["source"],
                        scaffold=turn["scaffold"],
                        scaffold_type=turn.get("scaffold_type", ""),
                        reason=turn.get("reason", ""),
                    ))
            for position, (task_id, item) in enumerate(data["origins"].items()):
                session.add(GenerationOriginRow(
                    position=position,
                    task_id=task_id,
                    kind=item["kind"],
                    version=item.get("version", ""),
                    volume=item.get("volume", ""),
                    lesson=item.get("lesson", ""),
                    stage=item.get("stage", ""),
                ))
            for position, item in enumerate(data["documents"]):
                session.add(LibraryDocumentRow(
                    position=position,
                    doc_id=item["doc_id"],
                    name=item["name"],
                    chunks=item["chunks"],
                ))
            session.commit()
        room.saved_sessions = _live_sessions(room)

    def load(self, room) -> None:
        with Session(self.engine) as session:
            profile = session.get(ClassroomProfile, 1)
            classes = session.query(SchoolClass).order_by(SchoolClass.position).all()
            students = session.query(StudentAccount).order_by(StudentAccount.position).all()
            tasks = session.query(TaskRow).order_by(TaskRow.position).all()
            drafts = session.query(DraftRow).order_by(DraftRow.task_position, DraftRow.position).all()
            assignments = session.query(AssignmentRow).order_by(AssignmentRow.task_position, AssignmentRow.position).all()
            works = session.query(StudentWorkRow).order_by(StudentWorkRow.position).all()
            answers = session.query(AnswerRow).order_by(AnswerRow.work_position, AnswerRow.position).all()
            helps = session.query(HelpRow).order_by(HelpRow.work_position, HelpRow.position).all()
            turns = session.query(ScaffoldTurnRow).order_by(ScaffoldTurnRow.work_position, ScaffoldTurnRow.position).all()
            origins = session.query(GenerationOriginRow).order_by(GenerationOriginRow.position).all()
            documents = session.query(LibraryDocumentRow).order_by(LibraryDocumentRow.position).all()
        grouped_drafts = {}
        for item in drafts:
            grouped_drafts.setdefault(item.task_id, []).append({
                "kind": item.kind,
                "prompt": item.prompt,
                "options": item.options,
                "requirements": item.requirements,
                "selected": item.selected,
                "answer": item.answer,
                "explanation": item.explanation,
            })
        grouped_assignments = {}
        for item in assignments:
            grouped_assignments.setdefault(item.task_id, []).append(item.class_id)
        answers_by_work = {}
        for item in answers:
            answers_by_work.setdefault(item.work_position, []).append({
                "text": item.text,
                "selected": item.selected,
                "text_revisions": item.text_revisions,
                "selected_revisions": item.selected_revisions,
            })
        helps_by_work = {}
        for item in helps:
            helps_by_work.setdefault(item.work_position, []).append({"text": item.text, "source": item.source})
        turns_by_work = {}
        for item in turns:
            turns_by_work.setdefault(item.work_position, []).append({
                "question": item.question,
                "source": item.source,
                "scaffold": item.scaffold,
                "scaffold_type": item.scaffold_type,
                "reason": item.reason,
            })
        _apply(room, {
            "teacher_password": profile.teacher_password,
            "next_class": profile.next_class,
            "classes": [{"class_id": item.class_id, "name": item.name} for item in classes],
            "students": [
                {"account": item.account, "password": item.password, "name": item.name, "class_id": item.class_id}
                for item in students
            ],
            "next_task": profile.next_task,
            "tasks": [
                {
                    "task_id": item.task_id,
                    "published": item.published,
                    "started": item.started,
                    "submitted": item.submitted,
                    "title": item.title,
                    "questions": item.questions,
                }
                for item in tasks
            ],
            "drafts": grouped_drafts,
            "assignments": grouped_assignments,
            "works": [
                {
                    "account": item.account,
                    "task_id": item.task_id,
                    "submitted": item.submitted,
                    "questions": item.questions,
                    "answers": answers_by_work.get(item.position, []),
                    "behavior": {
                        "dwell_seconds": item.dwell_seconds,
                        "helps": helps_by_work.get(item.position, []),
                    },
                    "dialogue": turns_by_work.get(item.position, []),
                    "presets": item.presets,
                    "scaffold": item.scaffold,
                }
                for item in works
            ],
            "lessons": [],
            "standards": [],
            "objectives": {"lessons": [], "stages": [], "next_id": 1},
            "origins": {_origin_key(item): _origin_value(item) for item in origins},
            "next_document": profile.next_document,
            "documents": [
                {"doc_id": item.doc_id, "name": item.name, "chunks": item.chunks}
                for item in documents
            ],
        })
        room.roster.teacher_account = profile.teacher_account


def _origin_key(item) -> str:
    return item.task_id


def _origin_value(item) -> dict:
    if item.kind == "lesson":
        return {"kind": "lesson", "version": item.version, "volume": item.volume, "lesson": item.lesson}
    return {"kind": "stage", "stage": item.stage}


def postgres_records() -> PostgresRecords:
    from sqlalchemy import create_engine

    return PostgresRecords(create_engine(sync_database_url()))


def _ensure_task_title(engine) -> None:
    with engine.begin() as connection:
        schema = connection.get_execution_options().get("schema_translate_map", {}).get(None)
        existing = {column["name"] for column in inspect(connection).get_columns("tasks", schema=schema)}
        if "title" in existing:
            return
        prefix = "" if schema in (None, "public") else schema + "."
        connection.execute(text(
            "ALTER TABLE " + prefix + "tasks ADD COLUMN IF NOT EXISTS title TEXT NOT NULL DEFAULT ''"
        ))


def _ensure_turn_columns(engine) -> None:
    with engine.begin() as connection:
        schema = connection.get_execution_options().get("schema_translate_map", {}).get(None)
        existing = {column["name"] for column in inspect(connection).get_columns("scaffold_turns", schema=schema)}
        prefix = "" if schema in (None, "public") else schema + "."
        for name in ("scaffold_type", "reason"):
            if name not in existing:
                connection.execute(text(
                    "ALTER TABLE " + prefix + "scaffold_turns ADD COLUMN " + name + " TEXT NOT NULL DEFAULT ''"
                ))
