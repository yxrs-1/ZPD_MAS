from scaffolding.generation import QuestionCounts, arrange_questions
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion


def _single(prompt: str) -> ChoiceQuestion:
    return ChoiceQuestion(prompt, SelectionMode.SINGLE, ("甲", "乙"), ("甲",), "解析")


def test_questions_are_grouped_and_keep_order_within_each_type():
    later_single = _single("单选乙")
    earlier_single = _single("单选甲")
    multiple = ChoiceQuestion("多选题", SelectionMode.MULTIPLE, ("甲", "乙", "丙"), ("甲", "丙"), "解析")
    judged = TrueFalseQuestion("判断题", "正确", "解析")
    opened = OpenQuestion("综合题", "写出过程")
    counts = QuestionCounts(single=2, multiple=1, true_false=1, open_ended=1)

    arranged = arrange_questions((opened, multiple, later_single, judged, earlier_single), counts)

    assert arranged == (later_single, earlier_single, multiple, judged, opened)


def test_a_zero_count_rejects_a_question_of_that_type():
    counts = QuestionCounts(single=1, multiple=0, true_false=0, open_ended=0)

    assert arrange_questions((_single("单选甲"), OpenQuestion("综合题", "写出过程")), counts) is None


def test_a_non_question_is_rejected():
    counts = QuestionCounts(single=0, multiple=0, true_false=0, open_ended=0)

    assert arrange_questions(("不是题目",), counts) is None
