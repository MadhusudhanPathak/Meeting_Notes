using System.IO;
using Microsoft.Extensions.Logging;
using MeetingNotesMaker.Domain.Common.Exceptions;

namespace MeetingNotesMaker.Infrastructure.Services
{
    public interface IFileService
    {
        Task<List<string>> FindSystemPromptFilesAsync();
        Task<List<string>> FindWhisperModelFilesAsync();
        Task<string> LoadSystemPromptContentAsync(string filePath);
        Task SaveTranscriptToFileAsync(string transcript, string outputPath);
        string GenerateDefaultPdfFileName();
        string GenerateDefaultTranscriptFileName();
        bool ValidateOllamaConnection();
        Task<bool> ValidateWhisperModelExistsAsync();
        void EnsureDirectoriesExist();
    }

    public class FileService : IFileService
    {
        private readonly string _appDirectory;
        private readonly string _systemPromptsDirectory;
        private readonly string _transcribingBinsDirectory;
        private readonly ILogger<FileService> _logger;

        public FileService(ILogger<FileService> logger)
        {
            _logger = logger;
            _appDirectory = Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location)!;
            _systemPromptsDirectory = Path.Combine(_appDirectory, "SystemPrompts");
            _transcribingBinsDirectory = Path.Combine(_appDirectory, "TranscribingBins");
        }

        public void EnsureDirectoriesExist()
        {
            try
            {
                Directory.CreateDirectory(_systemPromptsDirectory);
                Directory.CreateDirectory(_transcribingBinsDirectory);
                _logger.LogInformation("Ensured required directories exist: {SystemPromptsDir}, {TranscribingBinsDir}", 
                    _systemPromptsDirectory, _transcribingBinsDirectory);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error ensuring directories exist");
                throw new DomainException("Failed to create required directories", "FILE_SERVICE_ERROR", ex);
            }
        }

        public async Task<List<string>> FindSystemPromptFilesAsync()
        {
            var promptFiles = new List<string>();

            try
            {
                // Ensure directory exists
                Directory.CreateDirectory(_systemPromptsDirectory);

                // Search in the SystemPrompts directory
                if (Directory.Exists(_systemPromptsDirectory))
                {
                    var files = Directory.GetFiles(_systemPromptsDirectory, "*.txt", SearchOption.TopDirectoryOnly);
                    promptFiles.AddRange(files);
                    _logger.LogDebug("Found {Count} system prompt files", files.Length);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error finding system prompt files");
                throw new DomainException("Failed to find system prompt files", "FILE_SERVICE_ERROR", ex);
            }

            return promptFiles;
        }

        public async Task<List<string>> FindWhisperModelFilesAsync()
        {
            var modelFiles = new List<string>();

            try
            {
                // Ensure directory exists
                Directory.CreateDirectory(_transcribingBinsDirectory);

                // Search in the TranscribingBins directory
                if (Directory.Exists(_transcribingBinsDirectory))
                {
                    var files = Directory.GetFiles(_transcribingBinsDirectory, "*.bin", SearchOption.TopDirectoryOnly);
                    modelFiles.AddRange(files);
                    _logger.LogDebug("Found {Count} Whisper model files", files.Length);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error finding Whisper model files");
                throw new DomainException("Failed to find Whisper model files", "FILE_SERVICE_ERROR", ex);
            }

            return modelFiles;
        }

        public async Task<string> LoadSystemPromptContentAsync(string filePath)
        {
            try
            {
                if (!File.Exists(filePath))
                    throw new FileNotFoundException($"System prompt file not found: {filePath}");

                var content = await File.ReadAllTextAsync(filePath);
                _logger.LogDebug("Loaded system prompt from {FilePath}", filePath);
                return content;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error loading system prompt from {FilePath}", filePath);
                throw new DomainException($"Failed to load system prompt: {ex.Message}", "FILE_SERVICE_ERROR", ex);
            }
        }

        public async Task SaveTranscriptToFileAsync(string transcript, string outputPath)
        {
            try
            {
                await File.WriteAllTextAsync(outputPath, transcript);
                _logger.LogInformation("Transcript saved to {OutputPath}", outputPath);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error saving transcript to {OutputPath}", outputPath);
                throw new DomainException($"Failed to save transcript: {ex.Message}", "FILE_SERVICE_ERROR", ex);
            }
        }

        public string GenerateDefaultPdfFileName()
        {
            var timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            return $"Meeting_Notes_{timestamp}.pdf";
        }

        public string GenerateDefaultTranscriptFileName()
        {
            var timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            return $"Transcript_{timestamp}.txt";
        }

        public bool ValidateOllamaConnection()
        {
            try
            {
                using var client = new System.Net.Http.HttpClient();
                var response = client.GetAsync("http://localhost:11434/api/tags").Result;
                var isConnected = response.IsSuccessStatusCode;
                _logger.LogDebug("Ollama connection status: {IsConnected}", isConnected);
                return isConnected;
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Failed to validate Ollama connection");
                return false;
            }
        }

        public async Task<bool> ValidateWhisperModelExistsAsync()
        {
            try
            {
                // Look for any .bin files in the TranscribingBins directory
                var binFiles = Directory.GetFiles(_transcribingBinsDirectory, "*.bin", SearchOption.TopDirectoryOnly);
                var exists = binFiles.Length > 0;
                _logger.LogDebug("Whisper model validation: {Exists} ({Count} files)", exists, binFiles.Length);
                return exists;
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Error validating Whisper model existence");
                return false;
            }
        }
    }
}