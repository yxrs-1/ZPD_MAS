from collections.abc import Sequence
from dataclasses import dataclass

from scaffolding.knowledge import KnowledgeBase, LessonRetrieval, LessonSource, StageRetrieval, StandardSource


class Rejected(Exception):
    pass


def _filled(value: str) -> bool:
    return value.strip() != ""


_DIMENSIONS = frozenset({
    "信息意识",
    "计算思维",
    "数字化学习与创新",
    "信息社会责任",
})


@dataclass(frozen=True)
class ObjectiveDraft:
    dimension: str
    statement: str
    source: LessonSource | StandardSource


@dataclass(frozen=True)
class Objective:
    objective_id: str
    dimension: str
    statement: str
    source: LessonSource | StandardSource


class ObjectiveCatalog:
    def __init__(self, knowledge: KnowledgeBase, extractor) -> None:
        self._knowledge = knowledge
        self._extractor = extractor
        self._lessons: dict[tuple[str, str, str], tuple[Objective, ...]] = {}
        self._stages: dict[str, tuple[Objective, ...]] = {}
        self._next_id = 1

    def extract_lesson(self, version: str, volume: str, lesson: str) -> tuple[Objective, ...]:
        key = (version, volume, lesson)
        if key in self._lessons:
            raise Rejected("lesson objectives already exist")
        return self._save(self._lessons, key, self._knowledge.retrieve_lesson(version, volume, lesson))

    def extract_stage(self, stage: str) -> tuple[Objective, ...]:
        if stage in self._stages:
            raise Rejected("stage objectives already exist")
        return self._save(self._stages, stage, self._knowledge.retrieve_stage(stage))

    def lesson_objectives(self, version: str, volume: str, lesson: str) -> tuple[Objective, ...]:
        return self._lessons.get((version, volume, lesson), ())

    def stage_objectives(self, stage: str) -> tuple[Objective, ...]:
        return self._stages.get(stage, ())

    def _save(self, store: dict, key: object, retrieval: LessonRetrieval | StageRetrieval | None) -> tuple[Objective, ...]:
        if retrieval is None:
            return ()
        kept = select_objectives(self._extractor.extract(retrieval), retrieval)
        if not kept:
            return ()
        saved = tuple(self._allocate(draft) for draft in kept)
        store[key] = saved
        return saved

    def _allocate(self, draft: ObjectiveDraft) -> Objective:
        objective = Objective(f"objective-{self._next_id}", draft.dimension, draft.statement, draft.source)
        self._next_id += 1
        return objective


def select_objectives(
    drafts: Sequence[ObjectiveDraft],
    retrieval: LessonRetrieval | StageRetrieval,
) -> tuple[ObjectiveDraft, ...]:
    if isinstance(retrieval, LessonRetrieval):
        allowed = (retrieval.lesson_source, retrieval.standard_source)
    else:
        allowed = (retrieval.standard_source,)
    return tuple(
        draft
        for draft in drafts
        if draft.dimension in _DIMENSIONS and _filled(draft.statement) and draft.source in allowed
    )
