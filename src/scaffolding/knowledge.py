from dataclasses import dataclass


def _filled(value: str) -> bool:
    return value.strip() != ""


@dataclass(frozen=True)
class LessonSource:
    version: str
    volume: str
    lesson: str
    stage: str
    pages: str


@dataclass(frozen=True)
class StandardSource:
    name: str
    stage: str
    clauses: str
    current: bool = True


@dataclass(frozen=True)
class TextbookLesson:
    version: str
    volume: str
    lesson: str
    stage: str
    pages: str
    text: str

    def __post_init__(self) -> None:
        if not all(_filled(value) for value in (self.version, self.volume, self.lesson, self.stage, self.pages, self.text)):
            raise ValueError("lesson fields must be filled")

    def source(self) -> LessonSource:
        return LessonSource(self.version, self.volume, self.lesson, self.stage, self.pages)


@dataclass(frozen=True)
class CurriculumStandard:
    name: str
    stage: str
    clauses: str
    text: str

    def __post_init__(self) -> None:
        if not all(_filled(value) for value in (self.name, self.stage, self.clauses, self.text)):
            raise ValueError("standard fields must be filled")

    def source(self) -> StandardSource:
        return StandardSource(self.name, self.stage, self.clauses, current=True)


class Rejected(Exception):
    pass


class KnowledgeBase:
    def __init__(self) -> None:
        self._lessons: dict[tuple[str, str, str], TextbookLesson] = {}
        self._standards: dict[str, CurriculumStandard] = {}

    def add_lesson(self, lesson: TextbookLesson) -> None:
        key = (lesson.version, lesson.volume, lesson.lesson)
        if key in self._lessons:
            raise Rejected("this lesson is already stored")
        self._lessons[key] = lesson

    def add_standard(self, standard: CurriculumStandard) -> None:
        if standard.stage in self._standards:
            raise Rejected("this stage already has a current standard")
        self._standards[standard.stage] = standard

    def get_lesson(self, version: str, volume: str, lesson: str) -> TextbookLesson:
        return self._lessons[(version, volume, lesson)]

    def get_standard(self, stage: str) -> CurriculumStandard:
        return self._standards[stage]

    def lesson_count(self) -> int:
        return len(self._lessons)

    def standard_count(self) -> int:
        return len(self._standards)
