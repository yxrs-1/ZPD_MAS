import json

from scaffolding.figures import FigureRejected, render_svg
from scaffolding.records import Asset, AssetKind


_KINDS = {
    "提示": "思维导图",
    "指导": "思维导图",
    "解释": "结构图",
    "示范": "微格动画",
}
_PACK = ("思维导图", "结构图", "微格动画")


def kind_for(scaffold_type: str) -> str | None:
    return _KINDS.get(scaffold_type)


def figure_asset(kind: str, source: str, examples: dict) -> Asset | None:
    try:
        if source.strip() == "":
            raise FigureRejected("empty")
        content = render_svg(kind, source)
    except FigureRejected:
        saved = examples.get(kind)
        if saved is None:
            return None
        if kind == "微格动画":
            try:
                content = render_svg(kind, saved[0])
            except FigureRejected:
                return None
        else:
            content = saved[1]
    return Asset(AssetKind(kind), kind + ".svg", content)


def build_examples(text: str) -> dict[str, tuple[str, bytes]]:
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if not isinstance(body, dict):
        return {}
    found: dict[str, tuple[str, bytes]] = {}
    for kind in _PACK:
        source = body.get(kind, "")
        if type(source) is not str or source.strip() == "":
            continue
        try:
            found[kind] = (source, render_svg(kind, source))
        except FigureRejected:
            continue
    return found


def example_messages(questions: tuple) -> tuple[dict[str, str], dict[str, str]]:
    lines = ["为这个任务准备三件示例。只回一份 JSON 对象，不要代码块。"]
    lines.append("顶层只有「思维导图」「结构图」「微格动画」，三个值都是字符串。")
    lines.append("思维导图是缩进大纲，第一行是根，下一层多两个空格。")
    lines.append("结构图每行是「节点：名称」或「箭头：起点 -> 终点：标签」。")
    lines.append("微格动画在结构图之后写拍。至少两拍，秒数相加等于 10。回头边都要走一次。")
    lines.append("不要写 HTML，不要写文件名，不要写参考答案。")
    lines.append("思维导图例如：\n网络\n  带宽\n  延迟")
    lines.append("结构图例如：\n节点：带宽\n节点：延迟\n箭头：带宽 -> 延迟：不同")
    lines.append(
        "微格动画例如：\n"
        "节点：判断条件\n"
        "节点：执行循环体\n"
        "节点：退出\n"
        "箭头：判断条件 -> 执行循环体：条件为真\n"
        "箭头：执行循环体 -> 判断条件：回到判断\n"
        "箭头：判断条件 -> 退出：条件为假\n"
        "拍：判断条件：1.5：先看判断条件\n"
        "拍：判断条件 -> 执行循环体：1.5：条件为真就进入\n"
        "拍：执行循环体：2：执行循环体\n"
        "拍：执行循环体 -> 判断条件：2：执行完回到判断\n"
        "拍：判断条件：1.5：再判断一次\n"
        "拍：判断条件 -> 退出：1.5：条件为假就退出"
    )
    for number, question in enumerate(questions, start=1):
        lines.append("题目" + str(number) + "：" + question.prompt)
    return (
        {"role": "system", "content": "你为高中信息科技课准备支架示例。"},
        {"role": "user", "content": "\n".join(lines)},
    )
