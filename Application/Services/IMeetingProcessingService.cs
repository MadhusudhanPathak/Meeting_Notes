using System;
using System.IO;
using MeetingNotesMaker.Application.DTOs;
using MeetingNotesMaker.Domain.Entities;
using MeetingNotesMaker.Domain.Services;
using MeetingNotesMaker.Infrastructure.Services;

namespace MeetingNotesMaker.Application.Services
{
    public interface IMeetingProcessingService
    {
        Task<ProcessMeetingResponseDto> ProcessMeetingAsync(
            ProcessMeetingRequestDto request, 
            IProgress<TranscriptionProgressDto>? progress = null);
    }

    public class MeetingProcessingService : IMeetingProcessingService
    {
        private readonly IAudioTranscriptionService _transcriptionService;
        private readonly IMeetingNoteGenerationService _noteGenerationService;
        private readonly IPdfGenerationService _pdfGenerationService;

        public MeetingProcessingService(
            IAudioTranscriptionService transcriptionService,
            IMeetingNoteGenerationService noteGenerationService,
            IPdfGenerationService pdfGenerationService)
        {
            _transcriptionService = transcriptionService;
            _noteGenerationService = noteGenerationService;
            _pdfGenerationService = pdfGenerationService;
        }

        public async Task<ProcessMeetingResponseDto> ProcessMeetingAsync(
            ProcessMeetingRequestDto request, 
            IProgress<TranscriptionProgressDto>? progress = null)
        {
            var stopwatch = System.Diagnostics.Stopwatch.StartNew();
            
            try
            {
                // Validate inputs
                ValidateInputs(request);

                // Step 1: Transcribe audio
                progress?.Report(new TranscriptionProgressDto 
                { 
                    Percentage = 10, 
                    StatusMessage = "Starting audio transcription..." 
                });

                var transcriptionResult = await _transcriptionService.TranscribeAudioAsync(
                    request.AudioFilePath, 
                    request.WhisperModelPath,
                    new Progress<int>(value => progress?.Report(new TranscriptionProgressDto 
                    { 
                        Percentage = 10 + (int)(value * 0.4), // 10% to 50%
                        StatusMessage = $"Transcribing audio... ({value}%)"
                    })));

                progress?.Report(new TranscriptionProgressDto 
                { 
                    Percentage = 50, 
                    StatusMessage = "Transcription complete, generating meeting notes..." 
                });

                // Step 2: Load system prompt
                var systemPrompt = await LoadSystemPromptAsync(request.SystemPromptPath);

                // Step 3: Generate meeting notes
                var meetingNote = await _noteGenerationService.GenerateMeetingNotesAsync(
                    transcriptionResult.FullText,
                    systemPrompt,
                    request.OllamaModelName);

                // Step 4: Save transcript to file
                var transcriptDirectory = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "MeetingTranscriptions");
                Directory.CreateDirectory(transcriptDirectory);
                var transcriptFileName = $"{Path.GetFileNameWithoutExtension(request.AudioFilePath)}_{DateTime.UtcNow:yyyyMMdd_HHmmss}.txt";
                var transcriptFilePath = Path.Combine(transcriptDirectory, transcriptFileName);
                await File.WriteAllTextAsync(transcriptFilePath, transcriptionResult.FullText);

                progress?.Report(new TranscriptionProgressDto 
                { 
                    Percentage = 80, 
                    StatusMessage = "Generating PDF output..." 
                });

                // Step 5: Generate PDF output
                var notesDirectory = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "MeetingNotes");
                Directory.CreateDirectory(notesDirectory);
                var pdfFileName = $"Meeting_Notes_{Path.GetFileNameWithoutExtension(request.AudioFilePath)}_{DateTime.UtcNow:yyyyMMdd_HHmmss}.pdf";
                var pdfFilePath = Path.Combine(notesDirectory, pdfFileName);

                await _pdfGenerationService.SaveMeetingNotesPdfAsync(meetingNote, pdfFilePath);

                progress?.Report(new TranscriptionProgressDto
                {
                    Percentage = 100,
                    StatusMessage = "Processing complete!"
                });

                stopwatch.Stop();

                return new ProcessMeetingResponseDto
                {
                    Success = true,
                    Message = "Meeting processed successfully",
                    PdfFilePath = pdfFilePath,
                    TranscriptFilePath = transcriptFilePath,
                    ProcessingTimeMs = stopwatch.ElapsedMilliseconds
                };
            }
            catch (Exception ex)
            {
                stopwatch.Stop();
                
                return new ProcessMeetingResponseDto
                {
                    Success = false,
                    Message = ex.Message,
                    ProcessingTimeMs = stopwatch.ElapsedMilliseconds
                };
            }
        }

        private static void ValidateInputs(ProcessMeetingRequestDto request)
        {
            if (string.IsNullOrWhiteSpace(request.AudioFilePath))
                throw new ArgumentException("Audio file path is required", nameof(request.AudioFilePath));
            
            if (string.IsNullOrWhiteSpace(request.WhisperModelPath))
                throw new ArgumentException("Whisper model path is required", nameof(request.WhisperModelPath));
            
            if (string.IsNullOrWhiteSpace(request.SystemPromptPath))
                throw new ArgumentException("System prompt path is required", nameof(request.SystemPromptPath));
            
            if (string.IsNullOrWhiteSpace(request.OllamaModelName))
                throw new ArgumentException("Ollama model name is required", nameof(request.OllamaModelName));
        }

        private async Task<string> LoadSystemPromptAsync(string promptPath)
        {
            if (!File.Exists(promptPath))
                throw new FileNotFoundException($"System prompt file not found: {promptPath}");

            return await File.ReadAllTextAsync(promptPath);
        }
    }
}