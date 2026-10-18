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
