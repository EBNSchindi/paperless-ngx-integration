"""Platform service interfaces for cross-platform compatibility.

This module defines abstract interfaces for platform-specific operations,
ensuring consistent behavior across different operating systems.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple, List, Any
import tempfile


class PlatformService(ABC):
    """Abstract interface for platform-specific operations."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get platform name (e.g., 'Windows', 'Linux', 'Darwin')."""
        pass
    
    @property
    @abstractmethod
    def is_windows(self) -> bool:
        """Check if running on Windows."""
        pass
    
    @property
    @abstractmethod
    def is_posix(self) -> bool:
        """Check if running on POSIX-compliant system (Linux/macOS)."""
        pass
    
    @property
    @abstractmethod
    def path_separator(self) -> str:
        """Get platform-specific path separator."""
        pass
    
    @property
    @abstractmethod
    def line_separator(self) -> str:
        """Get platform-specific line separator."""
        pass
    
    @abstractmethod
    def get_temp_dir(self) -> Path:
        """Get platform-appropriate temporary directory.
        
        Returns:
            Path to temporary directory
        """
        pass
    
    @abstractmethod
    def get_user_data_dir(self, app_name: str) -> Path:
        """Get platform-appropriate user data directory.
        
        Args:
            app_name: Application name for directory creation
            
        Returns:
            Path to user data directory
        """
        pass
    
    @abstractmethod
    def get_config_dir(self, app_name: str) -> Path:
        """Get platform-appropriate configuration directory.
        
        Args:
            app_name: Application name for directory creation
            
        Returns:
            Path to configuration directory
        """
        pass
    
    @abstractmethod
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for platform-specific filesystem rules.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename safe for the platform
        """
        pass
    
    @abstractmethod
    def is_valid_path(self, path: Path) -> Tuple[bool, Optional[str]]:
        """Check if path is valid for the platform.
        
        Args:
            path: Path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def normalize_path(self, path: Path) -> Path:
        """Normalize path for the platform.
        
        Handles case sensitivity, UNC paths on Windows, etc.
        
        Args:
            path: Path to normalize
            
        Returns:
            Normalized path
        """
        pass
    
    @abstractmethod
    def create_temp_file(
        self, 
        suffix: Optional[str] = None,
        prefix: Optional[str] = None,
        text: bool = True
    ) -> tempfile._TemporaryFileWrapper:
        """Create a temporary file with platform-appropriate settings.
        
        Args:
            suffix: File suffix
            prefix: File prefix
            text: Whether to open in text mode
            
        Returns:
            Temporary file wrapper
        """
        pass
    
    @abstractmethod
    def create_temp_dir(
        self,
        suffix: Optional[str] = None,
        prefix: Optional[str] = None
    ) -> tempfile.TemporaryDirectory:
        """Create a temporary directory with platform-appropriate settings.
        
        Args:
            suffix: Directory suffix
            prefix: Directory prefix
            
        Returns:
            Temporary directory context manager
        """
        pass
    
    @abstractmethod
    def get_file_encoding(self) -> str:
        """Get platform-appropriate file encoding.
        
        Returns:
            Encoding string (e.g., 'utf-8')
        """
        pass
    
    @abstractmethod
    def is_case_sensitive_filesystem(self) -> bool:
        """Check if the filesystem is case-sensitive.
        
        Returns:
            True if case-sensitive, False otherwise
        """
        pass
    
    @abstractmethod
    def get_reserved_names(self) -> List[str]:
        """Get list of reserved filenames for the platform.
        
        Returns:
            List of reserved names (e.g., 'CON', 'PRN' on Windows)
        """
        pass
    
    @abstractmethod
    def get_invalid_path_chars(self) -> str:
        """Get characters that are invalid in paths on this platform.
        
        Returns:
            String of invalid characters
        """
        pass
    
    @abstractmethod
    def fix_long_path(self, path: Path) -> Path:
        """Fix long path issues (mainly for Windows).
        
        On Windows, this may add \\\\?\\ prefix for paths over 260 chars.
        
        Args:
            path: Path to fix
            
        Returns:
            Fixed path
        """
        pass
    
    def ensure_path_exists(self, path: Path, is_file: bool = False) -> Path:
        """Ensure a path exists, creating directories as needed.
        
        Args:
            path: Path to ensure exists
            is_file: If True, path is a file and parent directory is created
            
        Returns:
            The path
        """
        path = Path(path)
        if is_file:
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path.mkdir(parents=True, exist_ok=True)
        return path