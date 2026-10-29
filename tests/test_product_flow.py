import zipfile
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from app.database import get_connection, initialize_database
from app.main import app, app_settings
from app.services.source_products import ProductVariant, SourceProduct
from app.settings import Settings


def _write_template(path: Path) -> None:
    workbook_xml = """<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"><sheets><sheet name=\"Hidden_clothing_other\" sheetId=\"1\" state=\"hidden\" r:id=\"rId1\"/><sheet name=\"Vestuario\" sheetId=\"2\" r:id=\"rId2\"/></sheets></workbook>"""
    relationships_xml = """<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Target=\"worksheets/sheet1.xml\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\"/><Relationship Id=\"rId2\" Target=\"worksheets/sheet2.xml\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\"/></Relationships>"""
    hidden_sheet = """<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><sheetData/></worksheet>"""
    product_sheet = """<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><sheetData><row r=\"9\"><c r=\"D9\" t=\"inlineStr\"><is><t>SKU</t></is></c></row></sheetData></worksheet>"""
    with zipfile.ZipFile(path, "w") as workbook:
        workbook.writestr("xl/workbook.xml", workbook_xml)
        workbook.writestr("xl/_rels/workbook.xml.rels", relationships_xml)
        workbook.writestr("xl/worksheets/sheet1.xml", hidden_sheet)
        workbook.writestr("xl/worksheets/sheet2.xml", product_sheet)


def _product() -> SourceProduct:
    return SourceProduct(
        sku_base="L-569-14",
        description="Pantalón Jogger clínico PRIVE. - Verde Esmeralda",
        brand="Ripholia",
        responsible="Tomas",
        drive_status="",
        price=Decimal("31790"),
        height_cm=Decimal("4"),
        width_cm=Decimal("23"),
        depth_cm=Decimal("30"),
        shipping_weight_kg=Decimal("0.296"),
        variants=(
            ProductVariant("L-RIP-569-14-XS", "XS"),
            ProductVariant("L-RIP-569-14-S", "S"),
        ),
    )


def test_product_flow_creates_downloadable_walmart_file(tmp_path: Path, monkeypatch):
    source_template = tmp_path / "vestuario.xlsx"
    _write_template(source_template)
    settings = Settings(
        data_dir=tmp_path / "data",
        vestuario_template_path=source_template,
    )
    initialize_database(settings.database_path)
    product = _product()
    monkeypatch.setattr("app.main.fetch_products", lambda _url: [product])
    app.dependency_overrides[app_settings] = lambda: settings
    client = TestClient(app)
    try:
        detail = client.get("/sku-base/L-569-14")
        assert detail.status_code == 200
        assert "Pantalón Jogger" in detail.text

        generated = client.post(
            "/sku-base/L-569-14/generate",
            data={
                "ean_codes": "7801234567890\n7801234567891",
                "main_image_url": "https://example.com/imagen-1.jpg",
                "image_2_url": "https://example.com/imagen-2.jpg",
                "image_3_url": "https://example.com/imagen-3.jpg",
                "long_description": "Descripción larga de prueba.",
                "short_description": "Descripción corta.",
                "warranty_text": "Garantía del vendedor.",
                "warranty_condition": "Condiciones de garantía de prueba.",
                "gender": "Mujer",
                "color": "Verde Esmeralda",
                "material": "Poliéster.",
                "features": "Uso clínico.",
                "keywords": "pantalón, clínico",
            },
            follow_redirects=False,
        )
        assert generated.status_code == 303

        with get_connection(settings.database_path) as connection:
            output = connection.execute("SELECT id FROM product_outputs").fetchone()
        assert output is not None
        download = client.get(f"/product-outputs/{output['id']}/download")
        assert download.status_code == 200
        assert download.content[:2] == b"PK"
    finally:
        client.close()
        app.dependency_overrides.clear()
