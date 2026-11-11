"""Background threads that run transcription and note generation off the UI thread."""

from __future__ import annotations

import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from meeting_notes.core.note_generator import NoteGenerationError, NoteGenerator
from meeting_notes.core.transcriber import AudioTranscriber, TranscriptionError


class JobError(Exception):
    """Raised for an expected job failure that carries a user-facing message."""


@dataclass(frozen=True)
class JobResult:
    """Output of a finished job; ``notes`` is ``None`` for transcription-only jobs."""

    transcript: str
    notes: Optional[str] = None


class _Worker(QThread):
    """
    Base worker. Emits ``result_ready`` exactly once with a ``JobResult``,
    or with ``None`` after logging the reason for a failure.
    """

    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    result_ready = pyqtSignal(object)

    def __init__(
        self, whisper_exe: Path, model_path: Path, audio_path: str, parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)
        self._whisper_exe = whisper_exe
        self._model_path = model_path
        self._audio_path = audio_path

    def run(self) -> None:
        try:
            result = self._process()
        except FileNotFoundError as exc:
            message = f"File not found: {exc}"
        except TranscriptionError as exc:
            message = f"Transcription error: {exc}"
        except NoteGenerationError as exc:
            message = f"Note generation error: {exc}"
        except JobError as exc:
            message = str(exc)
        except Exception as exc:  # Thread boundary: report anything else instead of dying silently.
            message = f"An unexpected error occurred: {exc}\n{traceback.format_exc()}"
        else:
            self.result_ready.emit(result)
            return
        self.log.emit(message)
        self.result_ready.emit(None)

    def _process(self) -> JobResult:
        raise NotImplementedError

    def _transcribe(self) -> str:
        transcriber = AudioTranscriber(self._whisper_exe, self._model_path)
        transcript = transcriber.transcribe(self._audio_path)
        self.log.emit("Transcription complete.")
        return transcript


class TranscriptionWorker(_Worker):
    """Transcribes one audio file; does not require Ollama."""

    def _process(self) -> JobResult:
        self.log.emit("Starting audio transcription...")
        self.log.emit("Transcribing audio...")
        self.progress.emit(20)
        transcript = self._transcribe()
        self.progress.emit(90)
        return JobResult(transcript=transcript)


class NotesWorker(_Worker):
    """Transcribes one audio file, then generates meeting notes with Ollama."""

    def __init__(
        self,
        whisper_exe: Path,
        model_path: Path,
        audio_path: str,
        prompt_path: Path,
        ollama_model: str,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(whisper_exe, model_path, audio_path, parent)
        self._prompt_path = prompt_path
        self._ollama_model = ollama_model

    def _process(self) -> JobResult:
        self.log.emit("Starting meeting notes generation...")
        self.log.emit("Transcribing audio...")
        self.progress.emit(10)
        transcript = self._transcribe()
        self.progress.emit(50)

        self.log.emit("Generating notes...")
        notes = NoteGenerator().generate_notes(transcript, self._read_prompt(), self._ollama_model)
        self.log.emit("Note generation complete.")
        self.progress.emit(90)
        return JobResult(transcript=transcript, notes=notes)

    def _read_prompt(self) -> str:
        try:
            return Path(self._prompt_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise JobError(f"Could not load system prompt from {self._prompt_path}: {exc}") from exc
