from dataclasses import dataclass, replace

from scaffolding.agents import DecisionAgent, ScaffoldAgent, ScaffoldDraft
from scaffolding.html_assets import assets_from_html, safe_filename
from scaffolding.model_scaffold import begin_scaffold_progress, end_scaffold_progress
from scaffolding.figures import FigureRejected, render_svg
from scaffolding.scaffold_figures import figure_asset, kind_for
from scaffolding.records import (
    ASSET_KIND_VALUES,
    SCAFFOLD_TYPE_VALUES,
    Asset,
    HelpEvent,
    HelpSource,
    OpenQuestion,
    TaskRecord,
    TrueFalseQuestion,
)
from scaffolding.tasks import Rejected, StudentWork, TaskCatalog


@dataclass(frozen=True)
class Scaffold:
    text: str = ""
    assets: tuple[Asset, ...] = ()

    def is_empty(self) -> bool:
        return self.text.strip() == "" and len(self.assets) == 0


@dataclass(frozen=True)
class DialogueTurn:
    question: str
    source: HelpSource
    scaffold: Scaffold | None
    scaffold_type: str = ""
    reason: str = ""


@dataclass(frozen=True)
class Revealed:
    answer: str | tuple[str, ...]
    explanation: str


@dataclass(frozen=True)
class PageView:
    presets: tuple[str, ...]
    scaffold: Scaffold | None
    dialogue: tuple[DialogueTurn, ...] = ()
    answers_locked: bool = False
    send_closed: bool = False
    revealed: tuple = ()
    status: str = "待办"


class Session:
    def __init__(
        self,
        catalog: TaskCatalog,
        work: StudentWork,
        decision: DecisionAgent,
        scaffold_agent: ScaffoldAgent,
    ) -> None:
        self._catalog = catalog
        self.work = work
        self._decision = decision
        self._scaffold_agent = scaffold_agent
        self._presets = tuple(decision.suggest(self.record))
        self._scaffold: Scaffold | None = None
        self.examples: dict = {}

    @classmethod
    def restore(
        cls,
        catalog: TaskCatalog,
        work: StudentWork,
        decision: DecisionAgent,
        scaffold_agent: ScaffoldAgent,
        presets,
        scaffold: Scaffold | None,
    ):
        session = cls.__new__(cls)
        session._catalog = catalog
        session.work = work
        session._decision = decision
        session._scaffold_agent = scaffold_agent
        session._presets = tuple(presets)
        session._scaffold = scaffold
        session.examples = {}
        return session

    @property
    def record(self) -> TaskRecord:
        return TaskRecord(
            self.work.questions,
            self.work.answers,
            self.work.behavior,
            dialogue=self.work.dialogue,
        )

    def view(self) -> PageView:
        submitted = self.work.submitted
        return PageView(
            self._presets[:2],
            self._scaffold,
            dialogue=self.work.dialogue,
            answers_locked=submitted,
            send_closed=submitted,
            revealed=tuple(_revealed(question) for question in self.work.questions) if submitted else (),
            status="已完成" if submitted else "待办",
        )

    def edit_answer(
        self,
        index: int,
        *,
        text: str | None = None,
        selected: tuple[str, ...] | None = None,
    ) -> PageView:
        if self.work.submitted:
            raise Rejected("already submitted")
        self.work.edit(index, text=text, selected=selected)
        self._presets = tuple(self._decision.suggest(self.record))
        return self.view()

    def note_dwell(self, seconds: float) -> None:
        self.work.behavior = replace(self.work.behavior, dwell_seconds=seconds)

    def ask(self, question: str, source: HelpSource, *, on_text=None, on_kind=None) -> PageView:
        if self.work.submitted:
            raise Rejected("already submitted")
        if question.strip() == "":
            return self.view()
        self.work.behavior = replace(
            self.work.behavior,
            helps=self.work.behavior.helps + (HelpEvent(text=question, source=source),),
        )
        try:
            scaffold_type = self._decision.choose_type(self.record, question)
        except Exception:
            return self._keep_existing_scaffold(question, source)
        if scaffold_type not in SCAFFOLD_TYPE_VALUES:
            return self._keep_existing_scaffold(question, source)
        kind = kind_for(scaffold_type)
        example_source = ""
        if kind is not None and kind in self.examples:
            example_source = self.examples[kind][0]
            if kind == "微格动画":
                try:
                    render_svg(kind, example_source)
                except FigureRejected:
                    example_source = ""
        token = None
        if on_text is not None or on_kind is not None:
            token = begin_scaffold_progress(on_text)
            if on_kind is not None:
                on_kind("" if kind is None else kind)
        try:
            draft = self._scaffold_agent.produce(
                scaffold_type,
                question,
                self.work.questions,
                self.work.answers,
                example_source=example_source,
            )
        except Exception:
            return self._keep_existing_scaffold(question, source)
        finally:
            if token is not None:
                end_scaffold_progress(token)
        scaffold = _visible_scaffold(draft)
        if kind is not None:
            asset = figure_asset(kind, getattr(draft, "source", ""), self.examples)
            if asset is not None:
                scaffold = Scaffold(text=scaffold.text, assets=scaffold.assets + (asset,))
        if scaffold.is_empty():
            return self._keep_existing_scaffold(question, source)
        self._scaffold = scaffold
        reason = getattr(self._decision, "last_reason", "")
        self.work.dialogue = self.work.dialogue + (
            DialogueTurn(question, source, scaffold, scaffold_type, reason),
        )
        return self.view()

    def submit(self) -> PageView:
        if self.work.submitted:
            raise Rejected("already submitted")
        self._catalog.mark_submitted(self.work.task_id)
        self.work.submitted = True
        self._presets = ()
        return self.view()

    def _keep_existing_scaffold(self, question: str, source: HelpSource) -> PageView:
        self.work.dialogue = self.work.dialogue + (DialogueTurn(question, source, None),)
        return self.view()


def _revealed(question) -> Revealed:
    if isinstance(question, OpenQuestion):
        return Revealed(question.answer, question.explanation)
    if isinstance(question, TrueFalseQuestion):
        return Revealed(question.answer, question.explanation)
    return Revealed(question.answer, question.explanation)


def _visible_scaffold(draft: ScaffoldDraft) -> Scaffold:
    direct = tuple(
        asset
        for asset in draft.assets
        if asset.kind.value in ASSET_KIND_VALUES
        and safe_filename(asset.filename)
        and asset.content.strip() != b""
    )
    return Scaffold(text=draft.text, assets=direct + assets_from_html(draft.html))
