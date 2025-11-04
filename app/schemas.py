"""Pydantic schemas for API responses and requests."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class WatchlistBase(BaseModel):
    label: str = Field(..., description="Nombre descriptivo del vehículo o persona.")
    vehicle_type: Optional[str] = Field(None, description="Tipo de vehículo (auto, camioneta, camión, etc.).")
    color_name: Optional[str] = Field(None, description="Color dominante del vehículo.")
    model_name: Optional[str] = Field(None, description="Modelo o referencia adicional.")
    has_logo: bool = Field(False, description="Indica si se espera ver un logo distintivo.")
    is_person: bool = Field(False, description="Indica si se trata de una persona en lugar de un vehículo.")


class WatchlistCreate(WatchlistBase):
    pass


class WatchlistRead(WatchlistBase):
    id: int
    image_path: Path
    created_at: datetime

    class Config:
        orm_mode = True


class DetectionBase(BaseModel):
    detected_label: Optional[str] = None
    vehicle_type: Optional[str] = None
    color_name: Optional[str] = None
    model_name: Optional[str] = None
    has_logo: bool = False
    is_person: bool = False
    match_score: float = 0.0
    snapshot_path: Optional[Path] = None
    metadata: Optional[Any] = Field(None, alias="event_metadata")


class DetectionRead(DetectionBase):
    id: int
    watchlist_entry_id: Optional[int]
    created_at: datetime

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


class WatchlistResponse(BaseModel):
    items: List[WatchlistRead]


class DetectionResponse(BaseModel):
    items: List[DetectionRead]


class AlarmState(BaseModel):
    visual_alarm_active: bool
    last_alarm_at: Optional[datetime]


class CameraState(BaseModel):
    source: str
    frame_skip: int
    min_confidence: float
    connected: bool
    last_connected_at: Optional[datetime]
    last_error: Optional[str]


class CameraSettingsUpdate(BaseModel):
    source: Optional[str] = Field(None, description="Fuente de video para la cámara.")
    frame_skip: Optional[int] = Field(
        None, ge=1, description="Procesar únicamente un cuadro de cada N recibidos."
    )
    min_confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confianza mínima requerida para aceptar detecciones.",
    )
