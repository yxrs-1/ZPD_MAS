from html.parser import HTMLParser
from pathlib import Path
from typing import Protocol

from scaffolding.records import ASSET_KIND_VALUES, Asset, AssetKind

_WINDOWS_DEVICE_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)


class _AssetParser(HTMLParser):
    def __init__(self, html: str) -> None:
        super().__init__()
        self._html = html
        self.assets: list[Asset] = []
        self._kind: AssetKind | None = None
        self._name: str | None = None
        self._body_start: int | None = None
        self._depth = 0

    def _index(self) -> int:
        line, column = self.getpos()
        index = 0
        current = 1
        while current < line:
            newline = self._html.find("\n", index)
            if newline < 0:
                return len(self._html)
            index = newline + 1
            current += 1
        return index + column

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "asset":
            return
        if self._depth > 0:
            self._depth += 1
            return
        values = {key: value or "" for key, value in attrs}
        kind = values.get("kind", "")
        name = values.get("name", "")
        if kind in ASSET_KIND_VALUES and safe_filename(name):
            start_tag = self.get_starttag_text() or ""
            self._kind = AssetKind(kind)
            self._name = name
            self._body_start = self._index() + len(start_tag)
            self._depth = 1

    def handle_endtag(self, tag: str) -> None:
        if tag != "asset" or self._depth == 0:
            return
        self._depth -= 1
        if self._depth != 0 or self._kind is None or self._name is None or self._body_start is None:
            return
        body = self._html[self._body_start : self._index()]
        if body.strip():
            self.assets.append(Asset(self._kind, self._name, body.encode()))
        self._kind = None
        self._name = None
        self._body_start = None


def safe_filename(name: str) -> bool:
    if name == "" or name in {".", ".."}:
        return False
    if "/" in name or "\\" in name or ":" in name or "\x00" in name:
        return False
    if name.endswith(" ") or name.endswith("."):
        return False
    if Path(name).name != name:
        return False
    if name.upper() in _WINDOWS_DEVICE_NAMES:
        return False
    if Path(name).stem.upper() in _WINDOWS_DEVICE_NAMES:
        return False
    return True


def assets_from_html(html: str) -> tuple[Asset, ...]:
    parser = _AssetParser(html)
    parser.feed(html)
    parser.close()
    return tuple(parser.assets)


class _Exportable(Protocol):
    assets: tuple[Asset, ...]


def _inside_directory(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return path != directory


def export_assets(scaffold: _Exportable, directory: Path) -> tuple[Path, ...]:
    directory.mkdir(parents=True, exist_ok=True)
    root = directory.resolve()
    paths: list[Path] = []
    for asset in scaffold.assets:
        if not safe_filename(asset.filename):
            continue
        path = directory / asset.filename
        resolved = path.resolve()
        if not _inside_directory(resolved, root):
            continue
        path.write_bytes(asset.content)
        if path.read_bytes() != asset.content:
            continue
        paths.append(path)
    return tuple(paths)
