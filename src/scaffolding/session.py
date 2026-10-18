from dataclasses import dataclass

from scaffolding.agents import DecisionAgent, ScaffoldAgent
from scaffolding.records import Asset, TaskRecord


@dataclass(frozen=True)
class Scaffold:
    text: str = ""
    assets: tuple[Asset, ...] = ()


@dataclass(frozen=True)
class PageView:
    presets: tuple[str, ...]
    scaffold: Scaffold | None


class Session:
    def __init__(self, record: TaskRecord, decision: DecisionAgent, scaffold_agent: ScaffoldAgent) -> None:
        self.record = record
        self._decision = decision
        self._scaffold_agent = scaffold_agent
        self._presets = tuple(decision.suggest(record))
        self._scaffold: Scaffold | None = None

    def view(self) -> PageView:
        return PageView(self._presets, self._scaffold)
