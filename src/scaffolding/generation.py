from collections.abc import Sequence
from dataclasses import dataclass

from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion

Question = ChoiceQuestion | TrueFalseQuestion | OpenQuestion


@dataclass(frozen=True)
class QuestionCounts:
    single: int
    multiple: int
    true_false: int
    open_ended: int


def arrange_questions(questions: Sequence[object], counts: QuestionCounts) -> tuple[Question, ...] | None:
    singles: list[ChoiceQuestion] = []
    multiples: list[ChoiceQuestion] = []
    judged: list[TrueFalseQuestion] = []
    opened: list[OpenQuestion] = []
    for question in questions:
        if isinstance(question, ChoiceQuestion) and question.selection == SelectionMode.SINGLE:
            singles.append(question)
        elif isinstance(question, ChoiceQuestion) and question.selection == SelectionMode.MULTIPLE:
            multiples.append(question)
        elif isinstance(question, TrueFalseQuestion):
            judged.append(question)
        elif isinstance(question, OpenQuestion):
            opened.append(question)
        else:
            return None
    if (
        len(singles) != counts.single
        or len(multiples) != counts.multiple
        or len(judged) != counts.true_false
        or len(opened) != counts.open_ended
    ):
        return None
    return tuple(singles + multiples + judged + opened)
