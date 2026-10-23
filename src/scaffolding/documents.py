import io
import zipfile
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
