using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MeetingNotesMaker.Infrastructure.Exceptions
{
    public class InfrastructureException : Exception
    {
        public string ErrorCode { get; }

        public InfrastructureException(string message, string errorCode) : base(message)
        {
            ErrorCode = errorCode;
        }

        public InfrastructureException(string message, string errorCode, Exception innerException) : base(message, innerException)
        {
            ErrorCode = errorCode;
        }
    }

    public class FileValidationException : InfrastructureException
    {
        public FileValidationException(string message) : base(message, "FILE_VALIDATION_ERROR")
        {
        }

        public FileValidationException(string message, Exception innerException) : base(message, "FILE_VALIDATION_ERROR", innerException)
        {
        }
    }

    public class ConfigurationException : InfrastructureException
    {
        public ConfigurationException(string message) : base(message, "CONFIGURATION_ERROR")
        {
        }

        public ConfigurationException(string message, Exception innerException) : base(message, "CONFIGURATION_ERROR", innerException)
        {
        }
    }
}