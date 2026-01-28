# ⚠️ PROJECT SUSPENDED - INCOMPLETE ⚠️

## This project is currently incomplete and suspended due to technical issues.

A professional-grade Windows desktop application that processes meeting audio files locally and generates formatted meeting notes. The application works entirely offline (except for initial setup) and handles all processing on the user's machine with a clean, maintainable architecture.

## Features

- **Local Processing**: All audio transcription and note generation happens on your machine
- **Audio Support**: Accepts MP3, WAV, FLAC, and M4A audio files
- **Whisper Integration**: Uses Whisper models for accurate speech-to-text conversion
- **Ollama Integration**: Leverages local Ollama models for intelligent note generation
- **Professional Output**: Generates both PDF meeting notes and TXT transcripts
- **Configurable**: Customizable system prompts for tailored note generation
- **Simple File Selection**: Direct file selection for Whisper models and system prompts
- **Production Ready**: Clean architecture with proper error handling, logging, and validation

## Prerequisites

Before using the application, you need to install and configure the following:

### 1. Ollama
- Download and install from [ollama.ai](https://ollama.ai/)
- After installation, run `ollama serve` in your terminal
- Pull at least one model (e.g., `ollama pull llama2`)

### 2. Whisper Models
- Download Whisper models (`.bin` files) from [ggerganov/whisper.cpp](https://github.com/ggerganov/whisper.cpp)
- Models available: tiny, base, small, medium, large
- Example: `ggml-base.bin`, `ggml-small.bin`

## Setup

1. Launch the application
2. Select your audio file using the "Select Audio File" button
3. Select your Whisper model file using the "Browse..." button next to "Whisper Model"
4. Select your system prompt file using the "Browse..." button next to "System Prompt"
5. Select your Ollama model from the dropdown
6. Click "Process Meeting" to generate notes
7. Save the PDF and/or TXT files as needed

## How to Use

1. **Select Audio File**: Click "Select Audio File" to choose your meeting recording
2. **Select Whisper Model**: Click "Browse..." to select your .bin Whisper model file
3. **Select System Prompt**: Click "Browse..." to select your .txt system prompt file
4. **Choose Ollama Model**: Select from available Ollama models in the dropdown
5. **Process Meeting**: Click "Process Meeting" to start transcription and note generation
6. **Save Output**: Use "Save PDF Notes" and "Save Transcript" buttons to save your files

## Architecture

The application follows a clean architecture pattern with separation of concerns:

### Layers:
- **Presentation Layer**: WPF-based user interface with pure MVVM
- **Application Layer**: Use cases, DTOs, and application services
- **Domain Layer**: Business entities, domain services, and business rules
- **Infrastructure Layer**: External integrations, file operations, and configuration

### Key Features:
- Proper dependency injection throughout
- Comprehensive error handling and validation
- Structured logging with Serilog
- Input sanitization and security measures
- Asynchronous operations with progress reporting
- Configurable settings via appsettings.json

## Dependencies

The application requires the following NuGet packages:
- OllamaSharp
- QuestPDF
- Whisper.net
- NAudio
- Microsoft.Extensions.DependencyInjection
- Microsoft.Extensions.Configuration
- Microsoft.Extensions.Logging
- Serilog
- FluentValidation
- CommunityToolkit.Mvvm

## Troubleshooting

- **"Ollama service" missing**: Ensure Ollama is installed and running with `ollama serve`
- **Whisper model file missing**: Download a `.bin` model file and select it using the Browse button
- **System prompt file missing**: Create a `.txt` file with your desired system prompt and select it using the Browse button

### Example System_Prompt.txt Template

```
You are an expert meeting assistant. Your job is to analyze meeting transcripts and generate structured meeting notes that include:
- Key discussion points
- Decisions made
- Action items with responsible parties
- Important deadlines mentioned
- Questions raised and their answers

Format the output clearly with appropriate headings and bullet points.
```

## Configuration

The application uses `appsettings.json` for configuration. You can customize:
- Ollama API URL and default model
- Maximum file size limits
- Transcription timeout settings
- Whisper model path

## Building from Source

1. Clone the repository
2. Open `MeetingNotesMaker.sln` in Visual Studio
3. Restore NuGet packages
4. Build the solution
5. Ensure Whisper dependencies are available

## Contributing

Feel free to submit issues and enhancement requests. Pull requests are welcome!

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Project Status: Suspended Due to Technical Issues

### Current Issues

The project is currently suspended due to the following technical challenges:

1. **Whisper Executable Integration Problems**:
   - The Whisper transcription service encounters errors during audio processing
   - Exit code -2147024894 indicates issues with the underlying Whisper executable
   - Despite successful transcription output being generated, the process fails during SRT file handling
   - Media Foundation decoding errors occur when processing certain audio formats

2. **External Dependency Failures**:
   - The Whisper executable (main.exe) has compatibility issues with certain audio codecs
   - Temporary file handling in the transcription process causes failures
   - GPU acceleration conflicts with certain graphics drivers

3. **Incomplete Output Pipeline**:
   - While the transcript is generated successfully, the process fails before saving files to the Output folder
   - The meeting notes generation stage is not reached due to transcription failures

### Planned Improvements (When Resumed)

1. **Alternative Transcription Engine**:
   - Integrate Whisper.net library instead of relying on external executable
   - Implement fallback transcription methods for better reliability
   - Add support for additional audio format conversions

2. **Enhanced Error Handling**:
   - Implement graceful degradation when transcription fails
   - Add detailed logging for debugging transcription issues
   - Create recovery mechanisms for partial failures

3. **Improved File Management**:
   - Ensure Output folder is created regardless of transcription success
   - Implement atomic file operations to prevent corruption
   - Add file validation and cleanup routines

4. **Better Audio Format Support**:
   - Integrate audio preprocessing to normalize input formats
   - Add automatic format conversion before transcription
   - Implement codec detection and handling

5. **Robust Process Management**:
   - Replace external executable calls with native .NET implementations
   - Add timeout and retry mechanisms for transcription
   - Implement health checks for external dependencies

### Known Working State

Despite the suspension, the following components are properly implemented:
- UI has been updated to remove unnecessary save buttons
- Output folder creation and management is implemented
- Transcript saving and loading from the Output folder is coded
- Meeting notes generation pipeline is structured correctly
- The application builds successfully without compilation errors