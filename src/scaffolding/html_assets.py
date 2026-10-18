from html.parser import HTMLParser
from pathlib import Path
from typing import Protocol

from scaffolding.records import ASSET_KIND_VALUES, Asset, AssetKind


class _AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.assets: list[Asset] = []
        self._kind: AssetKind | None = None
        self._name: str | None = None
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "asset":
            return
        values = {key: value or "" for key, value in attrs}
        kind = values.get("kind", "")
        name = values.get("name", "")
        if kind in ASSET_KIND_VALUES and safe_filename(name):
            self._kind = AssetKind(kind)
            self._name = name
            self._chunks = []
        else:
            self._kind = None
            self._name = None

    def handle_data(self, data: str) -> None:
        if self._kind is not None:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "asset" and self._kind is not None and self._name is not None:
            self.assets.append(Asset(self._kind, self._name, "".join(self._chunks).encode()))
            self._kind = None
            self._name = None
            self._chunks = []


def safe_filename(name: str) -> bool:
    return name != "" and Path(name).name == name and "/" not in name and "\\" not in name


def assets_from_html(html: str) -> tuple[Asset, ...]:
    parser = _AssetParser()
    parser.feed(html)
    parser.close()
    return tuple(parser.assets)


class _Exportable(Protocol):
    assets: tuple[Asset, ...]


def export_assets(scaffold: _Exportable, directory: Path) -> tuple[Path, ...]:
    directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for asset in scaffold.assets:
        if not safe_filename(asset.filename):
            continue
        path = directory / asset.filename
        path.write_bytes(asset.content)
        paths.append(path)
    return tuple(paths)
