"""Enhanced secure configuration using Pydantic Settings v2.

This module provides type-safe configuration management with validation
and support for multiple environment files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set

from pydantic import (
    Field,
    SecretStr,
    field_validator,
    model_validator,
    ValidationError,
    field_serializer,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings with comprehensive validation.
    
    All sensitive data is stored using SecretStr for security.
    Supports loading from .env files with environment-based selection.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )
    
    # Environment configuration
    environment: Literal["development", "production", "testing"] = Field(
        default="production",
        description="Current environment mode"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    # Paperless NGX API Configuration
    paperless_base_url: str = Field(
        default="https://paperless.local/api",
        description="Base URL for Paperless NGX API",
        pattern=r"^https?://.*"
    )
    paperless_api_token: SecretStr = Field(
        description="API token for Paperless NGX authentication"
    )
    paperless_timeout_connect: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Connection timeout in seconds"
    )
    paperless_timeout_read: int = Field(
        default=120,
        ge=10,
        le=600,
        description="Read timeout in seconds"
    )
    paperless_rate_limit: float = Field(
        default=5.0,
        gt=0,
        le=100,
        description="Maximum requests per second to Paperless API"
    )
    
    # LLM Configuration
    use_litellm: bool = Field(
        default=True,
        description="Use LiteLLM for unified LLM interface"
    )
    
    # LLM Provider Order Configuration (stored as string, parsed to list)
    llm_provider_order_str: str = Field(
        default="openai,ollama,anthropic",
        description="Order in which to try LLM providers (comma-separated)",
        alias="LLM_PROVIDER_ORDER"
    )
    
    @property
    def llm_provider_order(self) -> List[str]:
        """Get provider order as list."""
        return [p.strip() for p in self.llm_provider_order_str.split(",") if p.strip()]
    
    # Ollama Configuration
    ollama_enabled: bool = Field(
        default=True,
        description="Enable Ollama as primary LLM"
    )
    ollama_model: str = Field(
        default="llama3.1:8b",
        description="Ollama model to use"
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL",
        pattern=r"^https?://.*"
    )
    ollama_timeout: int = Field(
        default=120,
        ge=10,
        le=600,
        description="Ollama request timeout in seconds"
    )
    ollama_max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retries for Ollama requests"
    )
    
    # OpenAI Configuration
    openai_enabled: bool = Field(
        default=True,
        description="Enable OpenAI provider"
    )
    openai_api_key: Optional[SecretStr] = Field(
        default=None,
        description="OpenAI API key"
    )
    openai_organization: Optional[str] = Field(
        default=None,
        description="OpenAI organization ID"
    )
    openai_model: str = Field(
        default="gpt-3.5-turbo",
        description="OpenAI model to use"
    )
    openai_timeout: int = Field(
        default=30,
        ge=5,
        le=120,
        description="OpenAI request timeout in seconds"
    )
    openai_max_tokens: int = Field(
        default=2000,
        ge=100,
        le=4000,
        description="Maximum tokens for OpenAI response"
    )
    openai_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Temperature for OpenAI model"
    )
    
    # Anthropic Configuration (Placeholder)
    anthropic_enabled: bool = Field(
        default=False,
        description="Enable Anthropic Claude provider"
    )
    anthropic_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Anthropic API key"
    )
    anthropic_model: str = Field(
        default="claude-3-sonnet",
        description="Anthropic model to use"
    )
    anthropic_max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retries for Anthropic requests"
    )
    
    # Google Gemini Configuration (Placeholder)
    gemini_enabled: bool = Field(
        default=False,
        description="Enable Google Gemini provider"
    )
    gemini_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Google Gemini API key"
    )
    gemini_model: str = Field(
        default="gemini-pro",
        description="Gemini model to use"
    )
    gemini_max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retries for Gemini requests"
    )
    
    # Custom LLM Configuration (Placeholder)
    custom_llm_enabled: bool = Field(
        default=False,
        description="Enable custom LLM provider"
    )
    custom_llm_name: str = Field(
        default="custom-provider",
        description="Name of custom LLM provider"
    )
    custom_llm_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Custom LLM API key"
    )
    custom_llm_base_url: Optional[str] = Field(
        default=None,
        description="Custom LLM base URL",
        pattern=r"^https?://.*"
    )
    custom_llm_model: str = Field(
        default="custom-model",
        description="Custom LLM model to use"
    )
    custom_llm_max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retries for custom LLM requests"
    )
    
    # Logging Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    log_file: Optional[Path] = Field(
        default=None,
        description="Path to log file"
    )
    log_rotation_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        gt=0,
        description="Log file rotation size in bytes"
    )
    log_backup_count: int = Field(
        default=5,
        ge=0,
        le=100,
        description="Number of backup log files to keep"
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s",
        description="Log message format"
    )
    
    # Application Settings
    app_name: str = Field(
        default="Paperless NGX Integration",
        description="Application name for logging and identification"
    )
    app_data_dir: Path = Field(
        default=Path.home() / ".paperless_ngx_integration",
        description="Application data directory"
    )
    
    # Document Processing Settings
    default_recipient: str = Field(
        default="Daniel Schindler / EBN Veranstaltungen und Consulting GmbH",
        description="Default document recipient"
    )
    recipient_address: str = Field(
        default="Alexiusstr. 6, 76275 Ettlingen",
        description="Recipient address for validation"
    )
    max_description_length: int = Field(
        default=128,
        ge=50,
        le=500,
        description="Maximum length for document descriptions"
    )
    min_tags: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Minimum number of tags per document"
    )
    max_tags: int = Field(
        default=7,
        ge=3,
        le=20,
        description="Maximum number of tags per document"
    )
    
    # Cost Tracking Settings
    enable_cost_tracking: bool = Field(
        default=True,
        description="Enable LLM cost tracking"
    )
    cost_alert_threshold: float = Field(
        default=10.0,
        ge=0,
        description="Alert threshold for LLM costs in EUR"
    )
    
    @field_validator("llm_provider_order", mode="before")
    @classmethod
    def parse_provider_order(cls, v: Any) -> List[str]:
        """Parse comma-separated provider order string."""
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v
    
    @field_validator("paperless_base_url", "ollama_base_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URLs don't end with trailing slash."""
        return v.rstrip("/")
    
    @field_validator("log_file")
    @classmethod
    def validate_log_file(cls, v: Optional[Path]) -> Optional[Path]:
        """Ensure log directory exists if log file is specified."""
        if v is not None:
            v = Path(v)
            v.parent.mkdir(parents=True, exist_ok=True)
        return v
    
    @field_validator("app_data_dir")
    @classmethod
    def validate_app_data_dir(cls, v: Path) -> Path:
        """Ensure application data directory exists."""
        v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    @model_validator(mode="after")
    def validate_llm_config(self) -> "Settings":
        """Ensure at least one LLM is configured and provider order is valid."""
        # Check that at least one provider in the order is enabled and configured
        available_providers = []
        
        for provider in self.llm_provider_order:
            if provider == "openai" and self.openai_enabled and self.openai_api_key:
                available_providers.append("openai")
            elif provider == "ollama" and self.ollama_enabled:
                available_providers.append("ollama")
            elif provider == "anthropic" and self.anthropic_enabled and self.anthropic_api_key:
                available_providers.append("anthropic")
            elif provider == "gemini" and self.gemini_enabled and self.gemini_api_key:
                available_providers.append("gemini")
            elif provider == "custom" and self.custom_llm_enabled and self.custom_llm_api_key:
                available_providers.append("custom")
        
        if not available_providers:
            raise ValueError(
                "At least one LLM provider must be properly configured. "
                "Check that providers in LLM_PROVIDER_ORDER are enabled and have API keys."
            )
        
        # Validate provider names in order
        valid_providers = {"openai", "ollama", "anthropic", "gemini", "custom"}
        invalid_providers = set(self.llm_provider_order) - valid_providers
        if invalid_providers:
            raise ValueError(
                f"Invalid provider(s) in LLM_PROVIDER_ORDER: {invalid_providers}. "
                f"Valid providers are: {valid_providers}"
            )
        
        return self
    
    @model_validator(mode="after")
    def validate_tag_counts(self) -> "Settings":
        """Ensure min_tags <= max_tags."""
        if self.min_tags > self.max_tags:
            raise ValueError(
                f"min_tags ({self.min_tags}) cannot be greater than "
                f"max_tags ({self.max_tags})"
            )
        return self
    
    def get_secret_value(self, field_name: str) -> Optional[str]:
        """Safely retrieve secret value.
        
        Args:
            field_name: Name of the field containing SecretStr
            
        Returns:
            The secret value as string or None if not set
        """
        value = getattr(self, field_name, None)
        if isinstance(value, SecretStr):
            return value.get_secret_value()
        return value
    
    @classmethod
    def load_from_env(cls, env_file: Optional[str] = None) -> "Settings":
        """Load settings from specific environment file.
        
        Args:
            env_file: Path to environment file (e.g., '.env.development')
            
        Returns:
            Configured Settings instance
            
        Raises:
            ValidationError: If configuration is invalid
        """
        if env_file:
            return cls(_env_file=env_file)
        
        # Try to load environment-specific file
        env = cls(paperless_api_token="temp", _env_file=".env").environment
        env_specific_file = f".env.{env}"
        
        if Path(env_specific_file).exists():
            logger.info(f"Loading configuration from {env_specific_file}")
            return cls(_env_file=env_specific_file)
        
        return cls()
    
    def validate_at_startup(self) -> Dict[str, Any]:
        """Perform comprehensive validation at application startup.
        
        Returns:
            Dictionary with validation results
            
        Raises:
            ValidationError: If critical configuration is missing or invalid
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "info": []
        }
        
        # Check Paperless API token
        if not self.paperless_api_token:
            results["errors"].append("Paperless API token is required")
            results["valid"] = False
        
        # Check LLM configuration
        results["info"].append(f"LLM provider order: {' -> '.join(self.llm_provider_order)}")
        
        available_providers = []
        for provider in self.llm_provider_order:
            if provider == "openai" and self.openai_enabled and self.openai_api_key:
                available_providers.append(f"OpenAI ({self.openai_model})")
            elif provider == "ollama" and self.ollama_enabled:
                available_providers.append(f"Ollama ({self.ollama_model})")
            elif provider == "anthropic" and self.anthropic_enabled and self.anthropic_api_key:
                available_providers.append(f"Anthropic ({self.anthropic_model})")
            elif provider == "gemini" and self.gemini_enabled and self.gemini_api_key:
                available_providers.append(f"Gemini ({self.gemini_model})")
            elif provider == "custom" and self.custom_llm_enabled and self.custom_llm_api_key:
                available_providers.append(f"Custom ({self.custom_llm_name}: {self.custom_llm_model})")
        
        if available_providers:
            results["info"].append(f"Available LLM providers: {', '.join(available_providers)}")
        else:
            results["errors"].append("No LLM providers properly configured")
            results["valid"] = False
        
        # Check URLs accessibility (optional)
        if self.paperless_base_url.startswith("http://"):
            results["warnings"].append(
                "Paperless API uses unencrypted HTTP connection. "
                "Consider using HTTPS for production."
            )
        
        # Check data directory
        if not self.app_data_dir.exists():
            try:
                self.app_data_dir.mkdir(parents=True, exist_ok=True)
                results["info"].append(f"Created app data directory: {self.app_data_dir}")
            except Exception as e:
                results["errors"].append(f"Cannot create app data directory: {e}")
                results["valid"] = False
        
        # Log validation results
        logger.info(f"Configuration validation: {'PASSED' if results['valid'] else 'FAILED'}")
        for error in results["errors"]:
            logger.error(f"Config error: {error}")
        for warning in results["warnings"]:
            logger.warning(f"Config warning: {warning}")
        for info in results["info"]:
            logger.info(f"Config info: {info}")
        
        if not results["valid"]:
            raise ValidationError(f"Configuration validation failed: {results['errors']}")
        
        return results
    
    def to_safe_dict(self) -> Dict[str, Any]:
        """Export settings as dictionary with masked secrets.
        
        Returns:
            Dictionary with all settings, secrets are masked
        """
        data = self.model_dump()
        
        # Mask sensitive fields
        sensitive_fields = {
            "paperless_api_token",
            "openai_api_key",
            "anthropic_api_key",
            "gemini_api_key",
            "custom_llm_api_key"
        }
        
        for field in sensitive_fields:
            if field in data and data[field]:
                data[field] = "***MASKED***"
        
        return data


# Singleton instance
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings singleton instance.
    
    Returns:
        Configured Settings instance
        
    Raises:
        ValidationError: If configuration is invalid
    """
    global _settings_instance
    
    if _settings_instance is None:
        _settings_instance = Settings.load_from_env()
        _settings_instance.validate_at_startup()
    
    return _settings_instance


def reload_settings(env_file: Optional[str] = None) -> Settings:
    """Reload settings from environment file.
    
    Args:
        env_file: Optional specific environment file to load
        
    Returns:
        New Settings instance
    """
    global _settings_instance
    
    _settings_instance = Settings.load_from_env(env_file)
    _settings_instance.validate_at_startup()
    
    return _settings_instance