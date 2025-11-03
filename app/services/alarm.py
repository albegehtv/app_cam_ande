"""Utilities for triggering audible/visual alarms and controlling a relay."""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:  # pragma: no cover - optional dependency
    import simpleaudio
except Exception:  # pragma: no cover - optional dependency
    simpleaudio = None

try:  # pragma: no cover - optional dependency
    from gpiozero import OutputDevice
except Exception:  # pragma: no cover - optional dependency
    OutputDevice = None

from ..config import settings
from ..database import session_scope
from ..models import AppState

LOGGER = logging.getLogger(__name__)


class RelayController:
    """Handles activation of the physical relay, if available."""

    def __init__(self, pin: Optional[int]):
        self.pin = pin
        if pin is not None and OutputDevice is None:
            LOGGER.warning("gpiozero no está disponible; la salida del relay será simulada.")
        self.device = OutputDevice(pin) if pin is not None and OutputDevice else None

    def activate(self, seconds: float) -> None:
        if self.device is not None:
            LOGGER.info("Activando relay en pin %s por %.1f segundos", self.pin, seconds)
            self.device.on()
            time.sleep(seconds)
            self.device.off()
        else:
            LOGGER.info("Simulación de activación de relay por %.1f segundos", seconds)
            time.sleep(seconds)


class AlarmManager:
    """Coordinates audio playback, relay output and visual alarms."""

    def __init__(self, sound_file: Optional[Path] = None, enable_audio: bool = True):
        self.sound_file = sound_file
        self.enable_audio = enable_audio and simpleaudio is not None
        if enable_audio and simpleaudio is None:
            LOGGER.warning("simpleaudio no está disponible; la alarma sonora será omitida.")
        self.relay = RelayController(settings.alarm.relay_pin)
        self._lock = threading.Lock()

    def trigger(self, reason: str) -> None:
        LOGGER.info("Activando alarmas por %s", reason)
        threading.Thread(target=self._handle_alarm, args=(reason,), daemon=True).start()

    def _handle_alarm(self, reason: str) -> None:
        with self._lock:
            if self.enable_audio and self.sound_file and self.sound_file.exists():
                try:  # pragma: no cover - audio playback is optional
                    wave_obj = simpleaudio.WaveObject.from_wave_file(str(self.sound_file))
                    play_obj = wave_obj.play()
                    play_obj.wait_done()
                except Exception as exc:
                    LOGGER.error("No se pudo reproducir el sonido de alarma: %s", exc)
            if settings.alarm.relay_active_seconds > 0:
                self.relay.activate(settings.alarm.relay_active_seconds)
            self._set_visual_alarm(True)
            time.sleep(1)
            self._set_visual_alarm(False)

    def _set_visual_alarm(self, active: bool) -> None:
        with session_scope() as session:
            state = AppState.get_singleton(session)
            state.visual_alarm_active = active
            state.last_alarm_at = datetime.utcnow()
            session.add(state)
