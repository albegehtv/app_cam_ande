"""Jinja2 powered web panel for managing the system."""
from __future__ import annotations

from pathlib import Path
from typing import Optional
from urllib.parse import quote, unquote
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..config import settings
from ..services import auth as auth_service
from ..services import camera as camera_service
from ..services import events as events_service
from ..services import watchlist as watchlist_service

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def _safe_next_url(value: Optional[str]) -> str:
    if not value:
        return "/panel"
    value = unquote(value.strip())
    if value.startswith("http://") or value.startswith("https://"):
        return "/panel"
    if not value.startswith("/"):
        return "/panel"
    return value


def _current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return auth_service.get_user_by_id(user_id)


@router.get("/panel", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = _current_user(request)
    if user is None:
        destination = request.url.path
        if request.url.query:
            destination = f"{destination}?{request.url.query}"
        next_url = quote(destination, safe="/=?&")
        return RedirectResponse(
            url=f"/login?next={next_url}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

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
            "user": user,
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
    user = _current_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

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
    return RedirectResponse(url="/panel", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str | None = None):
    user = _current_user(request)
    if user is not None:
        return RedirectResponse(url="/panel", status_code=status.HTTP_303_SEE_OTHER)

    context = {
        "request": request,
        "next_url": _safe_next_url(next),
    }
    return templates.TemplateResponse("login.html", context)


@router.post("/login")
async def login_action(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str | None = Form(None),
):
    user = auth_service.authenticate_user(username, password)
    if user is None:
        context = {
            "request": request,
            "next_url": _safe_next_url(next),
            "form_username": username,
            "error": "Credenciales inválidas. Verifica tus datos e inténtalo nuevamente.",
        }
        return templates.TemplateResponse(
            "login.html",
            context,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    request.session["user_id"] = user.id
    return RedirectResponse(
        url=_safe_next_url(next),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, next: str | None = None):
    user = _current_user(request)
    if user is not None:
        return RedirectResponse(url="/panel", status_code=status.HTTP_303_SEE_OTHER)

    context = {
        "request": request,
        "next_url": _safe_next_url(next),
    }
    return templates.TemplateResponse("register.html", context)


@router.post("/register")
async def register_action(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    full_name: str | None = Form(None),
    next: str | None = Form(None),
):
    if password != confirm_password:
        context = {
            "request": request,
            "next_url": _safe_next_url(next),
            "form_username": username,
            "form_full_name": full_name,
            "error": "Las contraseñas no coinciden.",
        }
        return templates.TemplateResponse(
            "register.html",
            context,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = auth_service.create_user(username, password, full_name=full_name)
    except ValueError as exc:
        context = {
            "request": request,
            "next_url": _safe_next_url(next),
            "form_username": username,
            "form_full_name": full_name,
            "error": str(exc),
        }
        return templates.TemplateResponse(
            "register.html",
            context,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    request.session["user_id"] = user.id
    return RedirectResponse(
        url=_safe_next_url(next),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/logout")
async def logout(request: Request):
    request.session.pop("user_id", None)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


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
