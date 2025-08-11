"""Email infrastructure module."""

from .email_client import EmailAttachment, EmailMessage, IMAPEmailClient
from .email_config import (
    DEFAULT_EMAIL_ACCOUNTS,
    EmailAccount,
    EmailSettings,
    load_email_config_from_env,
)

__all__ = [
    "DEFAULT_EMAIL_ACCOUNTS",
    "EmailAccount",
    "EmailAttachment",
    "EmailMessage",
    "EmailSettings",
    "IMAPEmailClient",
    "load_email_config_from_env",
]