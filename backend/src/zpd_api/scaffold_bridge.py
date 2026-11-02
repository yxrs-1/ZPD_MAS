import asyncio

from scaffolding.records import OpenQuestion, SCAFFOLD_TYPE_VALUES, ScaffoldType
from scaffolding.scaffold_decision import PreviousScaffold, decide_scaffold_type


def choose_scaffold_type(record, question: str) -> str:
    return _decision(record, question).scaffold_type.value


def _decision(record, question: str):
    return asyncio.run(
        decide_scaffold_type(
            _state(record, question),
            _answer(record),
            _previous(record),
        )
    )


def _state(record, question: str) -> str:
    helps = "；".join(item.text for item in record.behavior.helps)
    return "\n".join(
        (
            "本次求助：" + question,
            "停留秒数：" + str(record.behavior.dwell_seconds),
            "此前求助：" + helps,
        )
    )


def _answer(record) -> str:
    rows = []
    for index, (question, answer) in enumerate(zip(record.questions, record.answers), start=1):
        prompt = question.prompt
        if isinstance(question, OpenQuestion):
            wrote = answer.text
        else:
            wrote = "、".join(answer.selected)
        rows.append(str(index) + " " + prompt + " 作答：" + wrote)
    return "\n".join(rows)


def _previous(record) -> list[PreviousScaffold]:
    found = []
    for turn in record.dialogue:
        scaffold_type = getattr(turn, "scaffold_type", "")
        content = _scaffold_text(turn)
        if scaffold_type not in SCAFFOLD_TYPE_VALUES or content == "":
            continue
        found.append(PreviousScaffold(scaffold_type=ScaffoldType(scaffold_type), content=content))
    return found


def _scaffold_text(turn) -> str:
    scaffold = turn.scaffold
    if scaffold is None:
        return ""
    return scaffold.text.strip()


class RecordedScaffoldDecision:
    def __init__(self, presets) -> None:
        self._presets = presets

    def suggest(self, record):
        return self._presets.suggest(record)

    def choose_type(self, record, question: str) -> str:
        decision = _decision(record, question)
        self.last_reason = decision.reason
        return decision.scaffold_type.value


class PassageScaffoldAgent:
    def __init__(self, agent, retrieve) -> None:
        self._agent = agent
        self._retrieve = retrieve

    def produce(self, scaffold_type: str, question: str, questions: tuple, answers: tuple, example_source: str = ""):
        passages = tuple(self._retrieve(scaffold_type + "\n" + question))
        return self._agent.produce(
            scaffold_type,
            question,
            questions,
            answers,
            passages=passages,
            example_source=example_source,
        )
