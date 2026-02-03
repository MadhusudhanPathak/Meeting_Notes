# Local Meeting Notes Generator

A professional desktop application for generating structured meeting notes from audio recordings using local processing with Whisper.cpp and Ollama.

## Table of Contents
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)

## Features

- **Local Audio Transcription**: Uses Whisper.cpp for privacy-focused, offline audio-to-text conversion
- **AI-Powered Note Generation**: Leverages Ollama for intelligent meeting summary generation
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
   - Place `main.exe` and `Whisper.dll` in the **current directory** (same directory as main.py)
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
main.exe              # Whisper.cpp executable (in current directory)
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

4. Choose an Ollama model from the dropdown

5. Select a system prompt template

6. Select a Whisper model (.bin file) from the dropdown

7. Click "Generate Meeting Notes"

8. Monitor progress in the log panel

9. The generated transcript (TXT) and notes (PDF) will be automatically saved to the `output/` directory

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

**"main.exe not found"**: Ensure Whisper.cpp binaries are in the **current directory** (same directory as main.py)

**"Whisper.dll not found"**: Ensure Whisper.cpp binaries are in the **current directory** (same directory as main.py)

**"No .bin model file found"**: Ensure at least one .bin model file is in the `input/` directory. Download from [Hugging Face](https://huggingface.co/ggerganov/whisper.cpp/tree/main)

**"Cannot connect to Ollama"**: Verify Ollama is installed and running (`ollama serve` in terminal)

**"No models available"**: Pull a model with `ollama pull <model-name>` (e.g., `ollama pull llama2`)

**"Invalid audio format"**: Ensure audio file is in a supported format (MP3, WAV, M4A, FLAC, AAC, OGG)

### Getting Help

For additional support, check the logs in the application interface or file an issue in the repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.