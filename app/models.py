"""SQLAlchemy models for watchlist and detections."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(128), nullable=False)
    vehicle_type = Column(String(32), nullable=True)
    color_name = Column(String(32), nullable=True)
    model_name = Column(String(64), nullable=True)
    has_logo = Column(Boolean, default=False)
    is_person = Column(Boolean, default=False)
    image_path = Column(String(512), nullable=False)
    feature_vector = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    detections = relationship("DetectionEvent", back_populates="watchlist_entry")


class DetectionEvent(Base):
    __tablename__ = "detection_events"

    id = Column(Integer, primary_key=True, index=True)
    watchlist_entry_id = Column(Integer, ForeignKey("watchlist_entries.id"), nullable=True)
    detected_label = Column(String(128), nullable=True)
    vehicle_type = Column(String(32), nullable=True)
    color_name = Column(String(32), nullable=True)
    model_name = Column(String(64), nullable=True)
    has_logo = Column(Boolean, default=False)
    is_person = Column(Boolean, default=False)
    match_score = Column(Float, default=0.0)
    snapshot_path = Column(String(512), nullable=True)
    event_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    watchlist_entry = relationship("WatchlistEntry", back_populates="detections")


class AppState(Base):
    __tablename__ = "app_state"

    id = Column(Integer, primary_key=True, index=True)
    visual_alarm_active = Column(Boolean, default=False)
    last_alarm_at = Column(DateTime, nullable=True)

    @classmethod
    def get_singleton(cls, session) -> "AppState":
        instance: Optional[AppState] = session.query(cls).first()
        if instance is None:
            instance = cls()
            session.add(instance)
            session.commit()
            session.refresh(instance)
        return instance
