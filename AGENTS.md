# AGENTS.md

How this codebase is organized, what each component is responsible for, and the rules to follow when changing it. Read [README.md](README.md) for installation and usage. Packaging instructions (`BUILDING.md`) are published with each GitHub release.

## System overview

A PyQt5 desktop application that runs two local AI components in sequence:

1. **Whisper** (run as a subprocess) converts audio or video into a transcript and subtitles. On Windows this is Const-me Whisper (`Whisper.exe` + `Whisper.dll`, shipped in the repository root). On Linux and macOS it is whisper.cpp's `whisper-cli`, which users install themselves. ffmpeg converts formats `whisper-cli` cannot read.
2. **Ollama** (HTTP API at `http://localhost:11434`) turns the transcript into meeting notes, following a system prompt.

Everything runs locally. Network traffic goes only to the local Ollama server, and to Hugging Face or the Ollama library when the user downloads a model.

## Components

### Configuration — `meeting_notes/config.py`

- **Role:** Single source of truth for file locations and the active transcription engine.
- **Responsibilities:**
  - Resolve the application root: the project folder from source, or the executable's folder in a packaged build. Packaged macOS builds use `~/MeetingNotes`, because an `.app` bundle must not be written to.
  - Resolve the resource root for bundled `prompts/` and `assets/` (`sys._MEIPASS` when packaged).
  - Discover the engine: `Whisper.exe`/`Whisper.dll` on Windows; elsewhere `whisper-cli` in the app folder, on `PATH`, or in Homebrew folders, plus ffmpeg.
  - Discover `.bin` models, the user's `.txt` prompts in `input/`, and the built-in prompts in `prompts/`. Create `input/` and `output/`.
  - Report problems as blocking `transcription_errors()`/`prompt_errors()` or non-blocking `warnings()`.
- **Boundaries:** Never runs external tools or contacts Ollama. `AppConfig` is immutable; a new one is built on every startup check or refresh.

### Job control — `meeting_notes/core/control.py`

- **Role:** Thread-safe pause, resume, and cancel signals shared between the UI and a running job.
- **Contract:** Long operations call `checkpoint()` between steps and `attach()` hooks that act immediately: suspend or kill a subprocess, or close the Ollama socket. Cancellation surfaces as `JobCancelled`.

### Transcriber — `meeting_notes/core/transcriber.py`

- **Role:** Wraps the Whisper command-line tools. `engine_for()` treats `Whisper.exe` as Const-me and anything else as whisper.cpp.
- **Responsibilities:**
  - Work on a private hard link or copy of the input in a temporary folder, so the user's folder is never touched.
  - Const-me: `Whisper.exe -m <model> -f <media> -l <lang> -otxt -osrt -ovtt -nc [-tr] [-gpu <adapter>]`; `-la` lists graphics adapters.
  - whisper.cpp: `whisper-cli -m <model> -f <media> -l <lang> -otxt -osrt -ovtt -of <prefix> [-tr]`. Inputs other than WAV/MP3/FLAC are first converted to 16 kHz WAV with ffmpeg. Timestamped text is rebuilt from the SRT output, because whisper.cpp's `.txt` has no timestamps.
  - Parse segment lines on stdout for progress. They arrive in bursts because the tools buffer their output.
  - Return a `Transcript` with timestamped text, plain text, SRT, and VTT.
  - Define the supported extensions (`AUDIO_EXTENSIONS`, `VIDEO_EXTENSIONS`). Only list formats Windows Media Foundation can decode; Ogg is deliberately excluded.
- **Boundaries:** No Qt. Raises `FileNotFoundError`, `TranscriptionError`, or `JobCancelled`.

### Note generator — `meeting_notes/core/note_generator.py` and `chunking.py`

- **Role:** Client for the Ollama HTTP API.
- **Responsibilities:**
  - List models (`/api/tags`) and read each model's context length and thinking support (`/api/show`).
  - Generate notes (`/api/generate`, streamed) with `num_ctx` sized to the transcript, up to `MAX_CONTEXT_TOKENS`.
  - When a transcript does not fit, split it (`chunking.split_text`), summarise each part, condense if needed, then combine with the user's prompt.
  - Disable "thinking" for models that support it and strip `<think>` blocks.
  - Pull models (`/api/pull`).
- **Boundaries:** No Qt and no file I/O. Streaming uses a raw `http.client` connection so cancelling can close the socket even while Ollama is still reading the prompt. Failures raise `NoteGenerationError`.

### Downloads and media — `meeting_notes/core/downloads.py`, `media.py`, `languages.py`

- **`downloads.py`:** Lists the Whisper models offered for download. `large-v3` and `large-v3-turbo` are offered only with whisper.cpp, because Const-me cannot load them. Downloads go from Hugging Face to a `.part` file, which is renamed only when the download completes.
- **`media.py`:**
  - `find_program()` searches the app folder, `PATH`, and Homebrew/system folders.
  - Media duration comes from `wave` for WAV, the Windows property system on Windows, and `ffprobe` elsewhere.
  - Processes are suspended and resumed with `NtSuspendProcess` on Windows and `SIGSTOP`/`SIGCONT` on POSIX.
- **`languages.py`:** Whisper's language codes and names.

### Export — `meeting_notes/export/`

- **`writer.py`:** Builds timestamped output paths (`<stem>_<YYYY-MM-DD_HH-MM-SS>_transcript.txt`, `_notes.md`, `_notes.pdf`, `.srt`, `.vtt`). It never overwrites an existing file and writes UTF-8 text and PDFs.
- **`pdf.py`:** Converts the model's Markdown (GitHub dialect) into a styled PDF with Qt's `QTextDocument`: title block, coloured headings, bordered tables, checkboxes, shaded code, links, page numbers, and complex scripts.
  - Before rendering, it escapes angle brackets outside code, normalises bullets, and keeps single line breaks.
  - The body font is chosen per platform.
- **Boundaries:** Uses QtGui and QtPrintSupport only (no widgets). PDF rendering needs a running `QApplication` and runs on the UI thread.

### Workers — `meeting_notes/ui/workers.py`

- **Role:** Keep long work off the UI thread.
- **`DependencyCheckWorker`:** Discovers configuration, Ollama models, and GPUs at startup and on **Refresh**.
- **`TranscriptionWorker`** and **`NotesWorker`:** Process one media file each, sharing the job's `JobControl`.
  - While running, they emit `log(str)`, `status(str)`, and `progress(int)` (`BUSY` = -1 when the amount of work is unknown).
  - When finished, they emit `result_ready` exactly once, with a `JobResult` or with `None` after logging the reason.
- **`DownloadWorker`:** Whisper or Ollama model downloads for the download dialog.
- Workers never touch widgets or write output files.

### Main window — `meeting_notes/ui/main_window.py` (+ `download_dialog.py`, `preferences.py`, `styles.py`)

- **Role:** Presentation and orchestration.
- **Responsibilities:**
  - Run the dependency check and enable only the features that can work.
  - Collect selections from the file dialogs or drag and drop, and confirm before starting.
  - Run files one at a time (single or batch) and lock inputs while a job runs.
  - Drive **Pause**, **Cancel**, **Open Output Folder**, **Refresh**, and **Download Models**.
  - Save results through `export.writer`, with clickable links in the log and success dialog.
  - Remember selections with `Preferences` (QSettings).
- **Boundaries:** Holds no business logic.

### Packaging — `Releases/`

- **Role:** Turn the source into standalone packages; the project is not installed as a Python package.
- **Location:** The `Releases/` folder is ignored by git. Its files are published as assets on each GitHub release; to build, place them in `Releases/` inside a clone.
- **`MeetingNotes.spec`:** One-folder PyInstaller build for all platforms, plus a `.app` bundle on macOS. It bundles `prompts/` and the icon and drops Qt libraries the app never loads.
- **`build_release.py`:** Runs PyInstaller and copies `Whisper.exe`/`Whisper.dll` (Windows only), `LICENSE`, and `bundle/` (README, third-party notices, license texts) plus the license files of bundled Python packages. It then writes `Releases/MeetingNotes-<version>-<platform>.zip` (`.tar.gz` on Linux).
- **`build_windows.bat` / `build_unix.sh`:** Create `Releases/.venv`, install `requirements.txt` and `requirements-build.txt`, and run the build.
- **Boundaries:** Never bundle models or anything from `input/`/`output/`.

## Interaction flow

```text
app.run()
  └─ MainWindow(root)
        ├─ startup / Refresh: DependencyCheckWorker → AppConfig.discover(), Ollama models, GPUs
        └─ on click: for each selected file (shared JobControl)
              Worker.start() ──▶ AudioTranscriber.transcribe()       progress / pause / cancel
                              └▶ NoteGenerator.generate_notes()     (notes jobs only)
              result_ready ──▶ MainWindow saves via export.writer → output/
```

Dependency direction: `ui → core, export, config`, and `config → core.media`. `core` and `export` never import from `ui`. There are no circular imports.

## Conventions for contributors and coding agents

- Follow PEP 8 and type hints, and keep `from __future__ import annotations` so the code stays compatible with Python 3.8.
- Keep Qt out of `core/` and `config.py`. In `export/`, only `pdf.py` may use Qt (QtGui/QtPrintSupport).
- Keep platform-specific behaviour behind `config.py` (engine discovery), `core/transcriber.py` (engine commands), and `core/media.py` (OS calls). Windows is the primary platform; changes must not break the whisper.cpp path used on Linux and macOS.
- Raise module-specific exceptions (`TranscriptionError`, `NoteGenerationError`, `DownloadError`, `JobCancelled`) instead of returning error values. Workers turn them into log messages.
- Any new long-running step must call `JobControl.checkpoint()` or attach an abort hook so Pause and Cancel keep working.
- User-facing paths are relative to the application root, never the current working directory.
- Do not commit anything in `input/` (models, prompts), `output/` (generated notes), or `Releases/`. Built-in prompts belong in `prompts/`.
- Bump `__version__` in `meeting_notes/__init__.py` before building a release.
- Run the tests before committing: `python -m unittest discover -s tests -t .`
