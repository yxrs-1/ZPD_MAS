from dataclasses import dataclass
from enum import StrEnum


class ScaffoldType(StrEnum):
    FEEDBACK = "反馈"
    HINT = "提示"
    INSTRUCTION = "指导"
    EXPLANATION = "解释"
    MODELING = "示范"
    QUESTIONING = "提问"


SCAFFOLD_TYPE_VALUES = frozenset(item.value for item in ScaffoldType)


class HelpSource(StrEnum):
    PRESET = "预设提问"
    OWN = "自己写的"


class AssetKind(StrEnum):
    IMAGE = "图片素材"
    MIND_MAP = "思维导图"
    STRUCTURE = "结构图"
    MICRO_ANIMATION = "微格动画"


ASSET_KIND_VALUES = frozenset(item.value for item in AssetKind)


@dataclass(frozen=True)
class TaskStatement:
    prompt: str
    choices: tuple[str, ...] = ()
    requirements: str = ""


@dataclass(frozen=True)
class AnswerState:
    content: str = ""
    revisions: tuple[str, ...] = ()


@dataclass(frozen=True)
class HelpEvent:
    text: str
    source: HelpSource


@dataclass(frozen=True)
class Behavior:
    dwell_seconds: float = 0
    helps: tuple[HelpEvent, ...] = ()


@dataclass(frozen=True)
class TaskRecord:
    statement: TaskStatement
    answer: AnswerState = AnswerState()
    behavior: Behavior = Behavior()


@dataclass(frozen=True)
class Asset:
    kind: AssetKind
    filename: str
    content: bytes


class SelectionMode(StrEnum):
    SINGLE = "单选"
    MULTIPLE = "多选"


def _filled(value: str) -> bool:
    return value.strip() != ""


@dataclass(frozen=True)
class ChoiceQuestion:
    prompt: str
    selection: SelectionMode
    choices: tuple[str, ...]
    answer: tuple[str, ...]
    explanation: str

    def __post_init__(self) -> None:
        distinct = len(set(self.choices)) == len(self.choices)
        filled = all(_filled(choice) for choice in self.choices)
        if not _filled(self.prompt) or not _filled(self.explanation):
            raise ValueError("choice question needs a prompt and explanation")
        if len(self.choices) < 2 or not distinct or not filled:
            raise ValueError("choice question needs two distinct choices")
        if self.selection == SelectionMode.SINGLE and len(self.answer) != 1:
            raise ValueError("single choice answer must be one choice")
        if self.selection == SelectionMode.MULTIPLE and len(self.answer) < 1:
            raise ValueError("multiple choice answer must be chosen from the choices")
        if any(item not in self.choices for item in self.answer) or len(set(self.answer)) != len(self.answer):
            raise ValueError("answer must be chosen from the choices")


@dataclass(frozen=True)
class TrueFalseQuestion:
    prompt: str
    answer: str
    explanation: str

    def __post_init__(self) -> None:
        if not _filled(self.prompt) or not _filled(self.explanation) or self.answer not in {"正确", "错误"}:
            raise ValueError("true/false question needs a prompt, 正确 or 错误, and explanation")


@dataclass(frozen=True)
class OpenQuestion:
    prompt: str
    requirements: str
    answer: str = ""
    explanation: str = ""

    def __post_init__(self) -> None:
        if not _filled(self.prompt) or not _filled(self.requirements):
            raise ValueError("open question needs a prompt and requirements")


@dataclass(frozen=True)
class ItemAnswer:
    text: str = ""
    selected: tuple[str, ...] = ()
    text_revisions: tuple[str, ...] = ()
    selected_revisions: tuple[tuple[str, ...], ...] = ()
