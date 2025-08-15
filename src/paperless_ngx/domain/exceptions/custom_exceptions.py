"""Comprehensive exception hierarchy for the application.

This module defines custom exceptions with error codes, user-friendly messages,
and retry decorators for transient failures.
"""

from __future__ import annotations

import functools
import random
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union

from src.paperless_ngx.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class ErrorCode(Enum):
    """Application error codes for categorization."""
    
    # Configuration errors (1000-1099)
    CONFIG_INVALID = 1001
    CONFIG_MISSING = 1002
    CONFIG_VALIDATION_FAILED = 1003
    
    # API errors (2000-2099)
    API_CONNECTION_FAILED = 2001
    API_AUTHENTICATION_FAILED = 2002
    API_RATE_LIMIT_EXCEEDED = 2003
    API_TIMEOUT = 2004
    API_INVALID_RESPONSE = 2005
    API_NOT_FOUND = 2006
    API_SERVER_ERROR = 2007
    
    # LLM errors (3000-3099)
    LLM_CONNECTION_FAILED = 3001
    LLM_INVALID_RESPONSE = 3002
    LLM_RATE_LIMIT_EXCEEDED = 3003
    LLM_TIMEOUT = 3004
    LLM_MODEL_NOT_AVAILABLE = 3005
    LLM_COST_LIMIT_EXCEEDED = 3006
    LLM_ALL_PROVIDERS_FAILED = 3007
    
    # Document processing errors (4000-4099)
    DOCUMENT_NOT_FOUND = 4001
    DOCUMENT_INVALID_FORMAT = 4002
    DOCUMENT_PROCESSING_FAILED = 4003
    DOCUMENT_METADATA_INVALID = 4004
    DOCUMENT_OCR_FAILED = 4005
    
    # Validation errors (5000-5099)
    VALIDATION_FAILED = 5001
    VALIDATION_CORRESPONDENT_INVALID = 5002
    VALIDATION_TAGS_INVALID = 5003
    VALIDATION_DATE_INVALID = 5004
    
    # Business logic errors (6000-6099)
    BUSINESS_RULE_VIOLATION = 6001
    BUSINESS_RECIPIENT_AS_SENDER = 6002
    BUSINESS_INVALID_WORKFLOW = 6003
    
    # System errors (9000-9099)
    SYSTEM_ERROR = 9001
    SYSTEM_RESOURCE_UNAVAILABLE = 9002
    SYSTEM_PERMISSION_DENIED = 9003


class BaseApplicationException(Exception):
    """Base exception class for all application exceptions."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        recoverable: bool = True
    ):
        """Initialize base exception.
        
        Args:
            message: Technical error message
            error_code: Error code for categorization
            details: Additional error details
            user_message: User-friendly error message
            recoverable: Whether the error is recoverable
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.user_message = user_message or self._get_default_user_message()
        self.recoverable = recoverable
        
    def _get_default_user_message(self) -> str:
        """Get default user-friendly message based on error code.
        
        Returns:
            User-friendly error message
        """
        messages = {
            ErrorCode.CONFIG_INVALID: "Die Konfiguration ist ungültig. Bitte überprüfen Sie die Einstellungen.",
            ErrorCode.CONFIG_MISSING: "Erforderliche Konfiguration fehlt. Bitte vervollständigen Sie die Einstellungen.",
            ErrorCode.API_CONNECTION_FAILED: "Verbindung zur API fehlgeschlagen. Bitte überprüfen Sie die Netzwerkverbindung.",
            ErrorCode.API_AUTHENTICATION_FAILED: "Authentifizierung fehlgeschlagen. Bitte überprüfen Sie Ihre Zugangsdaten.",
            ErrorCode.API_RATE_LIMIT_EXCEEDED: "Zu viele Anfragen. Bitte versuchen Sie es später erneut.",
            ErrorCode.LLM_CONNECTION_FAILED: "Verbindung zum KI-Modell fehlgeschlagen.",
            ErrorCode.DOCUMENT_NOT_FOUND: "Dokument nicht gefunden.",
            ErrorCode.VALIDATION_FAILED: "Validierung fehlgeschlagen. Bitte überprüfen Sie die Eingaben.",
            ErrorCode.BUSINESS_RULE_VIOLATION: "Geschäftsregel verletzt.",
            ErrorCode.SYSTEM_ERROR: "Ein Systemfehler ist aufgetreten. Bitte kontaktieren Sie den Support.",
        }
        return messages.get(self.error_code, "Ein unerwarteter Fehler ist aufgetreten.")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization.
        
        Returns:
            Dictionary representation of the exception
        """
        return {
            "error_code": self.error_code.value,
            "error_name": self.error_code.name,
            "message": self.message,
            "user_message": self.user_message,
            "details": self.details,
            "recoverable": self.recoverable
        }


# Configuration Exceptions
class ConfigurationError(BaseApplicationException):
    """Base exception for configuration errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFIG_INVALID,
            **kwargs
        )


class MissingConfigurationError(ConfigurationError):
    """Exception for missing required configuration."""
    
    def __init__(self, config_key: str, **kwargs):
        super().__init__(
            message=f"Required configuration '{config_key}' is missing",
            error_code=ErrorCode.CONFIG_MISSING,
            details={"missing_key": config_key},
            **kwargs
        )


class ConfigurationValidationError(ConfigurationError):
    """Exception for configuration validation failures."""
    
    def __init__(self, validation_errors: Dict[str, Any], **kwargs):
        super().__init__(
            message="Configuration validation failed",
            error_code=ErrorCode.CONFIG_VALIDATION_FAILED,
            details={"validation_errors": validation_errors},
            **kwargs
        )


# API Exceptions
class APIError(BaseApplicationException):
    """Base exception for API-related errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.API_CONNECTION_FAILED,
            details={"status_code": status_code} if status_code else {},
            **kwargs
        )
        self.status_code = status_code


class APIConnectionError(APIError):
    """Exception for API connection failures."""
    
    def __init__(self, url: str, original_error: Optional[Exception] = None, **kwargs):
        super().__init__(
            message=f"Failed to connect to API at {url}",
            error_code=ErrorCode.API_CONNECTION_FAILED,
            details={
                "url": url,
                "original_error": str(original_error) if original_error else None
            },
            **kwargs
        )


class APIAuthenticationError(APIError):
    """Exception for API authentication failures."""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.API_AUTHENTICATION_FAILED,
            status_code=401,
            recoverable=False,
            **kwargs
        )


class APIRateLimitError(APIError):
    """Exception for API rate limit exceeded."""
    
    def __init__(self, retry_after: Optional[int] = None, **kwargs):
        super().__init__(
            message="API rate limit exceeded",
            error_code=ErrorCode.API_RATE_LIMIT_EXCEEDED,
            status_code=429,
            details={"retry_after": retry_after},
            **kwargs
        )
        self.retry_after = retry_after


class APITimeoutError(APIError):
    """Exception for API request timeouts."""
    
    def __init__(self, timeout: float, **kwargs):
        super().__init__(
            message=f"API request timed out after {timeout} seconds",
            error_code=ErrorCode.API_TIMEOUT,
            details={"timeout": timeout},
            **kwargs
        )


class APINotFoundError(APIError):
    """Exception for API resource not found."""
    
    def __init__(self, resource: str, **kwargs):
        super().__init__(
            message=f"Resource not found: {resource}",
            error_code=ErrorCode.API_NOT_FOUND,
            status_code=404,
            details={"resource": resource},
            **kwargs
        )


# Paperless-specific API Exceptions (aliases for compatibility)
class PaperlessAPIError(APIError):
    """Base exception for Paperless API errors."""
    pass


class PaperlessAuthenticationError(APIAuthenticationError):
    """Exception for Paperless authentication failures."""
    pass


class PaperlessConnectionError(APIConnectionError):
    """Exception for Paperless connection failures."""
    pass


class PaperlessRateLimitError(APIRateLimitError):
    """Exception for Paperless rate limit exceeded."""
    pass


class PaperlessTimeoutError(APITimeoutError):
    """Exception for Paperless request timeouts."""
    pass


# LLM Exceptions
class LLMError(BaseApplicationException):
    """Base exception for LLM-related errors."""
    
    def __init__(self, message: str, provider: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.LLM_CONNECTION_FAILED,
            details={"provider": provider} if provider else {},
            **kwargs
        )
        self.provider = provider


class LLMConnectionError(LLMError):
    """Exception for LLM connection failures."""
    
    def __init__(self, provider: str, original_error: Optional[Exception] = None, **kwargs):
        super().__init__(
            message=f"Failed to connect to LLM provider: {provider}",
            error_code=ErrorCode.LLM_CONNECTION_FAILED,
            provider=provider,
            details={
                "provider": provider,
                "original_error": str(original_error) if original_error else None
            },
            **kwargs
        )


class LLMInvalidResponseError(LLMError):
    """Exception for invalid LLM responses."""
    
    def __init__(self, provider: str, response: Any, **kwargs):
        super().__init__(
            message=f"Invalid response from LLM provider: {provider}",
            error_code=ErrorCode.LLM_INVALID_RESPONSE,
            provider=provider,
            details={
                "provider": provider,
                "response_preview": str(response)[:200] if response else None
            },
            **kwargs
        )


class LLMAllProvidersFailed(LLMError):
    """Exception when all LLM providers fail."""
    
    def __init__(self, failures: Dict[str, str], **kwargs):
        super().__init__(
            message="All LLM providers failed",
            error_code=ErrorCode.LLM_ALL_PROVIDERS_FAILED,
            details={"failures": failures},
            recoverable=False,
            **kwargs
        )


class LLMCostLimitExceeded(LLMError):
    """Exception when LLM costs exceed limit."""
    
    def __init__(self, current_cost: float, limit: float, **kwargs):
        super().__init__(
            message=f"LLM cost limit exceeded: {current_cost:.2f} EUR > {limit:.2f} EUR",
            error_code=ErrorCode.LLM_COST_LIMIT_EXCEEDED,
            details={
                "current_cost": current_cost,
                "limit": limit
            },
            recoverable=False,
            **kwargs
        )


# Document Processing Exceptions
class DocumentError(BaseApplicationException):
    """Base exception for document processing errors."""
    
    def __init__(self, message: str, document_id: Optional[int] = None, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.DOCUMENT_PROCESSING_FAILED,
            details={"document_id": document_id} if document_id else {},
            **kwargs
        )
        self.document_id = document_id


class DocumentNotFoundError(DocumentError):
    """Exception for document not found."""
    
    def __init__(self, document_id: int, **kwargs):
        super().__init__(
            message=f"Document with ID {document_id} not found",
            error_code=ErrorCode.DOCUMENT_NOT_FOUND,
            document_id=document_id,
            **kwargs
        )


class DocumentMetadataError(DocumentError):
    """Exception for document metadata errors."""
    
    def __init__(self, document_id: int, metadata_errors: Dict[str, Any], **kwargs):
        # Remove error_code from kwargs if present to avoid duplicate
        kwargs.pop('error_code', None)
        super().__init__(
            message=f"Invalid metadata for document {document_id}",
            error_code=ErrorCode.DOCUMENT_METADATA_INVALID,
            document_id=document_id,
            details={
                "document_id": document_id,
                "metadata_errors": metadata_errors
            },
            **kwargs
        )


# Validation Exceptions
class ValidationError(BaseApplicationException):
    """Base exception for validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_FAILED,
            details={"field": field} if field else {},
            **kwargs
        )


class CorrespondentValidationError(ValidationError):
    """Exception for correspondent validation errors."""
    
    def __init__(self, invalid_correspondent: str, **kwargs):
        super().__init__(
            message=f"Invalid correspondent: {invalid_correspondent}",
            error_code=ErrorCode.VALIDATION_CORRESPONDENT_INVALID,
            field="correspondent",
            details={"invalid_correspondent": invalid_correspondent},
            user_message=f"'{invalid_correspondent}' ist der Empfänger, nicht der Absender",
            **kwargs
        )


# Business Logic Exceptions
class BusinessRuleViolation(BaseApplicationException):
    """Exception for business rule violations."""
    
    def __init__(self, rule: str, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.BUSINESS_RULE_VIOLATION,
            details={"violated_rule": rule},
            **kwargs
        )


class RecipientAsSenderError(BusinessRuleViolation):
    """Exception when recipient is incorrectly identified as sender."""
    
    def __init__(self, name: str, **kwargs):
        super().__init__(
            rule="recipient_not_sender",
            message=f"{name} cannot be the sender as they are the recipient",
            error_code=ErrorCode.BUSINESS_RECIPIENT_AS_SENDER,
            user_message=f"{name} ist der Empfänger und kann nicht der Absender sein",
            **kwargs
        )


# Retry Decorators
def retry_on_exception(
    exceptions: Union[Type[Exception], tuple[Type[Exception], ...]],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to retry function on specific exceptions.
    
    Args:
        exceptions: Exception types to retry on
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier
        max_delay: Maximum delay between retries
        jitter: Add random jitter to delay
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        # Calculate next delay
                        if jitter:
                            actual_delay = current_delay * (1 + random.random() * 0.1)
                        else:
                            actual_delay = current_delay
                        
                        # Apply max delay limit
                        actual_delay = min(actual_delay, max_delay)
                        
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {actual_delay:.2f}s..."
                        )
                        
                        time.sleep(actual_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )
            
            # If we get here, all attempts failed
            if last_exception:
                raise last_exception
            else:
                raise RuntimeError(f"All retry attempts failed for {func.__name__}")
        
        return wrapper
    return decorator


def retry_on_transient_error(
    max_attempts: int = 3,
    delay: float = 1.0
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to retry on transient errors (network, timeout, rate limit).
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries
        
    Returns:
        Decorated function
    """
    transient_exceptions = (
        APIConnectionError,
        APITimeoutError,
        APIRateLimitError,
        LLMConnectionError,
        ConnectionError,
        TimeoutError,
    )
    
    return retry_on_exception(
        exceptions=transient_exceptions,
        max_attempts=max_attempts,
        delay=delay,
        backoff=2.0,
        jitter=True
    )


# Exception Handlers for Different Layers
class ExceptionHandler:
    """Central exception handler for different application layers."""
    
    @staticmethod
    def handle_infrastructure_error(error: Exception) -> None:
        """Handle infrastructure layer errors.
        
        Args:
            error: The exception to handle
        """
        if isinstance(error, (APIError, LLMError)):
            logger.error(f"Infrastructure error: {error.to_dict()}")
            if not error.recoverable:
                raise
        else:
            logger.error(f"Unexpected infrastructure error: {error}", exc_info=True)
            raise
    
    @staticmethod
    def handle_domain_error(error: Exception) -> None:
        """Handle domain layer errors.
        
        Args:
            error: The exception to handle
        """
        if isinstance(error, (ValidationError, BusinessRuleViolation)):
            logger.warning(f"Domain error: {error.to_dict()}")
            raise
        else:
            logger.error(f"Unexpected domain error: {error}", exc_info=True)
            raise
    
    @staticmethod
    def handle_application_error(error: Exception) -> Dict[str, Any]:
        """Handle application layer errors and return error response.
        
        Args:
            error: The exception to handle
            
        Returns:
            Error response dictionary
        """
        if isinstance(error, BaseApplicationException):
            logger.error(f"Application error: {error.to_dict()}")
            return {
                "success": False,
                "error": error.to_dict()
            }
        else:
            logger.error(f"Unexpected application error: {error}", exc_info=True)
            return {
                "success": False,
                "error": {
                    "error_code": ErrorCode.SYSTEM_ERROR.value,
                    "message": "An unexpected error occurred",
                    "user_message": "Ein unerwarteter Fehler ist aufgetreten"
                }
            }