# AGENTS.md

How this codebase is organized, what each component is responsible for, and the rules to follow when changing it. Read [README.md](README.md) for installation and usage.

## System overview

A PyQt5 desktop application that runs two local AI components in sequence:

1. **Whisper.cpp** (`Whisper.exe` + `Whisper.dll`, run as a subprocess) converts audio into a transcript.
2. **Ollama** (HTTP API at `http://localhost:11434`) turns the transcript into meeting notes, following a user-supplied system prompt.

Everything runs locally. The only network traffic goes to the local Ollama server.

## Components

### Configuration — `meeting_notes/config.py`

- **Role:** Single source of truth for file locations.
- **Responsibilities:** Resolve the application root (the project folder, or the executable's folder in a PyInstaller build). Discover Whisper binaries, `.bin` models, and `.txt` prompts. Create `input/` and `output/`. Report missing dependencies as user-facing messages.
- **Boundaries:** Never runs external tools or contacts Ollama. `AppConfig` is immutable; it is built once at startup with `AppConfig.discover()`.

### Transcriber — `meeting_notes/core/transcriber.py`

- **Role:** Wraps the Whisper.cpp command-line tool.
- **Responsibilities:** Run `Whisper.exe -m <model> -f <audio> -otxt`. Read the `<audio>.txt` file Whisper writes next to the audio file, then remove it. Define the supported audio extensions.
- **Boundaries:** No Qt and no UI. Raises `FileNotFoundError` for missing inputs and `TranscriptionError` for every other failure.

### Note generator — `meeting_notes/core/note_generator.py`

- **Role:** Client for the Ollama HTTP API.
- **Responsibilities:** List installed models (`/api/tags`) and generate notes (`/api/generate`, non-streaming) with retries and timeouts.
- **Boundaries:** No Qt and no file I/O. Every failure is raised as `NoteGenerationError` with a readable message.

### Export — `meeting_notes/export/`

- **`writer.py`:** Builds timestamped output paths (`<stem>_<YYYY-MM-DD_HH-MM-SS>_transcript.txt`, `_notes.md`, `_notes.pdf`) and writes UTF-8 text and PDF files.
- **`pdf.py`:** Converts the model's Markdown into a reportlab PDF (headings, lists, rules, bold, italics, strikethrough, inline code, links). All text is XML-escaped. A line whose generated markup is invalid falls back to plain text, so a single bad line cannot break the whole PDF.
- **Boundaries:** No Qt. reportlab is imported only when a PDF is written.

### Workers — `meeting_notes/ui/workers.py`

- **Role:** Run one job for one audio file on a background `QThread` so the UI stays responsive.
- **`TranscriptionWorker`:** Transcription only.
- **`NotesWorker`:** Transcription, then note generation.
- **Contract:** Emit `log(str)` and `progress(int)` while running, then emit `result_ready` exactly once, with a `JobResult` or with `None` after logging the reason for the failure. Workers never touch widgets or write output files.

### Main window — `meeting_notes/ui/main_window.py`

- **Role:** Presentation and orchestration.
- **Responsibilities:** Check dependencies at startup and enable only the features that can work. Collect file, model, and prompt selections. Confirm with the user. Run files one at a time (single or batch), lock inputs while a job runs, and save results through `export.writer`.
- **Boundaries:** Holds no business logic. It delegates to the workers, the core modules, and the export modules. Styling lives in `ui/styles.py`.

## Interaction flow

```text
app.run()
  └─ AppConfig.discover() → MainWindow(config)
        ├─ startup: config.validate() + NoteGenerator.get_available_models()
        └─ on click: for each selected file
              Worker.start() ──▶ AudioTranscriber.transcribe()
                              └▶ NoteGenerator.generate_notes()   (notes jobs only)
              result_ready ──▶ MainWindow saves via export.writer → output/
```

Dependency direction: `ui → core, export, config`. `core` and `export` never import from `ui`. There are no circular imports.

## Conventions for contributors and coding agents

- Follow PEP 8 and type hints, and keep `from __future__ import annotations` so the code stays compatible with Python 3.8.
- Keep Qt out of `core/`, `export/`, and `config.py`.
- Raise module-specific exceptions (`TranscriptionError`, `NoteGenerationError`) instead of returning error values. Workers turn them into log messages.
- User-facing paths are relative to the application root, never the current working directory.
- Do not commit anything in `input/` (models, prompts) or `output/` (generated notes).
- Run the tests before committing: `python -m unittest discover -s tests -t .`
