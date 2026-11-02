import pytest

from scaffolding.figures import FigureRejected, render_svg


OUTLINE = "带宽与延迟\n  带宽\n    单位时间的数据量\n  延迟\n"
STRUCTURE = "节点：带宽\n节点：延迟\n节点：实际网速\n箭头：带宽 -> 实际网速：共同决定\n"
ANIMATION = STRUCTURE + "帧：带宽\n帧：实际网速\n"


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


def test_an_animation_moves_the_highlight_between_frames():
    svg = render_svg("微格动画", ANIMATION).decode()

    assert "<animate" in svg
    assert "带宽" in svg
    assert "实际网速" in svg


def test_empty_or_marked_up_sources_are_rejected():
    with pytest.raises(FigureRejected):
        render_svg("思维导图", "   \n")
    with pytest.raises(FigureRejected):
        render_svg("结构图", "箭头：带宽 -> 延迟：影响\n")
    with pytest.raises(FigureRejected):
        render_svg("微格动画", STRUCTURE)
    with pytest.raises(FigureRejected):
        render_svg("思维导图", "根\n  <script>alert(1)</script>\n")
