import io
import zipfile
from html import escape

import pytest

from scaffolding.sheet import SheetError, read_student_rows


def _xlsx(rows: tuple[tuple[str, ...], ...]) -> bytes:
    sheet_rows = []
    for index, values in enumerate(rows, start=1):
        cells = []
        for column, value in enumerate(values):
            ref = chr(ord("A") + column) + str(index)
            cells.append(
                '<c r="' + ref + '" t="inlineStr"><is><t>' + escape(value) + "</t></is></c>"
            )
        sheet_rows.append('<row r="' + str(index) + '">' + "".join(cells) + "</row>")
    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>" + "".join(sheet_rows) + "</sheetData></worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="学生" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as book:
        book.writestr("xl/workbook.xml", workbook)
        book.writestr("xl/_rels/workbook.xml.rels", rels)
        book.writestr("xl/worksheets/sheet1.xml", sheet)
    return buffer.getvalue()


def test_the_first_sheet_returns_data_rows_after_the_header():
    data = _xlsx((
        ("账号", "密码", "姓名", "备注"),
        ("s1", "secret", "甲", "忽略"),
        ("", "", ""),
        ("s2", "secret", ""),
        ("s3", "secret"),
    ))

    assert read_student_rows(data) == (
        (2, "s1", "secret", "甲"),
        (4, "s2", "secret", ""),
        (5, "s3", "secret", None),
    )


def test_a_bad_header_or_unreadable_bytes_raise_the_spec_sentences():
    with pytest.raises(SheetError, match="表头必须是账号、密码、姓名"):
        read_student_rows(_xlsx((("姓名", "账号", "密码"),)))
    with pytest.raises(SheetError, match="不能读取这份表格"):
        read_student_rows(b"not a spreadsheet")


def _package(sheet: str, shared: str | None = None) -> bytes:
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="学生" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as book:
        book.writestr("xl/workbook.xml", workbook)
        book.writestr("xl/_rels/workbook.xml.rels", rels)
        book.writestr("xl/worksheets/sheet1.xml", sheet)
        if shared is not None:
            book.writestr("xl/sharedStrings.xml", shared)
    return buffer.getvalue()


def _worksheet(rows: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>" + rows + "</sheetData></worksheet>"
    )


def test_shared_strings_and_a_numeric_password_return_the_rows():
    shared = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<si><t>账号</t></si><si><t>密码</t></si><si><t>姓名</t></si>"
        "<si><t>s1</t></si><si><t>甲</t></si></sst>"
    )
    sheet = _worksheet(
        '<row r="1">'
        '<c r="A1" t="s"><v>0</v></c>'
        '<c r="B1" t="s"><v>1</v></c>'
        '<c r="C1" t="s"><v>2</v></c>'
        "</row>"
        '<row r="2">'
        '<c r="A2" t="s"><v>3</v></c>'
        '<c r="B2"><v>123456</v></c>'
        '<c r="C2" t="s"><v>4</v></c>'
        "</row>"
        '<row r="3">'
        '<c r="A3" t="s"><v>3</v></c>'
        '<c r="B3"><v>7</v></c>'
        '<c r="C3"></c>'
        "</row>"
        '<row r="4">'
        '<c r="A4" t="s"><v>3</v></c>'
        '<c r="B4"><v>8</v></c>'
        "</row>"
    )

    assert read_student_rows(_package(sheet, shared)) == (
        (2, "s1", "123456", "甲"),
        (3, "s1", "7", ""),
        (4, "s1", "8", None),
    )


def test_a_missing_shared_string_table_or_a_bad_index_cannot_be_read():
    sheet = _worksheet(
        '<row r="1">'
        '<c r="A1" t="s"><v>0</v></c>'
        '<c r="B1" t="s"><v>1</v></c>'
        '<c r="C1" t="s"><v>2</v></c>'
        "</row>"
    )
    shared = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<si><t>账号</t></si><si><t>密码</t></si><si><t>姓名</t></si></sst>"
    )
    bad_index = _worksheet(
        '<row r="1">'
        '<c r="A1" t="s"><v>0</v></c>'
        '<c r="B1" t="s"><v>9</v></c>'
        '<c r="C1" t="s"><v>2</v></c>'
        "</row>"
    )

    with pytest.raises(SheetError, match="不能读取这份表格"):
        read_student_rows(_package(sheet, None))
    with pytest.raises(SheetError, match="不能读取这份表格"):
        read_student_rows(_package(bad_index, shared))
