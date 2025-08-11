#!/usr/bin/env python3
"""
Comprehensive connection test script for Paperless NGX Integration.

Tests all configured endpoints and services:
- Paperless NGX API
- Ollama LLM
- OpenAI (if configured)
- Email accounts
"""

import sys
import os
from pathlib import Path
import json
import time
from typing import Dict, Any, List
import requests
from datetime import datetime

# Add src to path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import after path setup
from paperless_ngx.infrastructure.config.settings import get_settings
from paperless_ngx.infrastructure.llm.litellm_client import get_llm_client
from paperless_ngx.application.services.email_fetcher_service import EmailFetcherService
from paperless_ngx.infrastructure.email.email_config import load_email_config_from_env

# Try to use rich for better output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import print as rprint
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    console = None


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_colored(message: str, color: str = Colors.RESET, bold: bool = False):
    """Print colored message to console."""
    if RICH_AVAILABLE and console:
        if color == Colors.GREEN:
            console.print(f"[green]{message}[/green]", style="bold" if bold else "")
        elif color == Colors.RED:
            console.print(f"[red]{message}[/red]", style="bold" if bold else "")
        elif color == Colors.YELLOW:
            console.print(f"[yellow]{message}[/yellow]", style="bold" if bold else "")
        elif color == Colors.BLUE:
            console.print(f"[blue]{message}[/blue]", style="bold" if bold else "")
        else:
            console.print(message, style="bold" if bold else "")
    else:
        prefix = Colors.BOLD if bold else ""
        print(f"{prefix}{color}{message}{Colors.RESET}")


def print_header(title: str):
    """Print section header."""
    if RICH_AVAILABLE and console:
        console.print(Panel.fit(title, style="bold cyan"))
    else:
        print_colored(f"\n{'=' * 60}", Colors.CYAN)
        print_colored(f"  {title}", Colors.CYAN, bold=True)
        print_colored(f"{'=' * 60}", Colors.CYAN)


def test_paperless_api(settings) -> Dict[str, Any]:
    """Test Paperless NGX API connection."""
    print_header("Testing Paperless NGX API")
    
    result = {
        "service": "Paperless NGX API",
        "status": "unknown",
        "details": {},
        "error": None
    }
    
    try:
        # Get API URL and token
        api_url = settings.paperless_base_url
        api_token = settings.get_secret_value("paperless_api_token")
        
        if not api_token:
            raise ValueError("No Paperless API token configured")
        
        print_colored(f"API URL: {api_url}", Colors.BLUE)
        
        # Test API connection
        headers = {
            "Authorization": f"Token {api_token}",
            "Accept": "application/json"
        }
        
        # Try to get API status
        response = requests.get(
            f"{api_url}/documents/",
            headers=headers,
            timeout=(settings.paperless_timeout_connect, settings.paperless_timeout_read),
            params={"page_size": 1}  # Just get one document to test
        )
        
        if response.status_code == 200:
            data = response.json()
            result["status"] = "success"
            result["details"] = {
                "url": api_url,
                "total_documents": data.get("count", 0),
                "response_time": f"{response.elapsed.total_seconds():.2f}s"
            }
            print_colored(f"✓ Connected successfully", Colors.GREEN)
            print_colored(f"  Total documents: {data.get('count', 0)}", Colors.GREEN)
            print_colored(f"  Response time: {response.elapsed.total_seconds():.2f}s", Colors.GREEN)
        else:
            result["status"] = "failed"
            result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
            print_colored(f"✗ Connection failed: HTTP {response.status_code}", Colors.RED)
            
    except requests.exceptions.ConnectTimeout:
        result["status"] = "failed"
        result["error"] = "Connection timeout"
        print_colored(f"✗ Connection timeout", Colors.RED)
    except requests.exceptions.ConnectionError as e:
        result["status"] = "failed"
        result["error"] = f"Connection error: {str(e)}"
        print_colored(f"✗ Connection error: {str(e)[:100]}", Colors.RED)
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        print_colored(f"✗ Error: {str(e)}", Colors.RED)
    
    return result


def test_ollama(settings) -> Dict[str, Any]:
    """Test Ollama LLM connection."""
    print_header("Testing Ollama LLM")
    
    result = {
        "service": "Ollama",
        "status": "unknown",
        "details": {},
        "error": None
    }
    
    try:
        if not settings.ollama_enabled:
            result["status"] = "disabled"
            print_colored("⊘ Ollama is disabled in configuration", Colors.YELLOW)
            return result
        
        print_colored(f"Ollama URL: {settings.ollama_base_url}", Colors.BLUE)
        print_colored(f"Model: {settings.ollama_model}", Colors.BLUE)
        
        # Get LLM client and test
        llm_client = get_llm_client()
        health = llm_client.health_check()
        
        if health.get("ollama", False):
            result["status"] = "success"
            result["details"] = {
                "url": settings.ollama_base_url,
                "model": settings.ollama_model,
                "healthy": True
            }
            
            # Try a simple completion test
            print_colored("Testing completion...", Colors.BLUE)
            start_time = time.time()
            response, metadata = llm_client.complete_sync(
                prompt="Respond with 'OK' only",
                max_retries=1
            )
            elapsed = time.time() - start_time
            
            result["details"]["test_response"] = response.strip()
            result["details"]["response_time"] = f"{elapsed:.2f}s"
            
            print_colored(f"✓ Ollama is working", Colors.GREEN)
            print_colored(f"  Response: {response.strip()}", Colors.GREEN)
            print_colored(f"  Response time: {elapsed:.2f}s", Colors.GREEN)
        else:
            result["status"] = "failed"
            result["error"] = "Health check failed"
            print_colored(f"✗ Ollama health check failed", Colors.RED)
            
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        print_colored(f"✗ Error: {str(e)}", Colors.RED)
    
    return result


def test_openai(settings) -> Dict[str, Any]:
    """Test OpenAI connection."""
    print_header("Testing OpenAI (Fallback)")
    
    result = {
        "service": "OpenAI",
        "status": "unknown",
        "details": {},
        "error": None
    }
    
    try:
        if not settings.openai_api_key:
            result["status"] = "not_configured"
            print_colored("⊘ OpenAI API key not configured", Colors.YELLOW)
            return result
        
        print_colored(f"Model: {settings.openai_model}", Colors.BLUE)
        
        # Get LLM client and test
        llm_client = get_llm_client()
        health = llm_client.health_check()
        
        if health.get("openai", False):
            result["status"] = "success"
            result["details"] = {
                "model": settings.openai_model,
                "healthy": True
            }
            print_colored(f"✓ OpenAI is configured and working", Colors.GREEN)
        else:
            result["status"] = "failed"
            result["error"] = "Health check failed"
            print_colored(f"✗ OpenAI health check failed", Colors.RED)
            
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        print_colored(f"✗ Error: {str(e)}", Colors.RED)
    
    return result


def test_email_accounts(settings) -> List[Dict[str, Any]]:
    """Test email account connections."""
    print_header("Testing Email Accounts")
    
    results = []
    
    try:
        # Load email configuration
        email_config = load_email_config_from_env()
        
        if not email_config or not email_config.accounts:
            print_colored("⊘ No email accounts configured", Colors.YELLOW)
            return [{
                "service": "Email Accounts",
                "status": "not_configured",
                "error": "No email accounts found in configuration"
            }]
        
        print_colored(f"Found {len(email_config.accounts)} email account(s)", Colors.BLUE)
        
        # Initialize email service
        email_service = EmailFetcherService(email_settings=email_config)
        
        # Test each account
        for account_name, account_config in email_config.accounts.items():
            print_colored(f"\nTesting: {account_name}", Colors.CYAN)
            print_colored(f"  Server: {account_config.server}", Colors.BLUE)
            print_colored(f"  Username: {account_config.username}", Colors.BLUE)
            
            account_result = {
                "service": f"Email: {account_name}",
                "status": "unknown",
                "details": {
                    "server": account_config.server,
                    "username": account_config.username
                },
                "error": None
            }
            
            # Test connection
            connection_results = email_service.test_connections()
            
            if connection_results.get(account_name, False):
                account_result["status"] = "success"
                print_colored(f"  ✓ Connected successfully", Colors.GREEN)
                
                # Try to list folders
                try:
                    folders = email_service.list_folders(account_name)
                    account_result["details"]["folders"] = folders
                    account_result["details"]["folder_count"] = len(folders)
                    
                    print_colored(f"  Found {len(folders)} folder(s):", Colors.GREEN)
                    for folder in folders[:10]:  # Show first 10 folders
                        print_colored(f"    - {folder}", Colors.GREEN)
                    if len(folders) > 10:
                        print_colored(f"    ... and {len(folders) - 10} more", Colors.GREEN)
                        
                except Exception as e:
                    print_colored(f"  ⚠ Could not list folders: {str(e)}", Colors.YELLOW)
                    account_result["details"]["folder_error"] = str(e)
            else:
                account_result["status"] = "failed"
                account_result["error"] = "Connection failed"
                print_colored(f"  ✗ Connection failed", Colors.RED)
            
            results.append(account_result)
            
    except Exception as e:
        results.append({
            "service": "Email Service",
            "status": "failed",
            "error": str(e)
        })
        print_colored(f"✗ Error initializing email service: {str(e)}", Colors.RED)
    
    return results


def generate_summary(results: List[Dict[str, Any]]):
    """Generate and print test summary."""
    print_header("Test Summary")
    
    if RICH_AVAILABLE and console:
        # Create rich table
        table = Table(title="Connection Test Results")
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("Status", style="bold")
        table.add_column("Details", style="dim")
        
        for result in results:
            status = result["status"]
            if status == "success":
                status_str = "[green]✓ Success[/green]"
            elif status == "failed":
                status_str = "[red]✗ Failed[/red]"
            elif status == "disabled" or status == "not_configured":
                status_str = "[yellow]⊘ Not Available[/yellow]"
            else:
                status_str = "[dim]Unknown[/dim]"
            
            details = ""
            if result.get("error"):
                details = f"[red]{result['error'][:50]}[/red]"
            elif result.get("details"):
                if "folder_count" in result["details"]:
                    details = f"{result['details'].get('folder_count', 0)} folders"
                elif "total_documents" in result["details"]:
                    details = f"{result['details'].get('total_documents', 0)} documents"
                elif "healthy" in result["details"]:
                    details = "Healthy"
            
            table.add_row(result["service"], status_str, details)
        
        console.print(table)
    else:
        # Simple text output
        print("\n" + "=" * 60)
        for result in results:
            status = result["status"]
            if status == "success":
                symbol = "✓"
                color = Colors.GREEN
            elif status == "failed":
                symbol = "✗"
                color = Colors.RED
            else:
                symbol = "⊘"
                color = Colors.YELLOW
            
            print_colored(f"{symbol} {result['service']}: {status}", color)
            if result.get("error"):
                print_colored(f"  Error: {result['error']}", Colors.RED)
    
    # Statistics
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    other_count = len(results) - success_count - failed_count
    
    print("\nStatistics:")
    print_colored(f"  Successful: {success_count}", Colors.GREEN)
    if failed_count > 0:
        print_colored(f"  Failed: {failed_count}", Colors.RED)
    if other_count > 0:
        print_colored(f"  Not configured/disabled: {other_count}", Colors.YELLOW)
    
    # Overall status
    if failed_count == 0 and success_count > 0:
        print_colored("\n✓ All configured services are working!", Colors.GREEN, bold=True)
    elif failed_count > 0:
        print_colored(f"\n⚠ {failed_count} service(s) failed. Please check configuration.", Colors.RED, bold=True)
    else:
        print_colored("\n⊘ No services are properly configured.", Colors.YELLOW, bold=True)


def main():
    """Main test execution."""
    print_colored("\n" + "=" * 60, Colors.CYAN, bold=True)
    print_colored("  Paperless NGX Integration - Connection Test", Colors.CYAN, bold=True)
    print_colored("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"), Colors.CYAN)
    print_colored("=" * 60 + "\n", Colors.CYAN, bold=True)
    
    try:
        # Load settings
        print_colored("Loading configuration...", Colors.BLUE)
        settings = get_settings()
        print_colored("✓ Configuration loaded\n", Colors.GREEN)
        
        # Collect all test results
        all_results = []
        
        # Test Paperless API
        all_results.append(test_paperless_api(settings))
        
        # Test LLMs
        all_results.append(test_ollama(settings))
        all_results.append(test_openai(settings))
        
        # Test Email accounts
        email_results = test_email_accounts(settings)
        all_results.extend(email_results)
        
        # Generate summary
        generate_summary(all_results)
        
        # Save results to file
        results_file = project_root / "test_results.json"
        with open(results_file, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "results": all_results
            }, f, indent=2, default=str)
        print_colored(f"\nDetailed results saved to: {results_file}", Colors.BLUE)
        
    except Exception as e:
        print_colored(f"\n✗ Critical error: {str(e)}", Colors.RED, bold=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()