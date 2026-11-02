from html import escape


class FigureRejected(Exception):
    pass


def render_svg(kind: str, source: str) -> bytes:
    if kind == "思维导图":
        return _mind_map(source)
    if kind == "结构图":
        nodes, edges = _structure(source)
        return _draw_graph(nodes, edges).encode()
    if kind == "微格动画":
        nodes, edges, beats = _animation(source)
        return _draw_animation(nodes, edges, beats).encode()
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


_FORBIDDEN = ("学生", "教师", "引导", "让学生", "请学生", "学情")


def _animation(source: str) -> tuple[list[str], list[tuple[str, str, str]], list[tuple]]:
    _reject_markup(source)
    nodes: list[str] = []
    edges: list[tuple[str, str, str]] = []
    beats: list[tuple] = []
    for raw in source.splitlines():
        line = raw.strip()
        if line == "":
            continue
        if line.startswith("拍："):
            beats.append(_beat(line.removeprefix("拍：").strip(), nodes, edges))
            continue
        if beats:
            raise FigureRejected("line")
        if line.startswith("节点："):
            name = line.removeprefix("节点：").strip()
            if name == "" or name in nodes or "：" in name or "->" in name:
                raise FigureRejected("node")
            nodes.append(name)
            continue
        if line.startswith("箭头："):
            start, end, label = _arrow(line.removeprefix("箭头："), nodes)
            if start == end or "：" in label or "->" in label:
                raise FigureRejected("arrow")
            if any(item[0] == start and item[1] == end for item in edges):
                raise FigureRejected("arrow")
            edges.append((start, end, label))
            continue
        raise FigureRejected("line")
    if len(beats) < 2 or sum(beat[-2] for beat in beats) != 100:
        raise FigureRejected("beats")
    indexes = {name: index for index, name in enumerate(nodes)}
    back = [(start, end) for start, end, _label in edges if indexes[end] < indexes[start]]
    traveled = {(beat[1], beat[2]) for beat in beats if beat[0] == "move"}
    if back:
        if any(pair not in traveled for pair in back):
            raise FigureRejected("back edge")
    elif not traveled:
        raise FigureRejected("move")
    return nodes, edges, beats


def _beat(body: str, nodes: list[str], edges: list[tuple[str, str, str]]) -> tuple:
    if "->" in body:
        if body.count("->") != 1 or body.count("：") != 2:
            raise FigureRejected("beat")
        route, duration, caption = body.split("：")
        start, end = (part.strip() for part in route.split("->"))
        if not any(item[0] == start and item[1] == end for item in edges):
            raise FigureRejected("beat")
        return ("move", start, end, _tenths(duration.strip()), _caption(caption))
    if body.count("：") != 2:
        raise FigureRejected("beat")
    node, duration, caption = (part.strip() for part in body.split("："))
    if node not in nodes:
        raise FigureRejected("beat")
    return ("hold", node, _tenths(duration), _caption(caption))


def _tenths(token: str) -> int:
    if token == "" or ("." in token and token.count(".") != 1):
        raise FigureRejected("duration")
    if "." in token:
        whole, frac = token.split(".", 1)
        if whole == "" or len(frac) != 1 or not whole.isdigit() or not frac.isdigit():
            raise FigureRejected("duration")
        if whole != "0" and whole.startswith("0"):
            raise FigureRejected("duration")
        value = int(whole) * 10 + int(frac)
    elif not token.isdigit() or (len(token) > 1 and token.startswith("0")):
        raise FigureRejected("duration")
    else:
        value = int(token) * 10
    if value < 5:
        raise FigureRejected("duration")
    return value


def _caption(text: str) -> str:
    caption = text.strip()
    if caption == "" or len(caption) > 20 or any(word in caption for word in _FORBIDDEN):
        raise FigureRejected("caption")
    if "：" in caption or "->" in caption:
        raise FigureRejected("caption")
    return caption


def _draw_animation(nodes: list[str], edges: list[tuple[str, str, str]], beats: list[tuple]) -> str:
    indexes = {name: index for index, name in enumerate(nodes)}
    centers = _centers(nodes, edges, indexes)
    width, height, baseline = _canvas(centers)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="' + str(width) + '" height="' + str(height) + '">',
        '<rect width="100%" height="100%" fill="#f7f6f2"/>',
    ]
    for start, end, label in edges:
        x1, y1 = centers[start]
        x2, y2 = centers[end]
        if indexes[end] < indexes[start]:
            control = ((x1 + x2) / 2, min(y1, y2) - 72)
            parts.append(
                '<path d="M ' + _px(x1) + "," + _px(y1) + " Q " + _px(control[0]) + ","
                + _px(control[1]) + " " + _px(x2) + "," + _px(y2)
                + '" fill="none" stroke="#241c33" stroke-width="1.5"/>'
            )
        else:
            parts.append(
                '<line x1="' + _px(x1) + '" y1="' + _px(y1) + '" x2="' + _px(x2) + '" y2="'
                + _px(y2) + '" stroke="#241c33" stroke-width="1.5"/>'
            )
        parts.append(
            '<text x="' + _px((x1 + x2) / 2) + '" y="' + _px(min(y1, y2) - 16)
            + '" font-size="13" fill="#6d675f">' + escape(label) + "</text>"
        )
    for name, (x, y) in centers.items():
        parts.append('<g transform="translate(' + _px(x) + "," + _px(y) + ')">')
        parts.append("<g>")
        times, values = _pulse(name, beats)
        parts.append(
            '<animateTransform attributeName="transform" type="scale" dur="10s" repeatCount="indefinite" keyTimes="'
            + times + '" values="' + values + '"/>'
        )
        parts.append('<rect x="-70" y="-18" width="140" height="36" rx="8" fill="#fff" stroke="#d9d3c7"/>')
        parts.append(
            '<text x="-58" y="5" font-size="14" fill="#241c33">' + escape(name) + "</text>"
        )
        parts.append("</g></g>")
    frames = _token_frames(beats, centers, indexes)
    parts.append(
        '<circle cx="' + _px(frames[0][1]) + '" cy="' + _px(frames[0][2])
        + '" r="8" fill="#e4c84a">'
    )
    parts.append(_timed("cx", frames, 1))
    parts.append(_timed("cy", frames, 2))
    parts.append("</circle>")
    cursor = 0
    for beat in beats:
        tenths = beat[-2]
        times, values = _caption_keys(cursor, cursor + tenths)
        parts.append(
            '<text x="24" y="' + str(baseline) + '" font-size="14" fill="#241c33" opacity="0">'
            + '<animate attributeName="opacity" dur="10s" repeatCount="indefinite" keyTimes="'
            + times + '" values="' + values + '"/>' + escape(beat[-1]) + "</text>"
        )
        cursor += tenths
    parts.append("</svg>")
    return "".join(parts)


def _centers(nodes: list[str], edges: list[tuple[str, str, str]], indexes: dict[str, int]) -> dict[str, tuple[float, float]]:
    back = any(indexes[end] < indexes[start] for start, end, _label in edges)
    if not back:
        return {name: (40 + index * 190 + 70, 64) for index, name in enumerate(nodes)}
    ranks = {name: 0 for name in nodes}
    outgoing: dict[str, list[str]] = {}
    for start, end, _label in edges:
        if indexes[end] > indexes[start]:
            outgoing.setdefault(start, []).append(end)
    for name in nodes:
        for end in outgoing.get(name, []):
            ranks[end] = max(ranks[end], ranks[name] + 1)
    columns: dict[int, list[str]] = {}
    for name in nodes:
        columns.setdefault(ranks[name], []).append(name)
    centers = {}
    for rank, names in columns.items():
        for position, name in enumerate(names):
            centers[name] = (40 + rank * 220 + 70, 136 + position * 100)
    return centers


def _canvas(centers: dict[str, tuple[float, float]]) -> tuple[int, int, int]:
    right = max(x + 70 for x, _y in centers.values())
    lowest = max(y for _x, y in centers.values())
    baseline = int(lowest + 54)
    return int(right + 40), baseline + 24, baseline


def _token_frames(beats: list[tuple], centers: dict[str, tuple[float, float]], indexes: dict[str, int]) -> list[tuple[float, float, float]]:
    first = beats[0]
    origin = centers[first[1]]
    frames = [(0, origin[0], origin[1])]
    cursor = 0
    for beat in beats:
        tenths = beat[-2]
        if beat[0] == "move":
            start, end = centers[beat[1]], centers[beat[2]]
            if indexes[beat[2]] < indexes[beat[1]]:
                control = ((start[0] + end[0]) / 2, min(start[1], end[1]) - 72)
                for amount in (0.25, 0.5, 0.75):
                    remain = 1 - amount
                    point = (
                        remain * remain * start[0] + 2 * remain * amount * control[0] + amount * amount * end[0],
                        remain * remain * start[1] + 2 * remain * amount * control[1] + amount * amount * end[1],
                    )
                    frames.append((cursor + tenths * amount, point[0], point[1]))
            else:
                mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
                frames.append((cursor + tenths / 2, mid[0], mid[1]))
            frames.append((cursor + tenths, end[0], end[1]))
        else:
            point = centers[beat[1]]
            frames.append((cursor + tenths, point[0], point[1]))
        cursor += tenths
    return frames


def _pulse(node: str, beats: list[tuple]) -> tuple[str, str]:
    points = [(0.0, 1.0)]
    cursor = 0
    for beat in beats:
        cursor += beat[-2]
        arrives = beat[1] == node if beat[0] == "hold" else beat[2] == node
        if not arrives:
            continue
        start = cursor - 3
        if points[-1][0] < start:
            points.append((start, 1.0))
        points.append((cursor - 1.5, 0.92))
        points.append((float(cursor), 1.0))
    if points[-1][0] < 100:
        points.append((100.0, 1.0))
    return (
        ";".join(_unit(tenth) for tenth, _scale in points),
        ";".join("1" if scale == 1 else "0.92" for _tenth, scale in points),
    )


def _caption_keys(start: int, end: int) -> tuple[str, str]:
    if start == 0:
        times, values = [0, end, end + 0.1, 100], [1, 1, 0, 0]
    elif end == 100:
        times, values = [0, start, 100], [0, 1, 1]
    else:
        times, values = [0, start, end, end + 0.1, 100], [0, 1, 1, 0, 0]
    return ";".join(_unit(item) for item in times), ";".join(str(item) for item in values)


def _timed(attribute: str, frames: list[tuple[float, float, float]], index: int) -> str:
    return (
        '<animate attributeName="' + attribute + '" dur="10s" repeatCount="indefinite" keyTimes="'
        + ";".join(_unit(frame[0]) for frame in frames) + '" values="'
        + ";".join(_px(frame[index]) for frame in frames) + '"/>'
    )


def _px(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _unit(tenth: float) -> str:
    text = f"{tenth / 100:.4f}".rstrip("0").rstrip(".")
    if text in ("", "-0"):
        return "0"
    return text


def _arrow(body: str, nodes: list[str]) -> tuple[str, str, str]:
    if body.count("->") != 1 or body.count("：") != 1:
        raise FigureRejected("arrow")
    start, rest = body.split("->", 1)
    end, label = rest.split("：", 1)
    start, end, label = start.strip(), end.strip(), label.strip()
    if start not in nodes or end not in nodes or label == "":
        raise FigureRejected("arrow")
    return start, end, label


def _draw_graph(nodes: list[str], edges: list[tuple[str, str, str]]) -> str:
    positions = {name: (40 + index * 190, 78) for index, name in enumerate(nodes)}
    width = 40 + len(nodes) * 190
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="' + str(width) + '" height="160">',
        '<rect width="100%" height="100%" fill="#f7f6f2"/>',
    ]
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
