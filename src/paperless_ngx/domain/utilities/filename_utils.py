"""Filename sanitization utilities for German document processing.

This module provides functions to clean and sanitize filenames, handling
German umlauts and special characters appropriately. Uses pathlib exclusively
for cross-platform compatibility.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Optional, Tuple


# German character mappings
UMLAUT_MAPPINGS = {
    "ä": "ae",
    "Ä": "Ae",
    "ö": "oe",
    "Ö": "Oe",
    "ü": "ue",
    "Ü": "Ue",
    "ß": "ss",
    "€": "EUR",
    "§": "par",
    "&": "und",
    "@": "at",
    "#": "nr",
    "%": "prozent",
    "+": "plus",
    "°": "grad",
}

# Maximum filename length (leaving room for extensions and counters)
MAX_FILENAME_LENGTH = 200


def replace_umlauts(text: str) -> str:
    """Replace German umlauts and special characters.
    
    Args:
        text: Input text with potential umlauts
        
    Returns:
        Text with umlauts replaced by ASCII equivalents
    """
    result = text
    for umlaut, replacement in UMLAUT_MAPPINGS.items():
        result = result.replace(umlaut, replacement)
    return result


def remove_special_characters(text: str, keep_chars: str = "_-") -> str:
    """Remove special characters from text.
    
    Args:
        text: Input text
        keep_chars: Characters to keep in addition to alphanumeric
        
    Returns:
        Cleaned text with only allowed characters
    """
    # First normalize unicode characters
    text = unicodedata.normalize("NFKD", text)
    
    # Create pattern for allowed characters
    pattern = f"[^a-zA-Z0-9{re.escape(keep_chars)}\\s]"
    
    # Remove special characters
    cleaned = re.sub(pattern, "", text)
    
    # Replace multiple spaces with single underscore
    cleaned = re.sub(r"\s+", "_", cleaned)
    
    # Remove multiple underscores
    cleaned = re.sub(r"_{2,}", "_", cleaned)
    
    # Remove leading/trailing underscores or hyphens
    cleaned = cleaned.strip("_-")
    
    return cleaned


def sanitize_filename(
    filename: str,
    max_length: Optional[int] = None,
    preserve_extension: bool = True,
    allow_spaces: bool = False
) -> str:
    """Sanitize a filename for safe filesystem storage.
    
    Args:
        filename: Original filename
        max_length: Maximum length for filename (default: MAX_FILENAME_LENGTH)
        preserve_extension: Whether to preserve file extension
        allow_spaces: Whether to allow spaces (converted to underscores if False)
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    if not filename:
        return "unnamed_file"
    
    # Use pathlib for extension handling
    file_path = Path(filename)
    if preserve_extension and file_path.suffix:
        base_name = file_path.stem
        extension = file_path.suffix.lower()
    else:
        base_name = filename
        extension = ""
    
    # Replace umlauts
    base_name = replace_umlauts(base_name)
    
    # Remove or replace special characters
    if allow_spaces:
        base_name = remove_special_characters(base_name, keep_chars="_- ")
    else:
        base_name = remove_special_characters(base_name, keep_chars="_-")
    
    # Ensure filename is not empty after cleaning
    if not base_name:
        base_name = "document"
    
    # Truncate if necessary
    if max_length is None:
        max_length = MAX_FILENAME_LENGTH
    
    # Account for extension length
    max_base_length = max_length - len(extension)
    if len(base_name) > max_base_length:
        base_name = base_name[:max_base_length]
    
    # Combine base name and extension
    result = base_name + extension
    
    # Final safety checks
    result = result.strip(".")
    
    # Ensure we don't have reserved Windows filenames
    reserved_names = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    }
    
    name_upper = result.upper().split(".")[0]
    if name_upper in reserved_names:
        result = f"file_{result}"
    
    return result


def create_unique_filename(
    base_path: Path,
    filename: str,
    max_attempts: int = 1000
) -> str:
    """Create a unique filename by adding counter if necessary.
    
    Args:
        base_path: Directory where file will be saved
        filename: Desired filename
        max_attempts: Maximum number of attempts to find unique name
        
    Returns:
        Unique filename that doesn't exist in base_path
        
    Raises:
        ValueError: If unable to create unique filename after max_attempts
    """
    base_path = Path(base_path)
    base_path.mkdir(parents=True, exist_ok=True)
    
    # Use pathlib for existence check
    target_file = base_path / filename
    if not target_file.exists():
        return filename
    
    # Use pathlib's stem and suffix for splitting
    file_path = Path(filename)
    base_name = file_path.stem
    extension = file_path.suffix
    
    # Try adding counter
    for counter in range(1, max_attempts + 1):
        new_filename = f"{base_name}_{counter}{extension}"
        new_path = base_path / new_filename
        if not new_path.exists():
            return new_filename
    
    raise ValueError(
        f"Unable to create unique filename after {max_attempts} attempts"
    )


def format_email_attachment_filename(
    sender: str,
    subject: str,
    original_filename: str,
    max_length: Optional[int] = None
) -> str:
    """Format filename for email attachment following pattern.
    
    Pattern: {sender}_{subject}_{original_filename}
    
    Args:
        sender: Email sender address
        subject: Email subject
        original_filename: Original attachment filename
        max_length: Maximum total filename length
        
    Returns:
        Formatted and sanitized filename
    """
    # Extract sender name from email address
    if "@" in sender:
        sender_name = sender.split("@")[0]
        sender_domain = sender.split("@")[1].split(".")[0]
        sender_clean = f"{sender_name}_{sender_domain}"
    else:
        sender_clean = sender
    
    # Clean sender
    sender_clean = replace_umlauts(sender_clean)
    sender_clean = remove_special_characters(sender_clean, keep_chars="_-")
    sender_clean = sender_clean[:50]  # Limit sender length
    
    # Clean subject
    subject_clean = replace_umlauts(subject)
    subject_clean = remove_special_characters(subject_clean, keep_chars="_-")
    subject_clean = subject_clean[:80]  # Limit subject length
    
    # Clean original filename
    original_clean = sanitize_filename(original_filename, preserve_extension=False)
    
    # Use pathlib for extension handling
    original_path = Path(original_filename)
    extension = original_path.suffix.lower() if original_path.suffix else ""
    
    # Combine parts
    combined = f"{sender_clean}_{subject_clean}_{original_clean}"
    
    # Remove multiple underscores
    combined = re.sub(r"_{2,}", "_", combined)
    
    # Add extension back
    result = combined + extension
    
    # Apply max length if specified
    if max_length:
        if len(result) > max_length:
            # Preserve extension
            max_base = max_length - len(extension)
            result = combined[:max_base] + extension
    
    return result


def extract_date_from_filename(filename: str) -> Optional[str]:
    """Extract date from filename if present.
    
    Looks for common date patterns like:
    - YYYY-MM-DD
    - YYYY_MM_DD
    - YYYYMMDD
    - DD.MM.YYYY
    - DD-MM-YYYY
    
    Args:
        filename: Filename to extract date from
        
    Returns:
        Date string in YYYY-MM-DD format or None if not found
    """
    patterns = [
        (r"(\d{4})-(\d{2})-(\d{2})", r"\1-\2-\3"),  # YYYY-MM-DD
        (r"(\d{4})_(\d{2})_(\d{2})", r"\1-\2-\3"),  # YYYY_MM_DD
        (r"(\d{4})(\d{2})(\d{2})", r"\1-\2-\3"),    # YYYYMMDD
        (r"(\d{2})\.(\d{2})\.(\d{4})", r"\3-\2-\1"), # DD.MM.YYYY
        (r"(\d{2})-(\d{2})-(\d{4})", r"\3-\2-\1"),  # DD-MM-YYYY
    ]
    
    for pattern, replacement in patterns:
        match = re.search(pattern, filename)
        if match:
            date_str = re.sub(pattern, replacement, match.group())
            # Validate date format
            parts = date_str.split("-")
            if len(parts) == 3:
                year, month, day = parts
                if (1900 <= int(year) <= 2100 and
                    1 <= int(month) <= 12 and
                    1 <= int(day) <= 31):
                    return date_str
    
    return None


def split_filename_parts(filename: str) -> Tuple[str, str]:
    """Split filename into name and extension.
    
    Args:
        filename: Complete filename
        
    Returns:
        Tuple of (base_name, extension)
    """
    # Use pathlib for reliable splitting
    file_path = Path(filename)
    return file_path.stem, file_path.suffix


def normalize_path_separators(path: str) -> str:
    """Normalize path separators for current OS.
    
    Args:
        path: Path string with potentially mixed separators
        
    Returns:
        Path with normalized separators
    """
    # Use pathlib's as_posix() for consistent forward slashes
    # or native str() for OS-appropriate separators
    normalized = Path(path)
    return str(normalized)


def optimize_filename_for_sevdesk(
    filename: str,
    max_length: int = 128,
    preserve_extension: bool = True
) -> str:
    """Optimize filename for Sevdesk compatibility with 128 character limit.
    
    Sevdesk has a strict 128 character limit for filenames. This function
    ensures filenames are truncated appropriately while preserving readability.
    
    Args:
        filename: Original filename
        max_length: Maximum allowed filename length (default: 128 for Sevdesk)
        preserve_extension: Whether to preserve file extension
        
    Returns:
        Optimized filename that fits within Sevdesk limits
    """
    if not filename:
        return "document.pdf"
    
    # Use pathlib for reliable extension handling
    file_path = Path(filename)
    if preserve_extension and file_path.suffix:
        base_name = file_path.stem
        extension = file_path.suffix.lower()
    else:
        base_name = filename
        extension = ""
    
    # Clean the base name
    base_name = replace_umlauts(base_name)
    base_name = remove_special_characters(base_name, keep_chars="_-")
    
    # Calculate available space for base name
    available_length = max_length - len(extension)
    
    if len(base_name) <= available_length:
        # Filename is already within limits
        result = base_name + extension
    else:
        # Need to truncate intelligently
        # Try to preserve meaningful parts of the filename
        
        # Split by common separators to identify meaningful parts
        parts = re.split(r'[_\-\s]+', base_name)
        
        if len(parts) > 1:
            # Try to keep the most important parts
            # Priority: date patterns, sender info, document type
            important_parts = []
            remaining_length = available_length
            
            # Look for date patterns first (highest priority)
            date_parts = [p for p in parts if re.match(r'\d{4}.*\d{2}.*\d{2}', p)]
            for part in date_parts:
                if len(part) + 1 <= remaining_length:  # +1 for separator
                    important_parts.append(part)
                    remaining_length -= len(part) + 1
            
            # Add other parts in order of importance
            other_parts = [p for p in parts if p not in date_parts and len(p) > 2]
            for part in other_parts:
                if len(part) + 1 <= remaining_length:
                    important_parts.append(part)
                    remaining_length -= len(part) + 1
                elif remaining_length > 5:  # Keep partial part if enough space
                    truncated_part = part[:remaining_length - 1]
                    important_parts.append(truncated_part)
                    break
            
            if important_parts:
                base_name = "_".join(important_parts)
            else:
                # Fallback: simple truncation
                base_name = base_name[:available_length]
        else:
            # Single part filename - simple truncation
            base_name = base_name[:available_length]
        
        result = base_name + extension
    
    # Final validation and cleanup
    result = result.strip("_-.")
    if not result or result == extension:
        result = f"document{extension}"
    
    # Ensure we're within the limit
    if len(result) > max_length:
        available_for_base = max_length - len(extension)
        base_name = result[:available_for_base].rstrip("_-.")
        result = base_name + extension
    
    return result


def validate_sevdesk_filename(filename: str) -> Tuple[bool, Optional[str]]:
    """Validate filename for Sevdesk compatibility.
    
    Args:
        filename: Filename to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # First run standard validation
    is_valid, error = validate_filename(filename)
    if not is_valid:
        return is_valid, error
    
    # Sevdesk-specific checks
    if len(filename) > 128:
        return False, f"Filename too long for Sevdesk ({len(filename)} > 128 characters)"
    
    # Check for problematic characters that might cause issues in Sevdesk
    problematic_chars = ['ä', 'ö', 'ü', 'Ä', 'Ö', 'Ü', 'ß', '€', '§']
    for char in problematic_chars:
        if char in filename:
            return False, f"Filename contains umlaut/special character that should be replaced: {char}"
    
    return True, None


def validate_filename(filename: str) -> Tuple[bool, Optional[str]]:
    """Validate if filename is safe for filesystem.
    
    Args:
        filename: Filename to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename:
        return False, "Filename cannot be empty"
    
    if len(filename) > 255:
        return False, f"Filename too long ({len(filename)} > 255 characters)"
    
    # Check for path traversal attempts
    if ".." in filename or "/" in filename or "\\" in filename:
        return False, "Filename cannot contain path separators or .."
    
    # Check for null bytes
    if "\x00" in filename:
        return False, "Filename cannot contain null bytes"
    
    # Check for reserved characters on Windows
    reserved_chars = '<>:"|?*'
    for char in reserved_chars:
        if char in filename:
            return False, f"Filename cannot contain reserved character: {char}"
    
    # Check for reserved names
    reserved_names = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    }
    
    name_upper = filename.upper().split(".")[0]
    if name_upper in reserved_names:
        return False, f"Filename uses reserved name: {name_upper}"
    
    return True, None