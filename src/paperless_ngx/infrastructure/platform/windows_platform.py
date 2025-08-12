"""Windows-specific platform implementation.

This module provides Windows-specific implementations of platform operations,
handling Windows path conventions, reserved names, and filesystem quirks.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List
import re

from .interfaces import PlatformService


class WindowsPlatform(PlatformService):
    """Windows-specific platform service implementation."""
    
    # Windows reserved filenames
    RESERVED_NAMES = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    }
    
    # Invalid characters in Windows filenames
    INVALID_CHARS = '<>:"|?*'
    
    # Additional invalid characters for paths (excludes : for drive letters)
    INVALID_PATH_CHARS = '<>"|?*'
    
    @property
    def name(self) -> str:
        """Get platform name."""
        return "Windows"
    
    @property
    def is_windows(self) -> bool:
        """Check if running on Windows."""
        return True
    
    @property
    def is_posix(self) -> bool:
        """Check if running on POSIX-compliant system."""
        return False
    
    @property
    def path_separator(self) -> str:
        """Get platform-specific path separator."""
        return "\\"
    
    @property
    def line_separator(self) -> str:
        """Get platform-specific line separator."""
        return "\r\n"
    
    def get_temp_dir(self) -> Path:
        """Get Windows temporary directory.
        
        Returns:
            Path to temporary directory (usually %TEMP%)
        """
        # Use tempfile.gettempdir() for cross-platform compatibility
        return Path(tempfile.gettempdir())
    
    def get_user_data_dir(self, app_name: str) -> Path:
        """Get Windows user data directory.
        
        Args:
            app_name: Application name for directory creation
            
        Returns:
            Path to user data directory (usually %APPDATA%\\app_name)
        """
        # Try APPDATA first, then LOCALAPPDATA, then fallback to home
        app_data = os.environ.get("APPDATA")
        if app_data:
            return Path(app_data) / app_name
        
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / app_name
        
        # Fallback to home directory
        return Path.home() / f".{app_name}"
    
    def get_config_dir(self, app_name: str) -> Path:
        """Get Windows configuration directory.
        
        Args:
            app_name: Application name for directory creation
            
        Returns:
            Path to configuration directory (same as user data on Windows)
        """
        return self.get_user_data_dir(app_name)
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for Windows filesystem.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename safe for Windows
        """
        # Remove invalid characters
        for char in self.INVALID_CHARS:
            filename = filename.replace(char, "_")
        
        # Remove control characters (0-31)
        filename = "".join(char if ord(char) >= 32 else "_" for char in filename)
        
        # Remove trailing dots and spaces (Windows doesn't like them)
        filename = filename.rstrip(". ")
        
        # Check for reserved names
        name_without_ext = filename.split(".")[0].upper()
        if name_without_ext in self.RESERVED_NAMES:
            filename = f"file_{filename}"
        
        # Limit length (Windows max path is 260, leave room for directory)
        if len(filename) > 200:
            # Preserve extension if present
            if "." in filename:
                name, ext = filename.rsplit(".", 1)
                filename = name[:200-len(ext)-1] + "." + ext
            else:
                filename = filename[:200]
        
        # Ensure filename is not empty
        if not filename:
            filename = "unnamed_file"
        
        return filename
    
    def is_valid_path(self, path: Path) -> Tuple[bool, Optional[str]]:
        """Check if path is valid for Windows.
        
        Args:
            path: Path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        path_str = str(path)
        
        # Check for invalid characters (excluding : for drive letters)
        if any(char in path_str.replace(":\\", "\\") for char in self.INVALID_PATH_CHARS):
            return False, f"Path contains invalid characters: {self.INVALID_PATH_CHARS}"
        
        # Check path length (260 chars limit without extended path)
        if len(path_str) > 260 and not path_str.startswith("\\\\?\\"):
            return False, f"Path too long ({len(path_str)} > 260 characters)"
        
        # Check for reserved names in any path component
        parts = path.parts
        for part in parts:
            name_without_ext = part.split(".")[0].upper()
            if name_without_ext in self.RESERVED_NAMES:
                return False, f"Path contains reserved name: {part}"
        
        # Check for UNC paths
        if path_str.startswith("\\\\") and not path_str.startswith("\\\\?\\"):
            # Basic UNC path validation
            if len(parts) < 3:
                return False, "Invalid UNC path format"
        
        return True, None
    
    def normalize_path(self, path: Path) -> Path:
        """Normalize path for Windows.
        
        Args:
            path: Path to normalize
            
        Returns:
            Normalized path
        """
        # Convert to absolute path
        path = path.resolve()
        
        # Handle case-insensitive filesystem
        # Windows paths are case-insensitive but case-preserving
        # We don't change the case, just ensure consistency
        
        return path
    
    def create_temp_file(
        self, 
        suffix: Optional[str] = None,
        prefix: Optional[str] = None,
        text: bool = True
    ) -> tempfile._TemporaryFileWrapper:
        """Create a temporary file with Windows-appropriate settings.
        
        Args:
            suffix: File suffix
            prefix: File prefix
            text: Whether to open in text mode
            
        Returns:
            Temporary file wrapper
        """
        # Ensure text files use UTF-8 encoding
        if text:
            return tempfile.NamedTemporaryFile(
                mode='w+',
                suffix=suffix,
                prefix=prefix,
                delete=False,  # Windows often has issues with auto-delete
                encoding='utf-8',
                newline=''  # Universal newline mode
            )
        else:
            return tempfile.NamedTemporaryFile(
                mode='w+b',
                suffix=suffix,
                prefix=prefix,
                delete=False
            )
    
    def create_temp_dir(
        self,
        suffix: Optional[str] = None,
        prefix: Optional[str] = None
    ) -> tempfile.TemporaryDirectory:
        """Create a temporary directory with Windows-appropriate settings.
        
        Args:
            suffix: Directory suffix
            prefix: Directory prefix
            
        Returns:
            Temporary directory context manager
        """
        return tempfile.TemporaryDirectory(suffix=suffix, prefix=prefix)
    
    def get_file_encoding(self) -> str:
        """Get Windows file encoding.
        
        Returns:
            'utf-8' for consistency (with PYTHONUTF8=1 recommended)
        """
        # Always use UTF-8 for consistency
        return 'utf-8'
    
    def is_case_sensitive_filesystem(self) -> bool:
        """Check if the filesystem is case-sensitive.
        
        Returns:
            False (Windows filesystems are typically case-insensitive)
        """
        return False
    
    def get_reserved_names(self) -> List[str]:
        """Get list of reserved filenames for Windows.
        
        Returns:
            List of reserved names
        """
        return list(self.RESERVED_NAMES)
    
    def get_invalid_path_chars(self) -> str:
        """Get characters that are invalid in paths on Windows.
        
        Returns:
            String of invalid characters
        """
        return self.INVALID_PATH_CHARS
    
    def fix_long_path(self, path: Path) -> Path:
        """Fix long path issues on Windows.
        
        Adds \\\\?\\ prefix for paths over 260 characters.
        
        Args:
            path: Path to fix
            
        Returns:
            Fixed path
        """
        path_str = str(path.resolve())
        
        # Only fix if path is long and doesn't already have the prefix
        if len(path_str) > 260 and not path_str.startswith("\\\\?\\"):
            # Add long path prefix
            if path_str.startswith("\\\\"):
                # UNC path
                path_str = "\\\\?\\UNC\\" + path_str[2:]
            else:
                # Regular path
                path_str = "\\\\?\\" + path_str
            
            return Path(path_str)
        
        return path