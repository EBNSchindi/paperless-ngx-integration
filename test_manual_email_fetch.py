#!/usr/bin/env python3
"""Manual integration test for email fetching from all configured accounts.

This test script allows manual verification of email fetching functionality
from GMAIL1, GMAIL2, and IONOS email accounts with actual attachment downloads.

Usage:
    python test_manual_email_fetch.py [--dry-run] [--account ACCOUNT_NAME]
"""

import sys
import os
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.paperless_ngx.application.services.email_fetcher_service import EmailFetcherService
from src.paperless_ngx.infrastructure.email import load_email_config_from_env
from src.paperless_ngx.infrastructure.logging.logger import setup_logging

console = Console()
logger = setup_logging("test_email_fetch")


class EmailFetchTester:
    """Manual email fetch testing utility."""
    
    def __init__(self, dry_run: bool = False):
        """Initialize the email fetch tester.
        
        Args:
            dry_run: If True, don't actually download attachments
        """
        self.dry_run = dry_run
        self.service = None
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "accounts": {}
        }
    
    def setup(self) -> bool:
        """Setup email service and test connections."""
        console.print("\n[bold blue]📧 Email Fetch Test Setup[/bold blue]\n")
        
        try:
            # Load configuration
            settings = load_email_config_from_env()
            console.print(f"✅ Loaded email configuration")
            console.print(f"   Download directory: {settings.email_download_dir}")
            console.print(f"   State file: {settings.email_processed_db}")
            
            # Initialize service
            self.service = EmailFetcherService(email_settings=settings)
            console.print(f"✅ Initialized email service with {len(self.service.clients)} accounts")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Setup failed: {e}[/red]")
            logger.error(f"Setup failed: {e}", exc_info=True)
            return False
    
    def test_connections(self) -> Dict[str, bool]:
        """Test connections to all email accounts."""
        console.print("\n[bold cyan]🔌 Testing Email Connections[/bold cyan]\n")
        
        results = {}
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Testing connections...", total=len(self.service.clients))
            
            for account_name in self.service.clients.keys():
                progress.update(task, description=f"Testing {account_name}...")
                
                try:
                    success = self.service.clients[account_name].test_connection()
                    results[account_name] = success
                    
                    if success:
                        console.print(f"✅ {account_name}: Connection successful")
                    else:
                        console.print(f"❌ {account_name}: Connection failed")
                        
                except Exception as e:
                    console.print(f"❌ {account_name}: Error - {e}")
                    results[account_name] = False
                
                progress.advance(task)
        
        self.test_results["connection_test"] = results
        return results
    
    def fetch_from_account(self, account_name: str, since_days: int = 7) -> Dict:
        """Fetch emails from a specific account.
        
        Args:
            account_name: Name of the email account
            since_days: Fetch emails from the last N days
            
        Returns:
            Dictionary with fetch results
        """
        console.print(f"\n[bold green]📥 Fetching from {account_name}[/bold green]")
        
        since_date = datetime.now() - timedelta(days=since_days)
        console.print(f"   Since: {since_date.strftime('%Y-%m-%d %H:%M')}")
        console.print(f"   Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        
        result = {
            "account": account_name,
            "since_date": since_date.isoformat(),
            "dry_run": self.dry_run,
            "emails_processed": 0,
            "attachments_downloaded": 0,
            "errors": [],
            "attachments": []
        }
        
        try:
            # Fetch attachments
            attachments = self.service.fetch_account(
                account_name=account_name,
                since_date=since_date,
                dry_run=self.dry_run
            )
            
            result["attachments_downloaded"] = len(attachments)
            
            # Display results
            if attachments:
                table = Table(title=f"Attachments from {account_name}")
                table.add_column("Filename", style="cyan")
                table.add_column("Size", justify="right")
                table.add_column("From", style="green")
                table.add_column("Date")
                table.add_column("Path" if not self.dry_run else "Would Save To")
                
                for att in attachments:
                    att_info = {
                        "filename": att.filename,
                        "size": att.size,
                        "from": att.email_sender,
                        "date": att.email_date.isoformat() if att.email_date else "Unknown",
                        "path": str(att.saved_path) if att.saved_path else "N/A"
                    }
                    result["attachments"].append(att_info)
                    
                    table.add_row(
                        att.filename,
                        f"{att.size:,} bytes",
                        att.email_sender or "Unknown",
                        att.email_date.strftime("%Y-%m-%d") if att.email_date else "Unknown",
                        str(att.saved_path) if att.saved_path else "Would save"
                    )
                
                console.print(table)
            else:
                console.print(f"   [yellow]No new attachments found[/yellow]")
            
            # Get statistics
            state = self.service.processing_states.get(account_name)
            if state:
                result["total_processed_all_time"] = state.total_processed
                result["total_attachments_all_time"] = state.total_attachments
                console.print(f"\n   📊 Statistics for {account_name}:")
                console.print(f"      Total emails processed (all time): {state.total_processed}")
                console.print(f"      Total attachments downloaded (all time): {state.total_attachments}")
                console.print(f"      Unique emails tracked: {len(state.processed_uids)}")
            
        except Exception as e:
            error_msg = f"Error fetching from {account_name}: {e}"
            console.print(f"[red]❌ {error_msg}[/red]")
            result["errors"].append(str(e))
            logger.error(error_msg, exc_info=True)
        
        self.test_results["accounts"][account_name] = result
        return result
    
    def fetch_all_accounts(self, since_days: int = 7) -> Dict[str, Dict]:
        """Fetch emails from all configured accounts.
        
        Args:
            since_days: Fetch emails from the last N days
            
        Returns:
            Dictionary mapping account names to results
        """
        console.print("\n[bold magenta]📮 Fetching from All Accounts[/bold magenta]")
        
        all_results = {}
        total_attachments = 0
        
        for account_name in self.service.clients.keys():
            result = self.fetch_from_account(account_name, since_days)
            all_results[account_name] = result
            total_attachments += result["attachments_downloaded"]
        
        # Summary
        console.print("\n[bold yellow]📊 Overall Summary[/bold yellow]")
        
        summary_table = Table(title="Email Fetch Summary")
        summary_table.add_column("Account", style="cyan")
        summary_table.add_column("Status", justify="center")
        summary_table.add_column("Emails", justify="right")
        summary_table.add_column("Attachments", justify="right")
        summary_table.add_column("Errors", justify="right")
        
        for account_name, result in all_results.items():
            status = "✅" if not result["errors"] else "⚠️"
            summary_table.add_row(
                account_name,
                status,
                str(result.get("emails_processed", 0)),
                str(result["attachments_downloaded"]),
                str(len(result["errors"]))
            )
        
        console.print(summary_table)
        console.print(f"\n[green]Total attachments: {total_attachments}[/green]")
        
        return all_results
    
    def display_folder_structure(self):
        """Display the email attachment folder structure."""
        console.print("\n[bold blue]📁 Download Folder Structure[/bold blue]")
        
        download_dir = self.service.settings.email_download_dir
        if not download_dir.exists():
            console.print(f"[yellow]Download directory does not exist yet: {download_dir}[/yellow]")
            return
        
        # Count files by date and type
        file_stats = {}
        total_size = 0
        
        for file_path in download_dir.rglob("*"):
            if file_path.is_file():
                date_dir = file_path.parent.name
                ext = file_path.suffix.lower()
                
                if date_dir not in file_stats:
                    file_stats[date_dir] = {"count": 0, "size": 0, "types": {}}
                
                file_stats[date_dir]["count"] += 1
                file_stats[date_dir]["size"] += file_path.stat().st_size
                file_stats[date_dir]["types"][ext] = file_stats[date_dir]["types"].get(ext, 0) + 1
                total_size += file_path.stat().st_size
        
        if file_stats:
            table = Table(title="Downloaded Attachments by Date")
            table.add_column("Date", style="cyan")
            table.add_column("Files", justify="right")
            table.add_column("Size", justify="right")
            table.add_column("File Types")
            
            for date_dir in sorted(file_stats.keys(), reverse=True):
                stats = file_stats[date_dir]
                types_str = ", ".join(f"{ext}({count})" for ext, count in stats["types"].items())
                table.add_row(
                    date_dir,
                    str(stats["count"]),
                    f"{stats['size'] / 1024 / 1024:.2f} MB",
                    types_str
                )
            
            console.print(table)
            console.print(f"\n[green]Total: {sum(s['count'] for s in file_stats.values())} files, "
                         f"{total_size / 1024 / 1024:.2f} MB[/green]")
        else:
            console.print("[yellow]No files found in download directory[/yellow]")
    
    def save_results(self, filename: str = "test_email_fetch_results.json"):
        """Save test results to JSON file.
        
        Args:
            filename: Output filename
        """
        output_path = Path(filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        console.print(f"\n[green]✅ Results saved to {output_path}[/green]")
    
    def run_interactive(self):
        """Run interactive test menu."""
        while True:
            console.print("\n" + "="*60)
            console.print("[bold cyan]Email Fetch Test Menu[/bold cyan]")
            console.print("="*60)
            console.print("1. Test all connections")
            console.print("2. Fetch from specific account")
            console.print("3. Fetch from all accounts")
            console.print("4. Display folder structure")
            console.print("5. Reset account state")
            console.print("6. Show account statistics")
            console.print("7. List folders for account")
            console.print("8. Save results and exit")
            console.print("9. Exit without saving")
            
            choice = console.input("\n[bold]Select option (1-9): [/bold]")
            
            if choice == "1":
                self.test_connections()
                
            elif choice == "2":
                accounts = list(self.service.clients.keys())
                console.print("\nAvailable accounts:")
                for i, acc in enumerate(accounts, 1):
                    console.print(f"  {i}. {acc}")
                
                acc_choice = console.input("Select account number: ")
                try:
                    account = accounts[int(acc_choice) - 1]
                    days = int(console.input("Fetch emails from last N days (default 7): ") or "7")
                    self.fetch_from_account(account, days)
                except (ValueError, IndexError):
                    console.print("[red]Invalid selection[/red]")
                    
            elif choice == "3":
                days = int(console.input("Fetch emails from last N days (default 7): ") or "7")
                self.fetch_all_accounts(days)
                
            elif choice == "4":
                self.display_folder_structure()
                
            elif choice == "5":
                accounts = list(self.service.clients.keys())
                console.print("\nAvailable accounts:")
                for i, acc in enumerate(accounts, 1):
                    console.print(f"  {i}. {acc}")
                
                acc_choice = console.input("Select account to reset (or 'all'): ")
                if acc_choice.lower() == 'all':
                    for acc in accounts:
                        self.service.reset_account_state(acc)
                        console.print(f"✅ Reset state for {acc}")
                else:
                    try:
                        account = accounts[int(acc_choice) - 1]
                        self.service.reset_account_state(account)
                        console.print(f"✅ Reset state for {account}")
                    except (ValueError, IndexError):
                        console.print("[red]Invalid selection[/red]")
                        
            elif choice == "6":
                stats = self.service.get_statistics()
                console.print(Panel.fit(json.dumps(stats, indent=2, default=str), 
                                       title="Service Statistics"))
                                       
            elif choice == "7":
                accounts = list(self.service.clients.keys())
                console.print("\nAvailable accounts:")
                for i, acc in enumerate(accounts, 1):
                    console.print(f"  {i}. {acc}")
                
                acc_choice = console.input("Select account: ")
                try:
                    account = accounts[int(acc_choice) - 1]
                    folders = self.service.list_folders(account)
                    console.print(f"\nFolders in {account}:")
                    for folder in folders:
                        console.print(f"  - {folder}")
                except (ValueError, IndexError):
                    console.print("[red]Invalid selection[/red]")
                    
            elif choice == "8":
                self.save_results()
                break
                
            elif choice == "9":
                break
                
            else:
                console.print("[red]Invalid option[/red]")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test email fetching from configured accounts")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually download attachments")
    parser.add_argument("--account", help="Test specific account only")
    parser.add_argument("--days", type=int, default=7, help="Fetch emails from last N days")
    parser.add_argument("--interactive", action="store_true", help="Run interactive menu")
    
    args = parser.parse_args()
    
    # Create tester
    tester = EmailFetchTester(dry_run=args.dry_run)
    
    # Setup
    if not tester.setup():
        console.print("[red]Setup failed. Exiting.[/red]")
        return 1
    
    # Run tests
    if args.interactive:
        tester.run_interactive()
    else:
        # Test connections first
        connection_results = tester.test_connections()
        
        if not any(connection_results.values()):
            console.print("[red]No successful connections. Exiting.[/red]")
            return 1
        
        # Fetch emails
        if args.account:
            if args.account in tester.service.clients:
                tester.fetch_from_account(args.account, args.days)
            else:
                console.print(f"[red]Account '{args.account}' not found[/red]")
                return 1
        else:
            tester.fetch_all_accounts(args.days)
        
        # Display folder structure
        tester.display_folder_structure()
        
        # Save results
        tester.save_results()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())