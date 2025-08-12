"""POSIX-specific platform implementation (Linux/macOS).

This module provides POSIX-specific implementations of platform operations,
handling Unix-like path conventions and filesystem operations.
"""

from __future__ import annotations

import os
import platform
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List

from .interfaces import PlatformService


class PosixPlatform(PlatformService):
    """POSIX-specific platform service implementation."""
    
    def __init__(self):
        """Initialize POSIX platform service."""
        self._system = platform.system()
    
    @property
    def name(self) -> str:
        """Get platform name."""
        return self._system
    
    @property
    def is_windows(self) -> bool:
        """Check if running on Windows."""
        return False
    
    @property
    def is_posix(self) -> bool:
        """Check if running on POSIX-compliant system."""
        return True
    
    @property
    def path_separator(self) -> str:
        """Get platform-specific path separator."""
        return "/"
    
    @property
    def line_separator(self) -> str:
        """Get platform-specific line separator."""
        return "\n"
    
    def get_temp_dir(self) -> Path:
        """Get POSIX temporary directory.
        
        Returns:
            Path to temporary directory (usually /tmp or /var/tmp)
        """
        return Path(tempfile.gettempdir())
    
    def get_user_data_dir(self, app_name: str) -> Path:
        """Get POSIX user data directory.
        
        Follows XDG Base Directory Specification when available.
        
        Args:
            app_name: Application name for directory creation
            
        Returns:
            Path to user data directory
        """
        # Check XDG_DATA_HOME first
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            return Path(xdg_data_home) / app_name
        
        # Fallback to ~/.local/share
        return Path.home() / ".local" / "share" / app_name
    
    def get_config_dir(self, app_name: str) -> Path:
        """Get POSIX configuration directory.
        
        Follows XDG Base Directory Specification when available.
        
        Args:
            app_name: Application name for directory creation
            
        Returns:
            Path to configuration directory
        """
        # Check XDG_CONFIG_HOME first
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            return Path(xdg_config_home) / app_name
        
        # Fallback to ~/.config
        return Path.home() / ".config" / app_name
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for POSIX filesystem.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename safe for POSIX
        """
        # Remove null bytes
        filename = filename.replace("\x00", "")
        
        # Replace path separators
        filename = filename.replace("/", "_")
        
        # Remove leading dots (hidden files) unless that's all there is
        while filename.startswith(".") and len(filename) > 1:
            filename = filename[1:]
        
        # Limit length (most filesystems support 255 bytes)
        # Account for UTF-8 encoding where characters can be multiple bytes
        while len(filename.encode('utf-8')) > 255:
            # Remove characters from the end, preserving extension if possible
            if "." in filename:
                name, ext = filename.rsplit(".", 1)
                if len(name) > 1:
                    name = name[:-1]
                    filename = f"{name}.{ext}"
                else:
                    filename = filename[:-1]
            else:
                filename = filename[:-1]
        
        # Ensure filename is not empty
        if not filename or filename == ".":
            filename = "unnamed_file"
        
        return filename
    
    def is_valid_path(self, path: Path) -> Tuple[bool, Optional[str]]:
        """Check if path is valid for POSIX.
        
        Args:
            path: Path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        path_str = str(path)
        
        # Check for null bytes
        if "\x00" in path_str:
            return False, "Path cannot contain null bytes"
        
        # Check individual component length (255 bytes max)
        for component in path.parts:
            if len(component.encode('utf-8')) > 255:
                return False, f"Path component too long: {component}"
        
        # Check total path length (typically 4096 bytes max)
        if len(path_str.encode('utf-8')) > 4096:
            return False, f"Path too long ({len(path_str.encode('utf-8'))} > 4096 bytes)"
        
        return True, None
    
    def normalize_path(self, path: Path) -> Path:
        """Normalize path for POSIX.
        
        Args:
            path: Path to normalize
            
        Returns:
            Normalized path
        """
        # Resolve symlinks and make absolute
        try:
            path = path.resolve()
        except (OSError, RuntimeError):
            # If resolve fails (broken symlink, etc.), just make absolute
            path = path.absolute()
        
        # Remove redundant separators and up-level references
        path = Path(os.path.normpath(str(path)))
        
        return path
    
    def create_temp_file(
        self, 
        suffix: Optional[str] = None,
        prefix: Optional[str] = None,
        text: bool = True
    ) -> tempfile._TemporaryFileWrapper:
        """Create a temporary file with POSIX-appropriate settings.
        
        Args:
            suffix: File suffix
            prefix: File prefix
            text: Whether to open in text mode
            
        Returns:
            Temporary file wrapper
        """
        if text:
            return tempfile.NamedTemporaryFile(
                mode='w+',
                suffix=suffix,
                prefix=prefix,
                delete=True,  # POSIX handles auto-delete well
                encoding='utf-8'
            )
        else:
            return tempfile.NamedTemporaryFile(
                mode='w+b',
                suffix=suffix,
                prefix=prefix,
                delete=True
            )
    
    def create_temp_dir(
        self,
        suffix: Optional[str] = None,
        prefix: Optional[str] = None
    ) -> tempfile.TemporaryDirectory:
        """Create a temporary directory with POSIX-appropriate settings.
        
        Args:
            suffix: Directory suffix
            prefix: Directory prefix
            
        Returns:
            Temporary directory context manager
        """
        return tempfile.TemporaryDirectory(suffix=suffix, prefix=prefix)
    
    def get_file_encoding(self) -> str:
        """Get POSIX file encoding.
        
        Returns:
            'utf-8' (standard for modern POSIX systems)
        """
        return 'utf-8'
    
    def is_case_sensitive_filesystem(self) -> bool:
        """Check if the filesystem is case-sensitive.
        
        Returns:
            True for most POSIX filesystems (can be overridden for macOS)
        """
        # macOS can have case-insensitive filesystems
        if self._system == "Darwin":
            # Test by creating temp files with different cases
            test_dir = self.get_temp_dir()
            test_file_lower = test_dir / "test_case_sensitivity"
            test_file_upper = test_dir / "TEST_CASE_SENSITIVITY"
            
            try:
                test_file_lower.touch()
                test_file_upper.touch()
                # If both exist as separate files, filesystem is case-sensitive
                result = test_file_lower.stat().st_ino != test_file_upper.stat().st_ino
                test_file_lower.unlink(missing_ok=True)
                test_file_upper.unlink(missing_ok=True)
                return result
            except:
                # Assume case-sensitive if test fails
                return True
        
        # Linux and other Unix systems are typically case-sensitive
        return True
    
    def get_reserved_names(self) -> List[str]:
        """Get list of reserved filenames for POSIX.
        
        Returns:
            Empty list (POSIX has no reserved filenames like Windows)
        """
        return []
    
    def get_invalid_path_chars(self) -> str:
        """Get characters that are invalid in paths on POSIX.
        
        Returns:
            String of invalid characters (only null byte and forward slash)
        """
        return "\x00"
    
    def fix_long_path(self, path: Path) -> Path:
        """Fix long path issues on POSIX.
        
        POSIX systems don't have the same path length limitations as Windows,
        so this just returns the path unchanged.
        
        Args:
            path: Path to fix
            
        Returns:
            The same path (no fixing needed on POSIX)
        """
        return path