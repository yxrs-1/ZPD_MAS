import json

import pytest

from scaffolding.generation import Rejected
from scaffolding.model_generator import parse_questions
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion


def _body(**overrides) -> str:
    body = {
        "单选": [
            {"题目": "单选乙", "选项": ["甲", "乙", "丙", "丁"], "参考答案": ["乙"], "解析": "原因乙"},
            {"题目": "单选甲", "选项": ["甲", "乙", "丙", "丁"], "参考答案": ["甲"], "解析": "原因甲"},
        ],
        "多选": [
            {"题目": "多选题", "选项": ["甲", "乙", "丙", "丁"], "参考答案": ["甲", "丙"], "解析": "原因"},
        ],
        "判断": [
            {"题目": "判断题", "参考答案": "错误", "解析": "原因"},
        ],
        "综合": [
            {"题目": "综合题", "作答要求": "写出过程", "参考答案": "", "解析": ""},
        ],
    }
    body.update(overrides)
    return json.dumps(body, ensure_ascii=False)


def test_questions_keep_array_order_and_existing_types():
    questions = parse_questions("\n" + _body() + " ")

    assert questions == (
        ChoiceQuestion("单选乙", SelectionMode.SINGLE, ("甲", "乙", "丙", "丁"), ("乙",), "原因乙"),
        ChoiceQuestion("单选甲", SelectionMode.SINGLE, ("甲", "乙", "丙", "丁"), ("甲",), "原因甲"),
        ChoiceQuestion("多选题", SelectionMode.MULTIPLE, ("甲", "乙", "丙", "丁"), ("甲", "丙"), "原因"),
        TrueFalseQuestion("判断题", "错误", "原因"),
        OpenQuestion("综合题", "写出过程", "", ""),
    )


def test_an_empty_array_contributes_no_questions():
    questions = parse_questions(_body(综合=[]))

    assert [type(question) for question in questions] == [ChoiceQuestion, ChoiceQuestion, ChoiceQuestion, TrueFalseQuestion]


def test_a_code_fence_or_wrong_shape_is_rejected():
    fenced = "```json\n" + _body() + "\n```"
    extra = json.loads(_body())
    extra["其他"] = []
    missing = json.loads(_body())
    del missing["判断"]
    with pytest.raises(Rejected):
        parse_questions(fenced)
    with pytest.raises(Rejected):
        parse_questions(json.dumps(extra, ensure_ascii=False))
    with pytest.raises(Rejected):
        parse_questions(json.dumps(missing, ensure_ascii=False))


def test_choice_options_must_be_exactly_four_distinct_filled_strings():
    three = json.loads(_body())
    three["单选"][0]["选项"] = ["甲", "乙", "丙"]
    five = json.loads(_body())
    five["单选"][0]["选项"] = ["甲", "乙", "丙", "丁", "戊"]
    duplicate = json.loads(_body())
    duplicate["单选"][0]["选项"] = ["甲", "甲", "丙", "丁"]
    blank = json.loads(_body())
    blank["多选"][0]["选项"] = ["甲", " ", "丙", "丁"]
    for body in (three, five, duplicate, blank):
        with pytest.raises(Rejected):
            parse_questions(json.dumps(body, ensure_ascii=False))


def test_wrong_fields_types_or_question_rules_are_rejected():
    extra_field = json.loads(_body())
    extra_field["判断"][0]["多余"] = "不要"
    string_options = json.loads(_body())
    string_options["单选"][0]["选项"] = "甲乙丙丁"
    blank_prompt = json.loads(_body())
    blank_prompt["综合"][0]["题目"] = " "
    bad_answer = json.loads(_body())
    bad_answer["判断"][0]["参考答案"] = "不知道"
    for body in (extra_field, string_options, blank_prompt, bad_answer):
        with pytest.raises(Rejected):
            parse_questions(json.dumps(body, ensure_ascii=False))


def test_existing_choice_questions_still_allow_two_options():
    question = ChoiceQuestion("教师改过", SelectionMode.SINGLE, ("甲", "乙"), ("甲",), "解析")

    assert question.choices == ("甲", "乙")
