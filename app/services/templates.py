"""Operaciones seguras para plantillas XLSX entregadas por Walmart.

Las plantillas contienen hojas y validaciones internas que no se deben
reconstruir. Esta implementación modifica solo el XML de la hoja de datos
dentro del archivo XLSX original y copia intactos los demás archivos.
"""

from __future__ import annotations

import os
import posixpath
import zipfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree as ET


SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOCUMENT_RELATIONSHIP_NS = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)
PACKAGE_RELATIONSHIP_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


class TemplateProcessingError(ValueError):
    """La plantilla no tiene la estructura esperada para esta operación."""


@dataclass(frozen=True)
class CleanTemplateResult:
    output_path: Path
    cleared_cells: int


def _sheet_xml_path(workbook: zipfile.ZipFile, sheet_name: str) -> str:
    try:
        workbook_xml = ET.fromstring(workbook.read("xl/workbook.xml"))
        relationships_xml = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    except KeyError as error:
        raise TemplateProcessingError("El archivo no tiene la estructura de un Excel válido") from error
    except ET.ParseError as error:
        raise TemplateProcessingError("No se pudo leer la estructura interna del Excel") from error

    relationship_id = None
    for sheet in workbook_xml.findall(f".//{{{SPREADSHEET_NS}}}sheet"):
        if sheet.get("name") == sheet_name:
            relationship_id = sheet.get(f"{{{DOCUMENT_RELATIONSHIP_NS}}}id")
            break

    if not relationship_id:
        raise TemplateProcessingError(
            f"No se encontró la hoja requerida '{sheet_name}' en esta plantilla"
        )

    for relationship in relationships_xml.findall(
        f"{{{PACKAGE_RELATIONSHIP_NS}}}Relationship"
    ):
        if relationship.get("Id") == relationship_id:
            target = relationship.get("Target")
            if target:
                return posixpath.normpath(posixpath.join("xl", target)).lstrip("/")

    raise TemplateProcessingError(
        f"No se encontró el archivo interno de la hoja '{sheet_name}'"
    )


def _clear_sheet_values(sheet_xml: bytes, *, data_start_row: int) -> tuple[bytes, int]:
    try:
        root = ET.fromstring(sheet_xml)
    except ET.ParseError as error:
        raise TemplateProcessingError("No se pudo leer la hoja de productos") from error

    cleared_cells = 0
    value_tags = {
        f"{{{SPREADSHEET_NS}}}v",
        f"{{{SPREADSHEET_NS}}}f",
        f"{{{SPREADSHEET_NS}}}is",
    }

    for row in root.findall(f".//{{{SPREADSHEET_NS}}}sheetData/{{{SPREADSHEET_NS}}}row"):
        try:
            row_number = int(row.get("r", "0"))
        except ValueError:
            continue
        if row_number < data_start_row:
            continue

        for cell in row.findall(f"{{{SPREADSHEET_NS}}}c"):
            children_to_remove = [child for child in cell if child.tag in value_tags]
            if children_to_remove:
                for child in children_to_remove:
                    cell.remove(child)
                cleared_cells += 1

    return ET.tostring(root, encoding="utf-8", xml_declaration=True), cleared_cells


def create_clean_template(
    source_path: Path,
    output_path: Path,
    *,
    sheet_name: str = "Vestuario",
    data_start_row: int = 10,
) -> CleanTemplateResult:
    """Crea una copia sin productos y conserva la estructura original del XLSX."""
    source_path = source_path.resolve()
    output_path = output_path.resolve()

    if source_path == output_path:
        raise TemplateProcessingError("La copia limpia debe tener un nombre diferente")
    if not source_path.is_file():
        raise TemplateProcessingError("No se encontró el archivo de plantilla cargado")
    if source_path.suffix.lower() != ".xlsx":
        raise TemplateProcessingError("La plantilla debe ser un archivo .xlsx")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(f".{uuid4().hex}.tmp")

    try:
        with zipfile.ZipFile(source_path, "r") as source_book:
            target_sheet_path = _sheet_xml_path(source_book, sheet_name)
            if target_sheet_path not in source_book.namelist():
                raise TemplateProcessingError("No se encontró el contenido de la hoja de productos")

            with zipfile.ZipFile(temporary_path, "w") as clean_book:
                cleared_cells = 0
                for file_info in source_book.infolist():
                    content = source_book.read(file_info.filename)
                    if file_info.filename == target_sheet_path:
                        content, cleared_cells = _clear_sheet_values(
                            content, data_start_row=data_start_row
                        )
                    clean_book.writestr(file_info, content)

        os.replace(temporary_path, output_path)
    except zipfile.BadZipFile as error:
        raise TemplateProcessingError("El archivo cargado no es un Excel .xlsx válido") from error
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    return CleanTemplateResult(output_path=output_path, cleared_cells=cleared_cells)
