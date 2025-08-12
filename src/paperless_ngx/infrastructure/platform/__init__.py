"""Platform abstraction layer for cross-platform compatibility.

This module provides a unified interface for platform-specific operations,
ensuring the application works seamlessly on Windows, Linux, and macOS.
"""

from .factory import get_platform_service
from .interfaces import PlatformService

__all__ = ["PlatformService", "get_platform_service"]