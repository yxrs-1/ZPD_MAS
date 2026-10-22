import io
import zipfile

import pytest

from scaffolding.sheet import SheetError, read_student_rows


def _xlsx(rows: tuple[tuple[str, ...], ...]) -> bytes:
    sheet_rows = []
    for index, values in enumerate(rows, start=1):
        cells = []
        for column, value in enumerate(values):
            ref = chr(ord("A") + column) + str(index)
            cells.append(
                '<c r="' + ref + '" t="inlineStr"><is><t>' + value + "</t></is></c>"
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
