"""Lectura de productos desde la hoja de trabajo compartida en Google Sheets."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable
from urllib.request import Request, urlopen


class SourceProductsError(RuntimeError):
    """No fue posible obtener o interpretar la hoja fuente."""


@dataclass(frozen=True)
class ProductVariant:
    sku: str
    size: str


@dataclass(frozen=True)
class SourceProduct:
    sku_base: str
    description: str
    brand: str
    responsible: str
    drive_status: str
    price: Decimal
    height_cm: Decimal
    width_cm: Decimal
    depth_cm: Decimal
    shipping_weight_kg: Decimal
    variants: tuple[ProductVariant, ...]

    @property
    def suggested_color(self) -> str:
        """La hoja actual incluye el color al final de la descripción."""
        if " - " not in self.description:
            return ""
        return self.description.rsplit(" - ", maxsplit=1)[-1].strip()


# Posiciones de la hoja de Ripholia compartida por el equipo. La hoja tiene
# títulos agrupados y algunas celdas de encabezado combinadas, por eso estos
# campos no se deducen de los encabezados vacíos del CSV.
RESPONSIBLE = 0
DRIVE_STATUS = 1
SKU_BASE = 5
SKU = 6
DESCRIPTION = 7
BRAND = 8
SIZE = 9
HEIGHT = 13
WIDTH = 14
DEPTH = 15
SHIPPING_WEIGHT = 16
FINAL_PRICE = 31


def _value(row: list[str], position: int) -> str:
    return row[position].strip() if position < len(row) else ""


def _parse_number(value: str, field_name: str) -> Decimal:
    normalized = value.strip().replace("$", "").replace(" ", "")
    if not normalized:
        raise SourceProductsError(f"Falta {field_name} en la hoja fuente")
    if "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif normalized.count(".") == 1 and len(normalized.rsplit(".", 1)[1]) == 3:
        normalized = normalized.replace(".", "")
    try:
        return Decimal(normalized)
    except InvalidOperation as error:
        raise SourceProductsError(
            f"El valor de {field_name} no es numérico: {value}"
        ) from error


def _group_products(rows: Iterable[list[str]]) -> list[SourceProduct]:
    grouped: dict[str, list[list[str]]] = {}
    for row in rows:
        sku_base = _value(row, SKU_BASE)
        sku = _value(row, SKU)
        if not sku_base or not sku:
            continue
        grouped.setdefault(sku_base, []).append(row)

    products: list[SourceProduct] = []
    for sku_base, product_rows in grouped.items():
        complete_rows = [
            row
            for row in product_rows
            if all(
                _value(row, position)
                for position in (SKU, DESCRIPTION, BRAND, SIZE, HEIGHT, WIDTH, DEPTH, SHIPPING_WEIGHT, FINAL_PRICE)
            )
        ]
        if not complete_rows:
            continue

        first = complete_rows[0]
        variants = tuple(
            ProductVariant(sku=_value(row, SKU), size=_value(row, SIZE))
            for row in complete_rows
        )
        products.append(
            SourceProduct(
                sku_base=sku_base,
                description=_value(first, DESCRIPTION),
                brand=_value(first, BRAND),
                responsible=_value(first, RESPONSIBLE),
                drive_status=_value(first, DRIVE_STATUS),
                price=_parse_number(_value(first, FINAL_PRICE), "precio final redondeo"),
                height_cm=_parse_number(_value(first, HEIGHT), "alto"),
                width_cm=_parse_number(_value(first, WIDTH), "ancho"),
                depth_cm=_parse_number(_value(first, DEPTH), "profundidad"),
                shipping_weight_kg=_parse_number(
                    _value(first, SHIPPING_WEIGHT), "peso de envío"
                ),
                variants=variants,
            )
        )
    return sorted(products, key=lambda product: product.sku_base)


def fetch_products(csv_url: str) -> list[SourceProduct]:
    """Obtiene los productos vigentes desde la exportación CSV de Google Sheets."""
    try:
        request = Request(csv_url, headers={"User-Agent": "PlanillasWalmart/0.2"})
        with urlopen(request, timeout=20) as response:  # noqa: S310 - URL configurada
            csv_content = response.read().decode("utf-8-sig")
    except OSError as error:
        raise SourceProductsError(
            "No se pudo leer la hoja de productos de Drive. Intenta nuevamente."
        ) from error

    rows = list(csv.reader(io.StringIO(csv_content)))
    if len(rows) < 3:
        raise SourceProductsError("La hoja fuente no contiene filas de productos")
    return _group_products(rows[2:])


def get_product(products: Iterable[SourceProduct], sku_base: str) -> SourceProduct:
    for product in products:
        if product.sku_base.casefold() == sku_base.casefold():
            return product
    raise SourceProductsError(f"No se encontró el producto {sku_base} en la hoja fuente")
