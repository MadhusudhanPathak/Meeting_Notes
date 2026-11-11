"""Application paths and discovery/validation of external dependencies."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

APP_NAME = "Local Meeting Notes Generator"

WHISPER_DOWNLOAD_URL = "https://github.com/Const-me/Whisper"
MODEL_DOWNLOAD_URL = "https://huggingface.co/ggerganov/whisper.cpp/tree/main"


def app_root() -> Path:
    """Return the directory that holds the application and its runtime folders."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _list_files(directory: Path, pattern: str) -> Tuple[Path, ...]:
    if not directory.is_dir():
        return ()
    matches = (path for path in directory.glob(pattern) if path.is_file())
    return tuple(sorted(matches, key=lambda path: path.name.lower()))


@dataclass(frozen=True)
class AppConfig:
    """Resolved locations of every file and folder the application depends on."""

    input_dir: Path
    output_dir: Path
    whisper_exe: Path
    whisper_dll: Path
    model_paths: Tuple[Path, ...] = ()
    prompt_paths: Tuple[Path, ...] = ()

    @classmethod
    def discover(cls, root: Path) -> AppConfig:
        """Build a configuration by scanning ``root`` and its ``input`` folder."""
        input_dir = root / "input"
        return cls(
            input_dir=input_dir,
            output_dir=root / "output",
            whisper_exe=root / "Whisper.exe",
            whisper_dll=root / "Whisper.dll",
            model_paths=_list_files(input_dir, "*.bin"),
            prompt_paths=_list_files(input_dir, "*.txt"),
        )

    def ensure_directories(self) -> None:
        """Create the input and output folders if they are missing."""
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def transcription_errors(self) -> List[str]:
        """Return the problems that prevent audio transcription."""
        errors = []
        for path in (self.whisper_exe, self.whisper_dll):
            if not path.exists():
                errors.append(
                    f"ERROR: {path.name} not found in current directory. Please download Whisper.cpp "
                    f"binaries from {WHISPER_DOWNLOAD_URL} and place {path.name} in the same "
                    "directory as main.py"
                )
        if not self.model_paths:
            errors.append(
                f"ERROR: No .bin model file found in {self.input_dir.name}. Please download a model "
                f"file from {MODEL_DOWNLOAD_URL} and place it in the input folder. You can have "
                "multiple .bin files in the input folder and select from the dropdown."
            )
        return errors

    def prompt_errors(self) -> List[str]:
        """Return the problems that prevent note generation from having a system prompt."""
        if self.prompt_paths:
            return []
        return [
            f"ERROR: No .txt system prompt file found in {self.input_dir.name}. Please create a "
            "text file with your base system prompt for meeting notes generation in the input "
            "folder. You can have multiple system prompt files in the input folder and select "
            "from the dropdown."
        ]

    def validate(self) -> List[str]:
        """Return every configuration problem followed by guidance, or an empty list."""
        errors = self.transcription_errors() + self.prompt_errors()
        if errors:
            errors += [
                "",
                "INFO: For more information, please read the README.md file in the project directory.",
                f"INFO: You can download .bin model files from {MODEL_DOWNLOAD_URL}",
                "INFO: Create a text file with your system prompt in the input folder "
                "(e.g., System_Prompt_Meeting_Notes.txt)",
            ]
        return errors
