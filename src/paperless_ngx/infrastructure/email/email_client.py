"""Multi-provider email client with IMAP support.

This module provides a unified interface for downloading attachments from
multiple email accounts including Gmail and IONOS via IMAP.
"""

from __future__ import annotations

import email
import imaplib
import logging
import re
import ssl
import time
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
)
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
    
    def save_to_disk(self, directory: Path, use_custom_name: bool = True) -> Path:
        """Save attachment to disk.
        
        Args:
            directory: Directory to save attachment
            use_custom_name: Whether to use custom naming pattern
            
        Returns:
            Path to saved file
        """
        directory.mkdir(parents=True, exist_ok=True)
        
        if use_custom_name:
            filename = format_email_attachment_filename(
                self.email_sender,
                self.email_subject,
                self.filename
            )
        else:
            filename = sanitize_filename(self.filename)
        
        # Ensure unique filename
        filename = create_unique_filename(directory, filename)
        filepath = directory / filename
        
        # Write content
        filepath.write_bytes(self.content)
        logger.info(f"Saved attachment: {filepath} ({self.size} bytes)")
        
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
        """Establish IMAP connection."""
        try:
            # Create SSL context
            context = ssl.create_default_context()
            
            # For Gmail, might need special handling
            if self.account.provider == "gmail":
                # Gmail requires SSL
                self.connection = imaplib.IMAP4_SSL(
                    self.account.imap_server,
                    self.account.imap_port,
                    ssl_context=context
                )
            else:
                # Generic IMAP SSL connection
                self.connection = imaplib.IMAP4_SSL(
                    self.account.imap_server,
                    self.account.imap_port,
                    ssl_context=context
                )
            
            # Login
            self.connection.login(self.account.email, self.account.password)
            logger.info(f"Connected to {self.account.name} ({self.account.email})")
            
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP connection failed for {self.account.name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to {self.account.name}: {e}")
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
                    except:
                        decoded_parts.append(part.decode("utf-8", errors="ignore"))
                else:
                    decoded_parts.append(part.decode("utf-8", errors="ignore"))
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
                        body_parts.append(part.get_payload(decode=True).decode("utf-8", errors="ignore"))
                    except:
                        pass
        else:
            # Single part message
            try:
                body_parts.append(msg.get_payload(decode=True).decode("utf-8", errors="ignore"))
            except:
                pass
        
        return "\n".join(body_parts)
    
    def _extract_attachments(
        self,
        msg: EmailMessage,
        uid: str,
        subject: str,
        sender: str,
        date: datetime
    ) -> List[EmailAttachment]:
        """Extract attachments from email.
        
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
        
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition", ""))
            
            if "attachment" not in content_disposition:
                continue
            
            # Get filename
            filename = part.get_filename()
            if not filename:
                continue
            
            # Decode filename if needed
            filename = self._decode_header(filename)
            
            # Check extension
            file_ext = Path(filename).suffix.lower()
            if file_ext not in self.settings.allowed_extensions:
                logger.debug(f"Skipping attachment {filename} - extension not allowed")
                continue
            
            # Get content
            try:
                content = part.get_payload(decode=True)
                if not content:
                    continue
                
                # Check size
                if len(content) > self.settings.max_attachment_size:
                    logger.warning(
                        f"Skipping attachment {filename} - "
                        f"size {len(content)} exceeds limit {self.settings.max_attachment_size}"
                    )
                    continue
                
                attachment = EmailAttachment(
                    filename=filename,
                    content=content,
                    content_type=part.get_content_type(),
                    size=len(content),
                    email_uid=uid,
                    email_subject=subject,
                    email_sender=sender,
                    email_date=date
                )
                attachments.append(attachment)
                
            except Exception as e:
                logger.error(f"Error extracting attachment {filename}: {e}")
        
        return attachments
    
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
                # Parse folder name from response
                if isinstance(folder_data, bytes):
                    folder_str = folder_data.decode("utf-8", errors="ignore")
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