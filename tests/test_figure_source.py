import pytest

from scaffolding.figures import FigureRejected, render_svg


OUTLINE = "带宽与延迟\n  带宽\n    单位时间的数据量\n  延迟\n"
STRUCTURE = "节点：带宽\n节点：延迟\n节点：实际网速\n箭头：带宽 -> 实际网速：共同决定\n"
LOOP = """节点：判断条件
节点：执行循环体
节点：退出
箭头：判断条件 -> 执行循环体：条件为真
箭头：执行循环体 -> 判断条件：回到判断
箭头：判断条件 -> 退出：条件为假
拍：判断条件：1.5：先看判断条件
拍：判断条件 -> 执行循环体：1.5：条件为真就进入
拍：执行循环体：2：执行循环体
拍：执行循环体 -> 判断条件：2：执行完回到判断
拍：判断条件：1.5：再判断一次
拍：判断条件 -> 退出：1.5：条件为假就退出
"""

CHAIN = """节点：带宽
节点：延迟
箭头：带宽 -> 延迟：不同
拍：带宽：5：先看带宽
拍：带宽 -> 延迟：5：再看延迟
"""


def test_an_outline_becomes_an_svg_mind_map():
    svg = render_svg("思维导图", OUTLINE).decode()

    assert svg.startswith("<svg")
    assert "带宽与延迟" in svg
    assert "单位时间的数据量" in svg
    assert "<script" not in svg


def test_a_structure_becomes_an_svg_with_the_arrow_label():
    svg = render_svg("结构图", STRUCTURE).decode()

    assert "实际网速" in svg
    assert "共同决定" in svg


def _series(svg: str, attribute: str) -> tuple[list[str], list[str]]:
    needle = 'attributeName="' + attribute + '"'
    start = svg.index(needle)
    tag_start = svg.rindex("<", 0, start)
    tag = svg[tag_start:svg.index(">", start)]

    def values_of(name: str) -> list[str]:
        marker = name + '="'
        at = tag.index(marker) + len(marker)
        return tag[at:tag.index('"', at)].split(";")

    return values_of("keyTimes"), values_of("values")


def test_a_loop_follows_the_return_arc():
    svg = render_svg("微格动画", LOOP).decode()

    assert 'width="440"' in svg and 'height="314"' in svg
    assert "translate(110,136)" in svg
    assert "translate(330,136)" in svg
    assert "translate(330,236)" in svg
    assert 'd="M 330,136 Q 220,64 110,136"' in svg
    xs, x_values = _series(svg, "cx")
    ys, y_values = _series(svg, "cy")
    assert x_values[xs.index("0.6")] == "220"
    assert y_values[ys.index("0.6")] == "100"
    assert svg.count('dur="10s"') >= 1
    assert 'repeatCount="indefinite"' in svg
    assert "0.92" in svg
    assert svg.count('attributeName="opacity"') == 6
    assert svg.count('y="290"') == 6
    for caption in ("先看判断条件", "条件为真就进入", "执行循环体", "执行完回到判断", "再判断一次", "条件为假就退出"):
        assert caption in svg
    assert svg.rindex("</g>") < svg.index("<circle")
    assert "<script" not in svg


def test_a_chain_moves_along_a_straight_line():
    svg = render_svg("微格动画", CHAIN).decode()

    assert 'width="410"' in svg and 'height="142"' in svg
    assert "<line " in svg and " Q " not in svg
    xs, x_values = _series(svg, "cx")
    ys, y_values = _series(svg, "cy")
    assert x_values[xs.index("0.75")] == "205"
    assert y_values[ys.index("0.75")] == "64"
    assert svg.count('attributeName="opacity"') == 2
    assert svg.count('y="118"') == 2


def test_a_hold_stays_on_its_node_after_a_move():
    source = (
        "节点：带宽\n节点：延迟\n箭头：带宽 -> 延迟：不同\n"
        "拍：带宽 -> 延迟：5：先走过去\n拍：带宽：5：回到起点\n"
    )
    svg = render_svg("微格动画", source).decode()
    xs, x_values = _series(svg, "cx")
    ys, y_values = _series(svg, "cy")
    assert x_values[xs.index("0.501")] == "110"
    assert y_values[ys.index("0.501")] == "64"
    assert x_values[xs.index("1")] == "110"
    assert y_values[ys.index("1")] == "64"


def test_a_node_may_contain_the_voice_words():
    source = "节点：学生\n节点：作业\n箭头：学生 -> 作业：完成\n拍：学生：5：先看这里\n拍：学生 -> 作业：5：再看那里\n"
    svg = render_svg("微格动画", source).decode()

    assert "学生" in svg
    assert "<script" not in svg


@pytest.mark.parametrize("source", [
    "\n",
    "节点：带宽\n节点：延迟\n箭头：带宽 -> 延迟：不同\n帧：带宽\n",
    "节点：带宽\n节点：延迟\n箭头：带宽 -> 延迟：不同\n",
    "节点：带宽\n节点：延迟\n箭头：带宽 -> 延迟：不同\n拍：带宽：10：只停一下\n",
    "节点：带宽\n节点：延迟\n箭头：带宽 -> 延迟：不同\n拍：带宽：4：先看带宽\n拍：带宽 -> 延迟：4：再看延迟\n",
    "节点：带宽\n节点：延迟\n箭头：带宽 -> 延迟：不同\n拍：带宽：0.4：先看带宽\n拍：带宽 -> 延迟：9.6：再看延迟\n",
    "节点：带宽\n节点：延迟\n箭头：带宽 -> 延迟：不同\n拍：带宽：5：先看带宽\n拍：带宽 -> 延迟：1.50：再看延迟\n",
    "节点：带宽\n节点：延迟\n箭头：带宽 -> 延迟：不同\n拍：带宽 -> 没有：5：走过去\n拍：带宽：5：停一下\n",
    "节点：带宽\n节点：延迟\n箭头：带宽 -> 延迟：不同\n拍：没有：5：停一下\n拍：带宽 -> 延迟：5：走过去\n",
    "节点：带宽\n节点：延迟\n箭头：带宽 -> 延迟：不同\n拍：带宽：5：\n拍：带宽 -> 延迟：5：再看延迟\n",
    "节点：带宽\n节点：延迟\n箭头：带宽 -> 延迟：不同\n拍：带宽：5：一二三四五六七八九十一二三四五六七八九十一\n拍：带宽 -> 延迟：5：再看延迟\n",
    "节点：带宽\n节点：延迟\n箭头：带宽 -> 延迟：不同\n拍：带宽：5：引导学生\n拍：带宽 -> 延迟：5：再看延迟\n",
    "节点：带宽\n节点：延迟\n箭头：带宽 -> 延迟：不同\n拍：带宽：5：带宽->延迟\n拍：带宽 -> 延迟：5：再看延迟\n",
    "节点：带宽\n节点：延迟\n箭头：带宽 -> 延迟：不同\n拍：带宽：١：先看带宽\n拍：带宽 -> 延迟：5：再看延迟\n",
    "节点：甲\n节点：乙\n箭头：甲 -> 乙：去\n箭头：乙 -> 甲：回\n拍：甲：5：停在甲\n拍：甲 -> 乙：5：走向乙\n",
    "节点：甲\n节点：乙\n箭头：甲 -> 乙：去\n拍：甲：5：停在甲\n拍：乙：5：停在乙\n",
    "节点：甲\n节点：乙\n箭头：甲 -> 乙：去\n箭头：甲 -> 乙：再\n拍：甲：5：停在甲\n拍：甲 -> 乙：5：走向乙\n",
    "节点：甲：乙\n",
    "节点：甲\n箭头：甲 -> 甲：环\n",
    "拍：甲：5：先停\n节点：甲\n节点：乙\n箭头：甲 -> 乙：去\n拍：甲 -> 乙：5：再走\n",
    "节点：甲\n节点：乙\n箭头：甲 -> 乙：去\n拍：甲：5：停在甲\n节点：丙\n拍：甲 -> 乙：5：走向乙\n",
    "节点：<script>alert(1)</script>\n",
])
def test_bad_animation_sources_are_rejected(source: str):
    with pytest.raises(FigureRejected):
        render_svg("微格动画", source)


def test_empty_or_marked_up_sources_are_rejected():
    with pytest.raises(FigureRejected):
        render_svg("思维导图", "   \n")
    with pytest.raises(FigureRejected):
        render_svg("结构图", "箭头：带宽 -> 延迟：影响\n")
    with pytest.raises(FigureRejected):
        render_svg("微格动画", STRUCTURE)
    with pytest.raises(FigureRejected):
        render_svg("思维导图", "根\n  <script>alert(1)</script>\n")
