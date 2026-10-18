from dataclasses import dataclass

from scaffolding.agents import DecisionAgent, ScaffoldAgent, ScaffoldDraft
from scaffolding.html_assets import assets_from_html, safe_filename
from scaffolding.records import (
    ASSET_KIND_VALUES,
    SCAFFOLD_TYPE_VALUES,
    Asset,
    Behavior,
    HelpEvent,
    HelpSource,
    TaskRecord,
)


@dataclass(frozen=True)
class Scaffold:
    text: str = ""
    assets: tuple[Asset, ...] = ()

    def is_empty(self) -> bool:
        return self.text.strip() == "" and len(self.assets) == 0


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

    def ask(self, question: str, source: HelpSource) -> PageView:
        self.record = TaskRecord(
            statement=self.record.statement,
            answer=self.record.answer,
            behavior=Behavior(
                dwell_seconds=self.record.behavior.dwell_seconds,
                helps=self.record.behavior.helps + (HelpEvent(text=question, source=source),),
            ),
        )
        scaffold_type = self._decision.choose_type(self.record, question)
        if scaffold_type not in SCAFFOLD_TYPE_VALUES:
            return self.view()
        draft = self._scaffold_agent.produce(
            scaffold_type,
            question,
            self.record.statement,
            self.record.answer,
        )
        scaffold = _visible_scaffold(draft)
        if scaffold.is_empty():
            return self.view()
        self._scaffold = scaffold
        return self.view()


def _visible_scaffold(draft: ScaffoldDraft) -> Scaffold:
    direct = tuple(
        asset
        for asset in draft.assets
        if asset.kind.value in ASSET_KIND_VALUES and safe_filename(asset.filename)
    )
    return Scaffold(text=draft.text, assets=direct + assets_from_html(draft.html))
