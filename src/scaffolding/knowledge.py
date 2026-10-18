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
