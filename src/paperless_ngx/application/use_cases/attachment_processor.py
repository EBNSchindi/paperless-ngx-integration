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
from ...infrastructure.config.settings import get_settings

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
        organize_by_date: bool = False,
        organize_by_sender: bool = False,
        duplicate_check: bool = True,
        generate_metadata_files: bool = False
    ):
        """Initialize attachment processor.
        
        Args:
            base_dir: Base directory for organized attachments
            organize_by_date: Create date-based folder hierarchy (disabled for Sevdesk)
            organize_by_sender: Create sender-based folder hierarchy (disabled for Sevdesk)
            duplicate_check: Check for duplicate files
            generate_metadata_files: Generate JSON metadata files (disabled for Sevdesk)
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.organize_by_date = organize_by_date
        self.organize_by_sender = organize_by_sender
        self.duplicate_check = duplicate_check
        self.generate_metadata_files = generate_metadata_files
        self._processed_hashes: Set[str] = set()
        self._load_processed_hashes()
        self.settings = get_settings()
    
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
    
    def _generate_tags(self, attachment: EmailAttachment, doc_type: Optional[str], extracted_prices: List[str] = None) -> List[str]:
        """Generate tags for document with Sevdesk optimization.
        
        Implements intelligent tag generation with priority:
        1. Document type (Rechnung/Kassenbon)
        2. Price information (Gesamtpreise Brutto)
        3. Year
        4. Sender/Domain information
        
        Args:
            attachment: Email attachment
            doc_type: Document type
            extracted_prices: List of extracted gross prices from document
            
        Returns:
            List of tags (maximum 4 for Sevdesk compatibility)
        """
        tags = []
        max_tags = getattr(self.settings, 'max_tags_per_document', 4)  # Default to 4 for Sevdesk
        
        # Priority 1: Document type tags (Rechnung/Kassenbon detection)
        if doc_type:
            # Always add Rechnung or Kassenbon as first tag if detected
            if self._is_invoice_type(doc_type, attachment):
                tags.append("Rechnung")
            elif self._is_receipt_type(doc_type, attachment):
                tags.append("Kassenbon")
            elif doc_type not in ["Rechnung", "Kassenbon"]:
                tags.append(doc_type)
        
        # Priority 2: Price tags (Gesamtpreise Brutto)
        if extracted_prices and len(tags) < max_tags:
            # Add the main price as a tag (e.g., "123,45€")
            for price in extracted_prices[:1]:  # Only add first/main price
                if len(tags) < max_tags:
                    # Format price for tag (remove spaces, ensure proper format)
                    price_tag = self._format_price_tag(price)
                    if price_tag:
                        tags.append(price_tag)
        
        # Priority 3: Year tag
        if len(tags) < max_tags:
            year = str(attachment.email_date.year)
            tags.append(year)
        
        # Priority 4: Sender/Domain tag
        if len(tags) < max_tags:
            sender_tag = self._extract_sender_tag(attachment.email_sender)
            if sender_tag:
                tags.append(sender_tag)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        
        # Limit to max_tags (default 4 for Sevdesk)
        return unique_tags[:max_tags]
    
    def _is_invoice_type(self, doc_type: str, attachment: EmailAttachment) -> bool:
        """Check if document is an invoice type.
        
        Args:
            doc_type: Detected document type
            attachment: Email attachment
            
        Returns:
            True if document is an invoice
        """
        invoice_indicators = [
            "rechnung", "invoice", "bill", "abrechnung", 
            "faktura", "quittung", "zahlungsbeleg"
        ]
        
        # Check document type
        if doc_type and any(indicator in doc_type.lower() for indicator in invoice_indicators):
            return True
        
        # Check filename and subject
        combined = f"{attachment.filename} {attachment.email_subject}".lower()
        return any(indicator in combined for indicator in invoice_indicators)
    
    def _is_receipt_type(self, doc_type: str, attachment: EmailAttachment) -> bool:
        """Check if document is a receipt/Kassenbon type.
        
        Args:
            doc_type: Detected document type
            attachment: Email attachment
            
        Returns:
            True if document is a receipt
        """
        receipt_indicators = [
            "kassenbon", "kassenzettel", "beleg", "bon", 
            "receipt", "kassenschein", "kassenbeleg"
        ]
        
        # Check document type
        if doc_type and any(indicator in doc_type.lower() for indicator in receipt_indicators):
            return True
        
        # Check filename and subject
        combined = f"{attachment.filename} {attachment.email_subject}".lower()
        return any(indicator in combined for indicator in receipt_indicators)
    
    def _format_price_tag(self, price: str) -> Optional[str]:
        """Format price string as tag.
        
        Args:
            price: Price string (e.g., "123,45 EUR", "€123.45")
            
        Returns:
            Formatted price tag or None
        """
        try:
            # Extract numeric value
            import re
            numbers = re.findall(r'\d+[,.]?\d*', price)
            if numbers:
                # Take the first number found
                price_num = numbers[0].replace(',', '.')
                # Format as German currency
                return f"{price_num.replace('.', ',')}€"
        except Exception:
            pass
        return None
    
    def _extract_sender_tag(self, email_sender: str) -> Optional[str]:
        """Extract meaningful sender tag.
        
        Args:
            email_sender: Email sender string
            
        Returns:
            Sender tag or None
        """
        # Extract domain or sender name
        if "@" in email_sender:
            domain = email_sender.split("@")[1].split(">")[0]
            domain_name = domain.split(".")[0]
            
            # Skip generic email providers
            if domain_name and domain_name not in ["gmail", "outlook", "yahoo", "gmx", "web", "mail", "email"]:
                # Capitalize first letter
                return domain_name.capitalize()
        
        # Try to extract name from "Name <email>" format
        if "<" in email_sender:
            name = email_sender.split("<")[0].strip()
            if name and len(name) < 20:  # Reasonable length for a tag
                # Take first word or company name
                return name.split()[0] if " " in name else name
        
        return None
    
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
        
        Sevdesk optimization: Uses flat directory structure for simplified processing.
        
        Args:
            attachment: Email attachment
            
        Returns:
            Target directory path
        """
        target_dir = self.base_dir
        
        # Sevdesk optimization: Flat directory structure by default
        if self.organize_by_date:
            # Only organize by date if explicitly enabled
            year = attachment.email_date.strftime("%Y")
            month = attachment.email_date.strftime("%m-%B")
            target_dir = target_dir / year / month
        
        if self.organize_by_sender:
            # Only organize by sender if explicitly enabled
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
        
        # Save metadata only if enabled (disabled for Sevdesk optimization)
        if self.generate_metadata_files:
            self._save_attachment_metadata(processed)
        
        logger.info(f"Processed attachment: {processed.processed_filename}")
        
        return processed
    
    def _save_attachment_metadata(self, processed: ProcessedAttachment) -> None:
        """Save attachment metadata to JSON file.
        
        Note: Disabled by default for Sevdesk optimization.
        
        Args:
            processed: Processed attachment
        """
        if not self.generate_metadata_files:
            logger.debug("Metadata file generation disabled for Sevdesk optimization")
            return
            
        metadata_file = processed.file_path.with_suffix(".metadata.json")
        try:
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(processed.to_dict(), f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved metadata file: {metadata_file}")
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