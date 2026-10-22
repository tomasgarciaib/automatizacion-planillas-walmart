from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


ALLOWED_EXTENSIONS = {".xlsx"}


def validate_excel_file(file: UploadFile) -> None:
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Solo se permiten archivos Excel .xlsx")


async def save_upload(file: UploadFile, destination: Path, *, max_bytes: int) -> str:
    """Guarda un archivo con nombre no predecible y conserva el original en la base."""
    validate_excel_file(file)
    destination.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}.xlsx"
    output_path = destination / stored_name

    bytes_written = 0
    try:
        with output_path.open("wb") as output_file:
            while chunk := await file.read(1024 * 1024):
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    raise ValueError("El archivo supera el tamaño permitido")
                output_file.write(chunk)
    except Exception:
        if output_path.exists():
            output_path.unlink()
        raise
    finally:
        await file.close()
    return stored_name
