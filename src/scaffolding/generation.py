from collections.abc import Sequence
from dataclasses import dataclass

from scaffolding.objectives import Objective, ObjectiveCatalog
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion
from scaffolding.tasks import Task, TaskCatalog

Question = ChoiceQuestion | TrueFalseQuestion | OpenQuestion


@dataclass(frozen=True)
class QuestionCounts:
    single: int
    multiple: int
    true_false: int
    open_ended: int


def arrange_questions(questions: Sequence[object], counts: QuestionCounts) -> tuple[Question, ...] | None:
    singles: list[ChoiceQuestion] = []
    multiples: list[ChoiceQuestion] = []
    judged: list[TrueFalseQuestion] = []
    opened: list[OpenQuestion] = []
    for question in questions:
        if isinstance(question, ChoiceQuestion) and question.selection == SelectionMode.SINGLE:
            singles.append(question)
        elif isinstance(question, ChoiceQuestion) and question.selection == SelectionMode.MULTIPLE:
            multiples.append(question)
        elif isinstance(question, TrueFalseQuestion):
            judged.append(question)
        elif isinstance(question, OpenQuestion):
            opened.append(question)
        else:
            return None
    if (
        len(singles) != counts.single
        or len(multiples) != counts.multiple
        or len(judged) != counts.true_false
        or len(opened) != counts.open_ended
    ):
        return None
    return tuple(singles + multiples + judged + opened)


@dataclass(frozen=True)
class LessonOrigin:
    version: str
    volume: str
    lesson: str


@dataclass(frozen=True)
class StageOrigin:
    stage: str


class Rejected(Exception):
    pass


def _usable_count(value: object) -> bool:
    return type(value) is int and value >= 0


class TaskGeneration:
    def __init__(self, objectives: ObjectiveCatalog, tasks: TaskCatalog, generator) -> None:
        self._objectives = objectives
        self._tasks = tasks
        self._generator = generator
        self._origins: dict[str, LessonOrigin | StageOrigin] = {}

    def generate_lesson(
        self, version: str, volume: str, lesson: str, *, single: int, multiple: int, true_false: int, open_ended: int
    ) -> Task:
        return self._generate(
            self._objectives.lesson_objectives(version, volume, lesson),
            LessonOrigin(version, volume, lesson),
            single,
            multiple,
            true_false,
            open_ended,
        )

    def generate_stage(self, stage: str, *, single: int, multiple: int, true_false: int, open_ended: int) -> Task:
        return self._generate(
            self._objectives.stage_objectives(stage),
            StageOrigin(stage),
            single,
            multiple,
            true_false,
            open_ended,
        )

    def origin(self, task_id: str) -> LessonOrigin | StageOrigin | None:
        return self._origins.get(task_id)

    def _generate(
        self,
        objectives: tuple[Objective, ...],
        origin: LessonOrigin | StageOrigin,
        single: int,
        multiple: int,
        true_false: int,
        open_ended: int,
    ) -> Task:
        if not all(_usable_count(value) for value in (single, multiple, true_false, open_ended)):
            raise Rejected("counts must be zero or a positive integer")
        if (single, multiple, true_false, open_ended) == (0, 0, 0, 0) or not objectives:
            raise Rejected("there is no objective record to generate from")
        counts = QuestionCounts(single, multiple, true_false, open_ended)
        ordered = arrange_questions(self._generator.generate(counts, objectives), counts)
        if ordered is None:
            raise Rejected("generated questions do not match the requested counts")
        task = self._tasks.create(ordered)
        self._origins[task.task_id] = origin
        return task
