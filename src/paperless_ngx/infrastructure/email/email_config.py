"""Email configuration module for multi-provider support.

This module provides configuration for multiple email accounts including
Gmail and IONOS, with support for IMAP connections and secure password storage.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, SecretStr, field_validator


@dataclass
class EmailAccount:
    """Email account configuration."""
    
    name: str
    provider: str
    imap_server: str
    imap_port: int
    email: str
    password: str
    folder: str = "INBOX"
    enabled: bool = True
    use_ssl: bool = True
    
    def __post_init__(self) -> None:
        """Validate account configuration."""
        if not self.email:
            raise ValueError(f"Email address required for account {self.name}")
        if not self.password:
            raise ValueError(f"Password required for account {self.name}")
        if self.imap_port not in (993, 143, 995, 110):
            raise ValueError(f"Invalid IMAP port {self.imap_port} for account {self.name}")


class EmailSettings(BaseModel):
    """Email processing settings with validation."""
    
    # Email check configuration
    email_check_interval: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Interval between email checks in seconds"
    )
    
    # Download configuration
    email_download_dir: Path = Field(
        default=Path("./downloads/email_attachments"),
        description="Directory to save email attachments"
    )
    
    # Processing state
    email_processed_db: Path = Field(
        default=Path("./data/processed_emails.json"),
        description="Database file to track processed emails"
    )
    
    # Attachment filters
    allowed_extensions: List[str] = Field(
        default=[".pdf", ".doc", ".docx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg", ".tiff", ".txt"],
        description="Allowed file extensions for attachments"
    )
    
    max_attachment_size: int = Field(
        default=50 * 1024 * 1024,  # 50MB
        gt=0,
        description="Maximum attachment size in bytes"
    )
    
    # Processing options
    mark_as_read: bool = Field(
        default=True,
        description="Mark emails as read after processing"
    )
    
    delete_after_processing: bool = Field(
        default=False,
        description="Delete emails after successful processing"
    )
    
    # Gmail specific settings
    gmail1_email: Optional[SecretStr] = Field(
        default=None,
        description="Gmail account 1 email address"
    )
    gmail1_app_password: Optional[SecretStr] = Field(
        default=None,
        description="Gmail account 1 app-specific password"
    )
    
    gmail2_email: Optional[SecretStr] = Field(
        default=None,
        description="Gmail account 2 email address"
    )
    gmail2_app_password: Optional[SecretStr] = Field(
        default=None,
        description="Gmail account 2 app-specific password"
    )
    
    # IONOS specific settings
    ionos_email: Optional[SecretStr] = Field(
        default=None,
        description="IONOS account email address"
    )
    ionos_password: Optional[SecretStr] = Field(
        default=None,
        description="IONOS account password"
    )
    
    # Filtering options
    sender_whitelist: List[str] = Field(
        default=[],
        description="Only process emails from these senders"
    )
    
    sender_blacklist: List[str] = Field(
        default=[],
        description="Skip emails from these senders"
    )
    
    subject_patterns: List[str] = Field(
        default=[],
        description="Only process emails matching these subject patterns"
    )
    
    @field_validator("email_download_dir", "email_processed_db")
    @classmethod
    def ensure_directories(cls, v: Path) -> Path:
        """Ensure parent directories exist."""
        v = Path(v)
        v.parent.mkdir(parents=True, exist_ok=True)
        return v
    
    def get_email_accounts(self) -> List[EmailAccount]:
        """Get configured email accounts.
        
        Returns:
            List of configured and enabled EmailAccount instances
        """
        accounts = []
        
        # Gmail Account 1
        if self.gmail1_email and self.gmail1_app_password:
            accounts.append(EmailAccount(
                name="Gmail Account 1",
                provider="gmail",
                imap_server="imap.gmail.com",
                imap_port=993,
                email=self.gmail1_email.get_secret_value(),
                password=self.gmail1_app_password.get_secret_value(),
                folder="INBOX",
                enabled=True
            ))
        
        # Gmail Account 2
        if self.gmail2_email and self.gmail2_app_password:
            accounts.append(EmailAccount(
                name="Gmail Account 2",
                provider="gmail",
                imap_server="imap.gmail.com",
                imap_port=993,
                email=self.gmail2_email.get_secret_value(),
                password=self.gmail2_app_password.get_secret_value(),
                folder="INBOX",
                enabled=True
            ))
        
        # IONOS Account
        if self.ionos_email and self.ionos_password:
            accounts.append(EmailAccount(
                name="IONOS Account",
                provider="ionos",
                imap_server="imap.ionos.de",
                imap_port=993,
                email=self.ionos_email.get_secret_value(),
                password=self.ionos_password.get_secret_value(),
                folder="INBOX",
                enabled=True
            ))
        
        return [acc for acc in accounts if acc.enabled]
    
    def validate_accounts(self) -> Dict[str, Any]:
        """Validate email account configuration.
        
        Returns:
            Validation results dictionary
        """
        results = {
            "valid": True,
            "accounts": [],
            "errors": [],
            "warnings": []
        }
        
        accounts = self.get_email_accounts()
        
        if not accounts:
            results["warnings"].append("No email accounts configured")
        
        for account in accounts:
            account_info = {
                "name": account.name,
                "provider": account.provider,
                "email": account.email[:3] + "***",  # Mask email
                "configured": True
            }
            results["accounts"].append(account_info)
        
        return results


def load_email_config_from_env() -> EmailSettings:
    """Load email configuration from environment variables.
    
    Returns:
        Configured EmailSettings instance
    """
    # Load from environment
    config = {
        "email_check_interval": int(os.getenv("EMAIL_CHECK_INTERVAL", "300")),
        "email_download_dir": Path(os.getenv("EMAIL_DOWNLOAD_DIR", "./downloads/email_attachments")),
        "email_processed_db": Path(os.getenv("EMAIL_PROCESSED_DB", "./data/processed_emails.json")),
    }
    
    # Gmail Account 1
    if gmail1_email := os.getenv("GMAIL1_EMAIL"):
        config["gmail1_email"] = SecretStr(gmail1_email)
    if gmail1_password := os.getenv("GMAIL1_APP_PASSWORD"):
        config["gmail1_app_password"] = SecretStr(gmail1_password)
    
    # Gmail Account 2
    if gmail2_email := os.getenv("GMAIL2_EMAIL"):
        config["gmail2_email"] = SecretStr(gmail2_email)
    if gmail2_password := os.getenv("GMAIL2_APP_PASSWORD"):
        config["gmail2_app_password"] = SecretStr(gmail2_password)
    
    # IONOS Account
    if ionos_email := os.getenv("IONOS_EMAIL"):
        config["ionos_email"] = SecretStr(ionos_email)
    if ionos_password := os.getenv("IONOS_PASSWORD"):
        config["ionos_password"] = SecretStr(ionos_password)
    
    # Additional settings
    if mark_as_read := os.getenv("EMAIL_MARK_AS_READ"):
        config["mark_as_read"] = mark_as_read.lower() == "true"
    
    if delete_after := os.getenv("EMAIL_DELETE_AFTER_PROCESSING"):
        config["delete_after_processing"] = delete_after.lower() == "true"
    
    if max_size := os.getenv("EMAIL_MAX_ATTACHMENT_SIZE"):
        config["max_attachment_size"] = int(max_size)
    
    return EmailSettings(**config)


# Default configuration for development/testing
DEFAULT_EMAIL_ACCOUNTS = [
    {
        "name": "Gmail Account 1",
        "provider": "gmail",
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "email": os.getenv("GMAIL1_EMAIL", ""),
        "password": os.getenv("GMAIL1_APP_PASSWORD", ""),
        "folder": "INBOX",
        "enabled": bool(os.getenv("GMAIL1_EMAIL"))
    },
    {
        "name": "Gmail Account 2",
        "provider": "gmail",
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "email": os.getenv("GMAIL2_EMAIL", ""),
        "password": os.getenv("GMAIL2_APP_PASSWORD", ""),
        "folder": "INBOX",
        "enabled": bool(os.getenv("GMAIL2_EMAIL"))
    },
    {
        "name": "IONOS Account",
        "provider": "ionos",
        "imap_server": "imap.ionos.de",
        "imap_port": 993,
        "email": os.getenv("IONOS_EMAIL", ""),
        "password": os.getenv("IONOS_PASSWORD", ""),
        "folder": "INBOX",
        "enabled": bool(os.getenv("IONOS_EMAIL"))
    }
]