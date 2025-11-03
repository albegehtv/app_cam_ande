"""Service helpers for persisting detection events."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

from ..database import session_scope
from ..models import DetectionEvent, WatchlistEntry

LOGGER = logging.getLogger(__name__)


def record_detection(
    *,
    watchlist_entry: Optional[WatchlistEntry],
    detected_label: Optional[str],
    vehicle_type: Optional[str],
    color_name: Optional[str],
    match_score: float,
    snapshot_path: Optional[Path],
    metadata: Optional[dict[str, Any]] = None,
) -> DetectionEvent:
    with session_scope() as session:
        event = DetectionEvent(
            watchlist_entry_id=watchlist_entry.id if watchlist_entry else None,
            detected_label=detected_label,
            vehicle_type=vehicle_type,
            color_name=color_name,
            model_name=watchlist_entry.model_name if watchlist_entry else None,
            has_logo=watchlist_entry.has_logo if watchlist_entry else False,
            is_person=watchlist_entry.is_person if watchlist_entry else False,
            match_score=match_score,
            snapshot_path=snapshot_path.name if snapshot_path else None,
            event_metadata=metadata or {},
            created_at=datetime.utcnow(),
        )
        session.add(event)
        session.flush()
        session.refresh(event)
        session.expunge(event)
        LOGGER.info("Evento registrado (match=%.2f) contra %s", match_score, watchlist_entry.label if watchlist_entry else "desconocido")
        return event


def list_events(limit: int = 50) -> Iterable[DetectionEvent]:
    with session_scope() as session:
        from sqlalchemy.orm import joinedload

        events = (
            session.query(DetectionEvent)
            .options(joinedload(DetectionEvent.watchlist_entry))
            .order_by(DetectionEvent.created_at.desc())
            .limit(limit)
            .all()
        )
        for event in events:
            session.expunge(event)
        return events
