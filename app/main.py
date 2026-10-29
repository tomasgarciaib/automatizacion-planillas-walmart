from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote, urlencode
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import get_connection, initialize_database
from app.services.campaigns import (
    VALID_STATUSES,
    create_campaign,
    get_campaign,
    list_campaigns,
    update_status,
)
from app.services.files import save_upload
from app.services.ean import generate_ean13_massive, validate_ean13
from app.services.image_urls import ImageUrlsError, fetch_image_urls
from app.services.source_products import (
    SourceProduct,
    SourceProductsError,
    fetch_products,
    get_product,
)
from app.services.templates import (
    TemplateProcessingError,
    create_clean_template,
    create_filled_product_template,
)
from app.settings import Settings, get_settings


BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

UPLOAD_DOCUMENT_TYPES = {"Fuente", "Plantilla Walmart"}
GENERATED_DOCUMENT_TYPE = "Plantilla limpia"
RIPHOLIA_SKU_MARKER = "-RIP-"
WARRANTY_TEXT = "Garantia del Vendedor"
WARRANTY_CONDITION = (
    "La garantia aplica a productos usados para fines personales, no comerciales. "
    "Cubre fallas de fabricacion durante 6 meses conforme a la legislacion chilena. "
    "No cubre desgaste natural, uso indebido, falta de cuidado, danos accidentales "
    "ni uso comercial."
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    initialize_database(settings.database_path)
    yield


app = FastAPI(
    title="Automatización de planillas Walmart",
    version="0.1.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


def app_settings() -> Settings:
    return get_settings()


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ean-codes")
def generate_ean_codes(number_of_codes: int = 1) -> dict[str, list[str]]:
    if number_of_codes < 1 or number_of_codes > 100:
        raise HTTPException(
            status_code=400,
            detail="number_of_codes debe estar entre 1 y 100",
        )
    return {"codes": generate_ean13_massive(number_of_codes, unique=True)}


@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    q: str = "",
    show_all: bool = False,
    settings: Settings = Depends(app_settings),
):
    """Muestra una sola vez cada SKU Base pendiente de preparación."""
    source_error = None
    products: list[SourceProduct] = []
    try:
        products = fetch_products(settings.source_sheet_csv_url)
    except SourceProductsError as error:
        source_error = str(error)

    query = q.strip().casefold()
    if query:
        products = [
            product
            for product in products
            if query in product.sku_base.casefold()
            or any(query in variant.sku.casefold() for variant in product.variants)
            or query in product.description.casefold()
            or query in product.brand.casefold()
        ]
    elif not show_all:
        products = [product for product in products if not product.responsible.strip()]

    return templates.TemplateResponse(
        request,
        "products.html",
        {
            "products": products,
            "query": q,
            "show_all": show_all,
            "source_error": source_error,
            "source_sheet_url": settings.source_sheet_web_url,
        },
    )


def _sku_base_url(sku_base: str, message: str | None = None) -> str:
    url = f"/sku-base/{quote(sku_base, safe='')}"
    return f"{url}?{urlencode({'message': message})}" if message else url


def _format_price(value: object) -> str:
    return f"${int(value):,}".replace(",", ".")


def _format_walmart_parent_sku(sku_base: str) -> str:
    normalized = sku_base.strip()
    if RIPHOLIA_SKU_MARKER in normalized.upper():
        return normalized
    prefix, separator, suffix = normalized.partition("-")
    if not separator or not prefix or not suffix:
        return normalized
    return f"{prefix}{RIPHOLIA_SKU_MARKER}{suffix}"


def _image_sheet_sku(sku_base: str) -> str:
    parts = sku_base.strip().split("-")
    if len(parts) >= 3 and parts[1].casefold() == "rip":
        return "-".join(parts[2:])
    if len(parts) >= 2 and parts[0].casefold() == "l":
        return "-".join(parts[1:])
    return sku_base.strip()


def _get_source_product(settings: Settings, sku_base: str) -> SourceProduct:
    try:
        return get_product(fetch_products(settings.source_sheet_csv_url), sku_base)
    except SourceProductsError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


def _build_product_rows(
    product: SourceProduct,
    *,
    product_name: str,
    ean_codes: list[str],
    main_image_url: str,
    image_2_url: str,
    image_3_url: str,
    long_description: str,
    short_description: str,
    warranty_text: str,
    warranty_condition: str,
    gender: str,
    color: str,
    material: str,
    features: str,
    keywords: str,
) -> list[dict[str, object]]:
    """Convierte un producto de Drive al mapeo de columnas de Vestuario."""
    rows: list[dict[str, object]] = []
    walmart_parent_sku = _format_walmart_parent_sku(product.sku_base)
    for index, variant in enumerate(product.variants):
        rows.append(
            {
                "D": variant.sku,
                "E": "EAN",
                "F": ean_codes[index],
                "G": product_name,
                "H": product.brand,
                "I": product.price,
                "J": product.height_cm,
                "K": "cm",
                "L": product.width_cm,
                "M": "cm",
                "N": product.depth_cm,
                "O": "cm",
                "P": product.shipping_weight_kg,
                "Q": 1,
                "R": "un",
                "S": "CL - Chile",
                "T": product.brand,
                "U": warranty_text,
                "V": main_image_url,
                "W": image_2_url,
                "X": image_3_url,
                "Y": long_description,
                "Z": short_description,
                "AA": "Nuevo",
                "AB": "Garantia del Vendedor",
                "AC": warranty_condition,
                "AD": 6,
                "AE": gender,
                "AF": color,
                "AG": material,
                "AH": walmart_parent_sku,
                "AI": features,
                "AJ": keywords,
                "AR": variant.size,
                "AS": "Adulto",
                "EY": walmart_parent_sku,
                "EZ": "Color",
                "FA": "Talla de ropa",
                "FB": "Sí" if index == 0 else "No",
            }
        )
    return rows


@app.get("/sku-base/{sku_base}", response_class=HTMLResponse)
def sku_base_detail(
    sku_base: str,
    request: Request,
    message: str | None = None,
    settings: Settings = Depends(app_settings),
):
    product = _get_source_product(settings, sku_base)
    with get_connection(settings.database_path) as connection:
        outputs = connection.execute(
            "SELECT id, original_name, created_at FROM product_outputs "
            "WHERE sku_base = ? ORDER BY id DESC",
            (product.sku_base,),
        ).fetchall()
    return templates.TemplateResponse(
        request,
        "product_detail.html",
        {
            "product": product,
            "walmart_parent_sku": _format_walmart_parent_sku(product.sku_base),
            "image_sheet_sku": _image_sheet_sku(product.sku_base),
            "template_ready": settings.vestuario_template_path.is_file(),
            "template_name": settings.vestuario_template_path.name,
            "outputs": outputs,
            "message": message,
            "price_display": _format_price(product.price),
            "source_sheet_url": settings.source_sheet_web_url,
        },
    )


@app.get("/sku-ml/{sku_ml}")
def legacy_sku_ml_link(sku_ml: str, settings: Settings = Depends(app_settings)):
    """Mantiene los enlaces anteriores y redirige al SKU Base correspondiente."""
    try:
        products = fetch_products(settings.source_sheet_csv_url)
        product = next(
            item
            for item in products
            if any(variant.sku.casefold() == sku_ml.casefold() for variant in item.variants)
        )
    except (SourceProductsError, StopIteration) as error:
        raise HTTPException(status_code=404, detail="No se encontró el producto") from error
    return RedirectResponse(_sku_base_url(product.sku_base), status_code=303)


@app.post("/sku-base/{sku_base}/generate")
def generate_product_template(
    sku_base: str,
    product_name: str = Form(...),
    image_sheet_sku: str = Form(...),
    number_of_codes: int = Form(...),
    ean_codes: str = Form(...),
    long_description: str = Form(...),
    short_description: str = Form(...),
    gender: str = Form(...),
    color: str = Form(...),
    material: str = Form(...),
    features: str = Form(...),
    keywords: str = Form(...),
    settings: Settings = Depends(app_settings),
):
    product = _get_source_product(settings, sku_base)
    warranty_text = WARRANTY_TEXT
    warranty_condition = WARRANTY_CONDITION
    try:
        image_urls = fetch_image_urls(settings.image_sheet_csv_url, image_sheet_sku)
    except ImageUrlsError as error:
        return RedirectResponse(_sku_base_url(sku_base, str(error)), status_code=303)
    entered_values = {
        "Nombre del producto": product_name,
        "Descripción larga": long_description,
        "Descripción corta": short_description,
        "Texto de garantía": warranty_text,
        "Condiciones de garantía": warranty_condition,
        "Género": gender,
        "Color": color,
        "Material": material,
        "Características": features,
        "Palabras clave": keywords,
    }
    missing = [label for label, value in entered_values.items() if not value.strip()]
    if missing:
        return RedirectResponse(
            _sku_base_url(sku_base, f"Falta completar: {', '.join(missing)}."),
            status_code=303,
        )

    codes = [line.strip() for line in ean_codes.splitlines() if line.strip()]
    if number_of_codes != len(product.variants):
        return RedirectResponse(
            _sku_base_url(
                sku_base,
                f"La cantidad de EAN se calcula automaticamente: este SKU padre tiene {len(product.variants)} SKU hijos.",
            ),
            status_code=303,
        )
    if number_of_codes != len(codes):
        return RedirectResponse(
            _sku_base_url(
                sku_base,
                f"number_of_codes indica {number_of_codes}, pero se recibieron {len(codes)} codigos.",
            ),
            status_code=303,
        )
    if len(codes) != len(product.variants):
        return RedirectResponse(
            _sku_base_url(
                sku_base,
                f"Debes pegar {len(product.variants)} códigos EAN, uno por cada variante.",
            ),
            status_code=303,
        )
    if len(set(codes)) != len(codes) or any(not validate_ean13(code) for code in codes):
        return RedirectResponse(
            _sku_base_url(sku_base, "Los EAN deben ser códigos numéricos únicos de 8 a 14 dígitos."),
            status_code=303,
        )
    image_url_values = (image_urls.main, image_urls.secondary, image_urls.secondary_1)
    if any(not value.lower().startswith(("https://", "http://")) for value in image_url_values):
        return RedirectResponse(
            _sku_base_url(sku_base, "Las tres imágenes deben tener una URL que comience con http:// o https://."),
            status_code=303,
        )

    source_path = settings.vestuario_template_path
    if not source_path.is_file():
        return RedirectResponse(
            _sku_base_url(sku_base, "No se encontró la plantilla fija de Vestuario."),
            status_code=303,
        )

    display_name = f"{product.sku_base}.xlsx"
    stored_name = f"{uuid4().hex}.xlsx"
    output_path = settings.uploads_dir / stored_name
    try:
        create_filled_product_template(
            source_path,
            output_path,
            rows=_build_product_rows(
                product,
                product_name=product_name.strip(),
                ean_codes=codes,
                main_image_url=image_urls.main,
                image_2_url=image_urls.secondary,
                image_3_url=image_urls.secondary_1,
                long_description=long_description.strip(),
                short_description=short_description.strip(),
                warranty_text=warranty_text.strip(),
                warranty_condition=warranty_condition.strip(),
                gender=gender.strip(),
                color=color.strip(),
                material=material.strip(),
                features=features.strip(),
                keywords=keywords.strip(),
            ),
        )
    except TemplateProcessingError as error:
        return RedirectResponse(_sku_base_url(sku_base, str(error)), status_code=303)

    with get_connection(settings.database_path) as connection:
        connection.execute(
            "INSERT INTO product_outputs (sku_base, original_name, stored_name) VALUES (?, ?, ?)",
            (product.sku_base, display_name, stored_name),
        )
        connection.commit()
    return RedirectResponse(
        _sku_base_url(sku_base, "Planilla completada y lista para descargar."),
        status_code=303,
    )


@app.get("/configuracion/plantilla", response_class=HTMLResponse)
def template_settings(
    request: Request,
    message: str | None = None,
    settings: Settings = Depends(app_settings),
):
    return templates.TemplateResponse(
        request,
        "template_settings.html",
        {
            "template_ready": settings.vestuario_template_path.is_file(),
            "template_name": settings.vestuario_template_path.name,
            "message": message,
        },
    )


@app.get("/product-outputs/{output_id}/download")
def download_product_output(output_id: int, settings: Settings = Depends(app_settings)):
    with get_connection(settings.database_path) as connection:
        output = connection.execute(
            "SELECT original_name, stored_name FROM product_outputs WHERE id = ?", (output_id,)
        ).fetchone()
    if output is None:
        raise HTTPException(status_code=404, detail="No se encontró la planilla")
    file_path = settings.uploads_dir / Path(output["stored_name"]).name
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="El archivo ya no está disponible")
    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=output["original_name"],
    )


@app.post("/campaigns")
def add_campaign(
    name: str = Form(...),
    brand: str = Form(...),
    discount: str = Form(...),
    settings: Settings = Depends(app_settings),
):
    if not all(value.strip() for value in (name, brand, discount)):
        raise HTTPException(status_code=400, detail="Completa todos los campos de la campaña")
    with get_connection(settings.database_path) as connection:
        campaign = create_campaign(
            connection, name=name, brand=brand, discount=discount
        )
    return RedirectResponse(url=f"/campaigns/{campaign.id}", status_code=303)


@app.get("/campaigns/{campaign_id}", response_class=HTMLResponse)
def campaign_detail(
    campaign_id: int, request: Request, settings: Settings = Depends(app_settings)
):
    with get_connection(settings.database_path) as connection:
        try:
            campaign = get_campaign(connection, campaign_id)
            documents = connection.execute(
                "SELECT id, document_type, original_name, stored_name, uploaded_at "
                "FROM documents WHERE campaign_id = ? ORDER BY id DESC",
                (campaign_id,),
            ).fetchall()
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
    return templates.TemplateResponse(
        request,
        "campaign.html",
        {
            "campaign": campaign,
            "documents": documents,
            "has_walmart_template": any(
                document["document_type"] == "Plantilla Walmart"
                for document in documents
            ),
            "statuses": VALID_STATUSES,
        },
    )


@app.post("/campaigns/{campaign_id}/documents")
async def upload_document(
    campaign_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    settings: Settings = Depends(app_settings),
):
    if document_type not in UPLOAD_DOCUMENT_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de documento no válido")
    with get_connection(settings.database_path) as connection:
        try:
            get_campaign(connection, campaign_id)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

        try:
            stored_name = await save_upload(
                file,
                settings.uploads_dir,
                max_bytes=settings.max_upload_mb * 1024 * 1024,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        connection.execute(
            "INSERT INTO documents (campaign_id, document_type, original_name, stored_name) "
            "VALUES (?, ?, ?, ?)",
            (campaign_id, document_type, file.filename or "sin_nombre.xlsx", stored_name),
        )
        connection.commit()
    return RedirectResponse(url=f"/campaigns/{campaign_id}", status_code=303)


@app.post("/campaigns/{campaign_id}/clean-template")
def create_clean_campaign_template(
    campaign_id: int, settings: Settings = Depends(app_settings)
):
    """Genera una copia de la última plantilla Walmart sin filas de productos."""
    with get_connection(settings.database_path) as connection:
        try:
            get_campaign(connection, campaign_id)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

        template = connection.execute(
            "SELECT original_name, stored_name FROM documents "
            "WHERE campaign_id = ? AND document_type = ? "
            "ORDER BY id DESC LIMIT 1",
            (campaign_id, "Plantilla Walmart"),
        ).fetchone()
        if template is None:
            raise HTTPException(status_code=400, detail="Primero adjunta una plantilla Walmart")

        source_path = settings.uploads_dir / Path(template["stored_name"]).name
        original_stem = Path(template["original_name"]).stem
        display_name = f"{original_stem}-plantilla-limpia.xlsx"
        stored_name = f"{uuid4().hex}.xlsx"
        output_path = settings.uploads_dir / stored_name

        try:
            create_clean_template(source_path, output_path)
        except TemplateProcessingError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        connection.execute(
            "INSERT INTO documents (campaign_id, document_type, original_name, stored_name) "
            "VALUES (?, ?, ?, ?)",
            (campaign_id, GENERATED_DOCUMENT_TYPE, display_name, stored_name),
        )
        connection.commit()
    return RedirectResponse(url=f"/campaigns/{campaign_id}", status_code=303)


@app.get("/documents/{document_id}/download")
def download_document(document_id: int, settings: Settings = Depends(app_settings)):
    with get_connection(settings.database_path) as connection:
        document = connection.execute(
            "SELECT original_name, stored_name FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
    if document is None:
        raise HTTPException(status_code=404, detail="No se encontró el documento")

    file_path = settings.uploads_dir / Path(document["stored_name"]).name
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="El archivo ya no está disponible")
    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=document["original_name"],
    )


@app.post("/campaigns/{campaign_id}/status")
def change_campaign_status(
    campaign_id: int,
    status: str = Form(...),
    settings: Settings = Depends(app_settings),
):
    with get_connection(settings.database_path) as connection:
        try:
            update_status(connection, campaign_id=campaign_id, status=status)
        except (LookupError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
    return RedirectResponse(url=f"/campaigns/{campaign_id}", status_code=303)
