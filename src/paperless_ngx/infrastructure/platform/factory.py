"""Platform service factory for automatic platform detection.

This module provides factory functions to automatically detect the current
platform and return the appropriate platform service implementation.
"""

from __future__ import annotations

import platform
from typing import Optional

from .interfaces import PlatformService
from .posix_platform import PosixPlatform
from .windows_platform import WindowsPlatform


# Singleton instance
_platform_service: Optional[PlatformService] = None


def detect_platform() -> str:
    """Detect the current operating system platform.
    
    Returns:
        Platform name ('Windows', 'Linux', 'Darwin', etc.)
    """
    return platform.system()


def create_platform_service() -> PlatformService:
    """Create a platform service instance for the current platform.
    
    Returns:
        Platform service instance appropriate for the current OS
        
    Raises:
        NotImplementedError: If platform is not supported
    """
    current_platform = detect_platform()
    
    if current_platform == "Windows":
        return WindowsPlatform()
    elif current_platform in ("Linux", "Darwin", "FreeBSD", "OpenBSD", "NetBSD"):
        # All Unix-like systems use POSIX implementation
        return PosixPlatform()
    else:
        # Fallback to POSIX for unknown Unix-like systems
        # This is safer than failing completely
        import os
        if hasattr(os, 'posix'):
            return PosixPlatform()
        else:
            raise NotImplementedError(
                f"Platform '{current_platform}' is not supported. "
                "Supported platforms: Windows, Linux, macOS, BSD variants"
            )


def get_platform_service() -> PlatformService:
    """Get or create singleton platform service instance.
    
    This function ensures only one platform service instance exists
    throughout the application lifecycle.
    
    Returns:
        Singleton platform service instance
    """
    global _platform_service
    
    if _platform_service is None:
        _platform_service = create_platform_service()
    
    return _platform_service


def reset_platform_service() -> None:
    """Reset the singleton platform service instance.
    
    This is mainly useful for testing purposes.
    """
    global _platform_service
    _platform_service = None


def is_windows() -> bool:
    """Quick check if running on Windows.
    
    Returns:
        True if running on Windows, False otherwise
    """
    return detect_platform() == "Windows"


def is_linux() -> bool:
    """Quick check if running on Linux.
    
    Returns:
        True if running on Linux, False otherwise
    """
    return detect_platform() == "Linux"


def is_macos() -> bool:
    """Quick check if running on macOS.
    
    Returns:
        True if running on macOS, False otherwise
    """
    return detect_platform() == "Darwin"


def is_posix() -> bool:
    """Quick check if running on POSIX-compliant system.
    
    Returns:
        True if running on POSIX system, False otherwise
    """
    import os
    return hasattr(os, 'posix') or detect_platform() != "Windows"


def get_platform_info() -> dict:
    """Get detailed platform information.
    
    Returns:
        Dictionary with platform details
    """
    import sys
    
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "is_64bit": sys.maxsize > 2**32,
        "is_windows": is_windows(),
        "is_posix": is_posix(),
        "encoding": sys.getfilesystemencoding(),
        "file_encoding": get_platform_service().get_file_encoding()
    }