"""Command-line interface for Paperless NGX integration.

This module provides CLI commands for managing email attachments,
document processing, and API interactions.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from ...application.services import EmailFetcherService
from ...application.use_cases import AttachmentProcessor
from ...infrastructure.email import load_email_config_from_env
from ...infrastructure.config import get_settings
from ...infrastructure.logging import setup_logging

logger = logging.getLogger(__name__)


def setup_parser() -> argparse.ArgumentParser:
    """Set up command-line argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="Paperless NGX Integration CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch email attachments from all accounts
  python -m paperless_ngx.cli --fetch-email-attachments
  
  # Fetch from specific account only
  python -m paperless_ngx.cli --fetch-email-attachments --email-account "Gmail Account 1"
  
  # Dry run to see what would be downloaded
  python -m paperless_ngx.cli --fetch-email-attachments --dry-run
  
  # Fetch emails from last 7 days
  python -m paperless_ngx.cli --fetch-email-attachments --since-days 7
  
  # Test email connections
  python -m paperless_ngx.cli --test-email-connections
  
  # Run continuous email fetching
  python -m paperless_ngx.cli --run-email-fetcher
        """
    )
    
    # General options
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to .env configuration file"
    )
    
    # Email fetching commands
    email_group = parser.add_argument_group("Email Commands")
    email_group.add_argument(
        "--fetch-email-attachments",
        action="store_true",
        help="Download attachments from configured email accounts"
    )
    email_group.add_argument(
        "--email-account",
        type=str,
        metavar="NAME",
        help="Process specific email account only"
    )
    email_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading"
    )
    email_group.add_argument(
        "--since-date",
        type=str,
        metavar="YYYY-MM-DD",
        help="Only process emails after this date"
    )
    email_group.add_argument(
        "--since-days",
        type=int,
        metavar="N",
        help="Only process emails from last N days"
    )
    email_group.add_argument(
        "--test-email-connections",
        action="store_true",
        help="Test connections to all configured email accounts"
    )
    email_group.add_argument(
        "--list-email-folders",
        type=str,
        metavar="ACCOUNT",
        help="List available folders for specific email account"
    )
    email_group.add_argument(
        "--reset-email-state",
        type=str,
        metavar="ACCOUNT",
        help="Reset processing state for specific email account"
    )
    email_group.add_argument(
        "--email-stats",
        action="store_true",
        help="Show email processing statistics"
    )
    email_group.add_argument(
        "--run-email-fetcher",
        action="store_true",
        help="Run continuous email fetching service"
    )
    email_group.add_argument(
        "--fetch-interval",
        type=int,
        default=300,
        metavar="SECONDS",
        help="Interval between email checks in continuous mode (default: 300)"
    )
    email_group.add_argument(
        "--max-iterations",
        type=int,
        metavar="N",
        help="Maximum iterations for continuous mode (default: infinite)"
    )
    
    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--output",
        type=str,
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)"
    )
    output_group.add_argument(
        "--output-file",
        type=str,
        metavar="FILE",
        help="Save output to file"
    )
    
    return parser


def handle_fetch_email_attachments(
    args: argparse.Namespace,
    service: EmailFetcherService
) -> Dict[str, Any]:
    """Handle email attachment fetching.
    
    Args:
        args: Command-line arguments
        service: Email fetcher service
        
    Returns:
        Results dictionary
    """
    # Determine since date
    since_date = None
    if args.since_date:
        try:
            since_date = datetime.strptime(args.since_date, "%Y-%m-%d")
        except ValueError:
            logger.error(f"Invalid date format: {args.since_date}")
            sys.exit(1)
    elif args.since_days:
        since_date = datetime.now() - timedelta(days=args.since_days)
    
    # Fetch attachments
    if args.email_account:
        # Specific account
        logger.info(f"Fetching from account: {args.email_account}")
        attachments = service.fetch_account(
            args.email_account,
            since_date=since_date,
            dry_run=args.dry_run
        )
        results = {
            "account": args.email_account,
            "attachments_processed": len(attachments),
            "dry_run": args.dry_run,
            "files": [att.to_dict() for att in attachments]
        }
    else:
        # All accounts
        logger.info("Fetching from all configured accounts")
        all_attachments = service.fetch_all_accounts(
            since_date=since_date,
            dry_run=args.dry_run
        )
        results = {
            "accounts_processed": len(all_attachments),
            "total_attachments": sum(len(atts) for atts in all_attachments.values()),
            "dry_run": args.dry_run,
            "by_account": {
                name: [att.to_dict() for att in atts]
                for name, atts in all_attachments.items()
            }
        }
    
    return results


def handle_test_email_connections(service: EmailFetcherService) -> Dict[str, Any]:
    """Test email account connections.
    
    Args:
        service: Email fetcher service
        
    Returns:
        Test results dictionary
    """
    logger.info("Testing email account connections...")
    connection_results = service.test_connections()
    
    results = {
        "tested_accounts": len(connection_results),
        "successful": sum(1 for success in connection_results.values() if success),
        "failed": sum(1 for success in connection_results.values() if not success),
        "accounts": connection_results
    }
    
    return results


def handle_list_email_folders(
    account_name: str,
    service: EmailFetcherService
) -> Dict[str, Any]:
    """List folders for email account.
    
    Args:
        account_name: Email account name
        service: Email fetcher service
        
    Returns:
        Folder list results
    """
    logger.info(f"Listing folders for account: {account_name}")
    folders = service.list_folders(account_name)
    
    return {
        "account": account_name,
        "folder_count": len(folders),
        "folders": folders
    }


def handle_reset_email_state(
    account_name: str,
    service: EmailFetcherService
) -> Dict[str, Any]:
    """Reset email account state.
    
    Args:
        account_name: Email account name
        service: Email fetcher service
        
    Returns:
        Reset results
    """
    logger.info(f"Resetting state for account: {account_name}")
    success = service.reset_account_state(account_name)
    
    return {
        "account": account_name,
        "reset_successful": success
    }


def handle_email_stats(service: EmailFetcherService) -> Dict[str, Any]:
    """Get email processing statistics.
    
    Args:
        service: Email fetcher service
        
    Returns:
        Statistics dictionary
    """
    logger.info("Getting email processing statistics...")
    return service.get_statistics()


def handle_run_email_fetcher(
    args: argparse.Namespace,
    service: EmailFetcherService
) -> None:
    """Run continuous email fetching.
    
    Args:
        args: Command-line arguments
        service: Email fetcher service
    """
    logger.info("Starting continuous email fetcher...")
    service.run_continuous(
        interval=args.fetch_interval,
        max_iterations=args.max_iterations
    )


def format_output(results: Dict[str, Any], output_format: str) -> str:
    """Format results for output.
    
    Args:
        results: Results dictionary
        output_format: Output format (json or text)
        
    Returns:
        Formatted output string
    """
    if output_format == "json":
        return json.dumps(results, indent=2, ensure_ascii=False, default=str)
    
    # Text format
    lines = []
    
    def format_dict(d: Dict, indent: int = 0) -> None:
        """Recursively format dictionary."""
        prefix = "  " * indent
        for key, value in d.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                format_dict(value, indent + 1)
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}: [{len(value)} items]")
                if value and not isinstance(value[0], (dict, list)):
                    for item in value[:5]:  # Show first 5 items
                        lines.append(f"{prefix}  - {item}")
                    if len(value) > 5:
                        lines.append(f"{prefix}  ... and {len(value) - 5} more")
            else:
                lines.append(f"{prefix}{key}: {value}")
    
    format_dict(results)
    return "\n".join(lines)


def main() -> None:
    """Main CLI entry point."""
    # Parse arguments
    parser = setup_parser()
    args = parser.parse_args()
    
    # Setup logging
    if args.debug:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Load configuration
    if args.config:
        # Load from specific file
        email_settings = load_email_config_from_env()
    else:
        email_settings = load_email_config_from_env()
    
    # Initialize service
    service = EmailFetcherService(email_settings=email_settings)
    
    # Handle commands
    results = None
    
    try:
        if args.fetch_email_attachments:
            results = handle_fetch_email_attachments(args, service)
        
        elif args.test_email_connections:
            results = handle_test_email_connections(service)
        
        elif args.list_email_folders:
            results = handle_list_email_folders(args.list_email_folders, service)
        
        elif args.reset_email_state:
            results = handle_reset_email_state(args.reset_email_state, service)
        
        elif args.email_stats:
            results = handle_email_stats(service)
        
        elif args.run_email_fetcher:
            handle_run_email_fetcher(args, service)
            return  # Continuous mode doesn't return results
        
        else:
            parser.print_help()
            sys.exit(0)
        
        # Format and output results
        if results:
            output = format_output(results, args.output)
            
            if args.output_file:
                with open(args.output_file, "w", encoding="utf-8") as f:
                    f.write(output)
                logger.info(f"Results saved to {args.output_file}")
            else:
                print(output)
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.debug)
        sys.exit(1)


if __name__ == "__main__":
    main()