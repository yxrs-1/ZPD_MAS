from scaffolding.records import AssetKind
from scaffolding.scaffold_figures import build_examples, figure_asset, kind_for


OUTLINE = "带宽与延迟\n  带宽\n"
STRUCTURE = "节点：带宽\n节点：实际网速\n箭头：带宽 -> 实际网速：共同决定\n"
ANIMATION = STRUCTURE + "帧：带宽\n帧：实际网速\n"
PACK = (
    '{"思维导图": "带宽与延迟\\n  带宽\\n", '
    '"结构图": "节点：带宽\\n节点：实际网速\\n箭头：带宽 -> 实际网速：共同决定\\n", '
    '"微格动画": "节点：带宽\\n节点：实际网速\\n箭头：带宽 -> 实际网速：共同决定\\n帧：带宽\\n帧：实际网速\\n"}'
)


def test_scaffold_types_pick_one_example_kind():
    assert kind_for("提示") == "思维导图"
    assert kind_for("指导") == "思维导图"
    assert kind_for("解释") == "结构图"
    assert kind_for("示范") == "微格动画"
    assert kind_for("反馈") is None
    assert kind_for("提问") is None


def test_a_valid_source_replaces_the_example_drawing():
    examples = build_examples(PACK)
    asset = figure_asset("思维导图", "带宽与延迟\n  延迟\n", examples)

    assert asset is not None
    assert asset.kind == AssetKind.MIND_MAP
    assert asset.filename == "思维导图.svg"
    assert "延迟" in asset.content.decode()
    assert asset.content != examples["思维导图"][1]


def test_a_rejected_source_keeps_the_example_drawing_only():
    examples = build_examples(PACK)
    asset = figure_asset("结构图", "节点：<script>\n", examples)

    assert asset is not None
    assert asset.content == examples["结构图"][1]
    assert "<script" not in asset.content.decode()


def test_without_an_example_a_rejected_source_draws_nothing():
    assert figure_asset("微格动画", "节点：带宽\n", {}) is None


def test_a_bad_piece_is_left_out_of_the_example_pack():
    packed = build_examples(
        '{"思维导图": "根\\n  枝\\n", "结构图": "箭头：甲 -> 乙：关系\\n", "微格动画": "帧：甲\\n"}'
    )

    assert set(packed) == {"思维导图"}
    assert packed["思维导图"][0].startswith("根")
    assert packed["思维导图"][1].startswith(b"<svg")
