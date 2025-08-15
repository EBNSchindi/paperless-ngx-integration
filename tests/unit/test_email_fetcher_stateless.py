"""Unit tests for stateless EmailFetcherService.

This test suite verifies that the EmailFetcherService operates in a completely
stateless manner, without creating or maintaining any persistent state files.
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from paperless_ngx.application.services.email_fetcher_service import (
    EmailFetcherService,
    EmailProcessingState,
)
from paperless_ngx.infrastructure.email import EmailAccount, EmailSettings


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_email_settings(temp_dir):
    """Create mock email settings."""
    settings = Mock(spec=EmailSettings)
    settings.email_download_dir = temp_dir / "downloads"
    settings.email_check_interval = 300
    settings.mark_as_read = False
    settings.delete_after_processing = False
    settings.get_email_accounts.return_value = [
        EmailAccount(
            name="Test Account 1",
            provider="gmail",
            imap_server="imap.test1.com",
            imap_port=993,
            email="user1@test.com",
            password="password1",
            folder="INBOX",
            enabled=True,
            use_ssl=True,
        ),
        EmailAccount(
            name="Test Account 2",
            provider="exchange",
            imap_server="imap.test2.com",
            imap_port=993,
            email="user2@test.com",
            password="password2",
            folder="INBOX",
            enabled=True,
            use_ssl=True,
        ),
    ]
    return settings


@pytest.fixture
def mock_imap_client():
    """Create a mock IMAP client."""
    client = Mock()
    client.connect = Mock()
    client.disconnect = Mock()
    client.select_folder = Mock()
    client.search_emails = Mock(return_value=[])
    client.fetch_email = Mock(return_value=None)
    client.mark_as_read = Mock()
    client.delete_email = Mock()
    client.test_connection = Mock(return_value=True)
    client.get_folder_list = Mock(return_value=["INBOX", "Sent", "Drafts"])
    return client


@pytest.fixture
def mock_attachment_processor():
    """Create a mock attachment processor."""
    processor = Mock()
    processor.process_attachments = Mock(return_value=[])
    processor.cleanup_empty_directories = Mock(return_value=0)
    processor.get_processing_stats = Mock(
        return_value={
            "base_directory": "/tmp/downloads",
            "organize_by_date": False,
            "organize_by_sender": False,
            "duplicate_check_enabled": False,
            "total_files": 0,
            "total_directories": 0,
        }
    )
    return processor


class TestEmailFetcherStatelessBehavior:
    """Test suite for verifying stateless behavior of EmailFetcherService."""

    def test_no_state_file_created(
        self, mock_email_settings, mock_attachment_processor, temp_dir
    ):
        """Test that no state file is created during service initialization or operation."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )

        # Act - Initialize and perform operations
        with patch("paperless_ngx.application.services.email_fetcher_service.IMAPEmailClient") as mock_client_class:
            mock_client_class.return_value = Mock()
            service._initialize_clients()

        # Assert - No state files should exist
        state_files = list(temp_dir.glob("*.json"))
        assert len(state_files) == 0, "No JSON state files should be created"
        
        # Check for specific files that should NOT exist
        assert not (temp_dir / "processed_emails.json").exists()
        assert not (temp_dir / ".email_state.json").exists()
        assert not (temp_dir / "email_state.json").exists()

    def test_state_only_in_memory(
        self, mock_email_settings, mock_attachment_processor
    ):
        """Test that processing states are only kept in memory."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )

        # Act - Create state
        account_name = "Test Account 1"
        service.processing_states[account_name] = EmailProcessingState(
            account_name=account_name,
            last_check=datetime.now(),
            total_processed=10,
            total_attachments=5,
            last_error=None,
        )

        # Assert - State exists in memory
        assert account_name in service.processing_states
        assert service.processing_states[account_name].total_processed == 10

        # Create new service instance - state should not persist
        new_service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        # State should be initialized but empty (no data from previous instance)
        assert account_name in new_service.processing_states  # Account exists
        assert new_service.processing_states[account_name].total_processed == 0  # But with fresh state
        assert new_service.processing_states[account_name].last_check is None

    def test_no_uid_filtering(
        self, mock_email_settings, mock_attachment_processor, mock_imap_client
    ):
        """Test that ALL emails in date range are processed without UID filtering."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        # Mock email UIDs in date range
        test_uids = [101, 102, 103, 104, 105]
        mock_imap_client.search_emails.return_value = test_uids
        
        # Mock email messages
        mock_email = Mock()
        mock_email.attachments = []
        mock_imap_client.fetch_email.return_value = mock_email
        
        with patch("paperless_ngx.application.services.email_fetcher_service.IMAPEmailClient", return_value=mock_imap_client):
            service.clients["Test Account 1"] = mock_imap_client
            
            # Act - Fetch emails
            since_date = datetime.now() - timedelta(days=7)
            service.fetch_account("Test Account 1", since_date=since_date)
            
            # Assert - All UIDs should be fetched
            assert mock_imap_client.fetch_email.call_count == len(test_uids)
            for uid in test_uids:
                mock_imap_client.fetch_email.assert_any_call(uid)

    def test_date_filtering_only(
        self, mock_email_settings, mock_attachment_processor, mock_imap_client
    ):
        """Test that emails are filtered by date only, not by processing history."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        since_date = datetime(2025, 1, 1)
        mock_imap_client.search_emails.return_value = [201, 202, 203]
        
        with patch("paperless_ngx.application.services.email_fetcher_service.IMAPEmailClient", return_value=mock_imap_client):
            service.clients["Test Account 1"] = mock_imap_client
            
            # Act - Fetch emails with date filter
            service.fetch_account("Test Account 1", since_date=since_date)
            
            # Assert - Search was called with date filter only
            mock_imap_client.search_emails.assert_called_once_with(since_date=since_date)

    def test_multiple_runs_process_same_emails(
        self, mock_email_settings, mock_attachment_processor, mock_imap_client
    ):
        """Test that running the same date range multiple times processes the same emails."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        test_uids = [301, 302, 303]
        mock_imap_client.search_emails.return_value = test_uids
        mock_email = Mock()
        mock_email.attachments = []
        mock_imap_client.fetch_email.return_value = mock_email
        
        with patch("paperless_ngx.application.services.email_fetcher_service.IMAPEmailClient", return_value=mock_imap_client):
            service.clients["Test Account 1"] = mock_imap_client
            since_date = datetime(2025, 1, 1)
            
            # Act - Run fetch multiple times
            for _ in range(3):
                mock_imap_client.fetch_email.reset_mock()
                service.fetch_account("Test Account 1", since_date=since_date)
                
                # Assert - Same emails processed each time
                assert mock_imap_client.fetch_email.call_count == len(test_uids)

    def test_statistics_are_session_only(
        self, mock_email_settings, mock_attachment_processor, mock_imap_client
    ):
        """Test that statistics are only kept for the current session."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        # Act - Process some emails
        with patch("paperless_ngx.application.services.email_fetcher_service.IMAPEmailClient", return_value=mock_imap_client):
            service.clients["Test Account 1"] = mock_imap_client
            service.processing_states["Test Account 1"] = EmailProcessingState(
                account_name="Test Account 1",
                last_check=datetime.now(),
                total_processed=5,
                total_attachments=3,
                last_error=None,
            )
            
            stats = service.get_statistics()
            
            # Assert - Statistics reflect current session
            assert stats["total_processed_emails"] == 5
            assert stats["total_attachments"] == 3
            
            # Create new service - statistics should reset
            new_service = EmailFetcherService(
                email_settings=mock_email_settings,
                attachment_processor=mock_attachment_processor,
            )
            new_stats = new_service.get_statistics()
            
            assert new_stats["total_processed_emails"] == 0
            assert new_stats["total_attachments"] == 0

    def test_reset_account_state_memory_only(
        self, mock_email_settings, mock_attachment_processor
    ):
        """Test that resetting account state only affects memory, no files."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        # Set up initial state
        service.processing_states["Test Account 1"] = EmailProcessingState(
            account_name="Test Account 1",
            last_check=datetime.now(),
            total_processed=10,
            total_attachments=5,
            last_error="Previous error",
        )
        
        # Act - Reset state
        result = service.reset_account_state("Test Account 1")
        
        # Assert
        assert result is True
        state = service.processing_states["Test Account 1"]
        assert state.last_check is None
        assert state.total_processed == 0
        assert state.total_attachments == 0
        assert state.last_error is None


class TestDateRangeProcessing:
    """Test suite for date range-based email processing."""

    @pytest.mark.parametrize(
        "date_range,expected_count",
        [
            (timedelta(days=1), 5),   # Last day
            (timedelta(days=7), 20),  # Last week
            (timedelta(days=30), 50), # Last month
        ],
    )
    def test_different_date_ranges(
        self,
        mock_email_settings,
        mock_attachment_processor,
        mock_imap_client,
        date_range,
        expected_count,
    ):
        """Test processing with different date ranges."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        # Mock different email counts for different date ranges
        mock_imap_client.search_emails.return_value = list(range(expected_count))
        mock_email = Mock()
        mock_email.attachments = []
        mock_imap_client.fetch_email.return_value = mock_email
        
        with patch("paperless_ngx.application.services.email_fetcher_service.IMAPEmailClient", return_value=mock_imap_client):
            service.clients["Test Account 1"] = mock_imap_client
            
            # Act
            since_date = datetime.now() - date_range
            service.fetch_account("Test Account 1", since_date=since_date)
            
            # Assert
            assert mock_imap_client.fetch_email.call_count == expected_count

    def test_empty_date_range(
        self, mock_email_settings, mock_attachment_processor, mock_imap_client
    ):
        """Test handling of empty date range (no emails)."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        mock_imap_client.search_emails.return_value = []  # No emails in range
        
        with patch("paperless_ngx.application.services.email_fetcher_service.IMAPEmailClient", return_value=mock_imap_client):
            service.clients["Test Account 1"] = mock_imap_client
            
            # Act
            result = service.fetch_account(
                "Test Account 1",
                since_date=datetime.now() + timedelta(days=1),  # Future date
            )
            
            # Assert
            assert result == []
            assert mock_imap_client.fetch_email.call_count == 0

    def test_custom_date_range(
        self, mock_email_settings, mock_attachment_processor, mock_imap_client
    ):
        """Test processing with custom date range."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        # Specific date range
        start_date = datetime(2025, 1, 1)
        test_uids = [501, 502, 503, 504, 505]
        mock_imap_client.search_emails.return_value = test_uids
        
        with patch("paperless_ngx.application.services.email_fetcher_service.IMAPEmailClient", return_value=mock_imap_client):
            service.clients["Test Account 1"] = mock_imap_client
            
            # Act
            service.fetch_account("Test Account 1", since_date=start_date)
            
            # Assert
            mock_imap_client.search_emails.assert_called_with(since_date=start_date)


class TestMultipleAccountProcessing:
    """Test suite for processing multiple email accounts."""

    def test_all_accounts_processed(
        self, mock_email_settings, mock_attachment_processor
    ):
        """Test that all configured accounts are processed."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        mock_clients = {}
        for account in mock_email_settings.get_email_accounts():
            mock_client = Mock()
            mock_client.connect = Mock()
            mock_client.disconnect = Mock()
            mock_client.select_folder = Mock()
            mock_client.search_emails = Mock(return_value=[])
            mock_client.fetch_email = Mock(return_value=None)
            mock_clients[account.name] = mock_client
        
        with patch("paperless_ngx.application.services.email_fetcher_service.IMAPEmailClient") as mock_client_class:
            mock_client_class.side_effect = list(mock_clients.values())
            service._initialize_clients()
            
            # Replace with our mocks
            for name, client in mock_clients.items():
                service.clients[name] = client
            
            # Act
            results = service.fetch_all_accounts()
            
            # Assert
            assert len(results) == 2
            assert "Test Account 1" in results
            assert "Test Account 2" in results
            for client in mock_clients.values():
                client.connect.assert_called_once()
                client.disconnect.assert_called()

    def test_account_failure_doesnt_stop_others(
        self, mock_email_settings, mock_attachment_processor
    ):
        """Test that failure in one account doesn't prevent processing others."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        # Mock first account to fail
        mock_client1 = Mock()
        mock_client1.connect.side_effect = Exception("Connection failed")
        
        # Mock second account to succeed
        mock_client2 = Mock()
        mock_client2.connect = Mock()
        mock_client2.disconnect = Mock()
        mock_client2.select_folder = Mock()
        mock_client2.search_emails = Mock(return_value=[601, 602])
        mock_client2.fetch_email = Mock(return_value=Mock(attachments=[]))
        
        service.clients["Test Account 1"] = mock_client1
        service.clients["Test Account 2"] = mock_client2
        
        # Act
        results = service.fetch_all_accounts()
        
        # Assert
        assert len(results) == 2
        assert results["Test Account 1"] == []  # Failed account returns empty
        assert "Test Account 2" in results  # Second account still processed


class TestErrorHandling:
    """Test suite for error handling scenarios."""

    def test_invalid_credentials(
        self, mock_email_settings, mock_attachment_processor
    ):
        """Test handling of invalid email credentials."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        mock_client = Mock()
        mock_client.connect.side_effect = Exception("Authentication failed")
        service.clients["Test Account 1"] = mock_client
        
        # Act
        result = service.fetch_account("Test Account 1")
        
        # Assert
        assert result == []
        state = service.processing_states.get("Test Account 1")
        if state:
            assert "Authentication failed" in str(state.last_error)

    def test_network_disconnection(
        self, mock_email_settings, mock_attachment_processor, mock_imap_client
    ):
        """Test handling of network disconnection during processing."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        mock_imap_client.search_emails.return_value = [701, 702, 703]
        mock_imap_client.fetch_email.side_effect = [
            Mock(attachments=[]),
            Exception("Network error"),
            Mock(attachments=[]),
        ]
        
        service.clients["Test Account 1"] = mock_imap_client
        
        # Act
        result = service.fetch_account("Test Account 1")
        
        # Assert
        # Should continue processing despite error
        assert mock_imap_client.fetch_email.call_count == 3

    def test_corrupted_email_handling(
        self, mock_email_settings, mock_attachment_processor, mock_imap_client
    ):
        """Test handling of corrupted email messages."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        mock_imap_client.search_emails.return_value = [801, 802]
        mock_imap_client.fetch_email.side_effect = [
            None,  # Corrupted email returns None
            Mock(attachments=[]),  # Valid email
        ]
        
        service.clients["Test Account 1"] = mock_imap_client
        
        # Act
        result = service.fetch_account("Test Account 1")
        
        # Assert
        # Should continue processing valid emails
        assert mock_imap_client.fetch_email.call_count == 2


class TestContinuousOperation:
    """Test suite for continuous email fetching."""

    def test_continuous_fetch_iterations(
        self, mock_email_settings, mock_attachment_processor, mock_imap_client
    ):
        """Test continuous fetching with limited iterations."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        mock_imap_client.search_emails.return_value = []
        service.clients["Test Account 1"] = mock_imap_client
        service.clients["Test Account 2"] = mock_imap_client
        
        # Act
        with patch("time.sleep"):  # Skip actual sleep
            service.run_continuous(interval=1, max_iterations=3)
        
        # Assert
        # Each iteration should process all accounts
        assert mock_imap_client.connect.call_count >= 6  # 2 accounts * 3 iterations

    def test_continuous_fetch_keyboard_interrupt(
        self, mock_email_settings, mock_attachment_processor
    ):
        """Test that continuous fetching handles keyboard interrupt gracefully."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        # Act & Assert
        with patch("time.sleep", side_effect=KeyboardInterrupt):
            # Should not raise, just exit gracefully
            service.run_continuous(interval=1, max_iterations=None)


class TestConnectionManagement:
    """Test suite for email connection management."""

    def test_connection_testing(
        self, mock_email_settings, mock_attachment_processor
    ):
        """Test connection testing for all accounts."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        # Mock different connection results
        mock_client1 = Mock()
        mock_client1.test_connection.return_value = True
        
        mock_client2 = Mock()
        mock_client2.test_connection.return_value = False
        
        service.clients["Test Account 1"] = mock_client1
        service.clients["Test Account 2"] = mock_client2
        
        # Act
        results = service.test_connections()
        
        # Assert
        assert results["Test Account 1"] is True
        assert results["Test Account 2"] is False

    def test_folder_listing(
        self, mock_email_settings, mock_attachment_processor, mock_imap_client
    ):
        """Test listing folders for an account."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        expected_folders = ["INBOX", "Sent", "Drafts", "Trash"]
        mock_imap_client.get_folder_list.return_value = expected_folders
        service.clients["Test Account 1"] = mock_imap_client
        
        # Act
        folders = service.list_folders("Test Account 1")
        
        # Assert
        assert folders == expected_folders
        mock_imap_client.connect.assert_called_once()
        mock_imap_client.disconnect.assert_called()

    @pytest.mark.asyncio
    async def test_async_connection_management(
        self, mock_email_settings, mock_attachment_processor, mock_imap_client
    ):
        """Test async connection and disconnection methods."""
        # Arrange
        service = EmailFetcherService(
            email_settings=mock_email_settings,
            attachment_processor=mock_attachment_processor,
        )
        
        service.clients["Test Account 1"] = mock_imap_client
        
        # Act - Connect
        connected = await service.connect("Test Account 1")
        
        # Assert
        assert connected is True
        mock_imap_client.connect.assert_called_once()
        
        # Act - Disconnect
        await service.disconnect("Test Account 1")
        
        # Assert
        mock_imap_client.disconnect.assert_called_once()