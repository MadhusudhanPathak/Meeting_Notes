# Local Meeting Notes Generator

A desktop application that turns meeting recordings into transcripts and structured meeting notes, entirely on your own machine. Audio is transcribed with Whisper ([Const-me Whisper](https://github.com/Const-me/Whisper) on Windows, [whisper.cpp](https://github.com/ggml-org/whisper.cpp) on Linux and macOS) and notes are written by a local model served by [Ollama](https://ollama.com). Nothing is sent to the cloud.

**Video introduction and tutorial:** <https://youtu.be/WZOufhzwrFU>

## Philosophy

This project promotes the use of local, distilled Small Language Models (SLMs) instead of reaching for online Large Language Models (LLMs) for everyday tasks such as writing meeting notes. Keeping everything local is better for privacy, security, and the environment, and sends a positive signal to the AI market. It works well on a system with 16 GB RAM, a good CPU, and a decent GPU running any capable Ollama model. I used this pipeline for about six months and received enough good feedback to package it as a single program.

![Meeting Notes infographic](assets/Meeting_Notes_Infographics.jpg)

## Table of Contents

- [Features](#features)
- [Download (Windows)](#download-windows)
- [Run from Source](#run-from-source)
- [Usage](#usage)
- [Architecture](#architecture)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Features

- **Local transcription** with Whisper; audio never leaves your machine.
- **Audio and video files**: MP3, WAV, M4A, FLAC, AAC, WMA, MP4, M4V, MOV, WMV, AVI, MKV. Drag and drop them onto the window.
- **99 spoken languages**, with optional translation into English.
- **AI meeting notes** from any model installed in Ollama, including **long meetings**: the context window is sized to the transcript, and transcripts too long for the model are summarised in parts and then combined, so nothing is silently cut off.
- **Transcription-only mode** that works without Ollama.
- **Batch processing** of multiple files in one run.
- **Outputs**: transcript (`.txt`, with or without timestamps), notes (`.md`), formatted notes (`.pdf`), and optional subtitles (`.srt`, `.vtt`).
- **Polished PDFs**: tables, nested lists, checklists, code, links, page numbers, and non-Latin scripts such as Hindi and Chinese.
- **Pause, resume, and cancel** running jobs, with real transcription progress and elapsed time.
- **Download models inside the app**: Whisper models from Hugging Face and Ollama models.
- **Choose the graphics card** used for transcription (Windows).
- **Remembers your selections** between sessions, and ships with a ready-to-use default prompt.
- **Standalone Windows release**: no Python installation needed.

## Download (Windows)

1. Download `MeetingNotes-<version>-windows-x64.zip` from the [Releases page](https://github.com/MadhusudhanPathak/Meeting_Notes/releases).
2. Extract it to a folder you can write to, such as `Documents\MeetingNotes` (not `C:\Program Files`).
3. Run `MeetingNotes.exe`. The app is not code-signed, so if Windows SmartScreen appears, click **More info** → **Run anyway**.
4. Click **Download Models** and download a transcription model (`medium` is a good default).
5. For meeting notes, install [Ollama](https://ollama.com/download), start it, download a model (for example `llama3.2:3b`) with **Download Models**, and click **Refresh**.

The release includes the transcription engine but no models; models are downloaded on demand and saved in the `input` folder next to `MeetingNotes.exe`.

## Run from Source

### Windows

Requirements: Python 3.8 or newer, and [Ollama](https://ollama.com) for note generation.

1. Clone the repository and install the dependencies:

   ```bash
   git clone https://github.com/MadhusudhanPathak/Meeting_Notes.git
   cd Meeting_Notes
   pip install -r requirements.txt
   ```

2. Start the app with `python main.py`, or double-click **`Meeting Notes.bat`**. The batch file installs Python with `winget` if it is missing, installs the packages from `requirements.txt` when needed, and then launches the app.

`Whisper.exe` and `Whisper.dll` ship with this repository in the project root. Download models with **Download Models**, or copy `.bin` files from [Hugging Face](https://huggingface.co/ggerganov/whisper.cpp/tree/main) into `input/`.

### Linux and macOS

On Linux and macOS the app uses whisper.cpp's `whisper-cli` for transcription and ffmpeg to read video and other audio formats. In short:

- **macOS**: `brew install python@3.12 whisper-cpp ffmpeg`, install [Ollama](https://ollama.com/download/mac), then run the app from source or build `MeetingNotes.app`.
- **Linux**: install Python, ffmpeg, and Qt's system libraries, build `whisper-cli` from [whisper.cpp](https://github.com/ggml-org/whisper.cpp), install [Ollama](https://ollama.com/download/linux), then run from source or build a standalone package.

Step-by-step instructions are in `BUILDING.md`, attached to each [GitHub release](https://github.com/MadhusudhanPathak/Meeting_Notes/releases).

### Folder layout

The `input/` and `output/` folders are created automatically on first launch:

```text
Meeting_Notes/
├── Whisper.exe, Whisper.dll   transcription engine (Windows)
├── input/
│   ├── *.bin                  Whisper model(s)
│   └── *.txt                  your own system prompt(s)
├── prompts/                   built-in system prompt(s)
└── output/                    generated transcripts, notes, and subtitles
```

A packaged macOS app keeps `input/` and `output/` in `~/MeetingNotes`.

## Usage

The app checks its dependencies in the background at startup and reports the result in the log. Click **Refresh** after adding models or prompts, or after starting Ollama. Then:

1. Click **Select Audio/Video File** for one recording or **Select Multiple Files** for a batch, or drag and drop files onto the window.
2. Choose a **Transcription Model** and the **Spoken Language**. Tick **Translate to English** to get an English transcript of a non-English meeting.
3. Optionally pick a **Graphics Card** (leave **Automatic** if unsure) and the transcript options:
   - **Include timestamps in transcript**: each line starts with `[start --> end]`.
   - **Save subtitles (SRT and VTT)**: subtitle files for video players.
4. Choose what to produce:
   - **Transcribe Audio**: writes the transcript (and subtitles, if selected). Ollama is not needed.
   - **Generate Meeting Notes**: choose an **Ollama Model** and **System Prompt** first. Writes the transcript, Markdown notes, and PDF notes.
5. Follow progress in the progress bar, status line, and log. Use **Pause**/**Resume** or **Cancel** at any time.

When a job finishes, the success dialog and the log contain clickable links to every saved file, and **Open Output Folder** opens `output/`. Files are named with a timestamp:

```text
output/standup_2024-05-14_10-30-00_transcript.txt
output/standup_2024-05-14_10-30-00_notes.md
output/standup_2024-05-14_10-30-00_notes.pdf
output/standup_2024-05-14_10-30-00.srt
output/standup_2024-05-14_10-30-00.vtt
```

In batch mode files are processed one after another. If one file fails, the error is logged and the batch continues with the next file. Your selections (models, prompt, language, graphics card, and options) are remembered for next time.

### Long meetings, pausing, and progress

- **Long meetings**: the app asks Ollama for a context window large enough for the whole transcript (up to 32K tokens, to keep memory use reasonable). If the model's window is still too small, the transcript is summarised part by part and the parts are combined into the final notes. The log shows which path was taken.
- **Pause**: pausing freezes Whisper immediately. During note generation, Ollama may finish the text it is already working on before it stops.
- **Progress**: Whisper reports progress in bursts, so the bar may jump rather than move smoothly. The elapsed time keeps counting.

## Architecture

```text
main.py                        Entry point
meeting_notes/
├── app.py                     Qt application bootstrap
├── config.py                  Paths, engine discovery, and validation
├── core/                      Business logic (no Qt)
│   ├── transcriber.py         Whisper wrapper (Const-me / whisper.cpp): progress, pause/cancel, GPUs
│   ├── note_generator.py      Ollama client: context sizing, long-meeting summaries, pulls
│   ├── chunking.py            Token estimates and transcript splitting
│   ├── control.py             Pause/cancel signals shared with running jobs
│   ├── downloads.py           Whisper model downloads from Hugging Face
│   ├── media.py               Media duration, program lookup, process suspend/resume
│   └── languages.py           Languages supported by Whisper
├── export/                    Output persistence
│   ├── writer.py              Output file naming and writing
│   └── pdf.py                 Markdown → PDF rendering (Qt)
└── ui/                        Presentation layer (PyQt5)
    ├── main_window.py         Main window and job orchestration
    ├── workers.py             Background threads for jobs, checks, and downloads
    ├── download_dialog.py     "Download Models" dialog
    ├── preferences.py         Remembered selections (QSettings)
    └── styles.py              Qt style sheets
prompts/                       Built-in system prompts
assets/                        Application icon and documentation images
tests/                         Unit tests (unittest)
Releases/                      Packaging (not in git; published with each GitHub release)
```

Processing flow:

```text
MainWindow ──starts──▶ Worker thread ──▶ AudioTranscriber (Whisper.exe / whisper-cli)
     │                               └──▶ NoteGenerator (Ollama HTTP API)
     │  Pause / Cancel ──▶ JobControl ──▶ suspends/kills Whisper, closes Ollama connection
     ◀───────── result ──
MainWindow ──saves──▶ export.writer ──▶ output/*.txt, *.md, *.pdf, *.srt, *.vtt
```

`core` has no dependency on Qt and can be used or tested on its own; `export` uses Qt only to render PDFs. See [AGENTS.md](AGENTS.md) for each component's responsibilities and boundaries.

## Development

Run the test suite from the project root:

```bash
python -m unittest discover -s tests -t .
```

Standalone packages (no Python needed to run them) are built with the packaging files attached to each [GitHub release](https://github.com/MadhusudhanPathak/Meeting_Notes/releases): `BUILDING.md`, `MeetingNotes.spec`, `build_release.py`, `build_windows.bat`, `build_unix.sh`, `requirements-build.txt`, and the `bundle/` files. Put them in a `Releases/` folder inside your clone (the folder is ignored by git), then run:

```bash
Releases\build_windows.bat       # Windows → Releases/MeetingNotes-<version>-windows-x64.zip
bash Releases/build_unix.sh      # Linux → .tar.gz, macOS → .zip with MeetingNotes.app
```

The version number lives in `meeting_notes/__init__.py`. `BUILDING.md` covers platform requirements and how to publish a release.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `Whisper.exe not found` / `Whisper.dll not found` (Windows) | Place both files next to `main.py` or `MeetingNotes.exe`. |
| `whisper-cli (whisper.cpp) not found` (Linux/macOS) | Install whisper.cpp (`brew install whisper-cpp` on macOS) or put `whisper-cli` on `PATH`, then click **Refresh**. |
| `ffmpeg not found` (Linux/macOS) | Install ffmpeg to transcribe video, M4A, AAC, and WMA files. WAV, MP3, and FLAC work without it. |
| `No .bin model file found` | Click **Download Models**, or copy a model into `input/` and click **Refresh**. |
| `Cannot connect to Ollama` | Install Ollama and make sure it is running (`ollama serve`), then click **Refresh**. |
| `No Ollama models found` | Click **Download Models**, or run `ollama pull llama3.2:3b`. |
| Transcript is in the wrong language or nonsense | Set **Spoken Language** to the language actually spoken; it is not detected automatically. |
| A file is rejected or fails to transcribe | Not every format or codec can be decoded (Ogg Vorbis, for example, is not supported). Convert the file to MP3, WAV, or MP4. |
| Transcription fails with a chosen graphics card | Set **Graphics Card** back to **Automatic**. |
| Note generation is very slow | Long transcripts need a large context window. Use a smaller Ollama model, a GPU, or a shorter recording. |
| Windows SmartScreen blocks `MeetingNotes.exe` | The app is not code-signed. Click **More info** → **Run anyway**. |

Detailed error messages always appear in the log inside the application. If the problem persists, open an issue on the repository.

## License

This project is licensed under the [MIT License](LICENSE).

The standalone packages also bundle third-party components under their own licenses, including PyQt5 (GPL-3.0), Qt (LGPL-3.0), and Const-me Whisper (MPL-2.0). Each package includes `THIRD_PARTY_NOTICES.txt` and the full license texts.
