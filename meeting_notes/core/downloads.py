"""Downloading Whisper models from Hugging Face."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple

import requests

from meeting_notes.core.control import JobCancelled, JobControl

WHISPER_MODEL_BASE_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/"
CHUNK_BYTES = 1024 * 1024
CONNECT_TIMEOUT_SECONDS = 15
READ_TIMEOUT_SECONDS = 60

ProgressCallback = Optional[Callable[[int, int], None]]


class DownloadError(Exception):
    """Raised when a model download fails."""


@dataclass(frozen=True)
class WhisperModelSpec:
    """A downloadable Whisper model in the ggml format."""

    name: str
    size_label: str
    note: str
    whisper_cpp_only: bool = False

    @property
    def filename(self) -> str:
        return f"ggml-{self.name}.bin"

    @property
    def url(self) -> str:
        return WHISPER_MODEL_BASE_URL + self.filename

    @property
    def label(self) -> str:
        return f"{self.name} ({self.size_label}) - {self.note}"


WHISPER_MODELS: Tuple[WhisperModelSpec, ...] = (
    WhisperModelSpec("tiny", "75 MB", "fastest, lowest accuracy"),
    WhisperModelSpec("tiny.en", "75 MB", "English only"),
    WhisperModelSpec("base", "142 MB", "fast, basic accuracy"),
    WhisperModelSpec("base.en", "142 MB", "English only"),
    WhisperModelSpec("small", "466 MB", "good balance for slower PCs"),
    WhisperModelSpec("small.en", "466 MB", "English only"),
    WhisperModelSpec("medium", "1.5 GB", "recommended"),
    WhisperModelSpec("medium.en", "1.5 GB", "English only"),
    WhisperModelSpec("large-v2", "2.9 GB", "most accurate, slowest"),
    WhisperModelSpec("large-v1", "2.9 GB", "older large model"),
    WhisperModelSpec("large-v3-turbo", "1.6 GB", "fast and accurate (whisper.cpp only)", True),
    WhisperModelSpec("large-v3", "3.1 GB", "most accurate (whisper.cpp only)", True),
)


def available_whisper_models(const_me_engine: bool) -> Tuple[WhisperModelSpec, ...]:
    """Return the models the active engine can load; Const-me cannot load large-v3 models."""
    if const_me_engine:
        return tuple(spec for spec in WHISPER_MODELS if not spec.whisper_cpp_only)
    return WHISPER_MODELS


def download_whisper_model(
    spec: WhisperModelSpec,
    destination_dir: Path,
    on_progress: ProgressCallback = None,
    control: Optional[JobControl] = None,
) -> Path:
    """
    Download ``spec`` into ``destination_dir`` and return the saved path.

    The file is written to a ``.part`` file first and renamed only when complete.

    Raises:
        DownloadError: If the download fails.
        JobCancelled: If ``control`` is cancelled.
    """
    destination_dir.mkdir(parents=True, exist_ok=True)
    target = destination_dir / spec.filename
    partial = target.with_name(target.name + ".part")
    try:
        with requests.get(
            spec.url, stream=True, timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS)
        ) as response:
            response.raise_for_status()
            total = int(response.headers.get("Content-Length", 0) or 0)
            done = 0
            with (control.attach(abort=response.close) if control else nullcontext()):
                with partial.open("wb") as handle:
                    for chunk in response.iter_content(CHUNK_BYTES):
                        if control is not None:
                            control.checkpoint()
                        handle.write(chunk)
                        done += len(chunk)
                        if on_progress is not None:
                            on_progress(done, total)
        if total and done != total:
            raise DownloadError(
                f"Download of {spec.filename} was incomplete ({done} of {total} bytes)."
            )
        partial.replace(target)
        return target
    except JobCancelled:
        _remove(partial)
        raise
    except Exception as exc:
        _remove(partial)
        if control is not None and control.is_cancelled:
            raise JobCancelled() from exc
        if isinstance(exc, DownloadError):
            raise
        if isinstance(exc, (requests.exceptions.RequestException, OSError, AttributeError)):
            raise DownloadError(f"Could not download {spec.filename}: {exc}") from exc
        raise


def _remove(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass
