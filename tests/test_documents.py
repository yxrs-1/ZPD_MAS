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
