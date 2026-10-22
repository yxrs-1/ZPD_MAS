import zipfile
from xml.etree import ElementTree

_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_OFFICE = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


class SheetError(Exception):
    pass


def read_student_rows(data: bytes) -> tuple[tuple[int, str, str, str], ...]:
    try:
        with zipfile.ZipFile(__import__("io").BytesIO(data)) as book:
            workbook = ElementTree.fromstring(book.read("xl/workbook.xml"))
            rels = ElementTree.fromstring(book.read("xl/_rels/workbook.xml.rels"))
            sheet = workbook.find(_MAIN + "sheets").find(_MAIN + "sheet")
            relation_id = sheet.attrib[_OFFICE + "id"]
            target = ""
            for item in rels:
                if item.attrib.get("Id") == relation_id:
                    target = "xl/" + item.attrib["Target"].lstrip("/")
            worksheet = ElementTree.fromstring(book.read(target))
    except Exception as error:
        raise SheetError("不能读取这份表格") from error
    rows = _rows(worksheet)
    if not rows or rows[0][1:4] != ("账号", "密码", "姓名"):
        raise SheetError("表头必须是账号、密码、姓名")
    kept = []
    for number, account, password, name in rows[1:]:
        if all(item in ("", None) for item in (account, password, name)):
            continue
        kept.append((number, account, password, name))
    return tuple(kept)


def _rows(worksheet) -> list[tuple[int, str, str, str]]:
    found = []
    for row in worksheet.find(_MAIN + "sheetData"):
        number = int(row.attrib.get("r", "0"))
        values = {0: None, 1: None, 2: None}
        for cell in row:
            ref = cell.attrib.get("r", "A")
            column = ord(ref[0]) - ord("A")
            if column in values:
                values[column] = _text(cell)
        found.append((number, values[0], values[1], values[2]))
    return found


def _text(cell) -> str:
    inline = cell.find(_MAIN + "is")
    if inline is None:
        return ""
    node = inline.find(_MAIN + "t")
    if node is None or node.text is None:
        return ""
    return node.text
