"""Domain exceptions module."""

from .custom_exceptions import (
    # Base exceptions
    BaseApplicationException,
    ErrorCode,
    
    # Configuration exceptions
    ConfigurationError,
    MissingConfigurationError,
    ConfigurationValidationError,
    
    # API exceptions
    APIError,
    APIConnectionError,
    APIAuthenticationError,
    APIRateLimitError,
    APITimeoutError,
    APINotFoundError,
    
    # Paperless-specific exceptions
    PaperlessAPIError,
    PaperlessAuthenticationError,
    PaperlessConnectionError,
    PaperlessRateLimitError,
    PaperlessTimeoutError,
    
    # LLM exceptions
    LLMError,
    LLMConnectionError,
    LLMInvalidResponseError,
    LLMAllProvidersFailed,
    LLMCostLimitExceeded,
    
    # Document exceptions
    DocumentError,
    DocumentNotFoundError,
    DocumentMetadataError,
    
    # Validation exceptions
    ValidationError,
    CorrespondentValidationError,
    
    # Business logic exceptions
    BusinessRuleViolation,
    RecipientAsSenderError,
    
    # Utilities
    retry_on_exception,
    retry_on_transient_error,
    ExceptionHandler
)

__all__ = [
    "BaseApplicationException",
    "ErrorCode",
    "ConfigurationError",
    "MissingConfigurationError",
    "ConfigurationValidationError",
    "APIError",
    "APIConnectionError",
    "APIAuthenticationError",
    "APIRateLimitError",
    "APITimeoutError",
    "APINotFoundError",
    "PaperlessAPIError",
    "PaperlessAuthenticationError",
    "PaperlessConnectionError",
    "PaperlessRateLimitError",
    "PaperlessTimeoutError",
    "LLMError",
    "LLMConnectionError",
    "LLMInvalidResponseError",
    "LLMAllProvidersFailed",
    "LLMCostLimitExceeded",
    "DocumentError",
    "DocumentNotFoundError",
    "DocumentMetadataError",
    "ValidationError",
    "CorrespondentValidationError",
    "BusinessRuleViolation",
    "RecipientAsSenderError",
    "retry_on_exception",
    "retry_on_transient_error",
    "ExceptionHandler"
]