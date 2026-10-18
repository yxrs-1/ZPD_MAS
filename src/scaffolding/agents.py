from dataclasses import dataclass
from typing import Protocol

from scaffolding.records import AnswerState, Asset, TaskRecord, TaskStatement


@dataclass(frozen=True)
class ScaffoldDraft:
    text: str = ""
    html: str = ""
    assets: tuple[Asset, ...] = ()


class DecisionAgent(Protocol):
    def suggest(self, record: TaskRecord) -> tuple[str, ...]:
        ...

    def choose_type(self, record: TaskRecord, question: str) -> str:
        ...


class ScaffoldAgent(Protocol):
    def produce(
        self,
        scaffold_type: str,
        question: str,
        statement: TaskStatement,
        answer: AnswerState,
    ) -> ScaffoldDraft:
        ...
