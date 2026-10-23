import io
import json
import zipfile
from dataclasses import dataclass
from xml.etree import ElementTree

from pypdf import PdfReader


class DocumentError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_STYLES = frozenset({
    "Heading1", "Heading2", "Heading3",
    "Heading 1", "Heading 2", "Heading 3",
    "标题1", "标题2", "标题3",
    "标题 1", "标题 2", "标题 3",
})


def read_document(name: str, content: bytes) -> tuple[str, ...]:
    extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if extension not in ("docx", "pdf"):
        raise DocumentError("只接受 docx 或 pdf")
    try:
        blocks = _docx_blocks(content) if extension == "docx" else _pdf_blocks(content)
    except Exception as error:
        raise DocumentError("不能读取这份文件") from error
    chunks = _chunks(blocks)
    if chunks == ():
        raise DocumentError("这份文件没有可用的正文")
    return chunks


def _docx_blocks(content: bytes) -> tuple[tuple[str, bool], ...]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    blocks = []
    for paragraph in root.iter(_W + "p"):
        texts = [node.text or "" for node in paragraph.iter(_W + "t")]
        text = "".join(texts).strip()
        style = ""
        properties = paragraph.find(_W + "pPr")
        if properties is not None:
            marker = properties.find(_W + "pStyle")
            if marker is not None:
                style = marker.get(_W + "val") or ""
        if text == "":
            continue
        blocks.append((text, style in _STYLES or _heading_text(text)))
    return tuple(blocks)


def _pdf_blocks(content: bytes) -> tuple[tuple[str, bool], ...]:
    reader = PdfReader(io.BytesIO(content))
    lines = []
    for page in reader.pages:
        extracted = page.extract_text() or ""
        lines.extend(extracted.splitlines())
    return tuple((line.strip(), _heading_text(line)) for line in lines if line.strip())


def _heading_text(text: str) -> bool:
    stripped = text.strip()
    if stripped == "":
        return False
    token = stripped.split()[0]
    return len(token) >= 3 and token.startswith("第") and token.endswith(("章", "节"))


def _chunks(blocks: tuple[tuple[str, bool], ...]) -> tuple[str, ...]:
    if not any(is_heading for _, is_heading in blocks):
        whole = "\n".join(text for text, _ in blocks)
        return (whole,) if whole.strip() else ()
    chunks = []
    current: list[str] = []
    for text, is_heading in blocks:
        if is_heading:
            if current:
                chunks.append("\n".join(current))
            current = [text]
        else:
            current.append(text)
    if current:
        chunks.append("\n".join(current))
    return tuple(chunk for chunk in chunks if chunk.strip())


_PUNCTUATION = "，。！？、；：,.!?;:（）()【】[]《》<>\"'“”‘’"


@dataclass(frozen=True)
class StoredDocument:
    doc_id: str
    name: str
    chunks: tuple[str, ...]


def rank_passages(documents: tuple[StoredDocument, ...], query: str) -> tuple[tuple[str, str], ...]:
    terms = tuple(dict.fromkeys(_terms(query)))
    if terms == ():
        return ()
    ranked = []
    for doc_index, document in enumerate(documents):
        for chunk_index, chunk in enumerate(document.chunks):
            hits = sum(1 for term in terms if term in chunk)
            if hits:
                ranked.append((-hits, doc_index, chunk_index, document.name, chunk))
    ranked.sort()
    return tuple((name, chunk) for _, _, _, name, chunk in ranked[:5])


def _terms(query: str) -> tuple[str, ...]:
    characters = []
    for character in query.strip():
        characters.append(" " if character.isspace() or character in _PUNCTUATION else character)
    return tuple(term for term in "".join(characters).split(" ") if term)


@dataclass(frozen=True)
class DraftedObjective:
    dimension: str
    statement: str


class DraftError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


_DIMENSIONS = frozenset({
    "信息意识",
    "计算思维",
    "数字化学习与创新",
    "信息社会责任",
})
_RETRIEVAL_SYSTEM = (
    "只回一份 JSON 对象，不要代码块，不要其他文字。\n"
    "顶层只有「检索」。它的值是一个非空字符串，用作检索词。"
)
_OBJECTIVE_SYSTEM = (
    "只回一份 JSON 对象，不要代码块，不要其他文字。\n"
    "顶层只有「目标」。它的值是数组，至少一条。\n"
    "每条只有「维度」和「表述」。\n"
    "维度只能是信息意识、计算思维、数字化学习与创新、信息社会责任。\n"
    "表述去掉两端空白后还有内容。不要再交回检索词。"
)


def draft_objectives(complete, documents: tuple[StoredDocument, ...], demand: str) -> tuple[DraftedObjective, ...]:
    stripped = demand.strip()
    if stripped == "":
        raise DraftError("先填写需求")
    first = _call(complete, (
        {"role": "system", "content": _RETRIEVAL_SYSTEM},
        {"role": "user", "content": stripped},
    ))
    query = _retrieval_query(first)
    if _terms(query) == ():
        raise DraftError("没有写出目标")
    passages = rank_passages(documents, query)
    second = _call(complete, (
        {"role": "system", "content": _OBJECTIVE_SYSTEM},
        {"role": "user", "content": _second_message(stripped, passages)},
    ))
    return _drafted(second)


def format_objectives(items) -> str:
    return "\n\n".join("维度：" + item.dimension + "\n表述：" + item.statement for item in items)


def parse_objective_text(text: str) -> tuple[DraftedObjective, ...]:
    blocks = [block for block in text.replace("\r\n", "\n").split("\n\n") if block.strip()]
    if blocks == []:
        raise DraftError("目标格式不正确")
    parsed = []
    for block in blocks:
        lines = [line for line in block.split("\n") if line.strip()]
        if len(lines) != 2 or not lines[0].startswith("维度：") or not lines[1].startswith("表述："):
            raise DraftError("目标格式不正确")
        dimension = lines[0][len("维度："):].strip()
        statement = lines[1][len("表述："):].strip()
        if dimension not in _DIMENSIONS or statement == "":
            raise DraftError("目标格式不正确")
        parsed.append(DraftedObjective(dimension, statement))
    return tuple(parsed)


def confirm_prompt(demand: str, objectives: tuple[DraftedObjective, ...]) -> str:
    blocks = ["维度：" + item.dimension + "\n表述：" + item.statement for item in objectives]
    return "教师需求：\n" + demand.strip() + "\n\n目标：\n" + "\n\n".join(blocks)


def _call(complete, messages):
    try:
        reply = complete(messages)
    except DraftError:
        raise
    except Exception as error:
        raise DraftError("没有写出目标") from error
    if not isinstance(reply, str):
        raise DraftError("没有写出目标")
    return reply


def _object(reply: str):
    try:
        body = json.loads(reply.strip())
    except json.JSONDecodeError as error:
        raise DraftError("没有写出目标") from error
    if not isinstance(body, dict):
        raise DraftError("没有写出目标")
    return body


def _retrieval_query(reply: str) -> str:
    body = _object(reply)
    if set(body) != {"检索"} or not isinstance(body["检索"], str) or body["检索"].strip() == "":
        raise DraftError("没有写出目标")
    return body["检索"].strip()


def _second_message(demand: str, passages: tuple[tuple[str, str], ...]) -> str:
    if passages == ():
        return "教师需求：\n" + demand + "\n\n没有匹配内容"
    blocks = ["教师需求：", demand, "", "匹配片段："]
    for index, (name, chunk) in enumerate(passages):
        if index:
            blocks.append("")
        blocks.append("文件名：" + name)
        blocks.append(chunk)
    return "\n".join(blocks)


def _drafted(reply: str) -> tuple[DraftedObjective, ...]:
    body = _object(reply)
    if set(body) != {"目标"} or not isinstance(body["目标"], list) or body["目标"] == []:
        raise DraftError("没有写出目标")
    drafted = []
    for item in body["目标"]:
        if not isinstance(item, dict) or set(item) != {"维度", "表述"}:
            raise DraftError("没有写出目标")
        if not isinstance(item["维度"], str) or not isinstance(item["表述"], str):
            raise DraftError("没有写出目标")
        statement = item["表述"].strip()
        if item["维度"] not in _DIMENSIONS or statement == "":
            raise DraftError("没有写出目标")
        drafted.append(DraftedObjective(item["维度"], statement))
    return tuple(drafted)
