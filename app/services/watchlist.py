"""Service layer for CRUD operations on the watchlist."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Optional

import cv2

from ..config import settings
from ..database import session_scope
from ..models import WatchlistEntry
from .features import build_feature_vector, dominant_color_name

LOGGER = logging.getLogger(__name__)


def list_watchlist() -> Iterable[WatchlistEntry]:
    with session_scope() as session:
        entries = session.query(WatchlistEntry).order_by(WatchlistEntry.created_at.desc()).all()
        for entry in entries:
            session.expunge(entry)
        return entries


def create_watchlist_entry(
    label: str,
    image_path: Path,
    vehicle_type: Optional[str] = None,
    color_name: Optional[str] = None,
    model_name: Optional[str] = None,
    has_logo: bool = False,
    is_person: bool = False,
) -> WatchlistEntry:
    settings.watchlist_dir.mkdir(parents=True, exist_ok=True)
    image_path = Path(image_path)
    image_destination = settings.watchlist_dir / image_path.name
    if image_path != image_destination:
        image_destination.write_bytes(image_path.read_bytes())
    image = cv2.imread(str(image_destination))
    if image is None:
        raise ValueError("No se pudo leer la imagen proporcionada")
    if color_name is None:
        color_name = dominant_color_name(image)
    else:
        color_name = color_name.lower()
    features = build_feature_vector(image)
    with session_scope() as session:
        entry = WatchlistEntry(
            label=label,
            vehicle_type=vehicle_type,
            color_name=color_name,
            model_name=model_name,
            has_logo=has_logo,
            is_person=is_person,
            image_path=image_destination.name,
            feature_vector=features.to_dict(),
        )
        session.add(entry)
        session.flush()
        session.refresh(entry)
        session.expunge(entry)
        LOGGER.info("Agregado a la lista de vigilancia: %s", label)
        return entry


def delete_watchlist_entry(entry_id: int) -> None:
    with session_scope() as session:
        entry = session.query(WatchlistEntry).get(entry_id)
        if entry:
            session.delete(entry)
            LOGGER.info("Entrada eliminada: %s", entry.label)
