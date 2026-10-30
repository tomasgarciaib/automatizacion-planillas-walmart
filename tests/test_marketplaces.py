from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app, app_settings
from app.services.source_products import ProductVariant, SourceProduct
from app.settings import Settings


def _product_without_responsible() -> SourceProduct:
    return SourceProduct(
        sku_base="L-569-14",
        description="Pantalón Jogger clínico PRIVE.",
        brand="Ripholia",
        responsible="",
        drive_status="",
        price=Decimal("31790"),
        height_cm=Decimal("4"),
        width_cm=Decimal("23"),
        depth_cm=Decimal("30"),
        shipping_weight_kg=Decimal("0.296"),
        variants=(ProductVariant("L-RIP-569-14-XS", "XS"),),
    )


def test_home_shows_marketplace_buttons():
    client = TestClient(app)
    try:
        response = client.get("/")
        assert response.status_code == 200
        for marketplace in ("Walmart", "Falabella", "Sencosud", "Mercado Libre"):
            assert marketplace in response.text
        assert 'href="/walmart"' in response.text
    finally:
        client.close()


def test_walmart_shows_unassigned_skus(monkeypatch, tmp_path):
    settings = Settings(data_dir=tmp_path / "data")
    monkeypatch.setattr("app.main.fetch_products", lambda _url: [_product_without_responsible()])
    app.dependency_overrides[app_settings] = lambda: settings
    client = TestClient(app)
    try:
        response = client.get("/walmart")
        assert response.status_code == 200
        assert "L-RIP-569-14-XS" in response.text
        assert "Sin asignar" in response.text
    finally:
        client.close()
        app.dependency_overrides.clear()
