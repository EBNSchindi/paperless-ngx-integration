"""Multi-provider email client with IMAP support.

This module provides a unified interface for downloading attachments from
multiple email accounts including Gmail and IONOS via IMAP. Uses UTF-8 encoding
and platform-aware temporary file handling for cross-platform compatibility.
"""

from __future__ import annotations

import email
import imaplib
import logging
import re
import ssl
import time
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.header import decode_header
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ...domain.utilities.filename_utils import (
    format_email_attachment_filename,
    create_unique_filename,
    sanitize_filename,
    optimize_filename_for_sevdesk,
)
from ..platform import get_platform_service
from .email_config import EmailAccount, EmailSettings

logger = logging.getLogger(__name__)


@dataclass
class EmailAttachment:
    """Email attachment metadata."""
    
    filename: str
    content: bytes
    content_type: str
    size: int
    email_uid: str
    email_subject: str
    email_sender: str
    email_date: datetime
    
    def save_to_disk(self, directory: Path, use_custom_name: bool = True, sevdesk_optimization: bool = True) -> Path:
        """Save attachment to disk with platform-aware handling and Sevdesk optimization.
        
        Args:
            directory: Directory to save attachment
            use_custom_name: Whether to use custom naming pattern
            sevdesk_optimization: Whether to apply Sevdesk 128-character limit
            
        Returns:
            Path to saved file
        """
        platform = get_platform_service()
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        
        if use_custom_name:
            filename = format_email_attachment_filename(
                self.email_sender,
                self.email_subject,
                self.filename
            )
        else:
            filename = sanitize_filename(self.filename)
        
        # Apply Sevdesk optimization if enabled
        if sevdesk_optimization:
            filename = optimize_filename_for_sevdesk(filename, max_length=128)
            logger.debug(f"Applied Sevdesk optimization: {self.filename} -> {filename}")
        
        # Platform-specific filename sanitization
        filename = platform.sanitize_filename(filename)
        
        # Ensure unique filename
        filename = create_unique_filename(directory, filename)
        filepath = directory / filename
        
        # Write content using temporary file for safety
        try:
            # Create temporary file in same directory for atomic write
            with tempfile.NamedTemporaryFile(
                mode='wb',
                dir=directory,
                delete=False,
                prefix='.tmp_',
                suffix=Path(filename).suffix
            ) as tmp_file:
                tmp_file.write(self.content)
                tmp_path = Path(tmp_file.name)
            
            # Atomic rename to final location
            tmp_path.replace(filepath)
            logger.info(f"Saved attachment: {filepath} ({self.size} bytes)")
            
        except Exception as e:
            # Clean up temporary file on error
            if 'tmp_path' in locals() and tmp_path.exists():
                tmp_path.unlink()
            raise
        
        return filepath


@dataclass
class EmailMessage:
    """Parsed email message."""
    
    uid: str
    subject: str
    sender: str
    date: datetime
    body: str
    attachments: List[EmailAttachment]
    raw_message: Optional[EmailMessage] = None


class IMAPEmailClient:
    """IMAP email client for downloading attachments."""
    
    def __init__(self, account: EmailAccount, settings: EmailSettings):
        """Initialize IMAP client.
        
        Args:
            account: Email account configuration
            settings: Email processing settings
        """
        self.account = account
        self.settings = settings
        self.connection: Optional[imaplib.IMAP4_SSL] = None
        self._processed_uids: Set[str] = set()
    
    def connect(self) -> None:
        """Establish IMAP connection with provider-specific optimizations."""
        try:
            # Create SSL context with provider-specific settings
            context = ssl.create_default_context()
            
            # Provider-specific SSL and connection handling
            if self.account.provider == "gmail":
                # Gmail requires SSL with standard settings
                logger.debug(f"Setting up Gmail SSL connection for {self.account.name}")
                self.connection = imaplib.IMAP4_SSL(
                    self.account.imap_server,
                    self.account.imap_port,
                    ssl_context=context
                )
            elif self.account.provider == "ionos":
                # IONOS-specific SSL context configuration
                logger.debug(f"Setting up IONOS SSL connection for {self.account.name}")
                
                # Enhanced SSL context for IONOS compatibility
                context.check_hostname = True
                context.verify_mode = ssl.CERT_REQUIRED
                
                # Allow legacy server configurations
                context.set_ciphers('DEFAULT@SECLEVEL=1')
                
                # IONOS may need additional SSL options
                try:
                    self.connection = imaplib.IMAP4_SSL(
                        self.account.imap_server,
                        self.account.imap_port,
                        ssl_context=context
                    )
                    logger.debug(f"IONOS SSL connection established for {self.account.name}")
                except ssl.SSLError as ssl_err:
                    logger.warning(f"IONOS SSL error: {ssl_err}. Trying fallback SSL settings...")
                    
                    # Fallback: More permissive SSL context for IONOS
                    fallback_context = ssl.create_default_context()
                    fallback_context.check_hostname = False
                    fallback_context.verify_mode = ssl.CERT_NONE
                    
                    self.connection = imaplib.IMAP4_SSL(
                        self.account.imap_server,
                        self.account.imap_port,
                        ssl_context=fallback_context
                    )
                    logger.info(f"IONOS connection using fallback SSL settings for {self.account.name}")
            else:
                # Generic IMAP SSL connection for other providers
                logger.debug(f"Setting up generic SSL connection for {self.account.provider}")
                self.connection = imaplib.IMAP4_SSL(
                    self.account.imap_server,
                    self.account.imap_port,
                    ssl_context=context
                )
            
            # Login with enhanced error reporting
            try:
                self.connection.login(self.account.email, self.account.password)
                logger.info(f"Successfully connected to {self.account.name} ({self.account.email})")
            except imaplib.IMAP4.error as login_err:
                logger.error(f"Login failed for {self.account.name}: {login_err}")
                logger.debug(f"Server: {self.account.imap_server}:{self.account.imap_port}")
                raise
            
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP connection failed for {self.account.name}: {e}")
            logger.debug(f"Connection details - Server: {self.account.imap_server}, Port: {self.account.imap_port}, Provider: {self.account.provider}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to {self.account.name}: {e}")
            logger.debug(f"Error type: {type(e).__name__}, Provider: {self.account.provider}")
            raise
    
    def disconnect(self) -> None:
        """Close IMAP connection."""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except:
                pass
            self.connection = None
            logger.info(f"Disconnected from {self.account.name}")
    
    def select_folder(self, folder: str = "INBOX") -> Tuple[str, List[bytes]]:
        """Select email folder.
        
        Args:
            folder: Folder name to select
            
        Returns:
            Server response tuple
        """
        if not self.connection:
            raise RuntimeError("Not connected to IMAP server")
        
        return self.connection.select(folder)
    
    def search_emails(
        self,
        criteria: Optional[str] = None,
        since_date: Optional[datetime] = None,
        sender_filter: Optional[str] = None,
        subject_filter: Optional[str] = None,
        unseen_only: bool = False
    ) -> List[str]:
        """Search for emails matching criteria.
        
        Args:
            criteria: Raw IMAP search criteria
            since_date: Only emails after this date
            sender_filter: Filter by sender email/name
            subject_filter: Filter by subject substring
            unseen_only: Only return unread emails
            
        Returns:
            List of email UIDs
        """
        if not self.connection:
            raise RuntimeError("Not connected to IMAP server")
        
        # Build search criteria
        search_parts = []
        
        if criteria:
            search_parts.append(criteria)
        else:
            # Build criteria from parameters
            if unseen_only:
                search_parts.append("UNSEEN")
            
            if since_date:
                date_str = since_date.strftime("%d-%b-%Y")
                search_parts.append(f'SINCE "{date_str}"')
            
            if sender_filter:
                search_parts.append(f'FROM "{sender_filter}"')
            
            if subject_filter:
                search_parts.append(f'SUBJECT "{subject_filter}"')
        
        # Default to ALL if no criteria
        if not search_parts:
            search_parts = ["ALL"]
        
        search_string = " ".join(search_parts)
        
        # Perform search
        try:
            status, data = self.connection.search(None, search_string)
            if status != "OK":
                logger.warning(f"Search failed with status: {status}")
                return []
            
            # Extract UIDs
            if data[0]:
                uids = data[0].split()
                return [uid.decode() for uid in uids]
            
            return []
            
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []
    
    def fetch_email(self, uid: str) -> Optional[EmailMessage]:
        """Fetch complete email by UID.
        
        Args:
            uid: Email UID
            
        Returns:
            Parsed EmailMessage or None
        """
        if not self.connection:
            raise RuntimeError("Not connected to IMAP server")
        
        try:
            # Fetch email data
            status, data = self.connection.fetch(uid.encode(), "(RFC822)")
            if status != "OK":
                logger.warning(f"Failed to fetch email {uid}")
                return None
            
            # Parse email
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Extract headers
            subject = self._decode_header(msg.get("Subject", ""))
            sender = self._decode_header(msg.get("From", ""))
            date_str = msg.get("Date", "")
            
            # Parse date
            try:
                date = email.utils.parsedate_to_datetime(date_str)
            except:
                date = datetime.now()
            
            # Extract body
            body = self._extract_body(msg)
            
            # Extract attachments
            attachments = self._extract_attachments(msg, uid, subject, sender, date)
            
            return EmailMessage(
                uid=uid,
                subject=subject,
                sender=sender,
                date=date,
                body=body,
                attachments=attachments,
                raw_message=msg
            )
            
        except Exception as e:
            logger.error(f"Error fetching email {uid}: {e}")
            return None
    
    def _decode_header(self, header_value: str) -> str:
        """Decode email header value.
        
        Args:
            header_value: Raw header value
            
        Returns:
            Decoded string
        """
        if not header_value:
            return ""
        
        decoded_parts = []
        for part, encoding in decode_header(header_value):
            if isinstance(part, bytes):
                if encoding:
                    try:
                        decoded_parts.append(part.decode(encoding))
                    except Exception:
                        # Fallback to UTF-8 with replacement characters
                        decoded_parts.append(part.decode("utf-8", errors="replace"))
                else:
                    # No encoding specified, assume UTF-8
                    decoded_parts.append(part.decode("utf-8", errors="replace"))
            else:
                decoded_parts.append(str(part))
        
        return " ".join(decoded_parts)
    
    def _extract_body(self, msg: EmailMessage) -> str:
        """Extract email body text.
        
        Args:
            msg: Email message
            
        Returns:
            Body text
        """
        body_parts = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                if content_type == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_parts.append(payload.decode("utf-8", errors="replace"))
                    except Exception as e:
                        logger.debug(f"Failed to decode text/plain part: {e}")
        else:
            # Single part message
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    body_parts.append(payload.decode("utf-8", errors="replace"))
            except Exception as e:
                logger.debug(f"Failed to decode message payload: {e}")
        
        return "\n".join(body_parts)
    
    def _extract_attachments(
        self,
        msg: EmailMessage,
        uid: str,
        subject: str,
        sender: str,
        date: datetime
    ) -> List[EmailAttachment]:
        """Extract attachments from email with enhanced error logging.
        
        Args:
            msg: Email message
            uid: Email UID
            subject: Email subject
            sender: Email sender
            date: Email date
            
        Returns:
            List of EmailAttachment objects
        """
        attachments = []
        part_count = 0
        
        logger.debug(f"Extracting attachments from email {uid} ({sender})")
        
        for part in msg.walk():
            part_count += 1
            content_disposition = str(part.get("Content-Disposition", ""))
            content_type = part.get_content_type()
            
            logger.debug(f"Processing part {part_count}: type={content_type}, disposition={content_disposition}")
            
            if "attachment" not in content_disposition:
                # Also check for inline files that might be attachments
                if "inline" in content_disposition and content_type.startswith(("application/", "image/")):
                    logger.debug(f"Found inline attachment candidate: {content_type}")
                else:
                    continue
            
            # Get filename with enhanced error handling
            filename = part.get_filename()
            if not filename:
                # Try to get filename from Content-Type or other headers
                content_type_header = part.get("Content-Type", "")
                if "name=" in content_type_header:
                    try:
                        filename = content_type_header.split("name=")[1].split(";")[0].strip('"')
                        logger.debug(f"Extracted filename from Content-Type: {filename}")
                    except Exception as e:
                        logger.debug(f"Failed to extract filename from Content-Type: {e}")
                
                if not filename:
                    logger.debug(f"No filename found for part {part_count}, skipping")
                    continue
            
            # Decode filename if needed with error handling
            try:
                original_filename = filename
                filename = self._decode_header(filename)
                if filename != original_filename:
                    logger.debug(f"Decoded filename: {original_filename} -> {filename}")
            except Exception as e:
                logger.warning(f"Error decoding filename '{filename}': {e}")
                # Use original filename if decoding fails
                pass
            
            # Check extension with enhanced logging
            file_ext = Path(filename).suffix.lower()
            logger.debug(f"Checking extension '{file_ext}' for file: {filename}")
            
            if file_ext not in self.settings.allowed_extensions:
                logger.debug(f"Skipping attachment {filename} - extension '{file_ext}' not in allowed list: {self.settings.allowed_extensions}")
                continue
            
            # Get content with comprehensive error handling
            try:
                logger.debug(f"Attempting to extract content for: {filename}")
                content = part.get_payload(decode=True)
                
                if not content:
                    logger.warning(f"Empty content for attachment {filename} (UID: {uid})")
                    continue
                
                content_size = len(content)
                logger.debug(f"Successfully extracted {content_size} bytes for: {filename}")
                
                # Check size
                if content_size > self.settings.max_attachment_size:
                    logger.warning(
                        f"Skipping attachment {filename} - "
                        f"size {content_size} exceeds limit {self.settings.max_attachment_size}"
                    )
                    continue
                
                # Validate content (basic check for PDF/image headers)
                is_valid_content = self._validate_attachment_content(content, file_ext, filename)
                if not is_valid_content:
                    logger.warning(f"Skipping attachment {filename} - content validation failed")
                    continue
                
                attachment = EmailAttachment(
                    filename=filename,
                    content=content,
                    content_type=content_type,
                    size=content_size,
                    email_uid=uid,
                    email_subject=subject,
                    email_sender=sender,
                    email_date=date
                )
                attachments.append(attachment)
                logger.info(f"Successfully extracted attachment: {filename} ({content_size} bytes)")
                
            except Exception as e:
                logger.error(f"Error extracting attachment {filename} from email {uid}: {e}")
                logger.debug(f"Error details - Content-Type: {content_type}, Size estimate: {len(str(part))}")
                # Continue processing other attachments even if one fails
                continue
        
        logger.info(f"Extracted {len(attachments)} attachments from email {uid} (processed {part_count} parts)")
        return attachments
    
    def _validate_attachment_content(self, content: bytes, file_ext: str, filename: str) -> bool:
        """Validate attachment content based on file extension.
        
        Args:
            content: File content bytes
            file_ext: File extension (lowercase)
            filename: Original filename for logging
            
        Returns:
            True if content appears valid for the file type
        """
        if not content or len(content) < 4:
            logger.debug(f"Content too small for {filename}: {len(content)} bytes")
            return False
        
        # Check file signatures (magic numbers)
        header = content[:8]
        
        if file_ext == ".pdf":
            # PDF files start with %PDF
            if not header.startswith(b"%PDF"):
                logger.debug(f"PDF validation failed for {filename}: invalid header")
                return False
        elif file_ext in [".jpg", ".jpeg"]:
            # JPEG files start with FFD8
            if not header.startswith(b"\xff\xd8"):
                logger.debug(f"JPEG validation failed for {filename}: invalid header")
                return False
        elif file_ext == ".png":
            # PNG files start with specific signature
            if not header.startswith(b"\x89PNG\r\n\x1a\n"):
                logger.debug(f"PNG validation failed for {filename}: invalid header")
                return False
        elif file_ext == ".tiff":
            # TIFF files start with II or MM
            if not (header.startswith(b"II*\x00") or header.startswith(b"MM\x00*")):
                logger.debug(f"TIFF validation failed for {filename}: invalid header")
                return False
        
        logger.debug(f"Content validation passed for {filename}")
        return True
    
    def mark_as_read(self, uid: str) -> bool:
        """Mark email as read.
        
        Args:
            uid: Email UID
            
        Returns:
            Success status
        """
        if not self.connection:
            raise RuntimeError("Not connected to IMAP server")
        
        try:
            self.connection.store(uid.encode(), "+FLAGS", "\\Seen")
            logger.debug(f"Marked email {uid} as read")
            return True
        except Exception as e:
            logger.error(f"Error marking email {uid} as read: {e}")
            return False
    
    def delete_email(self, uid: str) -> bool:
        """Delete email (move to trash).
        
        Args:
            uid: Email UID
            
        Returns:
            Success status
        """
        if not self.connection:
            raise RuntimeError("Not connected to IMAP server")
        
        try:
            # Mark for deletion
            self.connection.store(uid.encode(), "+FLAGS", "\\Deleted")
            # Expunge to actually delete
            self.connection.expunge()
            logger.info(f"Deleted email {uid}")
            return True
        except Exception as e:
            logger.error(f"Error deleting email {uid}: {e}")
            return False
    
    def download_attachments(
        self,
        download_dir: Path,
        since_date: Optional[datetime] = None,
        mark_processed: bool = True,
        delete_after: bool = False,
        dry_run: bool = False
    ) -> List[Path]:
        """Download all attachments from emails.
        
        Args:
            download_dir: Directory to save attachments
            since_date: Only process emails after this date
            mark_processed: Mark emails as read after processing
            delete_after: Delete emails after processing
            dry_run: Don't actually download, just report what would be done
            
        Returns:
            List of downloaded file paths
        """
        downloaded_files = []
        
        try:
            # Connect if not connected
            if not self.connection:
                self.connect()
            
            # Select folder
            self.select_folder(self.account.folder)
            
            # Search for emails
            uids = self.search_emails(since_date=since_date)
            logger.info(f"Found {len(uids)} emails to process in {self.account.name}")
            
            for uid in uids:
                # Skip if already processed
                if uid in self._processed_uids:
                    logger.debug(f"Skipping already processed email {uid}")
                    continue
                
                # Fetch email
                email_msg = self.fetch_email(uid)
                if not email_msg:
                    continue
                
                # Process attachments
                for attachment in email_msg.attachments:
                    if dry_run:
                        logger.info(
                            f"[DRY RUN] Would download: {attachment.filename} "
                            f"({attachment.size} bytes) from {attachment.email_sender}"
                        )
                    else:
                        try:
                            filepath = attachment.save_to_disk(download_dir)
                            downloaded_files.append(filepath)
                        except Exception as e:
                            logger.error(f"Error saving attachment: {e}")
                            continue
                
                # Mark as processed
                self._processed_uids.add(uid)
                
                # Mark as read if requested
                if mark_processed and not dry_run:
                    self.mark_as_read(uid)
                
                # Delete if requested
                if delete_after and not dry_run:
                    self.delete_email(uid)
            
            return downloaded_files
            
        except Exception as e:
            logger.error(f"Error downloading attachments: {e}")
            raise
        finally:
            # Don't disconnect here - let caller manage connection
            pass
    
    def get_folder_list(self) -> List[str]:
        """Get list of available folders.
        
        Returns:
            List of folder names
        """
        if not self.connection:
            raise RuntimeError("Not connected to IMAP server")
        
        try:
            status, folders = self.connection.list()
            if status != "OK":
                return []
            
            folder_list = []
            for folder_data in folders:
                # Parse folder name from response with proper encoding
                if isinstance(folder_data, bytes):
                    folder_str = folder_data.decode("utf-8", errors="replace")
                else:
                    folder_str = str(folder_data)
                
                # Extract folder name (last part in quotes)
                match = re.search(r'"([^"]+)"$', folder_str)
                if match:
                    folder_list.append(match.group(1))
            
            return folder_list
            
        except Exception as e:
            logger.error(f"Error getting folder list: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test IMAP connection.
        
        Returns:
            True if connection successful
        """
        try:
            self.connect()
            self.select_folder()
            self.disconnect()
            return True
        except Exception as e:
            logger.error(f"Connection test failed for {self.account.name}: {e}")
            return False


class EmailClient:
    """Backward compatibility wrapper for EmailClient.
    
    This class provides backward compatibility for existing tests and code
    that expect the original EmailClient interface.
    """
    
    def __init__(self, account: EmailAccount, settings: EmailSettings):
        """Initialize EmailClient wrapper.
        
        Args:
            account: Email account configuration
            settings: Email processing settings
        """
        self.client = IMAPEmailClient(account, settings)
        self.account = account
        self.settings = settings
    
    def __getattr__(self, name):
        """Delegate all other methods to the underlying IMAPEmailClient."""
        return getattr(self.client, name)
    
    def connect(self) -> None:
        """Connect to email server."""
        return self.client.connect()
    
    def disconnect(self) -> None:
        """Disconnect from email server."""
        return self.client.disconnect()
    
    def test_connection(self) -> bool:
        """Test email connection."""
        return self.client.test_connection()
    
    def download_attachments(
        self,
        download_dir: Path,
        since_date: Optional[datetime] = None,
        mark_processed: bool = True,
        delete_after: bool = False,
        dry_run: bool = False
    ) -> List[Path]:
        """Download attachments from emails."""
        return self.client.download_attachments(
            download_dir=download_dir,
            since_date=since_date,
            mark_processed=mark_processed,
            delete_after=delete_after,
            dry_run=dry_run
        )