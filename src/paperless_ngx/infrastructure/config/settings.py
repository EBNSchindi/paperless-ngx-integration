"""Enhanced secure configuration using Pydantic Settings v2.

This module provides type-safe configuration management with validation
and support for multiple environment files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Set

from pydantic import (
    Field,
    SecretStr,
    field_validator,
    model_validator,
    ValidationError,
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
    
    # OpenAI Configuration (Fallback)
    openai_api_key: Optional[SecretStr] = Field(
        default=None,
        description="OpenAI API key for fallback"
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
        """Ensure at least one LLM is configured."""
        if not self.ollama_enabled and not self.openai_api_key:
            raise ValueError(
                "At least one LLM must be configured. "
                "Enable Ollama or provide OpenAI API key."
            )
        
        if self.openai_api_key is None and not self.ollama_enabled:
            raise ValueError(
                "OpenAI API key is required when Ollama is disabled"
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
        if self.ollama_enabled:
            results["info"].append(f"Ollama enabled with model: {self.ollama_model}")
        
        if self.openai_api_key:
            results["info"].append(f"OpenAI configured as fallback with model: {self.openai_model}")
        else:
            results["warnings"].append("No OpenAI API key configured - fallback unavailable")
        
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
            "openai_api_key"
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