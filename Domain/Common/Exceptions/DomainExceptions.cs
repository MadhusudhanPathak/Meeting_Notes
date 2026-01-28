using System;

namespace MeetingNotesMaker.Domain.Common.Exceptions
{
    public class DomainException : Exception
    {
        public string ErrorCode { get; }

        public DomainException(string message, string errorCode) : base(message)
        {
            ErrorCode = errorCode;
        }

        public DomainException(string message, string errorCode, Exception innerException) : base(message, innerException)
        {
            ErrorCode = errorCode;
        }
    }

    public class AudioFileValidationException : DomainException
    {
        public AudioFileValidationException(string message) : base(message, "AUDIO_FILE_VALIDATION_ERROR")
        {
        }

        public AudioFileValidationException(string message, Exception innerException) : base(message, "AUDIO_FILE_VALIDATION_ERROR", innerException)
        {
        }
    }

    public class TranscriptionException : DomainException
    {
        public TranscriptionException(string message) : base(message, "TRANSCRIPTION_ERROR")
        {
        }

        public TranscriptionException(string message, Exception innerException) : base(message, "TRANSCRIPTION_ERROR", innerException)
        {
        }
    }

    public class ModelNotFoundException : DomainException
    {
        public ModelNotFoundException(string message) : base(message, "MODEL_NOT_FOUND_ERROR")
        {
        }

        public ModelNotFoundException(string message, Exception innerException) : base(message, "MODEL_NOT_FOUND_ERROR", innerException)
        {
        }
    }

    public class OllamaConnectionException : DomainException
    {
        public OllamaConnectionException(string message) : base(message, "OLLAMA_CONNECTION_ERROR")
        {
        }

        public OllamaConnectionException(string message, Exception innerException) : base(message, "OLLAMA_CONNECTION_ERROR", innerException)
        {
        }
    }
}