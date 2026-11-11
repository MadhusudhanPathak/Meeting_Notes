"""
Audio/video-to-text transcription through a Whisper command-line executable.

Two engines are supported:

* Const-me's ``Whisper.exe`` (Windows, DirectCompute GPU), shipped with the app.
* whisper.cpp's ``whisper-cli`` (Linux and macOS). Formats it cannot read
  natively are converted to WAV with ffmpeg first.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Iterator, List, Optional, Tuple, Union

from meeting_notes.core.control import JobCancelled, JobControl
from meeting_notes.core.languages import DEFAULT_LANGUAGE
from meeting_notes.core.media import set_process_suspended

PathLike = Union[str, Path]

AUDIO_EXTENSIONS: Tuple[str, ...] = (".mp3", ".wav", ".m4a", ".flac", ".aac", ".wma")
VIDEO_EXTENSIONS: Tuple[str, ...] = (".mp4", ".m4v", ".mov", ".wmv", ".avi", ".mkv")
MEDIA_EXTENSIONS: Tuple[str, ...] = AUDIO_EXTENSIONS + VIDEO_EXTENSIONS

WHISPER_CPP_NATIVE_EXTENSIONS: Tuple[str, ...] = (".wav", ".mp3", ".flac")

_OUTPUT_SUFFIXES = (".txt", ".srt", ".vtt")
_SEGMENT_LINE = re.compile(
    r"^\[(?:(\d+):)?(\d{2}):(\d{2})\.(\d{3}) --> (?:(\d+):)?(\d{2}):(\d{2})\.(\d{3})\]\s*(.*)$"
)
_SRT_TIMES = re.compile(
    r"(\d+):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d+):(\d{2}):(\d{2})[,.](\d{3})"
)
_ADAPTER_LINE = re.compile(r'^\s*"(.+)"\s*$')
_CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
_ADAPTER_QUERY_TIMEOUT_SECONDS = 30


class TranscriptionError(Exception):
    """Raised when Whisper fails to produce a transcript."""


class WhisperEngine(Enum):
    CONST_ME = "Const-me Whisper"
    WHISPER_CPP = "whisper.cpp"


def engine_for(executable: PathLike) -> WhisperEngine:
    """Const-me's build is named ``Whisper.exe``; anything else is treated as whisper.cpp."""
    if Path(executable).name.lower() == "whisper.exe":
        return WhisperEngine.CONST_ME
    return WhisperEngine.WHISPER_CPP


def is_supported_media_file(path: PathLike) -> bool:
    """Return whether ``path`` has one of the supported audio or video extensions."""
    return Path(path).suffix.lower() in MEDIA_EXTENSIONS


@dataclass(frozen=True)
class TranscriptionOptions:
    """Per-run Whisper settings."""

    language: str = DEFAULT_LANGUAGE
    translate: bool = False
    gpu: Optional[str] = None


@dataclass(frozen=True)
class Transcript:
    """Whisper output in every format the application uses."""

    timestamped_text: str
    srt: str
    vtt: str

    def plain_text(self) -> str:
        """Return the transcript with the ``[start --> end]`` prefixes removed."""
        lines = []
        for line in self.timestamped_text.splitlines():
            match = _SEGMENT_LINE.match(line.strip())
            lines.append(match.group(9).strip() if match else line.strip())
        return "\n".join(line for line in lines if line)

    def text(self, include_timestamps: bool) -> str:
        return self.timestamped_text.strip() if include_timestamps else self.plain_text()


def segment_end_seconds(line: str) -> Optional[float]:
    """Return the end time of a Whisper console segment line, if ``line`` is one."""
    match = _SEGMENT_LINE.match(line.strip())
    if not match:
        return None
    hours, minutes, seconds, millis = (int(value or 0) for value in match.groups()[4:8])
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def srt_to_timestamped_text(srt: str) -> str:
    """Convert SRT subtitles into ``[HH:MM:SS.mmm --> HH:MM:SS.mmm]  text`` lines."""
    lines = []
    for block in re.split(r"\n\s*\n", srt.strip()):
        rows = [row.strip() for row in block.splitlines()]
        for position, row in enumerate(rows):
            match = _SRT_TIMES.search(row)
            if match:
                h1, m1, s1, ms1, h2, m2, s2, ms2 = match.groups()
                text = " ".join(item for item in rows[position + 1:] if item)
                lines.append(
                    f"[{int(h1):02d}:{m1}:{s1}.{ms1} --> {int(h2):02d}:{m2}:{s2}.{ms2}]  {text}"
                )
                break
    return "\n".join(lines)


def list_gpu_adapters(executable: PathLike) -> List[str]:
    """Return the graphics adapters Whisper.exe can use; whisper.cpp picks its GPU itself."""
    if engine_for(executable) is not WhisperEngine.CONST_ME:
        return []
    try:
        completed = subprocess.run(
            [str(Path(executable).resolve()), "-la"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=_ADAPTER_QUERY_TIMEOUT_SECONDS,
            creationflags=_CREATE_NO_WINDOW,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    adapters: List[str] = []
    for line in completed.stdout.splitlines():
        match = _ADAPTER_LINE.match(line)
        if match and match.group(1) not in adapters:
            adapters.append(match.group(1))
    return adapters


class AudioTranscriber:
    """Runs a Whisper executable with a given model to transcribe audio and video files."""

    def __init__(
        self, executable: PathLike, model_path: PathLike, ffmpeg: Optional[PathLike] = None
    ) -> None:
        """
        Args:
            executable: ``Whisper.exe`` (Const-me) or ``whisper-cli`` (whisper.cpp).
            model_path: Path to a Whisper ``.bin`` model.
            ffmpeg: ffmpeg executable, used to convert media whisper.cpp cannot read.

        Raises:
            FileNotFoundError: If the executable or the model does not exist.
        """
        self.executable = Path(executable).resolve()
        self.model_path = Path(model_path).resolve()
        self.ffmpeg = Path(ffmpeg) if ffmpeg else None
        self.engine = engine_for(self.executable)
        if not self.executable.exists():
            raise FileNotFoundError(f"{self.executable.name} not found at {self.executable}")
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found at {self.model_path}")

    def transcribe(
        self,
        media_path: PathLike,
        options: TranscriptionOptions = TranscriptionOptions(),
        on_progress: Optional[Callable[[float], None]] = None,
        control: Optional[JobControl] = None,
    ) -> Transcript:
        """
        Transcribe ``media_path``.

        Args:
            media_path: Audio or video file to transcribe.
            options: Language, translation, and GPU settings.
            on_progress: Called with the number of seconds of audio processed so far.
                Whisper buffers its console output, so updates arrive in bursts.
            control: Optional pause/cancel control; pausing suspends the Whisper process.

        Raises:
            FileNotFoundError: If the media file does not exist.
            TranscriptionError: If Whisper fails or its output cannot be read.
            JobCancelled: If ``control`` is cancelled.
        """
        media = Path(media_path)
        if not media.exists():
            raise FileNotFoundError(f"Audio file not found at {media}")

        with _staged_copy(media) as staged:
            if (
                self.engine is WhisperEngine.WHISPER_CPP
                and staged.suffix not in WHISPER_CPP_NATIVE_EXTENSIONS
            ):
                staged = self._convert_to_wav(staged, control)
            command = self._command(staged, options)
            stderr = self._run(command, on_progress, control)
            return self._read_outputs(staged, stderr)

    def _command(self, media: Path, options: TranscriptionOptions) -> List[str]:
        command = [
            str(self.executable), "-m", str(self.model_path), "-f", str(media),
            "-l", options.language or DEFAULT_LANGUAGE, "-otxt", "-osrt", "-ovtt",
        ]
        if self.engine is WhisperEngine.CONST_ME:
            command.append("-nc")
            if options.gpu:
                command += ["-gpu", options.gpu]
        else:
            command += ["-of", str(media.with_suffix(""))]
        if options.translate:
            command.append("-tr")
        return command

    def _convert_to_wav(self, media: Path, control: Optional[JobControl]) -> Path:
        """Convert ``media`` to 16 kHz mono WAV next to it, for whisper.cpp."""
        if self.ffmpeg is None:
            raise TranscriptionError(
                f"whisper.cpp cannot read {media.suffix} files directly. Install ffmpeg "
                "(for example 'brew install ffmpeg' or 'sudo apt install ffmpeg') or use a "
                "WAV, MP3, or FLAC file."
            )
        target = media.with_name(media.stem + "_16k.wav")
        command = [
            str(self.ffmpeg), "-nostdin", "-y", "-loglevel", "error", "-i", str(media),
            "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(target),
        ]
        stderr = self._run(command, None, control, failure="Converting media with ffmpeg failed")
        if not target.exists():
            raise TranscriptionError(f"ffmpeg did not produce {target.name}: {_tail(stderr)}")
        return target

    def _run(
        self,
        command: List[str],
        on_progress: Optional[Callable[[float], None]],
        control: Optional[JobControl],
        failure: str = "Error during transcription",
    ) -> str:
        """Run a subprocess, report Whisper progress, and return its stderr output."""
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=_CREATE_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise TranscriptionError(f"Could not run {Path(command[0]).name}: {exc}") from exc

        stderr_chunks: List[bytes] = []
        stderr_reader = threading.Thread(
            target=lambda: stderr_chunks.append(process.stderr.read()), daemon=True
        )
        stderr_reader.start()

        hooks = {
            "pause": lambda: set_process_suspended(process.pid, True),
            "resume": lambda: set_process_suspended(process.pid, False),
            "abort": process.kill,
        }
        with (control.attach(**hooks) if control else nullcontext()):
            for raw_line in process.stdout:
                seconds = segment_end_seconds(raw_line.decode("utf-8", errors="replace"))
                if seconds is not None and on_progress is not None:
                    on_progress(seconds)
            return_code = process.wait()
        stderr_reader.join()

        if control is not None and control.is_cancelled:
            raise JobCancelled()
        stderr = b"".join(stderr_chunks).decode("utf-8", errors="replace").strip()
        if return_code != 0:
            raise TranscriptionError(f"{failure}: {_tail(stderr)}")
        return stderr

    def _read_outputs(self, media: Path, stderr: str) -> Transcript:
        texts = []
        for suffix in _OUTPUT_SUFFIXES:
            output = media.with_suffix(suffix)
            if not output.exists():
                detail = f" Whisper reported: {_tail(stderr)}" if stderr else ""
                raise TranscriptionError(f"Transcription output file not found: {output}.{detail}")
            try:
                texts.append(output.read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeDecodeError) as exc:
                raise TranscriptionError(f"Could not read transcript {output}: {exc}") from exc
        timestamped = texts[0]
        if self.engine is WhisperEngine.WHISPER_CPP:
            timestamped = srt_to_timestamped_text(texts[1])
        return Transcript(timestamped_text=timestamped, srt=texts[1], vtt=texts[2])


def _tail(text: str, limit: int = 600) -> str:
    return text if len(text) <= limit else "..." + text[-limit:]


@contextmanager
def _staged_copy(media: Path) -> Iterator[Path]:
    """
    Yield a private path to ``media`` inside a temporary folder.

    Whisper writes its .txt/.srt/.vtt files next to the input, so working on a
    private link (or copy) never overwrites the user's own files and keeps the
    path free of characters the CLI may not handle.
    """
    staged_name = "media" + media.suffix.lower()
    attempts = (
        (None, os.link),
        (media.parent, os.link),
        (None, shutil.copy2),
    )
    last_error: Optional[OSError] = None
    for parent, place in attempts:
        try:
            folder = Path(tempfile.mkdtemp(prefix="meeting_notes_", dir=parent))
        except OSError as exc:
            last_error = exc
            continue
        staged = folder / staged_name
        try:
            place(str(media), str(staged))
        except OSError as exc:
            last_error = exc
            shutil.rmtree(folder, ignore_errors=True)
            continue
        try:
            yield staged
        finally:
            shutil.rmtree(folder, ignore_errors=True)
        return
    raise TranscriptionError(f"Could not prepare {media.name} for transcription: {last_error}")
