# Local Meeting Notes Generator

A professional desktop application for generating structured meeting notes from audio recordings using local processing with Whisper.cpp and Ollama.

## Table of Contents
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Architecture](#architecture)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

## Features

- **Local Audio Transcription**: Uses Whisper.cpp for privacy-focused, offline audio-to-text conversion
- **AI-Powered Note Generation**: Leverages Ollama for intelligent meeting summary generation
- **Professional UI**: Modern PyQt5-based desktop interface with progress tracking
- **Flexible Output**: Generates both detailed transcripts (TXT) and formatted notes (PDF)
- **Model Selection**: Choose from multiple available Ollama models
- **Prompt Customization**: Use custom system prompts for tailored note generation
- **Robust Error Handling**: Comprehensive error management and user feedback

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
   - Place `main.exe` and `Whisper.dll` in the `input/` directory
   - Download a Whisper model (e.g., `ggml-medium.bin`) and place it in the `input/` directory

4. Set up Ollama:
   - Install Ollama from [ollama.ai](https://ollama.ai)
   - Pull a model for note generation (e.g., `ollama pull llama2`)

5. Configure system prompts:
   - Create one or more system prompt files in the `input/` directory
   - Name them with the pattern `System_Prompt*.txt`

## Configuration

The application expects the following structure in the `input/` directory:
```
input/
├── main.exe          # Whisper.cpp executable
├── Whisper.dll       # Whisper.cpp dependency
├── ggml-*.bin        # Whisper model file(s)
└── System_Prompt*.txt # System prompt template(s)
```

## Usage

1. Launch the application:
   ```bash
   python main.py
   ```

2. The application will check for dependencies and display status

3. Select an audio file (MP3, WAV, M4A, FLAC, AAC, OGG)

4. Choose an Ollama model from the dropdown

5. Select a system prompt template

6. Click "Generate Meeting Notes"

7. Monitor progress in the log panel

8. Save the generated transcript (TXT) and notes (PDF) to your desired location

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

## Development

### Running Tests
```bash
# Run unit tests
python -m pytest tests/unit/

# Run integration tests
python -m pytest tests/integration/
```

### Code Standards
- Follow PEP 8 style guidelines
- Use type hints for all public functions
- Write docstrings for all modules, classes, and public methods
- Handle exceptions appropriately with custom exception types

### Adding New Features
1. Create feature-specific modules in the appropriate directory
2. Follow the existing patterns for error handling and logging
3. Add unit tests for new functionality
4. Update documentation as needed

## Troubleshooting

### Common Issues

**"main.exe not found"**: Ensure Whisper.cpp binaries are in the `input/` directory

**"Cannot connect to Ollama"**: Verify Ollama is running (`ollama serve`)

**"No models available"**: Pull a model with `ollama pull <model-name>`

**"Invalid audio format"**: Ensure audio file is in a supported format (MP3, WAV, etc.)

### Getting Help

For additional support, check the logs in the application interface or file an issue in the repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.