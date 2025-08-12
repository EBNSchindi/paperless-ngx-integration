#!/usr/bin/env python3
"""Quick connection test script for all services.

This script can be run directly to test connections to:
- Paperless NGX API
- All 3 email accounts (2x Gmail, 1x IONOS)
- LLM providers (OpenAI primary, Ollama fallback)

Usage:
    python test_all_connections.py
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.paperless_ngx.infrastructure.config.settings import Settings
from src.paperless_ngx.infrastructure.paperless.api_client import PaperlessApiClient
from src.paperless_ngx.infrastructure.email.email_client import EmailClient
from src.paperless_ngx.infrastructure.llm.litellm_client import LiteLLMClient


class ConnectionTester:
    """Test connections to all configured services."""
    
    def __init__(self, verbose: bool = True):
        """Initialize connection tester.
        
        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "paperless": None,
            "email_accounts": {},
            "llm_providers": {},
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0
            }
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp.
        
        Args:
            message: Message to log
            level: Log level (INFO, SUCCESS, WARNING, ERROR)
        """
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            colors = {
                "INFO": "\033[0m",      # Default
                "SUCCESS": "\033[92m",   # Green
                "WARNING": "\033[93m",   # Yellow
                "ERROR": "\033[91m"      # Red
            }
            color = colors.get(level, "\033[0m")
            reset = "\033[0m"
            print(f"[{timestamp}] {color}{level:8}{reset} {message}")
    
    def test_paperless_connection(self) -> bool:
        """Test Paperless NGX API connection.
        
        Returns:
            True if connection successful
        """
        self.log("Testing Paperless NGX API connection...")
        self.results["summary"]["total_tests"] += 1
        
        try:
            settings = Settings()
            client = PaperlessApiClient(settings)
            
            # Try to get documents (even if count is 0)
            documents = client.get_documents(limit=1)
            
            self.results["paperless"] = {
                "status": "connected",
                "base_url": settings.paperless_base_url,
                "document_count": documents.get("count", 0),
                "error": None
            }
            self.results["summary"]["passed"] += 1
            
            self.log(f"✓ Paperless NGX connected (Documents: {documents.get('count', 0)})", "SUCCESS")
            return True
            
        except Exception as e:
            self.results["paperless"] = {
                "status": "failed",
                "base_url": settings.paperless_base_url if 'settings' in locals() else "unknown",
                "error": str(e)
            }
            self.results["summary"]["failed"] += 1
            
            self.log(f"✗ Paperless NGX connection failed: {e}", "ERROR")
            return False
    
    def test_email_accounts(self) -> Dict[str, bool]:
        """Test all email account connections.
        
        Returns:
            Dictionary of account names to connection status
        """
        self.log("Testing email account connections...")
        
        # Define email accounts
        accounts = [
            {
                "name": "Gmail Account 1",
                "server": "imap.gmail.com",
                "port": 993,
                "username": os.getenv("EMAIL_ACCOUNT_1_USERNAME", "ebn.veranstaltungen.consulting@gmail.com"),
                "password": os.getenv("EMAIL_ACCOUNT_1_PASSWORD", ""),
                "use_ssl": True
            },
            {
                "name": "Gmail Account 2",
                "server": "imap.gmail.com",
                "port": 993,
                "username": os.getenv("EMAIL_ACCOUNT_2_USERNAME", "daniel.schindler1992@gmail.com"),
                "password": os.getenv("EMAIL_ACCOUNT_2_PASSWORD", ""),
                "use_ssl": True
            },
            {
                "name": "IONOS Account",
                "server": "imap.ionos.de",
                "port": 993,
                "username": os.getenv("EMAIL_ACCOUNT_3_USERNAME", "info@ettlingen-by-night.de"),
                "password": os.getenv("EMAIL_ACCOUNT_3_PASSWORD", ""),
                "use_ssl": True
            }
        ]
        
        results = {}
        
        for account in accounts:
            self.results["summary"]["total_tests"] += 1
            self.log(f"  Testing {account['name']}...")
            
            if not account["password"]:
                self.results["email_accounts"][account["name"]] = {
                    "status": "skipped",
                    "server": account["server"],
                    "error": "No password configured"
                }
                self.log(f"  ⚠ {account['name']}: Skipped (no password)", "WARNING")
                continue
            
            try:
                client = EmailClient(
                    server=account["server"],
                    port=account["port"],
                    username=account["username"],
                    password=account["password"],
                    use_ssl=account["use_ssl"]
                )
                
                if client.connect():
                    # Try to get message count
                    message_count = client.get_message_count() if hasattr(client, 'get_message_count') else "N/A"
                    
                    self.results["email_accounts"][account["name"]] = {
                        "status": "connected",
                        "server": account["server"],
                        "username": account["username"],
                        "message_count": message_count,
                        "error": None
                    }
                    self.results["summary"]["passed"] += 1
                    results[account["name"]] = True
                    
                    self.log(f"  ✓ {account['name']}: Connected", "SUCCESS")
                else:
                    raise Exception("Connection failed")
                    
            except Exception as e:
                self.results["email_accounts"][account["name"]] = {
                    "status": "failed",
                    "server": account["server"],
                    "username": account["username"],
                    "error": str(e)
                }
                self.results["summary"]["failed"] += 1
                results[account["name"]] = False
                
                self.log(f"  ✗ {account['name']}: {e}", "ERROR")
        
        return results
    
    def test_llm_providers(self) -> Dict[str, bool]:
        """Test LLM provider connections and priority.
        
        Returns:
            Dictionary of provider names to connection status
        """
        self.log("Testing LLM provider connections...")
        
        try:
            settings = Settings()
            client = LiteLLMClient()
            
            # Test health check
            health = client.health_check()
            
            # Check OpenAI (should be primary if configured)
            if "openai" in health:
                self.results["summary"]["total_tests"] += 1
                self.results["llm_providers"]["openai"] = {
                    "status": "available" if health["openai"] else "failed",
                    "model": settings.openai_model,
                    "priority": "primary" if settings.openai_api_key else "not configured"
                }
                
                if health["openai"]:
                    self.results["summary"]["passed"] += 1
                    self.log("  ✓ OpenAI: Available (Primary)", "SUCCESS")
                else:
                    self.results["summary"]["failed"] += 1
                    self.log("  ✗ OpenAI: Failed", "ERROR")
            
            # Check Ollama (fallback)
            if "ollama" in health:
                self.results["summary"]["total_tests"] += 1
                self.results["llm_providers"]["ollama"] = {
                    "status": "available" if health["ollama"] else "failed",
                    "model": settings.ollama_model,
                    "base_url": settings.ollama_base_url,
                    "priority": "fallback" if settings.openai_api_key else "primary"
                }
                
                if health["ollama"]:
                    self.results["summary"]["passed"] += 1
                    self.log("  ✓ Ollama: Available (Fallback)", "SUCCESS")
                else:
                    self.results["summary"]["failed"] += 1
                    self.log("  ✗ Ollama: Failed", "ERROR")
            
            # Test actual LLM call
            self.log("Testing LLM response...")
            self.results["summary"]["total_tests"] += 1
            
            try:
                response, metadata = client.complete_sync(
                    "Respond with 'OK' if you can read this.",
                    max_retries=2
                )
                
                self.results["llm_providers"]["test_response"] = {
                    "status": "success",
                    "provider_used": metadata.get("provider"),
                    "model_used": metadata.get("model"),
                    "response_time": metadata.get("elapsed_time")
                }
                self.results["summary"]["passed"] += 1
                
                self.log(f"  ✓ LLM Response: Success via {metadata.get('provider')}", "SUCCESS")
                
            except Exception as e:
                self.results["llm_providers"]["test_response"] = {
                    "status": "failed",
                    "error": str(e)
                }
                self.results["summary"]["failed"] += 1
                self.log(f"  ✗ LLM Response: {e}", "ERROR")
            
            return health
            
        except Exception as e:
            self.log(f"✗ LLM provider test failed: {e}", "ERROR")
            self.results["llm_providers"]["error"] = str(e)
            return {}
    
    def run_all_tests(self) -> Dict:
        """Run all connection tests.
        
        Returns:
            Complete test results dictionary
        """
        self.log("=" * 60)
        self.log("Starting Paperless NGX Integration Connection Tests")
        self.log("=" * 60)
        
        start_time = time.time()
        
        # Test each service
        self.test_paperless_connection()
        self.log("")
        
        self.test_email_accounts()
        self.log("")
        
        self.test_llm_providers()
        self.log("")
        
        # Calculate summary
        elapsed = time.time() - start_time
        self.results["summary"]["duration"] = f"{elapsed:.2f} seconds"
        self.results["summary"]["success_rate"] = (
            f"{(self.results['summary']['passed'] / self.results['summary']['total_tests'] * 100):.1f}%"
            if self.results['summary']['total_tests'] > 0 else "0%"
        )
        
        # Print summary
        self.log("=" * 60)
        self.log("Test Summary")
        self.log("=" * 60)
        self.log(f"Total Tests: {self.results['summary']['total_tests']}")
        self.log(f"Passed: {self.results['summary']['passed']}", "SUCCESS")
        self.log(f"Failed: {self.results['summary']['failed']}", "ERROR" if self.results['summary']['failed'] > 0 else "INFO")
        self.log(f"Success Rate: {self.results['summary']['success_rate']}")
        self.log(f"Duration: {self.results['summary']['duration']}")
        
        return self.results
    
    def save_results(self, filepath: str = "connection_test_results.json"):
        """Save test results to JSON file.
        
        Args:
            filepath: Path to save results
        """
        try:
            with open(filepath, "w") as f:
                json.dump(self.results, f, indent=2)
            self.log(f"Results saved to {filepath}", "SUCCESS")
        except Exception as e:
            self.log(f"Failed to save results: {e}", "ERROR")


def main():
    """Main entry point for connection testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test all Paperless NGX integration connections")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress verbose output")
    parser.add_argument("--save", "-s", help="Save results to JSON file")
    parser.add_argument("--env", "-e", help="Path to .env file", default=".env")
    
    args = parser.parse_args()
    
    # Load environment if specified
    if args.env and Path(args.env).exists():
        from dotenv import load_dotenv
        load_dotenv(args.env)
        if not args.quiet:
            print(f"Loaded environment from {args.env}")
    
    # Run tests
    tester = ConnectionTester(verbose=not args.quiet)
    results = tester.run_all_tests()
    
    # Save results if requested
    if args.save:
        tester.save_results(args.save)
    
    # Exit with appropriate code
    sys.exit(0 if results["summary"]["failed"] == 0 else 1)


if __name__ == "__main__":
    main()