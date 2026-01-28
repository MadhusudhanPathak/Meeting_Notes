using System.ComponentModel.DataAnnotations;

namespace MeetingNotesMaker.Application.DTOs
{
    public class ProcessMeetingRequestDto
    {
        [Required]
        [StringLength(500)]
        public string AudioFilePath { get; set; } = string.Empty;

        [Required]
        [StringLength(500)]
        public string WhisperModelPath { get; set; } = string.Empty;

        [Required]
        [StringLength(500)]
        public string SystemPromptPath { get; set; } = string.Empty;

        [Required]
        [StringLength(100)]
        public string OllamaModelName { get; set; } = string.Empty;
    }

    public class ProcessMeetingResponseDto
    {
        public bool Success { get; set; }
        public string Message { get; set; } = string.Empty;
        public string? PdfFilePath { get; set; }
        public string? TranscriptFilePath { get; set; }
        public double ProcessingTimeMs { get; set; }
    }

    public class DependencyCheckResultDto
    {
        public bool IsReady { get; set; }
        public List<DependencyIssueDto> Issues { get; set; } = new List<DependencyIssueDto>();
    }

    public class DependencyIssueDto
    {
        public string Component { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public string Severity { get; set; } = string.Empty; // "Warning" or "Error"
        public string ResolutionHint { get; set; } = string.Empty;
    }

    public class TranscriptionProgressDto
    {
        public int Percentage { get; set; }
        public string StatusMessage { get; set; } = string.Empty;
    }
}