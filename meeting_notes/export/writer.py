"""Output file naming and writing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from meeting_notes.export.pdf import render_markdown_pdf

TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"


def timestamped_stem(base_name: str, now: Optional[datetime] = None) -> str:
    """Return ``{base_name}_YYYY-MM-DD_HH-MM-SS``."""
    return f"{base_name}_{(now or datetime.now()).strftime(TIMESTAMP_FORMAT)}"


@dataclass(frozen=True)
class OutputPaths:
    """Destination files for one processed media file, sharing a single timestamp."""

    transcript: Path
    notes_markdown: Path
    notes_pdf: Path
    subtitles_srt: Path
    subtitles_vtt: Path

    @classmethod
    def for_media(
        cls, media_path: Union[str, Path], output_dir: Path, now: Optional[datetime] = None
    ) -> OutputPaths:
        stem = timestamped_stem(Path(media_path).stem, now)
        candidate = cls._build(output_dir, stem)
        suffix = 2
        while any(path.exists() for path in candidate.all()):
            candidate = cls._build(output_dir, f"{stem}_{suffix}")
            suffix += 1
        return candidate

    @classmethod
    def _build(cls, output_dir: Path, stem: str) -> OutputPaths:
        return cls(
            transcript=output_dir / f"{stem}_transcript.txt",
            notes_markdown=output_dir / f"{stem}_notes.md",
            notes_pdf=output_dir / f"{stem}_notes.pdf",
            subtitles_srt=output_dir / f"{stem}.srt",
            subtitles_vtt=output_dir / f"{stem}.vtt",
        )

    def all(self) -> tuple:
        return (
            self.transcript, self.notes_markdown, self.notes_pdf,
            self.subtitles_srt, self.subtitles_vtt,
        )


def write_text(path: Path, content: str) -> None:
    """Write ``content`` as UTF-8, creating parent folders as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_pdf(path: Path, markdown: str, subtitle: Optional[str] = None) -> None:
    """Render ``markdown`` to a PDF at ``path`` (requires a running QApplication)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    render_markdown_pdf(markdown, path, subtitle)
