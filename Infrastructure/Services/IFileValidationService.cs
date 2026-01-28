using System;
using System.IO;
using System.Linq;
using MeetingNotesMaker.Application.DTOs;
using MeetingNotesMaker.Domain.Common.Exceptions;

namespace MeetingNotesMaker.Infrastructure.Services
{
    public interface IFileValidationService
    {
        Task<bool> ValidateAudioFileAsync(string filePath);
        Task<bool> ValidateWhisperModelExistsAsync(string modelPath);
        Task<bool> ValidateSystemPromptExistsAsync(string promptPath);
        Task<long> GetFileSizeAsync(string filePath);
        string SanitizePath(string path);
    }

    public class FileValidationService : IFileValidationService
    {
        private readonly int _maxFileSizeMB;

        public FileValidationService(int maxFileSizeMB = 100)
        {
            _maxFileSizeMB = maxFileSizeMB;
        }

        public async Task<bool> ValidateAudioFileAsync(string filePath)
        {
            if (string.IsNullOrWhiteSpace(filePath))
                return false;

            if (!File.Exists(filePath))
                return false;

            // Check file extension
            var extension = Path.GetExtension(filePath).ToLowerInvariant();
            var supportedExtensions = new[] { ".mp3", ".wav", ".flac", ".m4a" };
            
            if (!supportedExtensions.Contains(extension))
                return false;

            // Check file size
            var fileSize = await GetFileSizeAsync(filePath);
            var maxSizeBytes = _maxFileSizeMB * 1024L * 1024L; // Convert MB to bytes
            
            return fileSize <= maxSizeBytes;
        }

        public async Task<bool> ValidateWhisperModelExistsAsync(string modelPath)
        {
            if (string.IsNullOrWhiteSpace(modelPath))
                return false;

            return await Task.FromResult(File.Exists(modelPath) && 
                                        Path.GetExtension(modelPath).Equals(".bin", StringComparison.OrdinalIgnoreCase));
        }

        public async Task<bool> ValidateSystemPromptExistsAsync(string promptPath)
        {
            if (string.IsNullOrWhiteSpace(promptPath))
                return false;

            return await Task.FromResult(File.Exists(promptPath) && 
                                        Path.GetExtension(promptPath).Equals(".txt", StringComparison.OrdinalIgnoreCase));
        }

        public async Task<long> GetFileSizeAsync(string filePath)
        {
            if (!File.Exists(filePath))
                throw new FileNotFoundException($"File not found: {filePath}");

            var fileInfo = new FileInfo(filePath);
            return await Task.FromResult(fileInfo.Length);
        }

        public string SanitizePath(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
                return string.Empty;

            // Remove potentially dangerous characters/sequences
            var sanitized = path.Replace("..\\", "").Replace("../", "");
            sanitized = Path.GetFullPath(sanitized); // Resolve relative paths
            
            return sanitized;
        }
    }
}