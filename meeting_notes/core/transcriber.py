"""Audio-to-text transcription through the Whisper.cpp command-line executable."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Tuple, Union

PathLike = Union[str, Path]

AUDIO_EXTENSIONS: Tuple[str, ...] = (".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg")


class TranscriptionError(Exception):
    """Raised when Whisper.cpp fails to produce a transcript."""


def is_supported_audio_file(path: PathLike) -> bool:
    """Return whether ``path`` has one of the supported audio extensions."""
    return Path(path).suffix.lower() in AUDIO_EXTENSIONS


class AudioTranscriber:
    """Runs Whisper.exe with a given model to transcribe audio files."""

    def __init__(self, executable: PathLike, model_path: PathLike) -> None:
        """
        Args:
            executable: Path to Whisper.exe.
            model_path: Path to a Whisper ``.bin`` model.

        Raises:
            FileNotFoundError: If the executable or the model does not exist.
        """
        self.executable = Path(executable)
        self.model_path = Path(model_path)
        if not self.executable.exists():
            raise FileNotFoundError(f"Whisper.exe not found at {self.executable}")
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found at {self.model_path}")

    def transcribe(self, audio_path: PathLike) -> str:
        """
        Transcribe ``audio_path`` and return the text.

        Whisper writes ``<audio>.txt`` next to the audio file; that file is read
        and then removed.

        Raises:
            FileNotFoundError: If the audio file does not exist.
            TranscriptionError: If Whisper fails or its output cannot be read.
        """
        audio = Path(audio_path)
        if not audio.exists():
            raise FileNotFoundError(f"Audio file not found at {audio}")

        output_file = audio.with_suffix(".txt")
        command = [str(self.executable), "-m", str(self.model_path), "-f", str(audio), "-otxt"]

        try:
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                errors="replace",
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise TranscriptionError(f"Could not run {self.executable.name}: {exc}") from exc

        if completed.returncode != 0:
            raise TranscriptionError(f"Error during transcription: {completed.stderr.strip()}")
        if not output_file.exists():
            raise TranscriptionError(f"Transcription output file not found: {output_file}")

        try:
            transcript = output_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise TranscriptionError(f"Could not read transcript {output_file}: {exc}") from exc

        try:
            output_file.unlink()
        except OSError:
            pass
        return transcript
