"""Persistence of the user's last selections between sessions."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QByteArray, QSettings

ORGANIZATION = "MeetingNotes"
APPLICATION = "LocalMeetingNotesGenerator"


class Keys:
    OLLAMA_MODEL = "selection/ollama_model"
    SYSTEM_PROMPT = "selection/system_prompt"
    WHISPER_MODEL = "selection/whisper_model"
    LANGUAGE = "selection/language"
    GPU = "selection/gpu"
    TRANSLATE = "options/translate"
    TIMESTAMPS = "options/timestamps"
    SUBTITLES = "options/subtitles"
    LAST_DIRECTORY = "paths/last_directory"
    GEOMETRY = "window/geometry"


class Preferences:
    """Typed access to ``QSettings`` (stored per user in the Windows registry)."""

    def __init__(self, settings: Optional[QSettings] = None) -> None:
        self._settings = settings or QSettings(ORGANIZATION, APPLICATION)

    def text(self, key: str, default: str = "") -> str:
        value = self._settings.value(key)
        return str(value) if value is not None else default

    def flag(self, key: str, default: bool) -> bool:
        value = self._settings.value(key)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("true", "1", "yes")

    def geometry(self) -> Optional[QByteArray]:
        value = self._settings.value(Keys.GEOMETRY)
        return value if isinstance(value, QByteArray) else None

    def set(self, key: str, value: object) -> None:
        self._settings.setValue(key, value)
