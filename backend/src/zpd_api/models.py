from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ScaffoldEvent(Base):
    __tablename__ = "scaffold_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[str] = mapped_column(String(64))
    task_id: Mapped[str] = mapped_column(String(64))
    student_state: Mapped[str] = mapped_column(Text)
    student_answer: Mapped[str] = mapped_column(Text)
    scaffold_type: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="queued")
    detail: Mapped[str] = mapped_column(Text, default="")


class ClassroomProfile(Base):
    __tablename__ = "classroom_profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_account: Mapped[str] = mapped_column(Text)
    teacher_password: Mapped[str] = mapped_column(Text)
    next_class: Mapped[int]
    next_task: Mapped[int]
    next_document: Mapped[int]


class SchoolClass(Base):
    __tablename__ = "classes"

    position: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)


class StudentAccount(Base):
    __tablename__ = "students"

    position: Mapped[int] = mapped_column(primary_key=True)
    account: Mapped[str] = mapped_column(Text)
    password: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    class_id: Mapped[str] = mapped_column(Text)


class TaskRow(Base):
    __tablename__ = "tasks"

    position: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(Text)
    published: Mapped[bool]
    started: Mapped[bool]
    submitted: Mapped[bool]
    title: Mapped[str] = mapped_column(Text, default="", server_default="")
    questions: Mapped[list] = mapped_column(JSON)


class DraftRow(Base):
    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_position: Mapped[int]
    task_id: Mapped[str] = mapped_column(Text)
    position: Mapped[int]
    kind: Mapped[str] = mapped_column(Text)
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON)
    requirements: Mapped[str] = mapped_column(Text)
    selected: Mapped[list] = mapped_column(JSON)
    answer: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)


class AssignmentRow(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_position: Mapped[int]
    task_id: Mapped[str] = mapped_column(Text)
    position: Mapped[int]
    class_id: Mapped[str] = mapped_column(Text)


class StudentWorkRow(Base):
    __tablename__ = "student_works"

    position: Mapped[int] = mapped_column(primary_key=True)
    account: Mapped[str] = mapped_column(Text)
    task_id: Mapped[str] = mapped_column(Text)
    submitted: Mapped[bool]
    questions: Mapped[list] = mapped_column(JSON)
    presets: Mapped[list | None] = mapped_column(JSON, nullable=True)
    scaffold: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dwell_seconds: Mapped[float] = mapped_column(Float)


class AnswerRow(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    work_position: Mapped[int]
    position: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    selected: Mapped[list] = mapped_column(JSON)
    text_revisions: Mapped[list] = mapped_column(JSON)
    selected_revisions: Mapped[list] = mapped_column(JSON)


class HelpRow(Base):
    __tablename__ = "helps"

    id: Mapped[int] = mapped_column(primary_key=True)
    work_position: Mapped[int]
    position: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)


class ScaffoldTurnRow(Base):
    __tablename__ = "scaffold_turns"

    id: Mapped[int] = mapped_column(primary_key=True)
    work_position: Mapped[int]
    position: Mapped[int]
    question: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    scaffold: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scaffold_type: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")


class GenerationOriginRow(Base):
    __tablename__ = "generation_origins"

    position: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(Text, default="")
    volume: Mapped[str] = mapped_column(Text, default="")
    lesson: Mapped[str] = mapped_column(Text, default="")
    stage: Mapped[str] = mapped_column(Text, default="")


class ScaffoldExampleRow(Base):
    __tablename__ = "scaffold_examples"

    task_id: Mapped[str] = mapped_column(Text, primary_key=True)
    kind: Mapped[str] = mapped_column(Text, primary_key=True)
    source: Mapped[str] = mapped_column(Text)
    svg: Mapped[str] = mapped_column(Text)


class LibraryDocumentRow(Base):
    __tablename__ = "library_documents"

    position: Mapped[int] = mapped_column(primary_key=True)
    doc_id: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    chunks: Mapped[list] = mapped_column(JSON)
