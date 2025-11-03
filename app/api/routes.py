"""FastAPI routes for managing the watchlist and detection events."""
from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..config import settings
from ..database import session_scope
from ..models import AppState, WatchlistEntry
from ..schemas import AlarmState, DetectionRead, DetectionResponse, WatchlistRead, WatchlistResponse
from ..services import events as events_service
from ..services import watchlist as watchlist_service

LOGGER = logging.getLogger(__name__)

router = APIRouter()


def _get_watchlist_entry(entry_id: int) -> WatchlistEntry:
    with session_scope() as session:
        entry = session.query(WatchlistEntry).get(entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Entrada no encontrada")
        session.expunge(entry)
        return entry


@router.get("/watchlist", response_model=WatchlistResponse)
def list_watchlist_entries() -> WatchlistResponse:
    entries = watchlist_service.list_watchlist()
    return WatchlistResponse(items=[WatchlistRead.from_orm(entry) for entry in entries])


@router.post("/watchlist", response_model=WatchlistRead)
def create_watchlist_item(
    label: str,
    vehicle_type: str | None = None,
    color_name: str | None = None,
    model_name: str | None = None,
    has_logo: bool = False,
    is_person: bool = False,
    image: UploadFile = File(...),
) -> WatchlistRead:
    filename = f"{uuid4().hex}_{image.filename}"
    destination = settings.watchlist_dir / filename
    destination.write_bytes(image.file.read())
    entry = watchlist_service.create_watchlist_entry(
        label=label,
        image_path=destination,
        vehicle_type=vehicle_type,
        color_name=color_name,
        model_name=model_name,
        has_logo=has_logo,
        is_person=is_person,
    )
    return WatchlistRead.from_orm(entry)


@router.delete("/watchlist/{entry_id}")
def delete_watchlist_item(entry_id: int) -> None:
    _get_watchlist_entry(entry_id)
    watchlist_service.delete_watchlist_entry(entry_id)


@router.get("/detections", response_model=DetectionResponse)
def list_detection_events(limit: int = 50) -> DetectionResponse:
    events = events_service.list_events(limit=limit)
    return DetectionResponse(items=[DetectionRead.from_orm(event) for event in events])


@router.get("/alarm", response_model=AlarmState)
def alarm_state() -> AlarmState:
    with session_scope() as session:
        state = AppState.get_singleton(session)
        session.expunge(state)
        return AlarmState(
            visual_alarm_active=state.visual_alarm_active,
            last_alarm_at=state.last_alarm_at,
        )
