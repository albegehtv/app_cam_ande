"""Detection pipeline that integrates YOLO with feature matching."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List, Optional

import cv2
import numpy as np

try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover - optional dependency
    YOLO = None  # type: ignore

from ..config import settings
from ..models import WatchlistEntry
from .features import FeatureVector, build_feature_vector, compare_feature_vectors, dominant_color_name

LOGGER = logging.getLogger(__name__)

YOLO_VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck", "train"}
YOLO_PERSON_CLASSES = {"person"}


@dataclass
class DetectionResult:
    label: str
    confidence: float
    bbox: np.ndarray
    class_name: str
    roi: np.ndarray


class VehicleDetector:
    """Wraps the object detection model and similarity matching logic."""

    def __init__(self, model_path: Optional[str] = None, min_confidence: Optional[float] = None):
        self.min_confidence = min_confidence or settings.camera.min_confidence
        self.model = None
        if model_path is None:
            model_path = "yolov8n.pt"
        if YOLO is None:
            LOGGER.warning(
                "No se pudo importar ultralytics.YOLO. Se utilizará un modo degradado sin detección real."
            )
        else:
            try:
                self.model = YOLO(model_path)
                LOGGER.info("Modelo YOLO cargado desde %s", model_path)
            except Exception as exc:  # pragma: no cover - optional dependency
                LOGGER.error("No se pudo cargar el modelo YOLO (%s). Se continuará en modo degradado.", exc)
                self.model = None

    def detect(self, frame: np.ndarray) -> List[DetectionResult]:
        if self.model is None:
            return self._degraded_detection(frame)
        results = self.model(frame, verbose=False)
        detections: List[DetectionResult] = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                confidence = float(box.conf)
                if confidence < self.min_confidence:
                    continue
                cls_idx = int(box.cls)
                class_name = self.model.names.get(cls_idx, str(cls_idx))  # type: ignore[attr-defined]
                bbox = box.xyxy.cpu().numpy().astype(int)[0]
                x1, y1, x2, y2 = bbox
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(frame.shape[1], x2)
                y2 = min(frame.shape[0], y2)
                roi = frame[y1:y2, x1:x2]
                if roi.size == 0:
                    continue
                detections.append(
                    DetectionResult(
                        label=class_name,
                        confidence=confidence,
                        bbox=bbox,
                        class_name=class_name,
                        roi=roi,
                    )
                )
        return detections

    def _degraded_detection(self, frame: np.ndarray) -> List[DetectionResult]:
        height, width = frame.shape[:2]
        roi = frame[height // 4 : height * 3 // 4, width // 4 : width * 3 // 4]
        return [
            DetectionResult(
                label="desconocido",
                confidence=0.3,
                bbox=np.array([width // 4, height // 4, width * 3 // 4, height * 3 // 4]),
                class_name="desconocido",
                roi=roi,
            )
        ]

    @staticmethod
    def _match_vehicle_type(detection: DetectionResult, watch_entry: WatchlistEntry) -> bool:
        if watch_entry.is_person:
            return detection.class_name in YOLO_PERSON_CLASSES
        if watch_entry.vehicle_type is None:
            return detection.class_name in YOLO_VEHICLE_CLASSES
        return watch_entry.vehicle_type.lower() in detection.class_name.lower()

    @staticmethod
    def _extract_features(roi: np.ndarray) -> FeatureVector:
        return build_feature_vector(roi)

    def find_matches(
        self, frame: np.ndarray, watchlist: Iterable[WatchlistEntry]
    ) -> List[tuple[DetectionResult, Optional[WatchlistEntry], float, FeatureVector]]:
        detections = self.detect(frame)
        matches: List[tuple[DetectionResult, Optional[WatchlistEntry], float, FeatureVector]] = []
        for detection in detections:
            roi_features = self._extract_features(detection.roi)
            best_match: Optional[WatchlistEntry] = None
            best_score = 0.0
            for entry in watchlist:
                if not self._match_vehicle_type(detection, entry):
                    continue
                if entry.feature_vector:
                    entry_features = FeatureVector.from_dict(entry.feature_vector)
                    score = compare_feature_vectors(roi_features, entry_features)
                else:
                    score = 0.1
                if entry.color_name:
                    detected_color = dominant_color_name(detection.roi)
                    if detected_color == entry.color_name.lower():
                        score += 0.1
                    else:
                        score -= 0.05
                if entry.has_logo:
                    if roi_features.edge_density > 0.15:
                        score += 0.05
                    else:
                        score -= 0.05
                if score > best_score:
                    best_score = score
                    best_match = entry
            matches.append((detection, best_match, best_score, roi_features))
        return matches


def save_detection_snapshot(frame: np.ndarray, bbox: np.ndarray, path: Path) -> None:
    x1, y1, x2, y2 = bbox
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), roi)
