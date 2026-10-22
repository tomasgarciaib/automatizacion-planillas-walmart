from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
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
from app.settings import Settings, get_settings


BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


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
def dashboard(request: Request, settings: Settings = Depends(app_settings)):
    with get_connection(settings.database_path) as connection:
        campaigns = list_campaigns(connection)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"campaigns": campaigns, "statuses": VALID_STATUSES},
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
                "SELECT id, document_type, original_name, uploaded_at "
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
    if document_type not in {"Fuente", "Plantilla Walmart"}:
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
