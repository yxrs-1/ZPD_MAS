from pathlib import Path

from scaffolding.agents import ScaffoldDraft
from scaffolding.html_assets import assets_from_html, export_assets, safe_filename
from scaffolding.records import Asset, AssetKind, HelpSource
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.session import Scaffold
from tests.helpers import open_session


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
    session = open_session(
        ScriptedDecisionAgent(presets=("看哪？",), scaffold_type="提示"),
        ScriptedScaffoldAgent(draft),
        prompt="完成作品",
    )

    view = session.ask("看哪？", HelpSource.PRESET)
    paths = export_assets(view.scaffold, tmp_path)

    assert view.scaffold is not None
    assert view.scaffold.text == "提示：看这张图"
    assert sorted(path.name for path in paths) == ["figure.png", "layout.svg"]
    assert (tmp_path / "figure.png").read_bytes() == "img".encode()
    assert sorted(path.name for path in tmp_path.iterdir()) == ["figure.png", "layout.svg"]
    assert "整页".encode() not in b"".join(path.read_bytes() for path in tmp_path.iterdir())


def test_unsafe_export_names_are_not_written(tmp_path: Path):
    scaffold = Scaffold(
        assets=(
            Asset(AssetKind.IMAGE, "nul", b"x"),
            Asset(AssetKind.MIND_MAP, "..", b"y"),
            Asset(AssetKind.STRUCTURE, "foo:bar", b"z"),
        )
    )

    paths = export_assets(scaffold, tmp_path)
    written = {path.name for path in tmp_path.iterdir()}

    assert "nul" not in written
    assert ".." not in written
    assert "foo:bar" not in written
    assert written == set()
    assert paths == ()
    assert all(path.name not in {"nul", "..", "foo:bar"} for path in paths)


def test_windows_device_filenames_are_rejected():
    assert safe_filename("NUL.png") is False
    assert safe_filename("COM1") is False


def test_asset_body_keeps_child_markup():
    html = '<asset kind="思维导图" name="map.svg"><svg><rect/></svg></asset>'

    assets = assets_from_html(html)

    assert assets == (Asset(AssetKind.MIND_MAP, "map.svg", b"<svg><rect/></svg>"),)


def test_nested_asset_tag_stays_in_the_outer_body():
    html = (
        '<asset kind="思维导图" name="map.svg">'
        '<asset kind="图片素材" name="inner.png">inner</asset>'
        "</asset>"
    )

    assets = assets_from_html(html)

    assert assets == (
        Asset(
            AssetKind.MIND_MAP,
            "map.svg",
            '<asset kind="图片素材" name="inner.png">inner</asset>'.encode(),
        ),
    )


def test_whitespace_only_asset_body_is_dropped():
    html = '<asset kind="思维导图" name="map.svg">   </asset>'

    assert assets_from_html(html) == ()


def test_empty_direct_asset_does_not_make_scaffold_visible():
    session = open_session(
        ScriptedDecisionAgent(presets=("看哪？",), scaffold_type="提示"),
        ScriptedScaffoldAgent(
            ScaffoldDraft(
                text="  ",
                assets=(Asset(AssetKind.IMAGE, "blank.png", b"   "),),
                html='<asset kind="思维导图" name="map.svg">\n</asset>',
            )
        ),
        prompt="完成作品",
    )

    view = session.ask("看哪？", HelpSource.PRESET)

    assert view.scaffold is None
    assert view.presets == ("看哪？",)
