"""Output file naming and writing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"


def timestamped_stem(base_name: str, now: Optional[datetime] = None) -> str:
    """Return ``{base_name}_YYYY-MM-DD_HH-MM-SS``."""
    return f"{base_name}_{(now or datetime.now()).strftime(TIMESTAMP_FORMAT)}"


@dataclass(frozen=True)
class OutputPaths:
    """Destination files for one processed audio file, sharing a single timestamp."""

    transcript: Path
    notes_markdown: Path
    notes_pdf: Path

    @classmethod
    def for_audio(
        cls, audio_path: Union[str, Path], output_dir: Path, now: Optional[datetime] = None
    ) -> OutputPaths:
        stem = timestamped_stem(Path(audio_path).stem, now)
        return cls(
            transcript=output_dir / f"{stem}_transcript.txt",
            notes_markdown=output_dir / f"{stem}_notes.md",
            notes_pdf=output_dir / f"{stem}_notes.pdf",
        )


def write_text(path: Path, content: str) -> None:
    """Write ``content`` as UTF-8, creating parent folders as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_pdf(path: Path, markdown: str) -> None:
    """
    Render ``markdown`` to a PDF at ``path``.

    Raises:
        ImportError: If reportlab is not installed.
    """
    from meeting_notes.export.pdf import render_markdown_pdf

    path.parent.mkdir(parents=True, exist_ok=True)
    render_markdown_pdf(markdown, path)
