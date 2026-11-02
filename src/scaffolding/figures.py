from html import escape


class FigureRejected(Exception):
    pass


def render_svg(kind: str, source: str) -> bytes:
    if kind == "思维导图":
        return _mind_map(source)
    if kind == "结构图":
        nodes, edges = _structure(source)
        return _draw_graph(nodes, edges, frames=()).encode()
    if kind == "微格动画":
        nodes, edges, frames = _animation(source)
        return _draw_graph(nodes, edges, frames=frames).encode()
    raise FigureRejected("unknown figure")


def _reject_markup(source: str) -> None:
    if "<" in source:
        raise FigureRejected("markup")


def _mind_map(source: str) -> bytes:
    _reject_markup(source)
    nodes: list[tuple[int, str]] = []
    for raw in source.splitlines():
        if raw.strip() == "":
            continue
        spaces = len(raw) - len(raw.lstrip(" "))
        if raw[:spaces] != " " * spaces or spaces % 2 != 0:
            raise FigureRejected("indent")
        nodes.append((spaces // 2, raw.strip()))
    if not nodes or nodes[0][0] != 0:
        raise FigureRejected("empty outline")
    width = (max(depth for depth, _text in nodes) + 1) * 180 + 40
    height = len(nodes) * 48 + 24
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="' + str(width) + '" height="' + str(height) + '">',
        '<rect width="100%" height="100%" fill="#f7f6f2"/>',
    ]
    parents: list[tuple[int, int, int]] = []
    for index, (depth, text) in enumerate(nodes):
        while parents and parents[-1][0] >= depth:
            parents.pop()
        x = 24 + depth * 180
        y = 28 + index * 48
        if parents:
            _px, parent_x, parent_y = parents[-1]
            parts.append(
                '<line x1="' + str(parent_x + 120) + '" y1="' + str(parent_y) + '" x2="'
                + str(x) + '" y2="' + str(y) + '" stroke="#241c33" stroke-width="1.5"/>'
            )
        parts.append(
            '<rect x="' + str(x) + '" y="' + str(y - 16) + '" width="140" height="32" rx="8" fill="#fff" stroke="#d9d3c7"/>'
        )
        parts.append(
            '<text x="' + str(x + 10) + '" y="' + str(y + 5) + '" font-size="14" fill="#241c33">'
            + escape(text) + "</text>"
        )
        parents.append((depth, x, y))
    parts.append("</svg>")
    return "".join(parts).encode()


def _structure(source: str) -> tuple[list[str], list[tuple[str, str, str]]]:
    _reject_markup(source)
    nodes: list[str] = []
    edges: list[tuple[str, str, str]] = []
    for raw in source.splitlines():
        line = raw.strip()
        if line == "":
            continue
        if line.startswith("节点："):
            name = line.removeprefix("节点：").strip()
            if name == "" or name in nodes:
                raise FigureRejected("node")
            nodes.append(name)
            continue
        if line.startswith("箭头："):
            edges.append(_arrow(line.removeprefix("箭头："), nodes))
            continue
        raise FigureRejected("line")
    if not nodes:
        raise FigureRejected("no nodes")
    return nodes, edges


def _animation(source: str) -> tuple[list[str], list[tuple[str, str, str]], list[str]]:
    _reject_markup(source)
    nodes: list[str] = []
    edges: list[tuple[str, str, str]] = []
    frames: list[str] = []
    for raw in source.splitlines():
        line = raw.strip()
        if line == "":
            continue
        if line.startswith("节点："):
            name = line.removeprefix("节点：").strip()
            if name == "" or name in nodes:
                raise FigureRejected("node")
            nodes.append(name)
            continue
        if line.startswith("箭头："):
            edges.append(_arrow(line.removeprefix("箭头："), nodes))
            continue
        if line.startswith("帧："):
            name = line.removeprefix("帧：").strip()
            if name not in nodes:
                raise FigureRejected("frame")
            frames.append(name)
            continue
        raise FigureRejected("line")
    if not nodes or not frames:
        raise FigureRejected("no frames")
    return nodes, edges, frames


def _arrow(body: str, nodes: list[str]) -> tuple[str, str, str]:
    if body.count("->") != 1 or body.count("：") != 1:
        raise FigureRejected("arrow")
    start, rest = body.split("->", 1)
    end, label = rest.split("：", 1)
    start, end, label = start.strip(), end.strip(), label.strip()
    if start not in nodes or end not in nodes or label == "":
        raise FigureRejected("arrow")
    return start, end, label


def _draw_graph(nodes: list[str], edges: list[tuple[str, str, str]], *, frames: tuple[str, ...] | list[str]) -> str:
    positions = {name: (40 + index * 190, 78) for index, name in enumerate(nodes)}
    width = 40 + len(nodes) * 190
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="' + str(width) + '" height="160">',
        '<rect width="100%" height="100%" fill="#f7f6f2"/>',
    ]
    if frames:
        xs = ";".join(str(positions[name][0] + 70) for name in frames)
        ys = ";".join(str(positions[name][1]) for name in frames)
        parts.append(
            '<circle r="26" fill="#e4c84a" opacity="0.55">'
            + '<animate attributeName="cx" values="' + xs + '" dur="3s" repeatCount="indefinite"/>'
            + '<animate attributeName="cy" values="' + ys + '" dur="3s" repeatCount="indefinite"/>'
            + "</circle>"
        )
    for start, end, label in edges:
        x1, y1 = positions[start]
        x2, y2 = positions[end]
        parts.append(
            '<line x1="' + str(x1 + 140) + '" y1="' + str(y1) + '" x2="' + str(x2) + '" y2="' + str(y2)
            + '" stroke="#241c33" stroke-width="1.5"/>'
        )
        parts.append(
            '<text x="' + str((x1 + x2) // 2 + 70) + '" y="' + str(y1 - 18) + '" font-size="13" fill="#6d675f">'
            + escape(label) + "</text>"
        )
    for name, (x, y) in positions.items():
        parts.append(
            '<rect x="' + str(x) + '" y="' + str(y - 18) + '" width="140" height="36" rx="8" fill="#fff" stroke="#d9d3c7"/>'
        )
        parts.append(
            '<text x="' + str(x + 12) + '" y="' + str(y + 5) + '" font-size="14" fill="#241c33">'
            + escape(name) + "</text>"
        )
    parts.append("</svg>")
    return "".join(parts)
