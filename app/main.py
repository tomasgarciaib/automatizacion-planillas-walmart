from contextlib import asynccontextmanager
from pathlib import Path
import re
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
EAN_PATTERN = re.compile(r"^\d{8,14}$")


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


@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    q: str = "",
    settings: Settings = Depends(app_settings),
):
    """Muestra los productos que el equipo debe trabajar desde la hoja de Drive."""
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
            or query in product.description.casefold()
            or query in product.brand.casefold()
        ]

    return templates.TemplateResponse(
        request,
        "products.html",
        {
            "products": products,
            "query": q,
            "source_error": source_error,
            "source_sheet_url": settings.source_sheet_web_url,
        },
    )


def _product_url(sku_base: str, message: str | None = None) -> str:
    url = f"/products/{quote(sku_base, safe='')}"
    return f"{url}?{urlencode({'message': message})}" if message else url


def _format_price(value: object) -> str:
    return f"${int(value):,}".replace(",", ".")


def _get_source_product(settings: Settings, sku_base: str) -> SourceProduct:
    try:
        return get_product(fetch_products(settings.source_sheet_csv_url), sku_base)
    except SourceProductsError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


def _build_product_rows(
    product: SourceProduct,
    *,
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
    for index, variant in enumerate(product.variants):
        rows.append(
            {
                "D": variant.sku,
                "E": "EAN",
                "F": ean_codes[index],
                "G": product.description,
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
                "AH": product.sku_base,
                "AI": features,
                "AJ": keywords,
                "AR": variant.size,
                "AS": "Adulto",
                "EY": product.sku_base,
                "EZ": "Color",
                "FA": "Talla de ropa",
                "FB": "Sí" if index == 0 else "No",
            }
        )
    return rows


@app.get("/products/{sku_base}", response_class=HTMLResponse)
def product_detail(
    sku_base: str,
    request: Request,
    message: str | None = None,
    settings: Settings = Depends(app_settings),
):
    product = _get_source_product(settings, sku_base)
    with get_connection(settings.database_path) as connection:
        template = connection.execute(
            "SELECT id, original_name, stored_name, uploaded_at "
            "FROM walmart_templates WHERE category = 'Vestuario' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if template and not (settings.uploads_dir / Path(template["stored_name"]).name).is_file():
            template = None
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
            "template": template,
            "outputs": outputs,
            "message": message,
            "price_display": _format_price(product.price),
            "source_sheet_url": settings.source_sheet_web_url,
        },
    )


@app.post("/walmart-templates")
async def upload_walmart_template(
    return_sku: str = Form(...),
    file: UploadFile = File(...),
    settings: Settings = Depends(app_settings),
):
    try:
        stored_name = await save_upload(
            file,
            settings.uploads_dir,
            max_bytes=settings.max_upload_mb * 1024 * 1024,
        )
    except ValueError as error:
        return RedirectResponse(_product_url(return_sku, str(error)), status_code=303)

    with get_connection(settings.database_path) as connection:
        connection.execute(
            "INSERT INTO walmart_templates (original_name, stored_name) VALUES (?, ?)",
            (file.filename or "plantilla-walmart.xlsx", stored_name),
        )
        connection.commit()
    return RedirectResponse(
        _product_url(return_sku, "Plantilla Vestuario cargada. Ya puedes preparar el producto."),
        status_code=303,
    )


@app.post("/products/{sku_base}/generate")
def generate_product_template(
    sku_base: str,
    template_id: int = Form(...),
    ean_codes: str = Form(...),
    main_image_url: str = Form(...),
    image_2_url: str = Form(...),
    image_3_url: str = Form(...),
    long_description: str = Form(...),
    short_description: str = Form(...),
    warranty_text: str = Form(...),
    warranty_condition: str = Form(...),
    gender: str = Form(...),
    color: str = Form(...),
    material: str = Form(...),
    features: str = Form(...),
    keywords: str = Form(...),
    settings: Settings = Depends(app_settings),
):
    product = _get_source_product(settings, sku_base)
    entered_values = {
        "URL imagen principal": main_image_url,
        "URL imagen secundaria": image_2_url,
        "URL imagen secundaria 1": image_3_url,
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
            _product_url(sku_base, f"Falta completar: {', '.join(missing)}."),
            status_code=303,
        )

    codes = [line.strip() for line in ean_codes.splitlines() if line.strip()]
    if len(codes) != len(product.variants):
        return RedirectResponse(
            _product_url(
                sku_base,
                f"Debes pegar {len(product.variants)} códigos EAN, uno por cada variante.",
            ),
            status_code=303,
        )
    if len(set(codes)) != len(codes) or any(not EAN_PATTERN.fullmatch(code) for code in codes):
        return RedirectResponse(
            _product_url(sku_base, "Los EAN deben ser códigos numéricos únicos de 8 a 14 dígitos."),
            status_code=303,
        )
    image_urls = (main_image_url, image_2_url, image_3_url)
    if any(not value.strip().lower().startswith(("https://", "http://")) for value in image_urls):
        return RedirectResponse(
            _product_url(sku_base, "Las tres imágenes deben tener una URL que comience con http:// o https://."),
            status_code=303,
        )

    with get_connection(settings.database_path) as connection:
        template = connection.execute(
            "SELECT id, original_name, stored_name FROM walmart_templates WHERE id = ?",
            (template_id,),
        ).fetchone()
        if template is None:
            return RedirectResponse(
                _product_url(sku_base, "La plantilla seleccionada ya no está disponible."),
                status_code=303,
            )

        source_path = settings.uploads_dir / Path(template["stored_name"]).name
        if not source_path.is_file():
            return RedirectResponse(
                _product_url(sku_base, "No se encontró el archivo de plantilla. Vuelve a cargarlo."),
                status_code=303,
            )

        display_name = f"{product.sku_base}-walmart.xlsx"
        stored_name = f"{uuid4().hex}.xlsx"
        output_path = settings.uploads_dir / stored_name
        try:
            create_filled_product_template(
                source_path,
                output_path,
                rows=_build_product_rows(
                    product,
                    ean_codes=codes,
                    main_image_url=main_image_url.strip(),
                    image_2_url=image_2_url.strip(),
                    image_3_url=image_3_url.strip(),
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
            return RedirectResponse(_product_url(sku_base, str(error)), status_code=303)

        connection.execute(
            "INSERT INTO product_outputs (sku_base, original_name, stored_name) VALUES (?, ?, ?)",
            (product.sku_base, display_name, stored_name),
        )
        connection.commit()
    return RedirectResponse(
        _product_url(sku_base, "Planilla completada y lista para descargar."),
        status_code=303,
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
