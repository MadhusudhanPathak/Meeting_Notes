using System;
using System.Collections.Generic;

namespace MeetingNotesMaker.Models
{
    public class TranscriptionResult
    {
        public string FullText { get; set; } = string.Empty;
        public List<TranscriptionSegment> Segments { get; set; } = new List<TranscriptionSegment>();
        public TimeSpan Duration { get; set; }
        public string FileName { get; set; } = string.Empty;
    }

    public class TranscriptionSegment
    {
        public TimeSpan StartTime { get; set; }
        public TimeSpan EndTime { get; set; }
        public string Text { get; set; } = string.Empty;
    }
}