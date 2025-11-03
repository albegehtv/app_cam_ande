"""FastAPI application entry point."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

from .api.routes import router as api_router
from .config import settings
from .database import engine
from .models import Base
from .web.views import router as web_router

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema de vigilancia de vehículos")
app.include_router(api_router, prefix="/api")
app.include_router(web_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_path = Path(__file__).resolve().parent / "web" / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/")
def index() -> RedirectResponse:
    return RedirectResponse(url="/panel")
