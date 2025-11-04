"""Application configuration utilities."""
from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class AlarmSettings(BaseModel):
    """Configuration for audio/visual alarms and relay outputs."""

    sound_file: Optional[Path] = Field(
        default=None,
        description="Path to a WAV file that will be played when an alarm is triggered.",
    )
    enable_audio: bool = Field(
        default=True,
        description="Whether to attempt playing an audible alarm when a match is detected.",
    )
    enable_visual_flag: bool = Field(
        default=True,
        description="Whether to expose a visual alarm flag through the API.",
    )
    relay_pin: Optional[int] = Field(
        default=None,
        description="GPIO pin used to toggle the shutdown relay. Only relevant on Raspberry Pi like hardware.",
    )
    relay_active_seconds: float = Field(
        default=5.0,
        description="How long the relay should remain active after a detection, in seconds.",
    )


class CameraSettings(BaseModel):
    """Camera specific settings."""

    source: str = Field(
        default="0",
        description="VideoCapture source that OpenCV should use. \n"
        "It can be an integer index, an RTSP URL or a video file path.",
    )
    frame_skip: int = Field(
        default=2,
        description="Process only one out of every `frame_skip` frames to save CPU cycles.",
    )
    min_confidence: float = Field(
        default=0.45,
        description="Minimum detection confidence required to consider a YOLO detection valid.",
    )


class DatabaseSettings(BaseModel):
    """Database connection configuration."""

    url: str = Field(
        default=f"sqlite:///{Path(os.getenv('APP_STATE_DIR', '.')).resolve() / 'app.db'}",
        description="SQLAlchemy compatible database URL.",
    )


class AppSettings(BaseModel):
    """Top level application settings container."""

    camera: CameraSettings = Field(default_factory=CameraSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    alarm: AlarmSettings = Field(default_factory=AlarmSettings)

    watchlist_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("APP_WATCHLIST_DIR", "./watchlist")),
        description="Directory where uploaded watchlist images are stored.",
    )
    detections_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("APP_DETECTIONS_DIR", "./detections")),
        description="Directory where snapshots from detections are saved.",
    )
    session_secret: str = Field(
        default_factory=lambda: os.getenv("APP_SESSION_SECRET", secrets.token_urlsafe(48)),
        description="Secret key used to sign session cookies.",
    )

    def ensure_directories(self) -> None:
        """Create the directories used by the application if they do not exist."""

        self.watchlist_dir.mkdir(parents=True, exist_ok=True)
        self.detections_dir.mkdir(parents=True, exist_ok=True)
        Path(self.database.url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)


settings = AppSettings()
settings.ensure_directories()
