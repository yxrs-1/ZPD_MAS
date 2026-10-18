from pathlib import Path

from scaffolding.agents import ScaffoldDraft
from scaffolding.html_assets import assets_from_html, export_assets
from scaffolding.records import Asset, AssetKind, HelpSource, TaskRecord, TaskStatement
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.session import Session


def test_html_keeps_only_the_four_asset_kinds():
    html = """
    <div>不要这段说明</div>
    <asset kind="思维导图" name="map.svg">mind</asset>
    <asset kind="答案" name="secret.txt">no</asset>
    <asset kind="结构图" name="../escape.svg">bad</asset>
    <asset kind="微格动画" name="clip.html">frames</asset>
    """

    assets = assets_from_html(html)

    assert assets == (
        Asset(AssetKind.MIND_MAP, "map.svg", "mind".encode()),
        Asset(AssetKind.MICRO_ANIMATION, "clip.html", "frames".encode()),
    )


def test_export_writes_asset_files_and_not_the_html_page(tmp_path: Path):
    html = '<p>整页</p><asset kind="图片素材" name="figure.png">img</asset>'
    draft = ScaffoldDraft(text="提示：看这张图", html=html, assets=(Asset(AssetKind.STRUCTURE, "layout.svg", b"box"),))
    session = Session(
        TaskRecord(statement=TaskStatement(prompt="完成作品")),
        ScriptedDecisionAgent(presets=("看哪？",), scaffold_type="提示"),
        ScriptedScaffoldAgent(draft),
    )

    view = session.ask("看哪？", HelpSource.PRESET)
    paths = export_assets(view.scaffold, tmp_path)

    assert view.scaffold is not None
    assert view.scaffold.text == "提示：看这张图"
    assert sorted(path.name for path in paths) == ["figure.png", "layout.svg"]
    assert (tmp_path / "figure.png").read_bytes() == "img".encode()
    assert sorted(path.name for path in tmp_path.iterdir()) == ["figure.png", "layout.svg"]
    assert "整页".encode() not in b"".join(path.read_bytes() for path in tmp_path.iterdir())
