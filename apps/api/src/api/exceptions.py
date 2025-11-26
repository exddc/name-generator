"""Custom exceptions with user-friendly error messages."""

from fastapi import HTTPException
from api.models.api_models import ErrorCode, ErrorResponse


# User-friendly error messages
ERROR_MESSAGES = {
    ErrorCode.SERVICE_UNAVAILABLE: "Our domain generation service is temporarily unavailable. Please try again in a few moments.",
    ErrorCode.TIMEOUT: "The request took too long to complete. Please try again.",
    ErrorCode.RATE_LIMITED: "You've made too many requests. Please wait a moment before trying again.",
    ErrorCode.GENERATION_FAILED: "We couldn't generate domain suggestions right now. Please try again.",
    ErrorCode.NO_DOMAINS_FOUND: "No available domains were found for your description. Try a different description or get creative!",
    ErrorCode.INVALID_INPUT: "The provided input is invalid. Please check your request and try again.",
    ErrorCode.DOMAIN_NOT_FOUND: "The specified domain was not found in our database.",
    ErrorCode.AUTH_REQUIRED: "You need to be logged in to perform this action.",
    ErrorCode.INTERNAL_ERROR: "Something went wrong on our end. Please try again later.",
}


class DomainGeneratorException(HTTPException):
    """Base exception for domain generator errors."""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str | None = None,
        details: str | None = None,
        retry_allowed: bool = False,
        status_code: int = 500,
    ):
        self.code = code
        self.user_message = message or ERROR_MESSAGES.get(code, "An unexpected error occurred.")
        self.details = details
        self.retry_allowed = retry_allowed
        
        super().__init__(
            status_code=status_code,
            detail=ErrorResponse(
                code=code,
                message=self.user_message,
                details=details,
                retry_allowed=retry_allowed,
            ).model_dump(),
        )


class ServiceUnavailableError(DomainGeneratorException):
    """Raised when the service (LLM, Redis, etc.) is unavailable."""
    
    def __init__(self, details: str | None = None):
        super().__init__(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            details=details,
            retry_allowed=True,
            status_code=503,
        )


class TimeoutError(DomainGeneratorException):
    """Raised when a request times out."""
    
    def __init__(self, details: str | None = None):
        super().__init__(
            code=ErrorCode.TIMEOUT,
            details=details,
            retry_allowed=True,
            status_code=504,
        )


class RateLimitedError(DomainGeneratorException):
    """Raised when the user or service is rate limited."""
    
    def __init__(self, details: str | None = None):
        super().__init__(
            code=ErrorCode.RATE_LIMITED,
            details=details,
            retry_allowed=True,
            status_code=429,
        )


class GenerationFailedError(DomainGeneratorException):
    """Raised when domain generation fails."""
    
    def __init__(self, details: str | None = None):
        super().__init__(
            code=ErrorCode.GENERATION_FAILED,
            details=details,
            retry_allowed=True,
            status_code=500,
        )


class NoDomainFoundError(DomainGeneratorException):
    """Raised when no domains are found."""
    
    def __init__(self, details: str | None = None):
        super().__init__(
            code=ErrorCode.NO_DOMAINS_FOUND,
            details=details,
            retry_allowed=True,
            status_code=404,
        )


class InvalidInputError(DomainGeneratorException):
    """Raised for invalid input."""
    
    def __init__(self, message: str | None = None, details: str | None = None):
        super().__init__(
            code=ErrorCode.INVALID_INPUT,
            message=message,
            details=details,
            retry_allowed=False,
            status_code=400,
        )


class DomainNotFoundError(DomainGeneratorException):
    """Raised when a domain is not found in the database."""
    
    def __init__(self, domain: str | None = None):
        super().__init__(
            code=ErrorCode.DOMAIN_NOT_FOUND,
            details=f"Domain: {domain}" if domain else None,
            retry_allowed=False,
            status_code=404,
        )


class AuthRequiredError(DomainGeneratorException):
    """Raised when authentication is required."""
    
    def __init__(self, details: str | None = None):
        super().__init__(
            code=ErrorCode.AUTH_REQUIRED,
            details=details,
            retry_allowed=False,
            status_code=401,
        )


def create_error_response(code: ErrorCode, details: str | None = None, retry_allowed: bool = False) -> ErrorResponse:
    """Create a user-friendly error response."""
    return ErrorResponse(
        code=code,
        message=ERROR_MESSAGES.get(code, "An unexpected error occurred."),
        details=details,
        retry_allowed=retry_allowed,
    )
