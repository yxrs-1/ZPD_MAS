from scaffolding.generation import Rejected


TEXT_SYSTEM = (
    "你是高中信息科技教师。只回一份 JSON 对象，不要代码块，不要其他文字。\n"
    "JSON 有且只有三个键：读法、目标、题目。\n"
    "读法有且只有单选、多选、判断、综合。"
    "教师文字里同时写明了某一种和数量时，该值是大于或等于 0 的整数。"
    "没有写明的类，值是「未指定」。"
    "数量说不清，或出现这四种以外的题型时，不要返回这份成功对象。\n"
    "目标是数组，至少一条。每条有且只有维度和表述。"
    "维度是信息意识、计算思维、数字化学习与创新、信息社会责任之一。"
    "表述不能为空白。\n"
    "题目有且只有单选、多选、判断、综合，每个值都是数组。\n"
    "单选和多选的每一项都有且只有题目、选项、参考答案、解析。"
    "选项至少两个，互不相同，且都不能为空白。选项和参考答案是字符串数组。"
    "单选的参考答案只有一项。多选的参考答案至少一项，且每一项都在选项里、互不相同。"
    "题目和解析都不能为空白。\n"
    "判断的每一项都有且只有题目、参考答案、解析。参考答案是「正确」或「错误」。题目和解析都不能为空白。\n"
    "综合的每一项都有且只有题目、作答要求、参考答案、解析。题目和作答要求都不能为空白。参考答案和解析可以空着。\n"
    "空白不算已填写。四类合起来至少一道。"
)


def build_text_messages(text: str) -> tuple[dict[str, str], dict[str, str]]:
    return (
        {"role": "system", "content": TEXT_SYSTEM},
        {"role": "user", "content": text},
    )


class ModelTextGenerator:
    def __init__(self, complete) -> None:
        self._complete = complete

    def generate(self, text: str) -> str:
        reply = self._complete(build_text_messages(text))
        if not isinstance(reply, str):
            raise Rejected("model reply is not the text task JSON")
        return reply
