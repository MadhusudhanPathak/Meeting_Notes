using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using Microsoft.Extensions.Logging;
using MeetingNotesMaker.Domain.Entities;
using MeetingNotesMaker.Domain.Services;
using MeetingNotesMaker.Domain.Common.Exceptions;

namespace MeetingNotesMaker.Infrastructure.Services
{
    public class WhisperService : IAudioTranscriptionService
    {
        private readonly string _baseDirectory;
        private readonly ILogger<WhisperService> _logger;
    
        public WhisperService(ILogger<WhisperService> logger)
        {
            _baseDirectory = AppDomain.CurrentDomain.BaseDirectory;
            _logger = logger;
        }
    
        public async Task<TranscriptionResult> TranscribeAudioAsync(string audioFilePath, string modelFilePath, IProgress<int>? progress = null)
        {
            try
            {
                // Validate inputs
                ValidateInputs(audioFilePath, modelFilePath);
    
                progress?.Report(0);
    
                var result = new TranscriptionResult
                {
                    FullText = string.Empty,
                    FileName = Path.GetFileName(audioFilePath),
                    Segments = new List<TranscriptionSegment>()
                };
    
                var mainExePath = Path.Combine(_baseDirectory, "main.exe");
                if (!File.Exists(mainExePath))
                {
                    var errorMsg = $"Whisper executable (main.exe) not found at: {mainExePath}. Please download 'cli.zip' from https://github.com/Const-me/Whisper/releases, extract all its contents, and place them into the application's root directory. 'main.exe' requires other files from the release to function correctly.";
                    _logger.LogError(errorMsg);
                    throw new TranscriptionException(errorMsg);
                }
    
                // Create a temporary file for SRT output
                var srtFilePath = Path.Combine(Path.GetTempPath(), $"{Guid.NewGuid()}.srt");
    
                try
                {
                    var startInfo = new ProcessStartInfo
                    {
                        FileName = mainExePath,
                        Arguments = $"-m \"{modelFilePath}\" -f \"{audioFilePath}\" -osrt \"{srtFilePath}\"",
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        UseShellExecute = false,
                        CreateNoWindow = true,
                        WorkingDirectory = _baseDirectory
                    };
                    using var process = new Process { StartInfo = startInfo };

                    _logger.LogInformation("Starting Whisper transcription for file: {AudioFile}", audioFilePath);
                    
                    process.Start();

                    // Read output/error to prevent deadlocks
                    string standardOutput = await process.StandardOutput.ReadToEndAsync();
                    string standardError = await process.StandardError.ReadToEndAsync();

                    await process.WaitForExitAsync();

                    progress?.Report(80); // Indicate progress after process exits

                    if (process.ExitCode != 0)
                    {
                        var errorMsg = $"Whisper transcription failed with exit code {process.ExitCode}.\nStandard Output: {standardOutput}\nStandard Error: {standardError}";
                        _logger.LogError(errorMsg);
                        throw new TranscriptionException(errorMsg);
                    }

                    if (!File.Exists(srtFilePath))
                    {
                        var errorMsg = $"SRT output file not found after transcription: {srtFilePath}";
                        _logger.LogError(errorMsg);
                        throw new TranscriptionException(errorMsg);
                    }

                    // Parse the SRT file
                    var srtContent = await File.ReadAllLinesAsync(srtFilePath);
                    var fullTextBuilder = new StringBuilder();
                    var currentSegment = new TranscriptionSegment();
                    bool parsingSegment = false;

                    foreach (var line in srtContent)
                    {
                        if (string.IsNullOrWhiteSpace(line))
                        {
                            if (parsingSegment && !string.IsNullOrWhiteSpace(currentSegment.Text))
                            {
                                result.Segments.Add(currentSegment.Normalize());
                                fullTextBuilder.Append(currentSegment.Text).Append(" ");
                            }
                            currentSegment = new TranscriptionSegment();
                            parsingSegment = false;
                            continue;
                        }

                        if (int.TryParse(line, out _)) // Sequence number
                        {
                            parsingSegment = true;
                            continue;
                        }

                        if (line.Contains("-->")) // Timestamp line
                        {
                            var parts = line.Split(new[] { " --> " }, StringSplitOptions.RemoveEmptyEntries);
                            if (parts.Length == 2)
                            {
                                currentSegment.StartTime = ParseSrtTime(parts[0]);
                                currentSegment.EndTime = ParseSrtTime(parts[1]);
                            }
                            continue;
                        }

                        if (parsingSegment) // Text line
                        {
                            currentSegment.Text = (currentSegment.Text + " " + line).Trim();
                        }
                    }

                    // Add the last segment if exists
                    if (parsingSegment && !string.IsNullOrWhiteSpace(currentSegment.Text))
                    {
                        result.Segments.Add(currentSegment.Normalize());
                        fullTextBuilder.Append(currentSegment.Text).Append(" ");
                    }

                    result.FullText = fullTextBuilder.ToString().Trim();
                    result.Duration = CalculateDuration(result.Segments);
                }
                finally
                {
                    // Clean up the temporary SRT file
                    if (File.Exists(srtFilePath))
                    {
                        File.Delete(srtFilePath);
                        _logger.LogDebug("Cleaned up temporary SRT file: {SrtFile}", srtFilePath);
                    }
                }

                progress?.Report(100);
                _logger.LogInformation("Completed Whisper transcription for file: {AudioFile}", audioFilePath);
                
                return result.Normalize();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error during Whisper transcription of file: {AudioFile}", audioFilePath);
                throw;
            }
        }

        public bool IsSupportedFormat(string fileName)
        {
            if (string.IsNullOrWhiteSpace(fileName))
                return false;

            var extension = Path.GetExtension(fileName).ToLowerInvariant();
            return extension == ".mp3" || extension == ".wav" || extension == ".flac" || extension == ".m4a";
        }

        private void ValidateInputs(string audioFilePath, string modelFilePath)
        {
            if (string.IsNullOrWhiteSpace(audioFilePath))
                throw new ArgumentException("Audio file path cannot be null or empty", nameof(audioFilePath));

            if (string.IsNullOrWhiteSpace(modelFilePath))
                throw new ArgumentException("Model file path cannot be null or empty", nameof(modelFilePath));

            if (!File.Exists(audioFilePath))
                throw new AudioFileValidationException($"Audio file not found: {audioFilePath}");

            if (!File.Exists(modelFilePath))
                throw new FileNotFoundException($"Whisper model file not found: {modelFilePath}");

            if (!IsSupportedFormat(audioFilePath))
                throw new AudioFileValidationException($"Unsupported audio format: {Path.GetExtension(audioFilePath)}");

            if (!Path.GetExtension(modelFilePath).Equals(".bin", StringComparison.OrdinalIgnoreCase))
                throw new ArgumentException($"Invalid model file format: {Path.GetExtension(modelFilePath)}. Expected .bin file.");
        }

        private TimeSpan ParseSrtTime(string srtTime)
        {
            // Expected format: HH:MM:SS,ms
            var parts = srtTime.Split(new[] { ',', ':' }, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length >= 4) // At least 4 parts: HH MM SS ms
            {
                if (int.TryParse(parts[0], out int hours) &&
                    int.TryParse(parts[1], out int minutes) &&
                    int.TryParse(parts[2], out int seconds) &&
                    int.TryParse(parts[3], out int milliseconds))
                {
                    return new TimeSpan(0, hours, minutes, seconds, milliseconds);
                }
            }
            return TimeSpan.Zero;
        }

        private TimeSpan CalculateDuration(List<TranscriptionSegment> segments)
        {
            if (segments == null || !segments.Any())
                return TimeSpan.Zero;

            var maxEndTime = TimeSpan.Zero;
            foreach (var segment in segments)
            {
                if (segment.EndTime > maxEndTime)
                    maxEndTime = segment.EndTime;
            }

            return maxEndTime;
        }
    }
}