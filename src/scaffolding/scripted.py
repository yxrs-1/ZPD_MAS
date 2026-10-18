from scaffolding.agents import ScaffoldDraft
from scaffolding.records import TaskRecord


class ScriptedDecisionAgent:
    def __init__(
        self,
        presets: tuple[str, ...] = (),
        scaffold_type: str = "提示",
        error: BaseException | None = None,
    ) -> None:
        self.presets = presets
        self.scaffold_type = scaffold_type
        self.error = error
        self.choose_calls: list[tuple[TaskRecord, str]] = []

    def suggest(self, record: TaskRecord) -> tuple[str, ...]:
        return self.presets

    def choose_type(self, record: TaskRecord, question: str) -> str:
        self.choose_calls.append((record, question))
        if self.error is not None:
            raise self.error
        return self.scaffold_type


class ScriptedScaffoldAgent:
    def __init__(self, draft: ScaffoldDraft | None = None, error: BaseException | None = None) -> None:
        self.draft = draft if draft is not None else ScaffoldDraft()
        self.error = error
        self.calls: list[dict[str, object]] = []

    def produce(self, scaffold_type: str, question: str, questions: tuple, answers: tuple) -> ScaffoldDraft:
        self.calls.append(
            {
                "scaffold_type": scaffold_type,
                "question": question,
                "questions": questions,
                "answers": answers,
            }
        )
        if self.error is not None:
            raise self.error
        return self.draft
