"""Lectura de URLs de imágenes desde la hoja compartida de productos."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from urllib.request import Request, urlopen


class ImageUrlsError(RuntimeError):
    """No fue posible obtener las URLs de imágenes para un SKU padre."""


@dataclass(frozen=True)
class ProductImageUrls:
    sku_parent: str
    main: str
    secondary: str
    secondary_1: str


def _normalize_header(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _find_column(fieldnames: list[str], expected: str) -> str:
    normalized_expected = _normalize_header(expected)
    for fieldname in fieldnames:
        if _normalize_header(fieldname) == normalized_expected:
            return fieldname
    raise ImageUrlsError(f"La hoja de imágenes no contiene la columna '{expected}'")


def fetch_image_urls(csv_url: str, sku_parent: str) -> ProductImageUrls:
    """Busca las tres URLs de imagen por el SKU padre numérico."""
    normalized_sku = sku_parent.strip().casefold()
    if not normalized_sku:
        raise ImageUrlsError("Ingresa el SKU padre numérico para buscar las imágenes")

    try:
        request = Request(csv_url, headers={"User-Agent": "PlanillasWalmart/0.3"})
        with urlopen(request, timeout=20) as response:  # noqa: S310 - URL configurada
            csv_content = response.read().decode("utf-8-sig")
    except OSError as error:
        raise ImageUrlsError(
            "No se pudo leer la hoja de imágenes. Intenta nuevamente."
        ) from error

    reader = csv.DictReader(io.StringIO(csv_content))
    fieldnames = reader.fieldnames or []
    sku_column = _find_column(fieldnames, "SKU")
    main_column = _find_column(fieldnames, "URL JPG 1")
    secondary_column = _find_column(fieldnames, "URL JPG 2")
    secondary_1_column = _find_column(fieldnames, "URL JPG 3")

    for row in reader:
        row_sku = (row.get(sku_column) or "").strip()
        if row_sku.casefold() != normalized_sku:
            continue

        urls = ProductImageUrls(
            sku_parent=row_sku,
            main=(row.get(main_column) or "").strip(),
            secondary=(row.get(secondary_column) or "").strip(),
            secondary_1=(row.get(secondary_1_column) or "").strip(),
        )
        missing = [
            label
            for label, value in (
                ("URL JPG 1", urls.main),
                ("URL JPG 2", urls.secondary),
                ("URL JPG 3", urls.secondary_1),
            )
            if not value
        ]
        if missing:
            raise ImageUrlsError(
                f"El SKU padre {row_sku} no tiene completa la información: {', '.join(missing)}."
            )
        return urls

    raise ImageUrlsError(
        f"No se encontró el SKU padre {sku_parent.strip()} en la hoja de imágenes"
    )
