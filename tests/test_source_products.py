from decimal import Decimal

from app.services.source_products import _group_products


def _source_row(
    *,
    responsible: str,
    drive_status: str,
    sku_base: str,
    sku: str,
    description: str,
    brand: str,
    size: str,
) -> list[str]:
    row = [""] * 32
    row[0] = responsible
    row[1] = drive_status
    row[5] = sku_base
    row[6] = sku
    row[7] = description
    row[8] = brand
    row[9] = size
    row[13] = "4"
    row[14] = "23"
    row[15] = "30"
    row[16] = "0,296"
    row[31] = "31.790"
    return row


def test_groups_variants_and_reads_chilean_numbers():
    products = _group_products(
        [
            _source_row(
                responsible="Tomas",
                drive_status="",
                sku_base="L-569-14",
                sku="L-RIP-569-14-XS",
                description="Pantalón Jogger clínico PRIVE. - Verde Esmeralda",
                brand="Ripholia",
                size="Xs",
            ),
            _source_row(
                responsible="Tomas",
                drive_status="",
                sku_base="L-569-14",
                sku="L-RIP-569-14-S",
                description="Pantalón Jogger clínico PRIVE. - Verde Esmeralda",
                brand="Ripholia",
                size="S",
            ),
        ]
    )

    assert len(products) == 1
    product = products[0]
    assert product.price == Decimal("31790")
    assert product.height_cm == Decimal("4")
    assert product.shipping_weight_kg == Decimal("0.296")
    assert product.suggested_color == "Verde Esmeralda"
    assert [variant.size for variant in product.variants] == ["Xs", "S"]
