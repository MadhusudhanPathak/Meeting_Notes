"""Background threads that keep long-running work off the UI thread."""

from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from meeting_notes.config import AppConfig
from meeting_notes.core.control import JobCancelled, JobControl
from meeting_notes.core.downloads import DownloadError, WhisperModelSpec, download_whisper_model
from meeting_notes.core.media import media_duration_seconds
from meeting_notes.core.note_generator import NoteGenerationError, NoteGenerator
from meeting_notes.core.transcriber import (
    AudioTranscriber,
    TranscriptionError,
    TranscriptionOptions,
    list_gpu_adapters,
)

BUSY = -1
_PROGRESS_LOG_INTERVAL_SECONDS = 60


def format_clock(seconds: float) -> str:
    """Format seconds as ``H:MM:SS`` or ``M:SS``."""
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


class JobError(Exception):
    """Raised for an expected job failure that carries a user-facing message."""


@dataclass(frozen=True)
class JobRequest:
    """Everything a worker needs to process one media file."""

    whisper_exe: Path
    model_path: Path
    ffmpeg: Optional[Path]
    media_path: str
    options: TranscriptionOptions
    include_timestamps: bool
    save_subtitles: bool
    prompt_path: Optional[Path] = None
    ollama_model: str = ""


@dataclass(frozen=True)
class JobResult:
    """Output of a finished job; ``notes`` is ``None`` for transcription-only jobs."""

    transcript: str
    notes: Optional[str] = None
    srt: Optional[str] = None
    vtt: Optional[str] = None


@dataclass(frozen=True)
class DependencyReport:
    """Result of the startup/refresh dependency check."""

    config: AppConfig
    ollama_models: List[str] = field(default_factory=list)
    ollama_warning: Optional[str] = None
    gpu_adapters: List[str] = field(default_factory=list)


class DependencyCheckWorker(QThread):
    """Discovers files, queries Ollama, and lists GPUs without blocking the UI."""

    report_ready = pyqtSignal(object)

    def __init__(
        self, root: Path, note_generator: NoteGenerator, parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)
        self._root = root
        self._note_generator = note_generator

    def run(self) -> None:
        config = AppConfig.discover(self._root)
        try:
            config.ensure_directories()
        except OSError:
            pass
        models: List[str] = []
        warning: Optional[str] = None
        try:
            models = self._note_generator.get_available_models()
        except NoteGenerationError as exc:
            warning = f"WARNING: {exc} Note generation feature will be disabled."
        if not models and warning is None:
            warning = (
                "WARNING: No Ollama models found. Note generation feature will be disabled. "
                "Use 'Download Models' or run 'ollama pull <model>' in a terminal."
            )
        whisper = config.whisper_exe
        adapters = list_gpu_adapters(whisper) if whisper is not None and whisper.exists() else []
        self.report_ready.emit(DependencyReport(config, models, warning, adapters))


class _JobWorker(QThread):
    """
    Base job worker. Emits ``result_ready`` exactly once with a ``JobResult``,
    or with ``None`` after logging why the job failed or was cancelled.

    ``progress`` carries a percentage, or ``BUSY`` when the amount of work is unknown.
    """

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    log = pyqtSignal(str)
    result_ready = pyqtSignal(object)

    transcription_share = 90

    def __init__(
        self, request: JobRequest, control: JobControl, parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)
        self._request = request
        self._control = control

    def run(self) -> None:
        try:
            self._control.checkpoint()
            result = self._process()
        except JobCancelled:
            message = "Cancelled."
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

    def _transcribe(self) -> JobResult:
        request = self._request
        self.log.emit("Transcribing audio...")
        duration = media_duration_seconds(request.media_path)
        if duration:
            self.log.emit(f"Media length: {format_clock(duration)}")
        self.progress.emit(BUSY)
        self.status.emit("Loading the transcription model...")

        last_logged = [0.0]

        def on_progress(seconds: float) -> None:
            position = format_clock(seconds)
            if duration:
                fraction = min(seconds / duration, 1.0)
                self.progress.emit(int(fraction * self.transcription_share))
                self.status.emit(f"Transcribing: {position} of {format_clock(duration)}")
            else:
                self.status.emit(f"Transcribing: {position} processed")
            now = time.monotonic()
            if now - last_logged[0] >= _PROGRESS_LOG_INTERVAL_SECONDS:
                last_logged[0] = now
                self.log.emit(f"Transcribed up to {position}")

        transcriber = AudioTranscriber(request.whisper_exe, request.model_path, request.ffmpeg)
        transcript = transcriber.transcribe(
            request.media_path, request.options, on_progress=on_progress, control=self._control
        )
        self.log.emit("Transcription complete.")
        self.progress.emit(self.transcription_share)
        subtitles = (transcript.srt, transcript.vtt) if request.save_subtitles else (None, None)
        return JobResult(
            transcript=transcript.text(request.include_timestamps),
            srt=subtitles[0],
            vtt=subtitles[1],
        )


class TranscriptionWorker(_JobWorker):
    """Transcribes one media file; does not require Ollama."""

    def _process(self) -> JobResult:
        self.log.emit("Starting audio transcription...")
        return self._transcribe()


class NotesWorker(_JobWorker):
    """Transcribes one media file, then generates meeting notes with Ollama."""

    transcription_share = 50

    def _process(self) -> JobResult:
        self.log.emit("Starting meeting notes generation...")
        result = self._transcribe()

        self.log.emit("Generating notes...")
        self.progress.emit(BUSY)
        self.status.emit("Generating notes (the model is reading the transcript)...")

        def on_status(message: str) -> None:
            self.log.emit(message)
            self.status.emit(message)

        def on_fraction(fraction: float) -> None:
            self.progress.emit(self.transcription_share + int(fraction * 40))

        notes = NoteGenerator().generate_notes(
            result.transcript,
            self._read_prompt(),
            self._request.ollama_model,
            control=self._control,
            on_status=on_status,
            on_fraction=on_fraction,
        )
        self.log.emit("Note generation complete.")
        self.progress.emit(90)
        return JobResult(transcript=result.transcript, notes=notes, srt=result.srt, vtt=result.vtt)

    def _read_prompt(self) -> str:
        path = self._request.prompt_path
        if path is None:
            raise JobError("No system prompt was selected.")
        try:
            return Path(path).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            raise JobError(f"Could not load system prompt from {path}: {exc}") from exc


class DownloadWorker(QThread):
    """Downloads a Whisper model from Hugging Face or pulls an Ollama model."""

    progress = pyqtSignal(object, object)
    status = pyqtSignal(str)
    succeeded = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(
        self,
        control: JobControl,
        whisper_spec: Optional[WhisperModelSpec] = None,
        destination: Optional[Path] = None,
        ollama_model: Optional[str] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._control = control
        self._whisper_spec = whisper_spec
        self._destination = destination
        self._ollama_model = ollama_model

    def run(self) -> None:
        try:
            if self._whisper_spec is not None and self._destination is not None:
                self.status.emit(f"Downloading {self._whisper_spec.filename}...")
                path = download_whisper_model(
                    self._whisper_spec, self._destination, self.progress.emit, self._control
                )
                self.succeeded.emit(f"Saved {path.name} to {path.parent}")
            elif self._ollama_model:
                NoteGenerator().pull_model(self._ollama_model, self._on_pull, self._control)
                self.succeeded.emit(f"Ollama model '{self._ollama_model}' is ready.")
        except JobCancelled:
            self.failed.emit("Download cancelled.")
        except (DownloadError, NoteGenerationError) as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # Thread boundary: report anything else instead of dying silently.
            self.failed.emit(f"Download failed: {exc}")

    def _on_pull(self, status: str, completed: int, total: int) -> None:
        self.status.emit(status.capitalize() if status else "Downloading...")
        self.progress.emit(completed, total)
