using System;
using System.IO;
using OllamaSharp;
using OllamaSharp.Models.Chat;
using Microsoft.Extensions.Logging;
using MeetingNotesMaker.Domain.Entities;
using MeetingNotesMaker.Domain.Services;
using MeetingNotesMaker.Domain.Common.Exceptions;

namespace MeetingNotesMaker.Infrastructure.Services
{
    public class OllamaService : IMeetingNoteGenerationService
    {
        private readonly OllamaApiClient _ollamaClient;
        private readonly ILogger<OllamaService> _logger;

        public OllamaService(string apiUrl, ILogger<OllamaService> logger)
        {
            _ollamaClient = new OllamaApiClient(apiUrl);
            _logger = logger;
        }

        public async Task<MeetingNote> GenerateMeetingNotesAsync(string transcript, string systemPrompt, string modelName)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(transcript))
                    throw new ArgumentException("Transcript cannot be empty", nameof(transcript));

                if (string.IsNullOrWhiteSpace(systemPrompt))
                    throw new ArgumentException("System prompt cannot be empty", nameof(systemPrompt));

                if (string.IsNullOrWhiteSpace(modelName))
                    throw new ArgumentException("Model name cannot be empty", nameof(modelName));

                var messages = new List<OllamaSharp.Models.Chat.Message>
                {
                    new OllamaSharp.Models.Chat.Message { Role = "system", Content = systemPrompt },
                    new OllamaSharp.Models.Chat.Message { Role = "user", Content = $"Please generate structured meeting notes from the following transcript:\n\n{transcript}" }
                };

                var request = new ChatRequest
                {
                    Model = modelName,
                    Messages = messages.ToArray()
                };

                // ChatAsync returns an IAsyncEnumerable for streaming, so we need to collect the full response
                var fullResponse = "";
                await foreach (var result in _ollamaClient.ChatAsync(request))
                {
                    if (result != null)
                    {
                        OllamaSharp.Models.Chat.Message? message = result.Message;
                        if (message != null && message.Content != null)
                        {
                            fullResponse += message.Content!;
                        }
                    }
                }

                // Parse the response to extract structured data
                return ParseMeetingNoteFromResponse(fullResponse, transcript);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error generating meeting notes using model {ModelName}", modelName);
                throw new OllamaConnectionException($"Failed to generate meeting notes: {ex.Message}", ex);
            }
        }

        public async Task<List<string>> GetAvailableModelsAsync()
        {
            try
            {
                var models = await _ollamaClient.ListLocalModelsAsync();
                return models.Select(m => m.Name).ToList();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error retrieving available Ollama models");
                throw new OllamaConnectionException("Failed to retrieve available models: " + ex.Message, ex);
            }
        }

        private MeetingNote ParseMeetingNoteFromResponse(string fullText, string rawTranscript)
        {
            // Improved parsing logic with better error handling
            var note = new MeetingNote
            {
                Title = "Meeting Notes",
                RawTranscript = rawTranscript,
                KeyDiscussionPoints = ExtractSection(fullText, "discussion points", "decisions made", "action items", "deadlines", "questions"),
                DecisionsMade = ExtractSection(fullText, "decisions made", "action items", "deadlines", "questions", "summary"),
                ActionItems = ExtractSection(fullText, "action items", "responsibilities", "tasks", "deadlines", "next steps"),
                Deadlines = ExtractSection(fullText, "deadlines", "due dates", "timeline", "schedule", "next steps"),
                QuestionsAndAnswers = ExtractSection(fullText, "questions", "qa", "q&a", "faq", "discussion")
            }.Normalize();

            return note;
        }

        private string ExtractSection(string fullText, params string[] markers)
        {
            if (string.IsNullOrWhiteSpace(fullText))
                return string.Empty;

            var lowerText = fullText.ToLowerInvariant();
            int startIndex = -1;
            string startMarker = "";

            // Find the first occurrence of any marker
            foreach (var marker in markers)
            {
                var index = lowerText.IndexOf(marker.ToLowerInvariant());
                if (index != -1 && (startIndex == -1 || index < startIndex))
                {
                    startIndex = index;
                    startMarker = marker;
                }
            }

            if (startIndex == -1)
                return string.Empty;

            startIndex += startMarker.Length;
            
            // Find the next section marker to determine end of current section
            int endIndex = fullText.Length;
            foreach (var marker in markers.Skip(1)) // Skip the first marker since it's our start
            {
                var index = lowerText.IndexOf(marker.ToLowerInvariant(), startIndex);
                if (index != -1 && index < endIndex)
                {
                    endIndex = index;
                }
            }

            if (endIndex <= startIndex)
                return string.Empty;

            var extracted = fullText.Substring(startIndex, endIndex - startIndex).Trim();
            
            // Clean up common formatting artifacts
            extracted = System.Text.RegularExpressions.Regex.Replace(extracted, @"^[:\-–—]\s*", "", 
                System.Text.RegularExpressions.RegexOptions.Multiline);
            
            return extracted;
        }
    }
}