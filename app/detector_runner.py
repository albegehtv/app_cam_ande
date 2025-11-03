"""Command line utility to run the detection loop."""
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

import cv2

from .config import settings
from .database import session_scope
from .models import AppState, WatchlistEntry
from .services import events as events_service
from .services.alarm import AlarmManager
from .services.detector import VehicleDetector, save_detection_snapshot

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sistema de detección de vehículos y personas")
    parser.add_argument("--source", default=settings.camera.source, help="Fuente de video para OpenCV")
    parser.add_argument(
        "--model", default="yolov8n.pt", help="Ruta al modelo YOLO compatible con ultralytics"
    )
    parser.add_argument("--confidence", type=float, default=settings.camera.min_confidence)
    parser.add_argument("--frame-skip", type=int, default=settings.camera.frame_skip)
    parser.add_argument(
        "--sound", type=str, default=str(settings.alarm.sound_file or ""), help="Archivo WAV para la alarma"
    )
    return parser.parse_args()


def load_watchlist(session) -> list[WatchlistEntry]:
    entries = session.query(WatchlistEntry).all()
    for entry in entries:
        session.expunge(entry)
    return entries


def detection_loop(args: argparse.Namespace) -> None:
    detector = VehicleDetector(model_path=args.model, min_confidence=args.confidence)
    alarm = AlarmManager(Path(args.sound) if args.sound else None, enable_audio=settings.alarm.enable_audio)

    source = args.source
    try:
        source = int(source)
    except ValueError:
        pass
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir la fuente de video: {source}")

    frame_index = 0
    LOGGER.info("Iniciando monitoreo en %s", source)
    with session_scope() as session:
        AppState.get_singleton(session)
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                LOGGER.warning("Fin del stream o error de lectura")
                break
            frame_index += 1
            if args.frame_skip > 1 and frame_index % args.frame_skip != 0:
                continue
            with session_scope() as session:
                watchlist = load_watchlist(session)
            matches = detector.find_matches(frame, watchlist)
            for detection, entry, score, features in matches:
                if entry is None:
                    continue
                timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")
                snapshot_file = settings.detections_dir / f"{timestamp}_{entry.id}.jpg"
                save_detection_snapshot(frame, detection.bbox, snapshot_file)
                events_service.record_detection(
                    watchlist_entry=entry,
                    detected_label=detection.label,
                    vehicle_type=entry.vehicle_type,
                    color_name=entry.color_name,
                    match_score=score,
                    snapshot_path=snapshot_file,
                    metadata={"confidence": detection.confidence},
                )
                alarm.trigger(reason=f"Coincidencia con {entry.label}")
    finally:
        cap.release()
        LOGGER.info("Monitoreo finalizado")


def main() -> None:
    """Entrypoint compatible con console_scripts."""

    detection_loop(parse_args())


if __name__ == "__main__":
    main()
