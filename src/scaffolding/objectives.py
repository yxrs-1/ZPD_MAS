from collections.abc import Sequence
from dataclasses import dataclass

from scaffolding.knowledge import LessonRetrieval, LessonSource, StageRetrieval, StandardSource


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
