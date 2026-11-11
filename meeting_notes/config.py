"""Application paths and discovery/validation of external dependencies."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from meeting_notes.core.media import find_program

APP_NAME = "Local Meeting Notes Generator"

WHISPER_DOWNLOAD_URL = "https://github.com/Const-me/Whisper"
WHISPER_CPP_URL = "https://github.com/ggml-org/whisper.cpp"
MODEL_DOWNLOAD_URL = "https://huggingface.co/ggerganov/whisper.cpp/tree/main"
WHISPER_CPP_NAMES = ("whisper-cli", "whisper-cpp")
MACOS_DATA_FOLDER = "MeetingNotes"


def app_root() -> Path:
    """
    Return the folder that holds ``input/``, ``output/`` and, on Windows, Whisper.exe.

    This is the project folder when running from source and the executable's folder
    in a packaged build. A macOS ``.app`` bundle must not be written to, so packaged
    macOS builds use ``~/MeetingNotes`` instead.
    """
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            return Path.home() / MACOS_DATA_FOLDER
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_root() -> Path:
    """Return the directory holding bundled read-only resources (prompts, assets)."""
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return Path(bundle_dir)
    return Path(__file__).resolve().parent.parent


def _list_files(directory: Path, pattern: str) -> Tuple[Path, ...]:
    if not directory.is_dir():
        return ()
    matches = (path for path in directory.glob(pattern) if path.is_file())
    return tuple(sorted(matches, key=lambda path: path.name.lower()))


@dataclass(frozen=True)
class AppConfig:
    """
    Resolved locations of every file and folder the application depends on.

    On Windows the transcription engine is Const-me's ``Whisper.exe`` + ``Whisper.dll``
    in the application folder. Elsewhere it is whisper.cpp's ``whisper-cli`` (in the
    application folder or on PATH), with ffmpeg used for formats it cannot read.
    """

    input_dir: Path
    output_dir: Path
    whisper_exe: Optional[Path]
    whisper_dll: Optional[Path] = None
    ffmpeg: Optional[Path] = None
    windows: bool = sys.platform == "win32"
    model_paths: Tuple[Path, ...] = ()
    user_prompt_paths: Tuple[Path, ...] = ()
    builtin_prompt_paths: Tuple[Path, ...] = ()

    @classmethod
    def discover(
        cls, root: Path, resources: Optional[Path] = None, windows: Optional[bool] = None
    ) -> AppConfig:
        """Build a configuration by scanning ``root``, its ``input`` folder, and bundled prompts."""
        windows = sys.platform == "win32" if windows is None else windows
        input_dir = root / "input"
        if windows:
            whisper_exe: Optional[Path] = root / "Whisper.exe"
            whisper_dll: Optional[Path] = root / "Whisper.dll"
            ffmpeg = None
        else:
            whisper_exe = find_program(WHISPER_CPP_NAMES, search_first=root)
            whisper_dll = None
            ffmpeg = find_program(["ffmpeg"])
        return cls(
            input_dir=input_dir,
            output_dir=root / "output",
            whisper_exe=whisper_exe,
            whisper_dll=whisper_dll,
            ffmpeg=ffmpeg,
            windows=windows,
            model_paths=_list_files(input_dir, "*.bin"),
            user_prompt_paths=_list_files(input_dir, "*.txt"),
            builtin_prompt_paths=_list_files((resources or resource_root()) / "prompts", "*.txt"),
        )

    @property
    def prompt_paths(self) -> Tuple[Path, ...]:
        """All system prompts: the user's own first, then the bundled defaults."""
        return self.user_prompt_paths + self.builtin_prompt_paths

    def is_builtin_prompt(self, path: Path) -> bool:
        return path in self.builtin_prompt_paths

    def ensure_directories(self) -> None:
        """Create the input and output folders if they are missing."""
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def transcription_errors(self) -> List[str]:
        """Return the problems that prevent audio transcription."""
        errors = []
        if self.windows:
            for path in (self.whisper_exe, self.whisper_dll):
                if path is not None and not path.exists():
                    errors.append(
                        f"ERROR: {path.name} not found in the application folder. Please "
                        f"download the Whisper binaries from {WHISPER_DOWNLOAD_URL} and place "
                        f"{path.name} next to the application."
                    )
        elif self.whisper_exe is None:
            errors.append(
                "ERROR: whisper-cli (whisper.cpp) not found. Install it (macOS: "
                f"'brew install whisper-cpp'; Linux: build it from {WHISPER_CPP_URL}) or "
                "place the whisper-cli binary next to the application."
            )
        if not self.model_paths:
            errors.append(
                f"ERROR: No .bin model file found in {self.input_dir.name}. Please use "
                f"'Download Models' or download a model file from {MODEL_DOWNLOAD_URL} and "
                "place it in the input folder. You can have multiple .bin files in the input "
                "folder and select from the dropdown."
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

    def warnings(self) -> List[str]:
        """Return non-blocking issues worth telling the user about."""
        if not self.windows and self.ffmpeg is None:
            return [
                "WARNING: ffmpeg not found, so only WAV, MP3, and FLAC files can be "
                "transcribed. Install ffmpeg to transcribe video and other audio formats."
            ]
        return []

    def validate(self) -> List[str]:
        """Return every configuration problem followed by guidance, or an empty list."""
        errors = self.transcription_errors() + self.prompt_errors()
        if errors:
            errors += [
                "",
                "INFO: For more information, please read the README.md file in the project "
                "directory.",
                f"INFO: You can download .bin model files from {MODEL_DOWNLOAD_URL}",
                "INFO: Create a text file with your system prompt in the input folder "
                "(e.g., System_Prompt_Meeting_Notes.txt)",
            ]
        return errors
