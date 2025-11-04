"""Jinja2 powered web panel for managing the system."""
from __future__ import annotations

from pathlib import Path
from typing import List

from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..config import settings
from ..services import camera as camera_service
from ..services import events as events_service
from ..services import watchlist as watchlist_service

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


@router.get("/panel", response_class=HTMLResponse)
async def dashboard(request: Request):
    watchlist = watchlist_service.list_watchlist()
    detections = events_service.list_events()
    camera_state = camera_service.get_state()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "watchlist": watchlist,
            "detections": detections,
            "camera_state": camera_state,
        },
    )


@router.post("/panel/watchlist")
async def upload_watchlist_item(
    request: Request,
    label: str = Form(...),
    vehicle_type: str | None = Form(None),
    color_name: str | None = Form(None),
    model_name: str | None = Form(None),
    has_logo: bool = Form(False),
    is_person: bool = Form(False),
    image: UploadFile = File(...),
):
    filename = f"{uuid4().hex}_{image.filename}"
    destination = settings.watchlist_dir / filename
    destination.write_bytes(await image.read())
    watchlist_service.create_watchlist_entry(
        label=label,
        image_path=destination,
        vehicle_type=vehicle_type,
        color_name=color_name,
        model_name=model_name,
        has_logo=has_logo,
        is_person=is_person,
    )
    return RedirectResponse(url="/panel", status_code=303)


@router.get("/media/watchlist/{filename}", name="watchlist_image")
async def watchlist_image(filename: str):
    path = settings.watchlist_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    return FileResponse(path)


@router.get("/media/detections/{filename}", name="detection_image")
async def detection_image(filename: str):
    path = settings.detections_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Captura no encontrada")
    return FileResponse(path)
