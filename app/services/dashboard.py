from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.dashboard import dashboard_data  # <- função que devolve o JSON do dashboard

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse, summary="Página do Dashboard (HTML)")
def dashboard_page(request: Request):
    # Vai renderizar templates/dashboard.html
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/data", summary="Dados do Dashboard (JSON)")
def dashboard_json():
    return dashboard_data()
