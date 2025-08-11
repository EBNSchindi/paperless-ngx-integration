"""Email fetcher service to coordinate multiple email accounts.

This service manages fetching attachments from all configured email accounts,
tracking processed emails, and coordinating with the attachment processor.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..use_cases.attachment_processor import AttachmentProcessor, ProcessedAttachment
from ...infrastructure.email import (
    EmailSettings,
    IMAPEmailClient,
    load_email_config_from_env,
)

logger = logging.getLogger(__name__)


@dataclass
class EmailProcessingState:
    """Track email processing state."""
    
    account_name: str
    last_check: Optional[datetime]
    processed_uids: Set[str]
    total_processed: int
    total_attachments: int
    last_error: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "account_name": self.account_name,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "processed_uids": list(self.processed_uids),
            "total_processed": self.total_processed,
            "total_attachments": self.total_attachments,
            "last_error": self.last_error,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EmailProcessingState:
        """Create from dictionary."""
        return cls(
            account_name=data["account_name"],
            last_check=datetime.fromisoformat(data["last_check"]) if data.get("last_check") else None,
            processed_uids=set(data.get("processed_uids", [])),
            total_processed=data.get("total_processed", 0),
            total_attachments=data.get("total_attachments", 0),
            last_error=data.get("last_error"),
        )


class EmailFetcherService:
    """Service to fetch and process email attachments from multiple accounts."""
    
    def __init__(
        self,
        email_settings: Optional[EmailSettings] = None,
        attachment_processor: Optional[AttachmentProcessor] = None,
        state_file: Optional[Path] = None
    ):
        """Initialize email fetcher service.
        
        Args:
            email_settings: Email configuration settings
            attachment_processor: Attachment processor instance
            state_file: Path to state persistence file
        """
        self.settings = email_settings or load_email_config_from_env()
        
        # Initialize attachment processor
        if attachment_processor:
            self.processor = attachment_processor
        else:
            self.processor = AttachmentProcessor(
                base_dir=self.settings.email_download_dir,
                organize_by_date=True,
                organize_by_sender=False,
                duplicate_check=True
            )
        
        # State management
        self.state_file = state_file or self.settings.email_processed_db
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.processing_states: Dict[str, EmailProcessingState] = {}
        self._load_state()
        
        # Email clients
        self.clients: Dict[str, IMAPEmailClient] = {}
        self._initialize_clients()
    
    def _initialize_clients(self) -> None:
        """Initialize IMAP clients for all configured accounts."""
        accounts = self.settings.get_email_accounts()
        
        for account in accounts:
            try:
                client = IMAPEmailClient(account, self.settings)
                self.clients[account.name] = client
                
                # Initialize state if not exists
                if account.name not in self.processing_states:
                    self.processing_states[account.name] = EmailProcessingState(
                        account_name=account.name,
                        last_check=None,
                        processed_uids=set(),
                        total_processed=0,
                        total_attachments=0,
                        last_error=None
                    )
                
                logger.info(f"Initialized client for {account.name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize client for {account.name}: {e}")
    
    def _load_state(self) -> None:
        """Load processing state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for account_data in data.get("accounts", []):
                        state = EmailProcessingState.from_dict(account_data)
                        self.processing_states[state.account_name] = state
                logger.info(f"Loaded state for {len(self.processing_states)} accounts")
            except Exception as e:
                logger.error(f"Error loading state: {e}")
    
    def _save_state(self) -> None:
        """Save processing state to file."""
        try:
            data = {
                "last_updated": datetime.now().isoformat(),
                "accounts": [state.to_dict() for state in self.processing_states.values()]
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def fetch_account(
        self,
        account_name: str,
        since_date: Optional[datetime] = None,
        dry_run: bool = False
    ) -> List[ProcessedAttachment]:
        """Fetch attachments from specific email account.
        
        Args:
            account_name: Name of email account
            since_date: Only process emails after this date
            dry_run: Don't actually download, just report
            
        Returns:
            List of processed attachments
        """
        if account_name not in self.clients:
            logger.error(f"Account {account_name} not configured")
            return []
        
        client = self.clients[account_name]
        state = self.processing_states[account_name]
        processed_attachments = []
        
        try:
            # Connect to email server
            client.connect()
            client.select_folder()
            
            # Load processed UIDs for this client
            client._processed_uids = state.processed_uids.copy()
            
            # Determine since date
            if not since_date and state.last_check:
                # Use last check minus 1 day for safety
                since_date = state.last_check - timedelta(days=1)
            
            # Search for emails
            uids = client.search_emails(since_date=since_date)
            new_uids = [uid for uid in uids if uid not in state.processed_uids]
            
            logger.info(
                f"{account_name}: Found {len(uids)} emails, "
                f"{len(new_uids)} new to process"
            )
            
            if dry_run:
                logger.info(f"[DRY RUN] Would process {len(new_uids)} emails from {account_name}")
            
            # Process emails
            for uid in new_uids:
                try:
                    # Skip if already processed
                    if uid in state.processed_uids:
                        continue
                    
                    # Fetch email
                    email_msg = client.fetch_email(uid)
                    if not email_msg:
                        continue
                    
                    # Process attachments
                    if email_msg.attachments:
                        if dry_run:
                            for att in email_msg.attachments:
                                logger.info(
                                    f"[DRY RUN] Would download: {att.filename} "
                                    f"({att.size} bytes) from {att.email_sender}"
                                )
                        else:
                            # Process attachments
                            processed = self.processor.process_attachments(
                                email_msg.attachments,
                                skip_duplicates=True
                            )
                            processed_attachments.extend(processed)
                            state.total_attachments += len(processed)
                    
                    # Mark as processed
                    state.processed_uids.add(uid)
                    state.total_processed += 1
                    
                    # Mark email as read if configured
                    if self.settings.mark_as_read and not dry_run:
                        client.mark_as_read(uid)
                    
                    # Delete if configured
                    if self.settings.delete_after_processing and not dry_run:
                        client.delete_email(uid)
                    
                except Exception as e:
                    logger.error(f"Error processing email {uid}: {e}")
                    state.last_error = str(e)
            
            # Update state
            state.last_check = datetime.now()
            state.last_error = None
            self._save_state()
            
            logger.info(
                f"{account_name}: Processed {len(processed_attachments)} attachments "
                f"from {len(new_uids)} emails"
            )
            
        except Exception as e:
            logger.error(f"Error fetching from {account_name}: {e}")
            state.last_error = str(e)
            self._save_state()
        finally:
            # Disconnect
            try:
                client.disconnect()
            except:
                pass
        
        return processed_attachments
    
    def fetch_all_accounts(
        self,
        since_date: Optional[datetime] = None,
        dry_run: bool = False
    ) -> Dict[str, List[ProcessedAttachment]]:
        """Fetch attachments from all configured accounts.
        
        Args:
            since_date: Only process emails after this date
            dry_run: Don't actually download, just report
            
        Returns:
            Dictionary mapping account names to processed attachments
        """
        results = {}
        
        for account_name in self.clients.keys():
            logger.info(f"Processing account: {account_name}")
            try:
                attachments = self.fetch_account(account_name, since_date, dry_run)
                results[account_name] = attachments
            except Exception as e:
                logger.error(f"Failed to process {account_name}: {e}")
                results[account_name] = []
        
        # Summary
        total_attachments = sum(len(atts) for atts in results.values())
        logger.info(
            f"Fetched total of {total_attachments} attachments "
            f"from {len(results)} accounts"
        )
        
        return results
    
    def run_continuous(
        self,
        interval: Optional[int] = None,
        max_iterations: Optional[int] = None
    ) -> None:
        """Run continuous email fetching.
        
        Args:
            interval: Seconds between checks (default from settings)
            max_iterations: Maximum iterations (None for infinite)
        """
        interval = interval or self.settings.email_check_interval
        iteration = 0
        
        logger.info(f"Starting continuous email fetching (interval: {interval}s)")
        
        try:
            while max_iterations is None or iteration < max_iterations:
                iteration += 1
                logger.info(f"Starting iteration {iteration}")
                
                # Fetch from all accounts
                self.fetch_all_accounts()
                
                # Cleanup empty directories
                self.processor.cleanup_empty_directories()
                
                if max_iterations is None or iteration < max_iterations:
                    logger.info(f"Sleeping for {interval} seconds...")
                    time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Continuous fetching interrupted by user")
        except Exception as e:
            logger.error(f"Error in continuous fetching: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics.
        
        Returns:
            Dictionary with service statistics
        """
        stats = {
            "configured_accounts": len(self.clients),
            "accounts": [],
            "total_processed_emails": 0,
            "total_attachments": 0,
            "processor_stats": self.processor.get_processing_stats(),
        }
        
        for name, state in self.processing_states.items():
            account_stats = {
                "name": name,
                "last_check": state.last_check.isoformat() if state.last_check else None,
                "total_processed": state.total_processed,
                "total_attachments": state.total_attachments,
                "processed_uids_count": len(state.processed_uids),
                "has_error": state.last_error is not None,
                "last_error": state.last_error,
            }
            stats["accounts"].append(account_stats)
            stats["total_processed_emails"] += state.total_processed
            stats["total_attachments"] += state.total_attachments
        
        return stats
    
    def reset_account_state(self, account_name: str) -> bool:
        """Reset processing state for specific account.
        
        Args:
            account_name: Name of account to reset
            
        Returns:
            Success status
        """
        if account_name in self.processing_states:
            self.processing_states[account_name] = EmailProcessingState(
                account_name=account_name,
                last_check=None,
                processed_uids=set(),
                total_processed=0,
                total_attachments=0,
                last_error=None
            )
            self._save_state()
            logger.info(f"Reset state for account: {account_name}")
            return True
        return False
    
    def test_connections(self) -> Dict[str, bool]:
        """Test connections to all configured accounts.
        
        Returns:
            Dictionary mapping account names to connection status
        """
        results = {}
        
        for account_name, client in self.clients.items():
            try:
                success = client.test_connection()
                results[account_name] = success
                if success:
                    logger.info(f"✓ Connection successful: {account_name}")
                else:
                    logger.warning(f"✗ Connection failed: {account_name}")
            except Exception as e:
                logger.error(f"✗ Connection test error for {account_name}: {e}")
                results[account_name] = False
        
        return results
    
    def list_folders(self, account_name: str) -> List[str]:
        """List available folders for specific account.
        
        Args:
            account_name: Name of email account
            
        Returns:
            List of folder names
        """
        if account_name not in self.clients:
            logger.error(f"Account {account_name} not configured")
            return []
        
        client = self.clients[account_name]
        folders = []
        
        try:
            client.connect()
            folders = client.get_folder_list()
            logger.info(f"Found {len(folders)} folders in {account_name}")
        except Exception as e:
            logger.error(f"Error listing folders for {account_name}: {e}")
        finally:
            try:
                client.disconnect()
            except:
                pass
        
        return folders