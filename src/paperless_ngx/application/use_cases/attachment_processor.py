"""Attachment processor use case for email downloads.

This module processes downloaded email attachments, organizing them
and preparing metadata for Paperless NGX upload.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ...domain.utilities.filename_utils import (
    create_unique_filename,
    extract_date_from_filename,
    sanitize_filename,
)
from ...infrastructure.email import EmailAttachment

logger = logging.getLogger(__name__)


@dataclass
class ProcessedAttachment:
    """Processed attachment with metadata."""
    
    original_filename: str
    processed_filename: str
    file_path: Path
    file_hash: str
    file_size: int
    email_sender: str
    email_subject: str
    email_date: datetime
    document_date: Optional[datetime]
    correspondent: str
    document_type: Optional[str]
    tags: List[str]
    description: str
    processed_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert Path and datetime objects
        data["file_path"] = str(data["file_path"])
        data["email_date"] = data["email_date"].isoformat()
        data["processed_at"] = data["processed_at"].isoformat()
        if data["document_date"]:
            data["document_date"] = data["document_date"].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProcessedAttachment:
        """Create from dictionary."""
        data["file_path"] = Path(data["file_path"])
        data["email_date"] = datetime.fromisoformat(data["email_date"])
        data["processed_at"] = datetime.fromisoformat(data["processed_at"])
        if data.get("document_date"):
            data["document_date"] = datetime.fromisoformat(data["document_date"])
        return cls(**data)


class AttachmentProcessor:
    """Process email attachments for Paperless NGX."""
    
    def __init__(
        self,
        base_dir: Path,
        organize_by_date: bool = True,
        organize_by_sender: bool = False,
        duplicate_check: bool = True
    ):
        """Initialize attachment processor.
        
        Args:
            base_dir: Base directory for organized attachments
            organize_by_date: Create date-based folder hierarchy
            organize_by_sender: Create sender-based folder hierarchy
            duplicate_check: Check for duplicate files
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.organize_by_date = organize_by_date
        self.organize_by_sender = organize_by_sender
        self.duplicate_check = duplicate_check
        self._processed_hashes: Set[str] = set()
        self._load_processed_hashes()
    
    def _load_processed_hashes(self) -> None:
        """Load previously processed file hashes."""
        hash_file = self.base_dir / ".processed_hashes.json"
        if hash_file.exists():
            try:
                with open(hash_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._processed_hashes = set(data.get("hashes", []))
                logger.info(f"Loaded {len(self._processed_hashes)} processed file hashes")
            except Exception as e:
                logger.error(f"Error loading processed hashes: {e}")
    
    def _save_processed_hashes(self) -> None:
        """Save processed file hashes."""
        hash_file = self.base_dir / ".processed_hashes.json"
        try:
            with open(hash_file, "w", encoding="utf-8") as f:
                json.dump({"hashes": list(self._processed_hashes)}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving processed hashes: {e}")
    
    def _calculate_file_hash(self, content: bytes) -> str:
        """Calculate SHA256 hash of file content.
        
        Args:
            content: File content
            
        Returns:
            Hex digest of SHA256 hash
        """
        return hashlib.sha256(content).hexdigest()
    
    def _extract_correspondent(self, email_sender: str) -> str:
        """Extract correspondent name from email sender.
        
        Args:
            email_sender: Email sender string (e.g., "John Doe <john@example.com>")
            
        Returns:
            Clean correspondent name
        """
        # Extract name from "Name <email>" format
        if "<" in email_sender and ">" in email_sender:
            name = email_sender.split("<")[0].strip()
            if name:
                return name
            # Fall back to email
            email = email_sender.split("<")[1].split(">")[0]
            return email.split("@")[0]
        
        # If just email address
        if "@" in email_sender:
            return email_sender.split("@")[0]
        
        return email_sender
    
    def _guess_document_type(self, filename: str, subject: str) -> Optional[str]:
        """Guess document type from filename and subject.
        
        Args:
            filename: Attachment filename
            subject: Email subject
            
        Returns:
            Guessed document type or None
        """
        # Common German document type patterns
        type_patterns = {
            "Rechnung": ["rechnung", "invoice", "bill"],
            "Vertrag": ["vertrag", "contract", "agreement"],
            "Angebot": ["angebot", "quote", "quotation", "offer"],
            "Bestellung": ["bestellung", "order", "purchase"],
            "Lieferschein": ["lieferschein", "delivery"],
            "Mahnung": ["mahnung", "reminder", "dunning"],
            "Quittung": ["quittung", "receipt"],
            "Bescheinigung": ["bescheinigung", "certificate"],
            "Antrag": ["antrag", "application"],
            "Kündigung": ["kündigung", "cancellation", "termination"],
            "Bestätigung": ["bestätigung", "confirmation"],
            "Gutschrift": ["gutschrift", "credit"],
            "Lastschrift": ["lastschrift", "debit"],
            "Überweisung": ["überweisung", "transfer"],
            "Kontoauszug": ["kontoauszug", "statement"],
        }
        
        # Check both filename and subject
        combined_text = f"{filename} {subject}".lower()
        
        for doc_type, patterns in type_patterns.items():
            for pattern in patterns:
                if pattern in combined_text:
                    return doc_type
        
        # Check file extension for specific types
        if filename.lower().endswith((".jpg", ".jpeg", ".png", ".tiff")):
            return "Scan"
        
        return None
    
    def _generate_tags(self, attachment: EmailAttachment, doc_type: Optional[str]) -> List[str]:
        """Generate tags for document.
        
        Args:
            attachment: Email attachment
            doc_type: Document type
            
        Returns:
            List of tags
        """
        tags = []
        
        # Add year tag
        year = attachment.email_date.year
        tags.append(str(year))
        
        # Add month tag
        month_name = attachment.email_date.strftime("%B")
        tags.append(month_name)
        
        # Add document type as tag if available
        if doc_type:
            tags.append(doc_type)
        
        # Add sender domain as tag
        if "@" in attachment.email_sender:
            domain = attachment.email_sender.split("@")[1].split(">")[0]
            domain_name = domain.split(".")[0]
            if domain_name and domain_name not in ["gmail", "outlook", "yahoo", "gmx", "web"]:
                tags.append(domain_name)
        
        # Add file type tag
        file_ext = Path(attachment.filename).suffix.lower()
        if file_ext == ".pdf":
            tags.append("PDF")
        elif file_ext in [".doc", ".docx"]:
            tags.append("Word")
        elif file_ext in [".xls", ".xlsx"]:
            tags.append("Excel")
        elif file_ext in [".jpg", ".jpeg", ".png", ".tiff"]:
            tags.append("Bild")
        
        # Check for keywords in subject
        subject_lower = attachment.email_subject.lower()
        keyword_tags = {
            "wichtig": "Wichtig",
            "urgent": "Dringend",
            "erinnerung": "Erinnerung",
            "mahnung": "Mahnung",
            "frist": "Frist",
            "termin": "Termin",
        }
        
        for keyword, tag in keyword_tags.items():
            if keyword in subject_lower:
                tags.append(tag)
        
        # Remove duplicates and limit
        tags = list(dict.fromkeys(tags))[:7]
        
        return tags
    
    def _create_description(self, attachment: EmailAttachment, doc_type: Optional[str]) -> str:
        """Create document description.
        
        Args:
            attachment: Email attachment
            doc_type: Document type
            
        Returns:
            Description string (max 128 chars)
        """
        parts = []
        
        if doc_type:
            parts.append(doc_type)
        
        # Add sender info
        correspondent = self._extract_correspondent(attachment.email_sender)
        parts.append(f"von {correspondent}")
        
        # Add date
        date_str = attachment.email_date.strftime("%d.%m.%Y")
        parts.append(date_str)
        
        # Add subject excerpt if room
        description = " ".join(parts)
        if len(description) < 100 and attachment.email_subject:
            subject_excerpt = attachment.email_subject[:100 - len(description)]
            description = f"{description} - {subject_excerpt}"
        
        return description[:128]
    
    def _get_target_directory(self, attachment: EmailAttachment) -> Path:
        """Get target directory for attachment based on organization settings.
        
        Args:
            attachment: Email attachment
            
        Returns:
            Target directory path
        """
        target_dir = self.base_dir
        
        if self.organize_by_date:
            # Organize by year/month
            year = attachment.email_date.strftime("%Y")
            month = attachment.email_date.strftime("%m-%B")
            target_dir = target_dir / year / month
        
        if self.organize_by_sender:
            # Organize by sender
            correspondent = self._extract_correspondent(attachment.email_sender)
            sender_dir = sanitize_filename(correspondent, preserve_extension=False)
            target_dir = target_dir / sender_dir
        
        return target_dir
    
    def process_attachment(
        self,
        attachment: EmailAttachment,
        skip_duplicates: bool = True
    ) -> Optional[ProcessedAttachment]:
        """Process single email attachment.
        
        Args:
            attachment: Email attachment to process
            skip_duplicates: Skip if file hash already processed
            
        Returns:
            ProcessedAttachment or None if skipped
        """
        # Calculate file hash
        file_hash = self._calculate_file_hash(attachment.content)
        
        # Check for duplicates
        if skip_duplicates and self.duplicate_check:
            if file_hash in self._processed_hashes:
                logger.info(f"Skipping duplicate file: {attachment.filename}")
                return None
        
        # Get target directory
        target_dir = self._get_target_directory(attachment)
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Save attachment
        file_path = attachment.save_to_disk(target_dir, use_custom_name=True)
        
        # Extract metadata
        correspondent = self._extract_correspondent(attachment.email_sender)
        doc_type = self._guess_document_type(attachment.filename, attachment.email_subject)
        tags = self._generate_tags(attachment, doc_type)
        description = self._create_description(attachment, doc_type)
        
        # Try to extract date from filename
        doc_date = None
        if date_str := extract_date_from_filename(attachment.filename):
            try:
                doc_date = datetime.strptime(date_str, "%Y-%m-%d")
            except:
                pass
        
        # Create processed attachment
        processed = ProcessedAttachment(
            original_filename=attachment.filename,
            processed_filename=file_path.name,
            file_path=file_path,
            file_hash=file_hash,
            file_size=attachment.size,
            email_sender=attachment.email_sender,
            email_subject=attachment.email_subject,
            email_date=attachment.email_date,
            document_date=doc_date,
            correspondent=correspondent,
            document_type=doc_type,
            tags=tags,
            description=description,
            processed_at=datetime.now()
        )
        
        # Mark as processed
        self._processed_hashes.add(file_hash)
        self._save_processed_hashes()
        
        # Save metadata
        self._save_attachment_metadata(processed)
        
        logger.info(f"Processed attachment: {processed.processed_filename}")
        
        return processed
    
    def _save_attachment_metadata(self, processed: ProcessedAttachment) -> None:
        """Save attachment metadata to JSON file.
        
        Args:
            processed: Processed attachment
        """
        metadata_file = processed.file_path.with_suffix(".metadata.json")
        try:
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(processed.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
    
    def process_attachments(
        self,
        attachments: List[EmailAttachment],
        skip_duplicates: bool = True
    ) -> List[ProcessedAttachment]:
        """Process multiple email attachments.
        
        Args:
            attachments: List of email attachments
            skip_duplicates: Skip duplicate files
            
        Returns:
            List of processed attachments
        """
        processed_list = []
        
        for attachment in attachments:
            try:
                processed = self.process_attachment(attachment, skip_duplicates)
                if processed:
                    processed_list.append(processed)
            except Exception as e:
                logger.error(f"Error processing attachment {attachment.filename}: {e}")
        
        logger.info(f"Processed {len(processed_list)} of {len(attachments)} attachments")
        
        return processed_list
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics.
        
        Returns:
            Dictionary with processing stats
        """
        stats = {
            "base_directory": str(self.base_dir),
            "total_processed_hashes": len(self._processed_hashes),
            "organize_by_date": self.organize_by_date,
            "organize_by_sender": self.organize_by_sender,
            "duplicate_check_enabled": self.duplicate_check,
        }
        
        # Count files in directory
        try:
            all_files = list(self.base_dir.rglob("*"))
            stats["total_files"] = sum(1 for f in all_files if f.is_file() and not f.name.startswith("."))
            stats["total_directories"] = sum(1 for d in all_files if d.is_dir())
        except:
            stats["total_files"] = 0
            stats["total_directories"] = 0
        
        return stats
    
    def cleanup_empty_directories(self) -> int:
        """Remove empty directories in base directory.
        
        Returns:
            Number of directories removed
        """
        removed_count = 0
        
        for dirpath in sorted(self.base_dir.rglob("*"), reverse=True):
            if dirpath.is_dir() and not any(dirpath.iterdir()):
                try:
                    dirpath.rmdir()
                    removed_count += 1
                    logger.debug(f"Removed empty directory: {dirpath}")
                except:
                    pass
        
        if removed_count:
            logger.info(f"Cleaned up {removed_count} empty directories")
        
        return removed_count