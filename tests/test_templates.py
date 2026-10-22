import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from app.services.templates import create_clean_template


SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def _write_minimal_walmart_workbook(path: Path) -> None:
    workbook_xml = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">
  <sheets>
    <sheet name=\"Hidden_clothing_other\" sheetId=\"1\" state=\"hidden\" r:id=\"rId1\"/>
    <sheet name=\"Vestuario\" sheetId=\"2\" r:id=\"rId2\"/>
  </sheets>
</workbook>"""
    relationships_xml = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">
  <Relationship Id=\"rId1\" Target=\"worksheets/sheet1.xml\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\"/>
  <Relationship Id=\"rId2\" Target=\"worksheets/sheet2.xml\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\"/>
</Relationships>"""
    hidden_sheet = """<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><sheetData><row r=\"1\"><c r=\"A1\"><v>9</v></c></row></sheetData></worksheet>"""
    clothing_sheet = """<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><sheetData>
  <row r=\"9\"><c r=\"D9\" t=\"inlineStr\"><is><t>SKU</t></is></c></row>
  <row r=\"10\"><c r=\"D10\" t=\"inlineStr\"><is><t>RIP-2451-XS</t></is></c><c r=\"E10\"><v>26390</v></c></row>
  <row r=\"11\"><c r=\"D11\" t=\"inlineStr\"><is><t>RIP-2451-S</t></is></c></row>
</sheetData><extLst><ext uri=\"{validation-preserved}\"><sample>keep</sample></ext></extLst></worksheet>"""
    with zipfile.ZipFile(path, "w") as workbook:
        workbook.writestr("xl/workbook.xml", workbook_xml)
        workbook.writestr("xl/_rels/workbook.xml.rels", relationships_xml)
        workbook.writestr("xl/worksheets/sheet1.xml", hidden_sheet)
        workbook.writestr("xl/worksheets/sheet2.xml", clothing_sheet)


def _cell_contents(sheet_xml: bytes, reference: str) -> list[str]:
    root = ET.fromstring(sheet_xml)
    cell = root.find(f".//{{{SPREADSHEET_NS}}}c[@r='{reference}']")
    if cell is None:
        return []
    return [child.tag for child in cell]


def test_clean_template_clears_product_rows_and_preserves_other_parts(tmp_path: Path):
    source = tmp_path / "source.xlsx"
    output = tmp_path / "clean.xlsx"
    _write_minimal_walmart_workbook(source)

    result = create_clean_template(source, output)

    assert result.cleared_cells == 3
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(output) as cleaned:
        assert original.read("xl/workbook.xml") == cleaned.read("xl/workbook.xml")
        assert original.read("xl/worksheets/sheet1.xml") == cleaned.read(
            "xl/worksheets/sheet1.xml"
        )
        clean_sheet = cleaned.read("xl/worksheets/sheet2.xml")

    assert _cell_contents(clean_sheet, "D9")
    assert _cell_contents(clean_sheet, "D10") == []
    assert _cell_contents(clean_sheet, "E10") == []
    assert _cell_contents(clean_sheet, "D11") == []
    assert b"validation-preserved" in clean_sheet
