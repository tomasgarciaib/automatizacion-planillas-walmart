import asyncio
import io
from pathlib import Path

import pytest
from starlette.datastructures import UploadFile

from app.services.files import save_upload


def test_rejects_file_over_configured_limit(tmp_path: Path):
    upload = UploadFile(filename="demasiado_grande.xlsx", file=io.BytesIO(b"12345"))

    with pytest.raises(ValueError, match="supera el tamaño"):
        asyncio.run(save_upload(upload, tmp_path, max_bytes=4))

    assert list(tmp_path.iterdir()) == []
