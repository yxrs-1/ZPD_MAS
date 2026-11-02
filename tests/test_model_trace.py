import asyncio
import json

import pytest

from scaffolding.documents import StoredDocument, draft_objectives, format_objectives
from scaffolding.generation import QuestionCounts
from scaffolding.knowledge import LessonSource
from scaffolding.model_decision import ModelDecisionAgent
from scaffolding.model_extractor import ModelObjectiveExtractor
from scaffolding.model_generator import ModelQuestionGenerator, deepseek_complete
from scaffolding.model_scaffold import ModelScaffoldAgent
from scaffolding.model_text import ModelTextGenerator
from scaffolding.model_trace import install_trace_sender
from scaffolding.objectives import Objective
from scaffolding.records import Behavior, ItemAnswer, TaskRecord, TrueFalseQuestion
from scaffolding.scaffold_decision import decide_scaffold_type
from tests.objective_helpers import sample_base


class RecordingPost:
    def __init__(self, content: str) -> None:
        self.content = content

    def __call__(self, url, headers, payload):
        return 200, {"choices": [{"message": {"content": self.content}}]}


@pytest.fixture
def traces():
    found = []
    install_trace_sender(found.append)
    try:
        yield found
    finally:
        install_trace_sender(None)


def _objective() -> Objective:
    source = LessonSource("人教版", "必修一", "信息系统的组成", "高中", "12")
    return Objective("objective-1", "信息意识", "能识别组成", source)


def _question_reply() -> str:
    return json.dumps(
        {
            "单选": [
                {
                    "题目": "单选乙",
                    "选项": ["甲", "乙", "丙", "丁"],
                    "参考答案": ["乙"],
                    "解析": "原因",
                }
            ],
            "多选": [],
            "判断": [],
            "综合": [],
        },
        ensure_ascii=False,
    )


def _record() -> TaskRecord:
    return TaskRecord(
        (TrueFalseQuestion("判断说法", "正确", "题目里有依据"),),
        (ItemAnswer(selected=("正确",)),),
        Behavior(dwell_seconds=1.0, helps=()),
    )


def test_question_generation_records_the_objective_and_the_question(traces):
    generator = ModelQuestionGenerator(lambda _messages: _question_reply())

    generator.generate(QuestionCounts(1, 0, 0, 0), (_objective(),))

    assert len(traces) == 1
    assert traces[0]["name"] == "生成题目"
    assert traces[0]["metadata"]["生成目标"] == "维度：信息意识\n表述：能识别组成"
    assert traces[0]["metadata"]["生成题目"] == "单选：单选乙"
    assert traces[0]["output"] == _question_reply()


def test_a_rejected_question_reply_still_records_the_objective(traces):
    from scaffolding.generation import Rejected

    generator = ModelQuestionGenerator(lambda _messages: "不是题目")

    with pytest.raises(Rejected):
        generator.generate(QuestionCounts(1, 0, 0, 0), (_objective(),))

    assert len(traces) == 1
    assert traces[0]["metadata"]["生成目标"] == "维度：信息意识\n表述：能识别组成"
    assert "生成题目" not in traces[0]["metadata"]
    assert traces[0]["output"] == "不是题目"


def test_scaffold_generation_records_the_type_and_the_body(traces):
    reply = json.dumps({"文字": "先看人员和硬件", "源码": ""}, ensure_ascii=False)
    questions = (TrueFalseQuestion("判断说法", "正确", "题目里有依据"),)
    answers = (ItemAnswer(selected=("正确",)),)

    ModelScaffoldAgent(lambda _messages: reply).produce("提示", "还缺什么？", questions, answers)

    assert len(traces) == 1
    assert traces[0]["metadata"]["支架类型"] == "提示"
    assert traces[0]["metadata"]["支架正文"] == "先看人员和硬件"
    assert traces[0]["output"] == reply


def test_a_rewritten_scaffold_records_the_final_wording(traces):
    first = json.dumps({"文字": "引导学生看空序列。", "源码": ""}, ensure_ascii=False)
    second = json.dumps({"文字": "你看空序列。", "源码": ""}, ensure_ascii=False)
    replies = [first, second]
    questions = (TrueFalseQuestion("判断说法", "正确", "题目里有依据"),)
    answers = (ItemAnswer(selected=("正确",)),)

    draft = ModelScaffoldAgent(lambda _messages: replies.pop(0)).produce(
        "反馈",
        "还缺什么？",
        questions,
        answers,
    )

    assert draft.text == "你看空序列。"
    assert len(traces) == 1
    assert traces[0]["metadata"]["支架类型"] == "反馈"
    assert traces[0]["metadata"]["支架正文"] == "你看空序列。"
    assert traces[0]["output"] == first


def test_a_failed_rewrite_keeps_the_first_record(traces):
    first = json.dumps({"文字": "引导学生看空序列。", "源码": ""}, ensure_ascii=False)
    replies = [first, RuntimeError("down")]
    questions = (TrueFalseQuestion("判断说法", "正确", "题目里有依据"),)
    answers = (ItemAnswer(selected=("正确",)),)

    def complete(_messages):
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    with pytest.raises(RuntimeError):
        ModelScaffoldAgent(complete).produce("反馈", "还缺什么？", questions, answers)

    assert len(traces) == 1
    assert traces[0]["output"] == first
    assert "支架正文" not in traces[0]["metadata"]


def test_choosing_a_scaffold_type_records_that_type(traces):
    reply = json.dumps({"类型": "指导"}, ensure_ascii=False)

    assert ModelDecisionAgent(lambda _messages: reply).choose_type(_record(), "还缺什么？") == "指导"

    assert traces[0]["name"] == "支架类型"
    assert traces[0]["metadata"]["支架类型"] == "指导"
    assert "支架正文" not in traces[0]["metadata"]


def test_preset_suggestions_are_recorded_too(traces):
    reply = json.dumps({"预设提问": ["先看题目"]}, ensure_ascii=False)

    assert ModelDecisionAgent(lambda _messages: reply).suggest(_record()) == ("先看题目",)

    assert len(traces) == 1
    assert traces[0]["name"] == "预设提问"
    assert traces[0]["metadata"] == {}


def test_text_generation_records_objectives_and_questions(traces):
    reply = json.dumps(
        {
            "读法": "未指定",
            "目标": [{"维度": "信息意识", "表述": "能识别信息"}],
            "题目": {
                "单选": [{"题目": "哪一项是信息"}],
                "多选": [],
                "判断": [],
                "综合": [],
            },
        },
        ensure_ascii=False,
    )

    assert ModelTextGenerator(lambda _messages: reply).generate("出一道题") == reply

    assert traces[0]["metadata"]["生成目标"] == "维度：信息意识\n表述：能识别信息"
    assert traces[0]["metadata"]["生成题目"] == "单选：哪一项是信息"


def test_objective_extraction_records_the_generated_objectives(traces):
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    reply = json.dumps(
        {"目标": [{"维度": "信息意识", "表述": "能识别信息", "来源": "教材"}]},
        ensure_ascii=False,
    )

    ModelObjectiveExtractor(lambda _messages: reply).extract(retrieval)

    assert traces[0]["metadata"]["生成目标"] == "维度：信息意识\n表述：能识别信息"


def test_drafting_objectives_records_both_calls_and_the_objectives(traces):
    replies = [
        json.dumps({"检索": "信息"}, ensure_ascii=False),
        json.dumps({"目标": [{"维度": "信息意识", "表述": "能识别信息"}]}, ensure_ascii=False),
    ]

    def complete(_messages):
        return replies.pop(0)

    drafted = draft_objectives(complete, (StoredDocument("doc-1", "a.docx", ("信息与数据",)),), "识别信息")

    assert [item["name"] for item in traces] == ["模型调用", "生成目标"]
    assert traces[1]["metadata"]["生成目标"] == format_objectives(drafted)


def test_the_api_scaffold_decision_records_the_chosen_type(traces):
    from types import SimpleNamespace

    content = json.dumps({"scaffold_type": "示范", "reason": "需要一个同类例子"}, ensure_ascii=False)

    class Completions:
        async def create(self, **_kwargs):
            message = SimpleNamespace(content=content)
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))

    decision = asyncio.run(decide_scaffold_type("首次求助", "我选了 A", [], client=client))

    assert decision.scaffold_type.value == "示范"
    assert traces[0]["metadata"]["支架类型"] == "示范"
    assert traces[0]["output"] == content


def test_each_completion_is_recorded_when_langfuse_is_configured(traces):
    messages = ({"role": "user", "content": "出题"},)

    assert deepseek_complete(messages, post=RecordingPost("第一份"), api_key="secret") == "第一份"
    assert deepseek_complete(messages, post=RecordingPost("第二份"), api_key="secret") == "第二份"

    assert [item["output"] for item in traces] == ["第一份", "第二份"]
    assert traces[0]["name"] == "模型调用"
    assert traces[0]["model"] == "deepseek-flash"
    assert traces[0]["input"] == [{"role": "user", "content": "出题"}]


def test_a_completion_inside_question_generation_is_recorded_once(traces):
    generator = ModelQuestionGenerator(
        lambda messages: deepseek_complete(messages, post=RecordingPost(_question_reply()), api_key="secret")
    )

    generator.generate(QuestionCounts(1, 0, 0, 0), (_objective(),))

    assert len(traces) == 1
    assert traces[0]["name"] == "生成题目"
    assert traces[0]["metadata"]["生成题目"] == "单选：单选乙"


def test_missing_langfuse_keys_do_not_send(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    sent = []
    monkeypatch.setattr("scaffolding.model_trace._langfuse_sender", lambda payload: sent.append(payload))
    install_trace_sender(None)

    assert deepseek_complete(({"role": "user", "content": "出题"},), post=RecordingPost("正文"), api_key="secret") == "正文"

    assert sent == []


def test_a_langfuse_send_failure_still_returns_the_model_text(traces):
    def fail(_payload):
        raise RuntimeError("langfuse down")

    install_trace_sender(fail)
    try:
        assert deepseek_complete(
            ({"role": "user", "content": "出题"},),
            post=RecordingPost("正文"),
            api_key="secret",
        ) == "正文"
    finally:
        install_trace_sender(traces.append)
