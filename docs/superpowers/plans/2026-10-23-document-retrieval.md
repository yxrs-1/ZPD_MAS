# 文档检索生成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 教师上传 docx 或 pdf 形成文档库；模型先给出检索词，应用按词面找出片段后再写出教学目标；教师改完并确认后生成一份未发布任务。

**Architecture:** 新模块 `documents.py` 负责读文件、按标题切分、词面排序，以及两次补全写出目标。`TaskGeneration.generate_from_confirmed` 复用现有文字生成核对，不写来源。文档库放在 `Classroom.documents` 上，教师页共用这份对象。`classroom.json` 增加 `documents` 和 `next_document`，保存时把字段知识库和已保存目标写空。

**Tech Stack:** Python 3.14，pytest 9，标准库，pypdf。实现从 `origin/main` 的 `c199ab2` 建工作区。规格在本地 `master` 的 `79566d3`，文件是 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-23-document-retrieval-design.md`。工作区里若没有这份规格，在 Task 7 从该文件原样复制，不要改写。测试命令是 `.\.venv\Scripts\python.exe -m pytest`。PowerShell 下不要使用 `&&` 或 bash heredoc；提交用 `git commit -m "message"`。不要改 git config，不要 push。不要提交本计划。

## Global Constraints

- 文档编号按上传顺序是 `doc-1`、`doc-2`，只增不减。删除不改其余文档的编号。
- docx 用标准库读取正文段落和样式，不另加 docx 库。表格里的段落也读取。图片忽略。pdf 用 pypdf 只提取文字。扩展名不区分大小写，只接受 docx 和 pdf。
- 切分只在标题处进行，不按字数切开。docx 样式名是 `Heading1`、`Heading2`、`Heading3`、`Heading 1`、`Heading 2`、`Heading 3`、`标题1`、`标题2`、`标题3`、`标题 1`、`标题 2`、`标题 3`。另外，去掉两端空白后，第一个半角或全角空白之前的文字以「第」开头、以「章」或「节」结尾，并且中间至少有一个字符，这样的单独段落或单独一行也是标题。第一个标题前的正文单独成段。没有标题时全文是一个片段。空白片段丢掉。
- 上传失败句只有三句：「只接受 docx 或 pdf」「不能读取这份文件」「这份文件没有可用的正文」。都不入库。
- 检索词按空白和标点拆开。标点包含中英文逗号、句号、叹号、问号、顿号、分号、冒号和括号。片段原文包含这个词即命中，不改变大小写。不同词命中越多越靠前；一样多时按上传顺序，再按片段顺序。最多 5 段。
- 生成目标最多两次补全。第一次用户消息只是去掉两端空白后的需求，交回仅有键「检索」。第二次不再检索。没有命中时用户消息以「没有匹配内容」结束。合格目标只有「维度」和「表述」。维度只能是信息意识、计算思维、数字化学习与创新、信息社会责任。
- 确认不再检索。用户消息含「教师需求：」和「目标：」，不追加「没有指定题型和数量。」。题目核对沿用文字生成。成功响应是未发布任务页，不写课时来源或学段来源，目标不写入目标库。
- 目标页仍是 `/objectives`。字段是 `action`、`file`、`text`、`objectives`、`doc_id`。动作是「上传」「删除」「生成目标」「确认」。页面不显示片段。HTML 用拼接，不用 `str.format`。文字按 `html.escape` 写入。
- 会话和这次写出的目标不写入文件。读取时忽略 `lessons`、`standards`、`objectives`。保存时 `lessons` 和 `standards` 是空数组，`objectives` 的课时列表和学段列表是空的。
- 决策智能体、支架智能体和文字生成不读文档库。教师未登录时的规则不变。测试不调用 `serve`，不打开浏览器，不访问网络。
- 不修改 `model_decision.py`、`model_scaffold.py`、`model_generator.py`、`model_extractor.py`、`model_text.py`、`text_generation.py`、`html_assets.py`、`agents.py`、`scripted.py`。

## File Map

- Create: `src/scaffolding/documents.py` — 读文件、切分、排序、起草目标、解析教师改过的目标文字。
- Modify: `src/scaffolding/generation.py` — `generate_from_confirmed`。
- Modify: `src/scaffolding/store.py` — 读写文档库，字段记录写空。
- Modify: `src/scaffolding/teacher_page.py` — 目标页改成上传、生成目标和确认。
- Modify: `src/scaffolding/classroom.py` — 持有文档库，把上传文件名传给教师页。
- Modify: `requirements.txt` — 增加 `pypdf`。
- Create: `tests/test_documents.py`、`tests/test_document_rank.py`、`tests/test_document_draft.py`、`tests/test_document_confirm.py`、`tests/test_document_page.py`、`tests/test_document_acceptance.py`。
- Modify: `tests/test_classroom_store.py` — 旧字段记录不再读回。
- Delete: 只覆盖旧目标页的测试，见 Task 6。

---

### Task 1: 按标题读出文档片段

**Files:**
- Create: `src/scaffolding/documents.py`
- Create: `tests/test_documents.py`
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: 无。
- Produces: `DocumentError(message: str)`。`read_document(name: str, content: bytes) -> tuple[str, ...]`。失败时抛出 `DocumentError`，`message` 是规格里的三句之一。成功时每个元素是一个片段，标题和正文用 `\n` 连接。

- [ ] **Step 1: 安装 pypdf 并写失败测试**

在 `requirements.txt` 已有的 `pytest` 下一行加上 `pypdf`。运行 `.\.venv\Scripts\python.exe -m pip install pypdf`。

Create `tests/test_documents.py`：

```python
import io
import zipfile

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from scaffolding.documents import DocumentError, read_document


_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _docx(paragraphs: tuple[tuple[str, str], ...]) -> bytes:
    body = ""
    for text, style in paragraphs:
        style_xml = ""
        if style:
            style_xml = '<w:pPr><w:pStyle w:val="' + style + '"/></w:pPr>'
        body += "<w:p>" + style_xml + "<w:r><w:t>" + text + "</w:t></w:r></w:p>"
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="' + _W + '"><w:body>' + body + "</w:body></w:document>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


def _pdf(lines: tuple[str, ...]) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type0"),
        NameObject("/BaseFont"): NameObject("/STSong-Light"),
        NameObject("/Encoding"): NameObject("/UniGB-UTF16-H"),
    })
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref}),
    })
    commands = ["BT /F1 12 Tf 72 700 Td"]
    for index, line in enumerate(lines):
        if index:
            commands.append("0 -20 Td")
        commands.append("<" + line.encode("utf-16-be").hex() + "> Tj")
    commands.append("ET")
    stream = DecodedStreamObject()
    stream.set_data(" ".join(commands).encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_docx_splits_on_styles_and_keeps_a_long_section():
    body = "正" * 401
    content = _docx((
        ("前言", ""),
        ("第一章 数据与计算", "Heading 1"),
        (body, ""),
        ("第二节 信息", ""),
        ("后文", "标题 2"),
    ))

    chunks = read_document("教材.DOCX", content)

    assert chunks == ("前言", "第一章 数据与计算\n" + body, "第二节 信息", "后文")
    assert len(chunks[1]) > 400
    plain = read_document("笔记.docx", _docx((("这一章讲数据", ""), ("第章", ""))))
    assert plain == ("这一章讲数据\n第章",)


def test_pdf_splits_on_chapter_lines_and_a_plain_file_is_one_chunk():
    split = read_document("课标.pdf", _pdf(("前言", "第一章 数据", "正文一行", "第二节 信息")))
    whole = read_document("笔记.pdf", _pdf(("只有正文", "没有标题")))

    assert split == ("前言", "第一章 数据\n正文一行", "第二节 信息")
    assert whole == ("只有正文\n没有标题",)
    PdfReader(io.BytesIO(_pdf(("第一章 数据",)))).pages[0].extract_text()


def test_bad_files_are_rejected_without_chunks():
    with pytest.raises(DocumentError, match="只接受 docx 或 pdf"):
        read_document("笔记.txt", b"hello")
    with pytest.raises(DocumentError, match="不能读取这份文件"):
        read_document("坏.docx", b"not a zip")
    with pytest.raises(DocumentError, match="这份文件没有可用的正文"):
        read_document("空.docx", _docx((("   ", ""),)))
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_documents.py -v`

Expected: FAIL，`scaffolding.documents` 不存在。

- [ ] **Step 3: 实现读取和切分**

Create `src/scaffolding/documents.py`：

```python
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
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_documents.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```powershell
git add requirements.txt src/scaffolding/documents.py tests/test_documents.py
git commit -m "feat: split uploaded documents on headings"
```

---

### Task 2: 按词面选出最多五段

**Files:**
- Modify: `src/scaffolding/documents.py`
- Create: `tests/test_document_rank.py`

**Interfaces:**
- Consumes: 无。本任务不调用 `read_document`。
- Produces: `StoredDocument(doc_id: str, name: str, chunks: tuple[str, ...])`。`rank_passages(documents: tuple[StoredDocument, ...], query: str) -> tuple[tuple[str, str], ...]`。每一项是 `(文件名, 片段)`。检索词拆不开时返回空元组。

- [ ] **Step 1: 写失败测试**

Create `tests/test_document_rank.py`：

```python
from scaffolding.documents import StoredDocument, rank_passages


def _doc(doc_id: str, name: str, *chunks: str) -> StoredDocument:
    return StoredDocument(doc_id, name, chunks)


def test_more_distinct_words_rank_first_and_the_sixth_is_dropped():
    documents = (
        _doc("doc-1", "a.docx", "只有信息", "信息 与 数据"),
        _doc("doc-2", "b.pdf", "信息，数据，系统"),
    )

    ranked = rank_passages(documents, "信息，数据！系统")

    assert ranked[0] == ("b.pdf", "信息，数据，系统")
    assert ranked[1] == ("a.docx", "信息 与 数据")
    assert ("a.docx", "只有信息") in ranked
    assert len(ranked) == 3


def test_ties_follow_upload_order_then_chunk_order_and_case_is_exact():
    documents = tuple(
        _doc("doc-" + str(index), "f" + str(index) + ".docx", "Data", "data")
        for index in range(1, 5)
    )

    ranked = rank_passages(documents, "data")

    assert ranked[0] == ("f1.docx", "data")
    assert rank_passages(documents, "，，，") == ()
    assert len(rank_passages(tuple(
        _doc("doc-" + str(index), "n.docx", "词" + str(index)) for index in range(6)
    ), "词0 词1 词2 词3 词4 词5")) == 5
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_document_rank.py -v`

Expected: FAIL，`StoredDocument` 未定义。

- [ ] **Step 3: 实现排序**

在 `documents.py` 末尾追加：

```python
from dataclasses import dataclass


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
```

把 `dataclass` 的 import 放到文件顶部，不要留在末尾。

- [ ] **Step 4: 运行测试，确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_document_rank.py tests/test_documents.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```powershell
git add src/scaffolding/documents.py tests/test_document_rank.py
git commit -m "feat: rank document passages by matching words"
```

---

### Task 3: 两次补全起草目标

**Files:**
- Modify: `src/scaffolding/documents.py`
- Create: `tests/test_document_draft.py`

**Interfaces:**
- Consumes: `StoredDocument`，`rank_passages`。
- Produces: `DraftedObjective(dimension: str, statement: str)`。`DraftError(message: str)`。`draft_objectives(complete, documents: tuple[StoredDocument, ...], demand: str) -> tuple[DraftedObjective, ...]`。`format_objectives(items) -> str`。空白需求抛出 `DraftError("先填写需求")`，并且不调用 `complete`。其他失败抛出 `DraftError("没有写出目标")`。没有命中时仍调用第二次，用户消息包含需求原文和「没有匹配内容」，即使第二次交回检索词也不再调用 `complete`。

- [ ] **Step 1: 写失败测试**

Create `tests/test_document_draft.py`：

```python
import json

import pytest

from scaffolding.documents import DraftError, StoredDocument, draft_objectives, format_objectives


def _reply(body: dict) -> str:
    return json.dumps(body, ensure_ascii=False)


def test_a_match_is_shown_to_the_second_call_and_formatted():
    calls = []

    def complete(messages):
        calls.append(messages[1]["content"])
        if len(calls) == 1:
            return _reply({"检索": "信息，数据"})
        return _reply({"目标": [
            {"维度": "信息意识", "表述": "能识别信息"},
            {"维度": "信息意识", "表述": "能保护数据"},
        ]})

    documents = (StoredDocument("doc-1", "a.docx", ("信息与数据",)),)
    drafted = draft_objectives(complete, documents, "  数据怎么识别  ")

    assert calls[0] == "数据怎么识别"
    assert "教师需求：\n数据怎么识别\n\n匹配片段：\n文件名：a.docx\n信息与数据" == calls[1]
    assert format_objectives(drafted) == "维度：信息意识\n表述：能识别信息\n\n维度：信息意识\n表述：能保护数据"
    assert len(calls) == 2


def test_an_empty_match_uses_the_demand_and_does_not_search_again():
    calls = []

    def complete(messages):
        calls.append(messages[1]["content"])
        if len(calls) == 1:
            return _reply({"检索": "没有的词"})
        return _reply({"检索": "再找一次"})

    with pytest.raises(DraftError, match="没有写出目标"):
        draft_objectives(complete, (StoredDocument("doc-1", "a.docx", ("其他",)),), "教师需求原文")

    assert calls[1].endswith("没有匹配内容")
    assert "教师需求原文" in calls[1]
    assert len(calls) == 2


def test_blank_demand_does_not_call_the_model():
    def complete(messages):
        raise AssertionError("called")

    with pytest.raises(DraftError, match="先填写需求"):
        draft_objectives(complete, (), "  ")
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_document_draft.py -v`

Expected: FAIL，`draft_objectives` 未定义。

- [ ] **Step 3: 实现起草**

在 `documents.py` 追加：

```python
import json


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
```

`json` 的 import 放在文件顶部。

- [ ] **Step 4: 运行测试，确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_document_draft.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```powershell
git add src/scaffolding/documents.py tests/test_document_draft.py
git commit -m "feat: draft objectives from one document search"
```

---

### Task 4: 确认后的目标生成任务

**Files:**
- Modify: `src/scaffolding/documents.py`
- Modify: `src/scaffolding/generation.py`
- Create: `tests/test_document_confirm.py`

**Interfaces:**
- Consumes: `DraftedObjective`，`ModelTextGenerator.generate(text) -> str`，`parse_text_task`。
- Produces: `parse_objective_text(text: str) -> tuple[DraftedObjective, ...]`。格式不对抛出 `DraftError("目标格式不正确")`。`confirm_prompt(demand: str, objectives: tuple[DraftedObjective, ...]) -> str`。`TaskGeneration.generate_from_confirmed(demand: str, objectives) -> Task`。它调用文字生成方一次，不写入 `_origins`。没有文字生成方时抛出 `Rejected`。

- [ ] **Step 1: 写失败测试**

Create `tests/test_document_confirm.py`：

```python
import json

import pytest

from scaffolding.documents import DraftError, DraftedObjective, confirm_prompt, parse_objective_text
from scaffolding.generation import TaskGeneration
from scaffolding.tasks import TaskCatalog


_REPLY = json.dumps({
    "读法": {"单选": 1, "多选": "未指定", "判断": "未指定", "综合": "未指定"},
    "目标": [{"维度": "信息意识", "表述": "模型另写的目标"}],
    "题目": {
        "单选": [{
            "题目": "哪一项是数据",
            "选项": ["数据", "电线"],
            "参考答案": ["数据"],
            "解析": "题干已说明",
        }],
        "多选": [],
        "判断": [],
        "综合": [],
    },
}, ensure_ascii=False)


class _Text:
    def __init__(self) -> None:
        self.messages = []

    def generate(self, text: str) -> str:
        self.messages.append(text)
        return _REPLY


def test_edited_text_parses_and_the_prompt_has_no_fixed_count_line():
    parsed = parse_objective_text("维度：信息意识\n表述：能识别信息\n\n维度：计算思维\n表述：能分解问题")

    prompt = confirm_prompt("做一道单选", parsed)

    assert parsed[0] == DraftedObjective("信息意识", "能识别信息")
    assert "没有指定题型和数量。" not in prompt
    assert prompt.startswith("教师需求：\n做一道单选\n\n目标：\n维度：信息意识\n表述：能识别信息")
    with pytest.raises(DraftError, match="目标格式不正确"):
        parse_objective_text("维度：其他\n表述：能识别信息")


def test_confirmation_creates_an_unpublished_task_without_an_origin():
    catalog = TaskCatalog()
    text = _Text()
    generation = TaskGeneration(None, catalog, None, text)
    objectives = (DraftedObjective("信息意识", "能识别信息"),)

    task = generation.generate_from_confirmed("做一道单选", objectives)

    assert task.published is False
    assert task.questions[0].prompt == "哪一项是数据"
    assert generation.origin(task.task_id) is None
    assert text.messages[0] == confirm_prompt("做一道单选", objectives)
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_document_confirm.py -v`

Expected: FAIL，`parse_objective_text` 未定义。

- [ ] **Step 3: 实现解析和确认生成**

在 `documents.py` 追加：

```python
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
```

在 `TaskGeneration` 里、`generate_from_objectives` 之后追加：

```python
def generate_from_confirmed(self, demand: str, objectives) -> Task:
    from scaffolding.documents import confirm_prompt
    from scaffolding.text_generation import parse_text_task

    if self._text_generator is None:
        raise Rejected("there is no text generator")
    reply = self._text_generator.generate(confirm_prompt(demand, tuple(objectives)))
    return self._tasks.create(parse_text_task(reply))
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_document_confirm.py tests/test_objective_generation_record.py -v`

Expected: PASS。已有的 `generate_from_objectives` 测试仍通过。

- [ ] **Step 5: 提交**

```powershell
git add src/scaffolding/documents.py src/scaffolding/generation.py tests/test_document_confirm.py
git commit -m "feat: create a task from confirmed objectives"
```

---

### Task 5: 把文档库写入文件

**Files:**
- Modify: `src/scaffolding/documents.py`
- Modify: `src/scaffolding/classroom.py`
- Modify: `src/scaffolding/store.py`
- Modify: `tests/test_classroom_store.py`

**Interfaces:**
- Consumes: `read_document`，`StoredDocument`，`DocumentError`。
- Produces: `DocumentLibrary`。`documents() -> tuple[StoredDocument, ...]`。`add(name: str, content: bytes) -> StoredDocument`。`delete(doc_id: str) -> None`，未知编号抛出 `DocumentError("文档不存在")`。`load(documents: tuple[StoredDocument, ...], next_id: int) -> None`。`Classroom.documents` 与 `Classroom.teacher.library` 是同一个对象。保存后的 JSON 含 `next_document` 和 `documents`。`lessons`、`standards` 保存为空数组。`objectives["lessons"]` 和 `objectives["stages"]` 保存为空数组。

- [ ] **Step 1: 改存储测试里对旧字段的断言**

在 `tests/test_classroom_store.py` 的 `_KEYS` 元组末尾加上 `"documents"` 和 `"next_document"`。

在 `test_the_saved_classroom_reloads_without_login_or_the_model` 里，把这三行断言：

```python
assert second.knowledge.get_lesson("人教版", "必修一", "信息系统的组成").text == "课时原文"
assert second.knowledge.get_standard("高中").name == "普通高中信息科技课程标准"
found = second.objectives.lesson_objectives("人教版", "必修一", "信息系统的组成")
assert found[0].statement == "能分辨系统和要素"
```

换成：

```python
assert saved["lessons"] == []
assert saved["standards"] == []
assert saved["objectives"]["lessons"] == []
assert saved["objectives"]["stages"] == []
assert second.knowledge.lesson_count() == 0
assert second.knowledge.standard_count() == 0
assert second.objectives.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
```

`generation.origin("task-1")` 的断言保留。

另加一个测试：

```python
def test_documents_reload_and_old_field_records_are_ignored(tmp_path):
    path = tmp_path / "classroom.json"
    page = _room(path)
    page.documents.add("教材.docx", _docx((("第一章 数据", ""), ("正文", ""))))
    page.documents.delete("doc-1")
    page.documents.add("课标.pdf", _pdf(("第一节 信息", "条款")))
    raw = {
        "lessons": [{"version": "人教版", "volume": "必修一", "lesson": "旧课", "stage": "高中", "pages": "1", "text": "旧原文"}],
        "standards": [{"name": "旧课标", "stage": "高中", "clauses": "1", "text": "旧全文"}],
        "objectives": {"lessons": [], "stages": [], "next_id": 4},
    }
    saved = json.loads(path.read_text(encoding="utf-8"))
    saved.update(raw)
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")

    second = _room(path)

    assert [item.doc_id for item in second.documents.documents()] == ["doc-2"]
    assert second.documents.documents()[0].chunks == ("第一节 信息\n条款",)
    assert second.knowledge.lesson_count() == 0
    assert second.knowledge.standard_count() == 0
```

这个测试要能调用 Task 1 的 `_docx` 和 `_pdf`。把这两个函数从 `tests/test_documents.py` 改为可导入，并在存储测试里 `from tests.test_documents import _docx, _pdf`。若 `_room` 在添加文档后没有自动保存，测试在 `add` 和 `delete` 之后调用 `store.save_classroom(path, page)`。先读 `tests/test_classroom_store.py` 里的 `_room`，沿用它创建带路径的 `Classroom`。

- [ ] **Step 2: 运行测试，确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_classroom_store.py::test_documents_reload_and_old_field_records_are_ignored tests/test_classroom_store.py::test_the_saved_classroom_reloads_without_login_or_the_model -v`

Expected: FAIL，`Classroom` 没有 `documents`。

- [ ] **Step 3: 实现文档库和保存**

在 `documents.py` 追加：

```python
class DocumentLibrary:
    def __init__(self) -> None:
        self._docs: dict[str, StoredDocument] = {}
        self._order: list[str] = []
        self._next = 1

    def documents(self) -> tuple[StoredDocument, ...]:
        return tuple(self._docs[doc_id] for doc_id in self._order)

    def add(self, name: str, content: bytes) -> StoredDocument:
        chunks = read_document(name, content)
        doc_id = "doc-" + str(self._next)
        self._next += 1
        stored = StoredDocument(doc_id, name, chunks)
        self._docs[doc_id] = stored
        self._order.append(doc_id)
        return stored

    def delete(self, doc_id: str) -> None:
        if doc_id not in self._docs:
            raise DocumentError("文档不存在")
        del self._docs[doc_id]
        self._order.remove(doc_id)

    def load(self, documents: tuple[StoredDocument, ...], next_id: int) -> None:
        self._docs = {item.doc_id: item for item in documents}
        self._order = [item.doc_id for item in documents]
        self._next = next_id
```

`Classroom.__init__` 在创建 `TeacherPage` 之前增加 `self.documents = DocumentLibrary()`，并把 `library=self.documents` 传给 `TeacherPage`。`TeacherPage.__init__` 增加关键字参数 `library=None`，保存为 `self.library`；未传入时自己 `DocumentLibrary()`。

`store.classroom_state` 里把 `lessons` 和 `standards` 改成 `[]`。`objectives` 改成：

```python
{"lessons": [], "stages": [], "next_id": 1}
```

增加：

```python
"next_document": room.documents._next,
"documents": [
    {"doc_id": item.doc_id, "name": item.name, "chunks": list(item.chunks)}
    for item in room.documents.documents()
],
```

`load_classroom` 不再把文件里的课时、课标和目标装回内存。`_apply_knowledge` 改为把 `room.knowledge._lessons` 和 `_standards` 设成空字典。`_apply_objectives` 改为把课时和学段字典清空，`_next_id = 1`。然后：

```python
loaded = tuple(
    StoredDocument(item["doc_id"], item["name"], tuple(item["chunks"]))
    for item in data.get("documents", [])
)
next_id = data.get("next_document", len(loaded) + 1)
room.documents.load(loaded, next_id)
```

没有 `documents` 键时文档库为空，`next_document` 缺省为 `1`。上面的 `len(loaded) + 1` 只在有文档但没有 `next_document` 时使用。

- [ ] **Step 4: 运行测试，确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_classroom_store.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```powershell
git add src/scaffolding/documents.py src/scaffolding/classroom.py src/scaffolding/teacher_page.py src/scaffolding/store.py tests/test_classroom_store.py tests/test_documents.py
git commit -m "feat: keep uploaded documents in the classroom file"
```

---

### Task 6: 目标页上传、起草和确认

**Files:**
- Modify: `src/scaffolding/teacher_page.py`
- Create: `tests/test_document_page.py`
- Delete: `tests/test_teacher_objectives_edit.py`、`tests/test_teacher_objectives_extract.py`、`tests/test_teacher_objectives_open.py`、`tests/test_teacher_objectives_stage.py`、`tests/test_teacher_objectives_view.py`、`tests/test_teacher_objectives_links.py`、`tests/test_teacher_objective_generation_page.py`、`tests/test_teacher_objective_generation_success.py`

**Interfaces:**
- Consumes: `DocumentLibrary`，`draft_objectives`，`format_objectives`，`parse_objective_text`，`DraftError`，`DocumentError`，`generate_from_confirmed`。
- Produces: `TeacherPage.library`。`response_for(page, method, path, body, uploads=None, filenames=None)`。`filenames` 是字段名到文件名的字典，`uploads` 是字段名到字节的字典。目标页 POST 读取 `action`。

- [ ] **Step 1: 删除只覆盖旧目标页的测试，并写新页面测试**

删除上面列出的 8 个文件。不要删除 `tests/test_objective_*.py`、`tests/test_knowledge_*.py`、`tests/test_objective_generation_record.py`。

Create `tests/test_document_page.py`：

```python
import json

from scaffolding.generation import TaskGeneration
from scaffolding.tasks import TaskCatalog
from scaffolding.teacher_page import TeacherPage, response_for
from tests.teacher_objectives_helpers import form, text
from tests.test_documents import _docx


_OBJECTIVE = json.dumps({"目标": [{"维度": "信息意识", "表述": "能识别信息"}]}, ensure_ascii=False)
_TASK = json.dumps({
    "读法": {"单选": 1, "多选": "未指定", "判断": "未指定", "综合": "未指定"},
    "目标": [{"维度": "信息意识", "表述": "模型另写的目标"}],
    "题目": {
        "单选": [{
            "题目": "哪一项是数据",
            "选项": ["数据", "电线"],
            "参考答案": ["数据"],
            "解析": "题干已说明",
        }],
        "多选": [],
        "判断": [],
        "综合": [],
    },
}, ensure_ascii=False)


class _Text:
    def generate(self, message: str) -> str:
        return _TASK


def _page(calls):
    catalog = TaskCatalog()

    def complete(messages):
        calls.append(messages[1]["content"])
        if len(calls) == 1:
            return json.dumps({"检索": "数据"}, ensure_ascii=False)
        return _OBJECTIVE

    return TeacherPage(catalog, generation=TaskGeneration(None, catalog, None, _Text()), complete=complete), catalog


def test_get_lists_upload_and_does_not_call_the_model():
    calls = []
    page, _catalog = _page(calls)

    listed = text(response_for(page, "GET", "/", ""))
    opened = text(response_for(page, "GET", "/objectives/?ready=1", ""))

    assert 'href="/objectives"' in listed
    assert 'name="file"' in opened
    assert "上传" in opened
    assert 'name="text"' in opened
    assert "生成目标" in opened
    assert 'href="/generation"' in opened
    assert 'name="objectives"' not in opened
    assert calls == []


def test_upload_delete_and_a_bad_extension():
    calls = []
    page, _catalog = _page(calls)
    content = _docx((("第一章 数据", ""), ("片段秘密", "")))

    uploaded = text(response_for(
        page, "POST", "/objectives", form(action="上传"),
        {"file": content}, {"file": "a<b.docx"},
    ))
    missing = text(response_for(page, "POST", "/objectives", form(action="删除", doc_id="doc-9"), None, None))
    rejected = text(response_for(
        page, "POST", "/objectives", form(action="上传"),
        {"file": b"notes"}, {"file": "笔记.txt"},
    ))

    assert page.library.documents()[0].doc_id == "doc-1"
    assert "&lt;" in uploaded
    assert "文档不存在" in missing
    assert "只接受 docx 或 pdf" in rejected
    assert len(page.library.documents()) == 1
    assert calls == []
    removed = text(response_for(page, "POST", "/objectives", form(action="删除", doc_id="doc-1"), None, None))
    assert "a&lt;b.docx" not in removed
    assert page.library.documents() == ()


def test_draft_shows_editable_objectives_without_the_passage():
    calls = []
    page, _catalog = _page(calls)
    content = _docx((("第一章 数据", ""), ("片段秘密", "")))
    response_for(page, "POST", "/objectives", form(action="上传"), {"file": content}, {"file": "教材.docx"})

    drafted = text(response_for(page, "POST", "/objectives", form(action="生成目标", text="  识别数据  ")))
    blank = text(response_for(page, "POST", "/objectives", form(action="生成目标", text="  ")))

    assert calls[0] == "识别数据"
    assert "文件名：教材.docx" in calls[1]
    assert "片段秘密" in calls[1]
    assert 'name="objectives"' in drafted
    assert "确认" in drafted
    assert "识别数据" in drafted
    assert "匹配片段" not in drafted
    assert "片段秘密" not in drafted
    assert "先填写需求" in blank
    assert 'name="objectives"' not in blank


def test_confirm_creates_an_unpublished_task_and_a_bad_edit_stays():
    calls = []
    page, catalog = _page(calls)
    confirmed = text(response_for(page, "POST", "/objectives", form(
        action="确认", text="做一道单选", objectives="维度：信息意识\n表述：能识别信息",
    )))
    rejected = text(response_for(page, "POST", "/objectives", form(
        action="确认", text="做一道单选", objectives="维度：其他\n表述：能识别信息",
    )))
    unknown = text(response_for(page, "POST", "/objectives", form(action="发布")))

    assert "task-1" in confirmed
    assert "未发布" in confirmed
    assert page.generation.origin("task-1") is None
    assert page.objectives.lesson_objectives("人教版", "必修一", "信息系统的组成") == ()
    assert len(catalog._tasks) == 1
    assert "目标格式不正确" in rejected
    assert "维度：其他" in rejected
    assert "做一道单选" in rejected
    assert len(catalog._tasks) == 1
    assert "生成目标" in unknown
    assert "失败" not in unknown
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_document_page.py -v`

Expected: FAIL，页面仍是旧的课时查询，没有上传字段。

- [ ] **Step 3: 换掉目标页**

`TeacherPage.__init__` 增加 `complete=None`，保存为 `self.complete`。`open_objectives` 改为：

```python
def open_objectives(self, message: str = "", text: str = "", objectives: str = "") -> str:
    return _render_library(self, message, text, objectives)
```

`apply_objectives` 改为接收 `uploads=None, filenames=None`：

```python
def apply_objectives(self, fields, action: str, uploads=None, filenames=None) -> str:
    if action == "上传":
        return _upload_document(self, uploads or {}, filenames or {})
    if action == "删除":
        return _delete_document(self, fields.get("doc_id", [""])[-1])
    if action == "生成目标":
        return _draft_on_page(self, fields.get("text", [""])[-1])
    if action == "确认":
        return _confirm_on_page(self, fields.get("text", [""])[-1], fields.get("objectives", [""])[-1])
    return self.open_objectives()
```

`response_for` 增加参数 `uploads=None, filenames=None`。目标页 POST 把这两个参数传给 `apply_objectives`。

删除只服务旧目标页的函数：`_objective_query`、`_retrieve`、`_saved`、`_source_text`、`_query_fields`、`_query_form`、`_render_objectives`、`_edit_objective`、`_delete_objective`、`_generate_from_objectives`、`_extract_objectives`、`_task_links`。去掉因此不再使用的 import。不要删除任务编辑、发布、布置和文字生成。

新函数：

```python
def _render_library(page, message: str, text: str, objectives: str) -> str:
    action = _with_prefix(page.prefix, "/objectives")
    parts = ["<h1>目标</h1>"]
    if message:
        parts.append("<p>" + escape(message) + "</p>")
    if page.library.documents():
        items = []
        for item in page.library.documents():
            items.append(
                "<li>" + escape(item.name)
                + "<form method=\"post\" action=\"" + action + "\">"
                + "<input type=\"hidden\" name=\"action\" value=\"删除\">"
                + "<input type=\"hidden\" name=\"doc_id\" value=\"" + escape(item.doc_id) + "\">"
                + "<button type=\"submit\">删除</button></form></li>"
            )
        parts.append("<ul>" + "".join(items) + "</ul>")
    parts.append(
        "<form method=\"post\" action=\"" + action + "\" enctype=\"multipart/form-data\">"
        + "<input type=\"hidden\" name=\"action\" value=\"上传\">"
        + "<input type=\"file\" name=\"file\">"
        + "<button type=\"submit\">上传</button></form>"
    )
    parts.append(
        "<form method=\"post\" action=\"" + action + "\">"
        + "<textarea name=\"text\">" + escape(text) + "</textarea>"
        + "<button type=\"submit\" name=\"action\" value=\"生成目标\">生成目标</button>"
        + "<a href=\"" + _with_prefix(page.prefix, "/generation") + "\">生成</a></form>"
    )
    if objectives:
        parts.append(
            "<form method=\"post\" action=\"" + action + "\">"
            + "<input type=\"hidden\" name=\"action\" value=\"确认\">"
            + "<input type=\"hidden\" name=\"text\" value=\"" + escape(text) + "\">"
            + "<textarea name=\"objectives\">" + escape(objectives) + "</textarea>"
            + "<button type=\"submit\">确认</button></form>"
        )
    return _document("".join(parts))


def _upload_document(page, uploads: dict, filenames: dict) -> str:
    name = filenames.get("file", "")
    content = uploads.get("file")
    if content is None:
        return page.open_objectives("只接受 docx 或 pdf")
    try:
        page.library.add(name, content)
    except DocumentError as error:
        return page.open_objectives(error.message)
    return page.open_objectives()


def _delete_document(page, doc_id: str) -> str:
    try:
        page.library.delete(doc_id)
    except DocumentError as error:
        return page.open_objectives(error.message)
    return page.open_objectives()


def _draft_on_page(page, text: str) -> str:
    if text.strip() == "":
        return page.open_objectives("先填写需求", text)
    if page.complete is None:
        return page.open_objectives("没有写出目标", text)
    try:
        drafted = draft_objectives(page.complete, page.library.documents(), text)
    except DraftError as error:
        return page.open_objectives(error.message, text)
    return page.open_objectives("", text, format_objectives(drafted))


def _confirm_on_page(page, text: str, objectives: str) -> str:
    if text.strip() == "":
        return page.open_objectives("先填写需求", text, objectives)
    try:
        parsed = parse_objective_text(objectives)
    except DraftError as error:
        return page.open_objectives(error.message, text, objectives)
    if page.generation is None:
        return page.open_objectives("生成失败，没有创建任务", text, objectives)
    try:
        task = page.generation.generate_from_confirmed(text, parsed)
    except Exception:
        return page.open_objectives("生成失败，没有创建任务", text, objectives)
    return _render(page, task.task_id)
```

从 `documents` 导入 `DocumentError`、`DraftError`、`draft_objectives`、`format_objectives`、`parse_objective_text`。

生成目标的按钮用 `name="action"`，这样文字框表单里的动作是「生成目标」。确认表单用隐藏字段 `action=确认`，避免按钮文字再写进另一个字段。上传和删除同样用隐藏的 `action`。

- [ ] **Step 4: 运行测试，确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_document_page.py tests/test_teacher_page_list.py tests/test_teacher_text_generation_page.py tests/test_teacher_objectives_acceptance.py -v`

Expected: PASS。`tests/test_teacher_objectives_acceptance.py` 里把 `assert "查看" in opened` 改成 `assert "生成目标" in opened` 和 `assert 'name="file"' in opened`。不要恢复旧的课时查询。

- [ ] **Step 5: 提交**

```powershell
git add src/scaffolding/teacher_page.py tests/test_document_page.py tests/test_teacher_objectives_acceptance.py tests/test_teacher_objectives_edit.py tests/test_teacher_objectives_extract.py tests/test_teacher_objectives_open.py tests/test_teacher_objectives_stage.py tests/test_teacher_objectives_view.py tests/test_teacher_objectives_links.py tests/test_teacher_objective_generation_page.py tests/test_teacher_objective_generation_success.py
git commit -m "feat: draft and confirm objectives from uploaded documents"
```

被删除的测试也要放进这次提交。

---

### Task 7: 课堂接收上传并验收

**Files:**
- Modify: `src/scaffolding/classroom.py`
- Modify: `tests/test_teacher_objective_generation_acceptance.py`
- Create: `tests/test_document_acceptance.py`
- Copy if missing: `docs/superpowers/specs/2026-10-23-document-retrieval-design.md`

**Interfaces:**
- Consumes: Task 6 的 `response_for(..., uploads, filenames)`，`files_from_body`。
- Produces: `filenames_from_body(content_type: str, body: bytes) -> dict[str, str]`。`Classroom.__init__` 增加关键字参数 `complete=None`，并传给 `TeacherPage`。`production_classroom` 把同一个 `complete` 传给 `Classroom`。正式运行的 multipart 同时取出文件字节和文件名。

- [ ] **Step 1: 写验收测试**

若工作区没有规格文件，从 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-23-document-retrieval-design.md` 原样复制，不要改写。

Create `tests/test_document_acceptance.py`：

```python
import json
from pathlib import Path

from scaffolding.classroom import Classroom, production_classroom, response_for
from scaffolding.model_text import ModelTextGenerator
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.tasks import TaskCatalog
from tests.classroom_helpers import form, student_cookie, teacher_cookie, text
from tests.test_documents import _docx, _pdf


def test_the_spec_is_present_and_text_generation_is_wired():
    spec = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "specs" / "2026-10-23-document-retrieval-design.md"
    calls = []

    def post(url, headers, payload):
        calls.append(url)
        raise AssertionError("network")

    room = production_classroom(post=post)
    assert spec.is_file()
    assert isinstance(room.generation._text_generator, ModelTextGenerator)
    assert calls == []


def test_a_logged_in_teacher_uploads_and_the_student_does_not_read_documents(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    room = Classroom(TaskCatalog(), ScriptedDecisionAgent(), ScriptedScaffoldAgent(), path="classroom.json")
    headers = teacher_cookie(room)
    uploaded = response_for(
        room, "POST", "/teacher/objectives", form(action="上传"), 0, headers,
        {"file": _docx((("第一章 数据", ""), ("正文", "")))},
        {"file": "教材.docx"},
    )
    saved = json.loads(Path("classroom.json").read_text(encoding="utf-8"))
    student = response_for(room, "GET", "/student/objectives", "", 0, student_cookie(room))

    assert "教材.docx" in text(uploaded)
    assert saved["documents"][0]["doc_id"] == "doc-1"
    assert student.status == 404
    assert "任务不存在" in text(student)
    assert "教材.docx" not in text(student)
```

`response_for` 现在的参数顺序是 `room, method, path, body, now, headers="", uploads=None`。本任务给它加上 `filenames=None`，测试用关键字传入文件名，避免把文件名当成 `headers`。

在 `tests/test_teacher_objective_generation_acceptance.py` 删除 `test_the_classroom_generates_from_saved_objectives`。保留「目标链接、生成链接、学生 404、首页没有按目标生成」的测试；若它仍要求页面含旧查询字段，改成要求含 `name="file"` 和「生成目标」。

- [ ] **Step 2: 运行测试，确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_document_acceptance.py -v`

Expected: FAIL，`response_for` 不接受文件名，或 `production_classroom` 没有把 `complete` 交给教师页。

- [ ] **Step 3: 接通课堂**

`classroom.response_for` 增加 `filenames=None`，传给 `_dispatch_response` 和 `_teacher_response`。

```python
def filenames_from_body(content_type: str, body: bytes) -> dict[str, str]:
    names = {}
    for part in _multipart_parts(content_type, body):
        name = _part_name(part)
        filename = part.get_filename()
        if name and filename:
            names[name] = str(filename)
    return names
```

`serve` 在解析 multipart 时同时调用 `filenames_from_body`，并把结果传给 `response_for`。`files_from_body` 的返回值仍是字节，班级导入不用改。

`_teacher_response` 在调用 `teacher_response_for` 时传入 `uploads` 和 `filenames`。

`Classroom.__init__` 增加 `complete=None`，创建教师页时传入 `complete=complete`。`production_classroom` 把已有的 `complete` 传进 `Classroom`。不要改决策、支架、提炼和出题模型的构造。

- [ ] **Step 4: 运行全部测试，确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS。学生求助和文字生成的原有测试不需要改调用文档库的代码；它们失败时，只确认这些路径没有读 `room.documents`，不要让它们发起检索。

- [ ] **Step 5: 提交**

```powershell
git add src/scaffolding/classroom.py tests/test_document_acceptance.py tests/test_teacher_objective_generation_acceptance.py docs/superpowers/specs/2026-10-23-document-retrieval-design.md
git commit -m "test: accept document retrieval in the classroom"
```

规格只在工作区原先没有它时才加入提交。不要提交本计划。
