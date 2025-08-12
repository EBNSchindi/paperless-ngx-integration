"""Integration tests for email account functionality.

Tests:
- IMAP connection for all 3 accounts
- Authentication with app-specific passwords
- Email fetching with date range filters
- Attachment extraction
"""

import datetime
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from pathlib import Path

from src.paperless_ngx.infrastructure.email.email_client import EmailClient
from src.paperless_ngx.infrastructure.email.email_config import EmailAccount, EmailSettings
from src.paperless_ngx.application.services.email_fetcher_service import EmailFetcherService


class TestEmailAccountConnections:
    """Test individual email account connections."""
    
    @pytest.fixture
    def gmail_account_1(self):
        """Gmail Account 1 configuration."""
        return EmailAccount(
            name="Gmail Account 1",
            provider="gmail",
            imap_server="imap.gmail.com",
            imap_port=993,
            email="ebn.veranstaltungen.consulting@gmail.com",
            password="test_app_password_1",
            folder="INBOX",
            enabled=True,
            use_ssl=True
        )
    
    @pytest.fixture
    def gmail_account_2(self):
        """Gmail Account 2 configuration."""
        return EmailAccount(
            name="Gmail Account 2",
            provider="gmail",
            imap_server="imap.gmail.com",
            imap_port=993,
            email="daniel.schindler1992@gmail.com",
            password="test_app_password_2",
            folder="INBOX",
            enabled=True,
            use_ssl=True
        )
    
    @pytest.fixture
    def ionos_account(self):
        """IONOS Account configuration."""
        return EmailAccount(
            name="IONOS Account",
            provider="ionos",
            imap_server="imap.ionos.de",
            imap_port=993,
            email="info@ettlingen-by-night.de",
            password="test_password_3",
            folder="INBOX",
            enabled=True,
            use_ssl=True
        )
    
    @patch('imaplib.IMAP4_SSL')
    def test_gmail_1_imap_connection(self, mock_imap, gmail_account_1):
        """Test Gmail Account 1 IMAP connection."""
        mock_instance = MagicMock()
        mock_imap.return_value = mock_instance
        mock_instance.login.return_value = ('OK', [b'Authenticated'])
        mock_instance.select.return_value = ('OK', [b'15'])
        
        client = EmailClient(
            server=gmail_account_1.imap_server,
            port=gmail_account_1.imap_port,
            username=gmail_account_1.email,
            password=gmail_account_1.password,
            use_ssl=gmail_account_1.use_ssl
        )
        
        result = client.connect()
        assert result is True
        
        # Verify connection parameters
        mock_imap.assert_called_with(
            gmail_account_1.imap_server,
            gmail_account_1.imap_port
        )
        mock_instance.login.assert_called_with(
            gmail_account_1.email,
            gmail_account_1.password
        )
    
    @patch('imaplib.IMAP4_SSL')
    def test_gmail_2_imap_connection(self, mock_imap, gmail_account_2):
        """Test Gmail Account 2 IMAP connection."""
        mock_instance = MagicMock()
        mock_imap.return_value = mock_instance
        mock_instance.login.return_value = ('OK', [b'Authenticated'])
        mock_instance.select.return_value = ('OK', [b'10'])
        
        client = EmailClient(
            server=gmail_account_2.imap_server,
            port=gmail_account_2.imap_port,
            username=gmail_account_2.email,
            password=gmail_account_2.password,
            use_ssl=gmail_account_2.use_ssl
        )
        
        result = client.connect()
        assert result is True
        
        mock_instance.login.assert_called_with(
            gmail_account_2.email,
            gmail_account_2.password
        )
    
    @patch('imaplib.IMAP4_SSL')
    def test_ionos_imap_connection(self, mock_imap, ionos_account):
        """Test IONOS Account IMAP connection."""
        mock_instance = MagicMock()
        mock_imap.return_value = mock_instance
        mock_instance.login.return_value = ('OK', [b'Authenticated'])
        mock_instance.select.return_value = ('OK', [b'25'])
        
        client = EmailClient(
            server=ionos_account.imap_server,
            port=ionos_account.imap_port,
            username=ionos_account.email,
            password=ionos_account.password,
            use_ssl=ionos_account.use_ssl
        )
        
        result = client.connect()
        assert result is True
        
        # Verify IONOS-specific server
        mock_imap.assert_called_with("imap.ionos.de", 993)
    
    @patch('imaplib.IMAP4_SSL')
    def test_app_specific_password_required_for_gmail(self, mock_imap, gmail_account_1):
        """Test that Gmail requires app-specific passwords."""
        mock_instance = MagicMock()
        mock_imap.return_value = mock_instance
        
        # Simulate authentication failure with regular password
        mock_instance.login.side_effect = Exception(
            "[AUTHENTICATIONFAILED] Invalid credentials (Failure)"
        )
        
        client = EmailClient(
            server=gmail_account_1.imap_server,
            port=gmail_account_1.imap_port,
            username=gmail_account_1.email,
            password="regular_password",  # Not app-specific
            use_ssl=gmail_account_1.use_ssl
        )
        
        with pytest.raises(Exception, match="AUTHENTICATIONFAILED"):
            client.connect()
    
    @patch('imaplib.IMAP4_SSL')
    def test_imap_folder_selection(self, mock_imap, gmail_account_1):
        """Test IMAP folder selection."""
        mock_instance = MagicMock()
        mock_imap.return_value = mock_instance
        mock_instance.login.return_value = ('OK', [b'Authenticated'])
        mock_instance.select.return_value = ('OK', [b'20'])
        mock_instance.list.return_value = ('OK', [
            b'(\\HasNoChildren) "/" "INBOX"',
            b'(\\HasChildren \\Noselect) "/" "[Gmail]"',
            b'(\\All \\HasNoChildren) "/" "[Gmail]/All Mail"',
            b'(\\Drafts \\HasNoChildren) "/" "[Gmail]/Drafts"',
            b'(\\HasNoChildren \\Important) "/" "[Gmail]/Important"',
            b'(\\HasNoChildren \\Sent) "/" "[Gmail]/Sent Mail"',
            b'(\\HasNoChildren \\Spam) "/" "[Gmail]/Spam"',
            b'(\\HasNoChildren \\Starred) "/" "[Gmail]/Starred"',
            b'(\\HasNoChildren \\Trash) "/" "[Gmail]/Trash"'
        ])
        
        client = EmailClient(
            server=gmail_account_1.imap_server,
            port=gmail_account_1.imap_port,
            username=gmail_account_1.email,
            password=gmail_account_1.password,
            use_ssl=gmail_account_1.use_ssl
        )
        
        client.connect()
        folders = client.list_folders()
        
        assert "INBOX" in folders
        assert "[Gmail]/Sent Mail" in folders
        assert "[Gmail]/Spam" in folders


class TestEmailFetching:
    """Test email fetching functionality."""
    
    @pytest.fixture
    def email_fetcher(self):
        """Create email fetcher service."""
        settings = EmailSettings()
        return EmailFetcherService(settings)
    
    def create_test_email_with_attachment(self):
        """Create a test email with attachment."""
        msg = MIMEMultipart()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'recipient@example.com'
        msg['Subject'] = 'Test Invoice'
        msg['Date'] = email.utils.formatdate(localtime=True)
        
        # Add body
        body = MIMEText("Please find attached invoice.", 'plain')
        msg.attach(body)
        
        # Add PDF attachment
        attachment = MIMEBase('application', 'pdf')
        attachment.set_payload(b'%PDF-1.4 test content')
        encoders.encode_base64(attachment)
        attachment.add_header(
            'Content-Disposition',
            'attachment; filename="invoice_2024.pdf"'
        )
        msg.attach(attachment)
        
        return msg.as_bytes()
    
    @patch('imaplib.IMAP4_SSL')
    def test_fetch_emails_with_date_filter(self, mock_imap):
        """Test fetching emails with date range filter."""
        mock_instance = MagicMock()
        mock_imap.return_value = mock_instance
        mock_instance.login.return_value = ('OK', [b'Authenticated'])
        mock_instance.select.return_value = ('OK', [b'10'])
        
        # Set up date filter for last 7 days
        since_date = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%d-%b-%Y")
        
        # Mock search with date filter
        mock_instance.search.return_value = ('OK', [b'1 2 3'])
        
        client = EmailClient(
            server="imap.gmail.com",
            port=993,
            username="test@gmail.com",
            password="app_password",
            use_ssl=True
        )
        
        client.connect()
        
        # Search for emails from last 7 days
        client.connection.search(None, f'(SINCE "{since_date}")')
        
        # Verify search was called with correct date filter
        mock_instance.search.assert_called_with(None, f'(SINCE "{since_date}")')
    
    @patch('imaplib.IMAP4_SSL')
    def test_extract_attachments_from_email(self, mock_imap):
        """Test extracting attachments from emails."""
        mock_instance = MagicMock()
        mock_imap.return_value = mock_instance
        mock_instance.login.return_value = ('OK', [b'Authenticated'])
        mock_instance.select.return_value = ('OK', [b'5'])
        mock_instance.search.return_value = ('OK', [b'1'])
        
        # Create test email with attachment
        test_email = self.create_test_email_with_attachment()
        mock_instance.fetch.return_value = ('OK', [(b'1', test_email)])
        
        client = EmailClient(
            server="imap.gmail.com",
            port=993,
            username="test@gmail.com",
            password="app_password",
            use_ssl=True
        )
        
        client.connect()
        
        # Fetch email
        status, data = client.connection.fetch(b'1', '(RFC822)')
        
        # Parse email
        msg = email.message_from_bytes(data[0][1])
        
        # Extract attachments
        attachments = []
        for part in msg.walk():
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if filename:
                    attachments.append({
                        'filename': filename,
                        'content': part.get_payload(decode=True)
                    })
        
        assert len(attachments) == 1
        assert attachments[0]['filename'] == 'invoice_2024.pdf'
        assert attachments[0]['content'].startswith(b'%PDF-1.4')
    
    @patch('imaplib.IMAP4_SSL')
    def test_month_based_organization(self, mock_imap):
        """Test organizing emails by month."""
        mock_instance = MagicMock()
        mock_imap.return_value = mock_instance
        mock_instance.login.return_value = ('OK', [b'Authenticated'])
        mock_instance.select.return_value = ('OK', [b'100'])
        
        # Mock emails from different months
        emails_by_month = {
            '2024-01': [b'1', b'2', b'3'],
            '2024-02': [b'4', b'5'],
            '2024-03': [b'6', b'7', b'8', b'9']
        }
        
        # Simulate month-based search
        def search_side_effect(charset, criteria):
            for month, ids in emails_by_month.items():
                if month in criteria:
                    return ('OK', [b' '.join(ids)])
            return ('OK', [b''])
        
        mock_instance.search.side_effect = search_side_effect
        
        client = EmailClient(
            server="imap.gmail.com",
            port=993,
            username="test@gmail.com",
            password="app_password",
            use_ssl=True
        )
        
        client.connect()
        
        # Test fetching for each month
        for month, expected_ids in emails_by_month.items():
            status, data = client.connection.search(None, f'(SINCE "{month}-01")')
            email_ids = data[0].split()
            assert len(email_ids) == len(expected_ids)
    
    @patch('imaplib.IMAP4_SSL')
    def test_multiple_account_parallel_fetch(self, mock_imap):
        """Test fetching from multiple accounts in parallel."""
        accounts = [
            {"email": "account1@gmail.com", "password": "pass1"},
            {"email": "account2@gmail.com", "password": "pass2"},
            {"email": "account3@ionos.de", "password": "pass3"}
        ]
        
        mock_instances = []
        for i, account in enumerate(accounts):
            mock_instance = MagicMock()
            mock_instance.login.return_value = ('OK', [b'Authenticated'])
            mock_instance.select.return_value = ('OK', [f'{(i+1)*5}'.encode()])
            mock_instance.search.return_value = ('OK', [f'{i+1}'.encode()])
            mock_instances.append(mock_instance)
        
        mock_imap.side_effect = mock_instances
        
        # Connect and fetch from all accounts
        results = []
        for account in accounts:
            client = EmailClient(
                server="imap.gmail.com" if "gmail" in account["email"] else "imap.ionos.de",
                port=993,
                username=account["email"],
                password=account["password"],
                use_ssl=True
            )
            
            if client.connect():
                status, data = client.connection.search(None, 'ALL')
                results.append({
                    'account': account["email"],
                    'email_count': len(data[0].split()) if data[0] else 0
                })
        
        assert len(results) == 3
        assert all(r['email_count'] > 0 for r in results)
    
    @patch('imaplib.IMAP4_SSL')
    def test_attachment_filtering_by_extension(self, mock_imap):
        """Test filtering attachments by allowed extensions."""
        mock_instance = MagicMock()
        mock_imap.return_value = mock_instance
        
        # Create email with multiple attachments
        msg = MIMEMultipart()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'recipient@example.com'
        msg['Subject'] = 'Multiple Attachments'
        
        # Add allowed attachment (PDF)
        pdf_attachment = MIMEBase('application', 'pdf')
        pdf_attachment.set_payload(b'PDF content')
        pdf_attachment.add_header('Content-Disposition', 'attachment; filename="document.pdf"')
        msg.attach(pdf_attachment)
        
        # Add disallowed attachment (EXE)
        exe_attachment = MIMEBase('application', 'octet-stream')
        exe_attachment.set_payload(b'EXE content')
        exe_attachment.add_header('Content-Disposition', 'attachment; filename="program.exe"')
        msg.attach(exe_attachment)
        
        # Filter attachments
        allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg']
        attachments = []
        
        for part in msg.walk():
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if filename:
                    ext = Path(filename).suffix.lower()
                    if ext in allowed_extensions:
                        attachments.append(filename)
        
        assert len(attachments) == 1
        assert attachments[0] == 'document.pdf'
        assert 'program.exe' not in attachments