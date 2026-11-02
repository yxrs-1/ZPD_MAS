import json
import os
from collections.abc import Sequence

from openai import AsyncOpenAI
from pydantic import BaseModel

from scaffolding.model_trace import remember_model_result, tracing_model_call
from scaffolding.records import ScaffoldType


class PreviousScaffold(BaseModel):
    scaffold_type: ScaffoldType
    content: str


class ScaffoldDecision(BaseModel):
    scaffold_type: ScaffoldType
    reason: str


_SYSTEM = """你是教学支架类型的评估者。请根据学生状态、学生作答和已经给过的支架，自行决定下一次使用哪一种支架，并写出理由。
只返回一个 json 对象，不要写其他文字。
json 有且只有两个字段：scaffold_type、reason。
scaffold_type 只能是这些值之一：反馈、提示、指导、解释、示范、提问。
这些值的含义是：反馈仅评价学生表现，不告诉怎么做；提示给出线索或建议，不提供完整解法；解释说明相关概念；示范给出一个同类例子；提问用一个问题把思考引回去。
reason 只说明为什么选择这个类型。不要写出参考答案，不要替学生完成题目。
格式示例：{"scaffold_type": "提问", "reason": "这里写选择理由"}
"""


def _user_message(
    student_state: str,
    student_answer: str,
    previous_scaffolds: Sequence[PreviousScaffold],
) -> str:
    return json.dumps(
        {
            "student_state": student_state,
            "student_answer": student_answer,
            "previous_scaffolds": [item.model_dump(mode="json") for item in previous_scaffolds],
        },
        ensure_ascii=False,
    )


async def decide_scaffold_type(
    student_state: str,
    student_answer: str,
    previous_scaffolds: Sequence[PreviousScaffold],
    *,
    client: AsyncOpenAI | None = None,
) -> ScaffoldDecision:
    active = client or AsyncOpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
    )
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": _user_message(student_state, student_answer, previous_scaffolds)},
    ]
    completion = await active.chat.completions.create(
        model="deepseek-flash",
        messages=messages,
        response_format={"type": "json_object"},
        extra_body={"thinking": {"type": "disabled"}},
    )
    content = completion.choices[0].message.content
    with tracing_model_call("支架类型") as meta:
        if isinstance(content, str):
            remember_model_result(messages, content)
        decision = ScaffoldDecision.model_validate_json(content)
        meta["支架类型"] = decision.scaffold_type.value
        return decision


