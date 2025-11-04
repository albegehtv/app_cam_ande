"""Utilities to manage camera connectivity and runtime configuration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Any, Dict, Optional

from ..config import settings


@dataclass
class CameraSnapshot:
    """Serializable representation of the current camera state."""

    source: str
    frame_skip: int
    min_confidence: float
    connected: bool = False
    last_connected_at: Optional[datetime] = None
    last_error: Optional[str] = None


class CameraController:
    """In-memory controller that keeps track of camera connectivity."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._state = CameraSnapshot(
            source=settings.camera.source,
            frame_skip=settings.camera.frame_skip,
            min_confidence=settings.camera.min_confidence,
        )

    def _apply_updates(
        self,
        *,
        source: Optional[str] = None,
        frame_skip: Optional[int] = None,
        min_confidence: Optional[float] = None,
    ) -> None:
        if source is not None:
            if not source.strip():
                raise ValueError("La fuente de la cámara no puede estar vacía.")
            self._state.source = source.strip()
        if frame_skip is not None:
            if frame_skip < 1:
                raise ValueError("El número de saltos de cuadro debe ser al menos 1.")
            self._state.frame_skip = frame_skip
        if min_confidence is not None:
            if not 0.0 <= min_confidence <= 1.0:
                raise ValueError("La confianza mínima debe estar entre 0 y 1.")
            self._state.min_confidence = min_confidence

    def snapshot(self) -> CameraSnapshot:
        """Return an immutable copy of the current camera state."""

        state = self._state
        return CameraSnapshot(
            source=state.source,
            frame_skip=state.frame_skip,
            min_confidence=state.min_confidence,
            connected=state.connected,
            last_connected_at=state.last_connected_at,
            last_error=state.last_error,
        )

    def to_dict(self, snapshot: Optional[CameraSnapshot] = None) -> Dict[str, Any]:
        """Return a dictionary representation of the current state."""

        snap = snapshot or self._state
        return {
            "source": snap.source,
            "frame_skip": snap.frame_skip,
            "min_confidence": snap.min_confidence,
            "connected": snap.connected,
            "last_connected_at": snap.last_connected_at,
            "last_error": snap.last_error,
        }

    def connect(
        self,
        *,
        source: Optional[str] = None,
        frame_skip: Optional[int] = None,
        min_confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Mark the camera as connected and optionally update its configuration."""

        with self._lock:
            self._apply_updates(
                source=source, frame_skip=frame_skip, min_confidence=min_confidence
            )
            self._state.connected = True
            self._state.last_error = None
            self._state.last_connected_at = datetime.utcnow()
            return self.to_dict(self._state)

    def disconnect(self) -> Dict[str, Any]:
        """Mark the camera as disconnected."""

        with self._lock:
            self._state.connected = False
            return self.to_dict(self._state)

    def update(
        self,
        *,
        source: Optional[str] = None,
        frame_skip: Optional[int] = None,
        min_confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Update runtime parameters without changing the connectivity state."""

        with self._lock:
            if not any(value is not None for value in (source, frame_skip, min_confidence)):
                return self.to_dict(self._state)
            self._apply_updates(
                source=source, frame_skip=frame_skip, min_confidence=min_confidence
            )
            return self.to_dict(self._state)

    def set_error(self, message: Optional[str]) -> Dict[str, Any]:
        """Persist a recoverable connection error message for UI consumption."""

        with self._lock:
            self._state.last_error = message
            if message:
                self._state.connected = False
            return self.to_dict(self._state)


_controller = CameraController()


def get_state() -> Dict[str, Any]:
    """Expose the current camera state for other layers."""

    return _controller.to_dict(_controller.snapshot())


def connect(**kwargs: Any) -> Dict[str, Any]:
    """Public helper to mark the camera as connected."""

    return _controller.connect(**kwargs)


def disconnect() -> Dict[str, Any]:
    """Public helper to mark the camera as disconnected."""

    return _controller.disconnect()


def update(**kwargs: Any) -> Dict[str, Any]:
    """Public helper to adjust camera configuration."""

    return _controller.update(**kwargs)


def set_error(message: Optional[str]) -> Dict[str, Any]:
    """Surface an error originating from the detector runner or the UI."""

    return _controller.set_error(message)
