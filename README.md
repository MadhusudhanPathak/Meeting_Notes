# Local Meeting Notes Generator

A professional desktop application for generating structured meeting notes from audio recordings using local processing with Whisper.cpp and Ollama.

## Philosophy

My base philosophy for making this is to promote local distilled Small Language Models (SMLs) use and promoting people to not go to Online available Large Language Models (LLMs) for each and every small thing, for instance making meeting notes. This is a great initiative in a lot of way, keeping everything local is good for Privacy, Security as well as for Environment and giving positive signal to AI Market. This program will be work well enough if you have any good performing model installed in a system with 16 GB RAM, Good CPU and Decent GPU. I use this pipeline for around 6 months and I got good enough suggestions to share how I make my meeting notes, then I thought of stitching it all together in this program.

## Table of Contents
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Batch File Usage](#batch-file-usage)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)

## Features

- **Local Audio Transcription**: Uses Whisper.cpp for privacy-focused, offline audio-to-text conversion
- **AI-Powered Note Generation**: Leverages Ollama for intelligent meeting summary generation
- **Transcription-Only Mode**: Simple audio transcription without requiring Ollama (uses only .bin file)
- **Professional UI**: Modern PyQt5-based desktop interface with progress tracking
- **Flexible Output**: Generates both detailed transcripts (TXT) and formatted notes (PDF)
- **Model Selection**: Choose from multiple available Ollama models
- **Prompt Customization**: Use custom system prompts for tailored note generation
- **Robust Error Handling**: Comprehensive error management and user feedback
- **Modern UI Design**: Clean interface with Times New Roman font, teal color scheme, and intuitive layout

## Prerequisites

- Python 3.8 or higher
- Ollama running locally (download from [ollama.ai](https://ollama.ai))
- Whisper.cpp binaries (executable and model files)

## Installation

1. Clone or download this repository
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up Whisper.cpp:
   - Download Whisper.cpp binaries from [GitHub](https://github.com/Const-me/Whisper)
   - Place `Whisper.exe` and `Whisper.dll` in the **current directory** (same directory as main.py)
   - Download a Whisper model (e.g., from [Hugging Face](https://huggingface.co/ggerganov/whisper.cpp/tree/main)) and place it in the `input/` directory

4. Set up Ollama:
   - Install Ollama from [ollama.ai](https://ollama.ai)
   - Pull a model for note generation (e.g., `ollama pull llama2`)

5. Configure system prompts:
   - Create one or more system prompt files in the `input/` directory
   - Name them with any `.txt` extension (e.g., `meeting_prompt.txt`, `System_Prompt_Meeting_Notes.txt`)

## Configuration

The application expects the following structure:

```
Whisper.exe           # Whisper.cpp executable (in current directory)
Whisper.dll           # Whisper.cpp dependency (in current directory)
input/                # Input directory (created automatically if not exists)
├── *.bin             # Whisper model file(s)
└── *.txt             # System prompt template(s)
output/               # Output directory (created automatically if not exists)
```

The application will automatically create `input/` and `output/` directories if they don't exist.

## Usage

1. Launch the application:
   ```bash
   python main.py
   ```

2. The application will check for dependencies and display status

3. Select an audio file (MP3, WAV, M4A, FLAC, AAC, OGG)

4. Select a Whisper model (.bin file) from the dropdown

5. **For transcription only (no Ollama required)**: Click the "Transcribe Audio" button (left button)
   - This generates only the transcript file in the output folder
   - Does not require Ollama to be installed or running

6. **For full meeting notes generation (requires Ollama)**:
   - Choose an Ollama model from the dropdown
   - Select a system prompt template
   - Click "Generate Meeting Notes" (right button)
   - This generates transcript (TXT), notes (MD), and notes (PDF) in the output folder

7. Monitor progress in the log panel

8. The generated files will be automatically saved to the `output/` directory

## Batch File Usage

Alternatively, you can use the provided batch file `Meeting Notes.bat` to run the application with automatic dependency management:

1. Double-click on `Meeting Notes.bat` to run the application

2. The batch file will automatically:
   - Check if Python is installed, and install it using winget if needed
   - Check if winget is available (required for installing Python)
   - Verify pip is available and install it if needed
   - Check if all required packages from `requirements.txt` are installed
   - Install any missing packages from `requirements.txt`
   - Run the main application (`main.py`)
   - Display status messages during the process
   - Pause at the end to show completion status

3. The batch file handles all setup requirements automatically, making it easier to run the application without manual dependency management.

## Architecture

The application follows a modular architecture with clear separation of concerns:

```
src/
├── config/           # Configuration management
│   └── settings.py   # Application settings and validation
├── core/             # Core business logic
│   └── note_generator.py # Ollama API integration
├── models/           # Data models and audio processing
│   └── transcriber.py # Whisper.cpp integration
├── ui/               # User interface components
│   └── main_window.py # Main application window
├── utils/            # Utility functions
│   └── helpers.py    # Helper functions
└── workers/          # Background processing
    └── processing_worker.py # Threading for long operations
```

## Troubleshooting

### Common Issues

**"Whisper.exe not found"**: Ensure Whisper.cpp binaries are in the **current directory** (same directory as main.py)

**"Whisper.dll not found"**: Ensure Whisper.cpp binaries are in the **current directory** (same directory as main.py)

**"No .bin model file found"**: Ensure at least one .bin model file is in the `input/` directory. Download from [Hugging Face](https://huggingface.co/ggerganov/whisper.cpp/tree/main)

**"Cannot connect to Ollama"**: Verify Ollama is installed and running (`ollama serve` in terminal)

**"No models available"**: Pull a model with `ollama pull <model-name>` (e.g., `ollama pull llama2`)

**"Invalid audio format"**: Ensure audio file is in a supported format (MP3, WAV, M4A, FLAC, AAC, OGG)

### Getting Help

For additional support, check the logs in the application interface or file an issue in the repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.