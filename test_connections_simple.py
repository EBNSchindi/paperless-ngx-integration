#!/usr/bin/env python3
"""
Simple connection test script without external dependencies.
Tests basic connectivity to configured services.
"""

import json
import os
import socket
import ssl
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from pathlib import Path

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_colored(message, color=RESET, bold=False):
    """Print colored message."""
    prefix = BOLD if bold else ""
    print(f"{prefix}{color}{message}{RESET}")


def print_header(title):
    """Print section header."""
    print_colored(f"\n{'=' * 60}", CYAN)
    print_colored(f"  {title}", CYAN, bold=True)
    print_colored(f"{'=' * 60}", CYAN)


def load_env():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent / ".env"
    env_vars = {}
    
    if not env_path.exists():
        print_colored("✗ .env file not found!", RED)
        return env_vars
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes if present
                value = value.strip().strip('"').strip("'")
                env_vars[key.strip()] = value
                os.environ[key.strip()] = value
    
    return env_vars


def test_url_connection(url, headers=None, timeout=10):
    """Test HTTP/HTTPS connection to a URL."""
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return True, response.status, response.read(100).decode('utf-8', errors='ignore')
    except urllib.error.HTTPError as e:
        return False, e.code, str(e)
    except urllib.error.URLError as e:
        return False, None, str(e)
    except Exception as e:
        return False, None, str(e)


def test_socket_connection(host, port, timeout=10):
    """Test TCP socket connection."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        return False


def test_paperless_api(env_vars):
    """Test Paperless NGX API."""
    print_header("Testing Paperless NGX API")
    
    api_url = env_vars.get('PAPERLESS_BASE_URL')
    api_token = env_vars.get('PAPERLESS_API_TOKEN')
    
    if not api_url or not api_token:
        print_colored("✗ Missing PAPERLESS_BASE_URL or PAPERLESS_API_TOKEN", RED)
        return False
    
    print_colored(f"API URL: {api_url}", BLUE)
    
    # Test connection
    headers = {
        'Authorization': f'Token {api_token}',
        'Accept': 'application/json'
    }
    
    test_url = f"{api_url}/documents/?page_size=1"
    success, status, content = test_url_connection(test_url, headers)
    
    if success:
        print_colored(f"✓ Connected successfully (HTTP {status})", GREEN)
        try:
            # Try to parse JSON response
            data = json.loads(content) if len(content) > 2 else {}
            if 'count' in str(content).lower():
                print_colored(f"  API is responding with valid JSON", GREEN)
        except:
            pass
        return True
    else:
        print_colored(f"✗ Connection failed: {content}", RED)
        if status:
            print_colored(f"  HTTP Status: {status}", RED)
        return False


def test_ollama(env_vars):
    """Test Ollama connection."""
    print_header("Testing Ollama LLM")
    
    enabled = env_vars.get('OLLAMA_ENABLED', 'true').lower() == 'true'
    if not enabled:
        print_colored("⊘ Ollama is disabled", YELLOW)
        return None
    
    ollama_url = env_vars.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    model = env_vars.get('OLLAMA_MODEL', 'llama3.1:8b')
    
    print_colored(f"Ollama URL: {ollama_url}", BLUE)
    print_colored(f"Model: {model}", BLUE)
    
    # Parse URL to get host and port
    from urllib.parse import urlparse
    parsed = urlparse(ollama_url)
    host = parsed.hostname or 'localhost'
    port = parsed.port or 11434
    
    # Test socket connection
    if test_socket_connection(host, port, timeout=5):
        print_colored(f"✓ Ollama server is reachable at {host}:{port}", GREEN)
        
        # Try API endpoint
        test_url = f"{ollama_url}/api/tags"
        success, status, content = test_url_connection(test_url, timeout=5)
        if success:
            print_colored(f"  API endpoint is responding", GREEN)
        return True
    else:
        print_colored(f"✗ Cannot connect to Ollama at {host}:{port}", RED)
        print_colored(f"  Make sure Ollama is running: ollama serve", YELLOW)
        return False


def test_openai(env_vars):
    """Test OpenAI configuration."""
    print_header("Testing OpenAI (Fallback)")
    
    api_key = env_vars.get('OPENAI_API_KEY')
    
    if not api_key or api_key.startswith('sk-...'):
        print_colored("⊘ OpenAI API key not configured or placeholder", YELLOW)
        return None
    
    print_colored(f"✓ OpenAI API key is configured", GREEN)
    print_colored(f"  Key starts with: {api_key[:7]}...", BLUE)
    
    # Test OpenAI API endpoint (without making actual request to save credits)
    if test_socket_connection('api.openai.com', 443, timeout=5):
        print_colored(f"  OpenAI API is reachable", GREEN)
        return True
    else:
        print_colored(f"  Warning: Cannot reach OpenAI API", YELLOW)
        return False


def test_email_accounts(env_vars):
    """Test email account connections."""
    print_header("Testing Email Accounts")
    
    results = []
    
    # Check for GMAIL1, GMAIL2, etc. pattern
    for i in range(1, 10):  # Check up to 9 Gmail accounts
        email_key = f"GMAIL{i}_EMAIL"
        password_key = f"GMAIL{i}_APP_PASSWORD"
        
        email = env_vars.get(email_key)
        password = env_vars.get(password_key)
        
        if not email:
            continue
        
        # Gmail server settings
        server = "imap.gmail.com"
        port = 993
        use_ssl = True
        
        print_colored(f"\nTesting: Gmail Account {i}", CYAN)
        print_colored(f"  Email: {email}", BLUE)
        print_colored(f"  Server: {server}:{port}", BLUE)
        print_colored(f"  SSL: {use_ssl}", BLUE)
        
        if not password or password == "your_app_specific_password_here":
            print_colored(f"  ✗ App password not configured or placeholder", RED)
            results.append(False)
        else:
            # Test connection
            if test_socket_connection(server, port, timeout=10):
                print_colored(f"  ✓ Server is reachable", GREEN)
                
                # Test SSL
                try:
                    context = ssl.create_default_context()
                    with socket.create_connection((server, port), timeout=10) as sock:
                        with context.wrap_socket(sock, server_hostname=server) as ssock:
                            print_colored(f"  ✓ SSL connection successful", GREEN)
                            print_colored(f"  ✓ Ready for IMAP authentication", GREEN)
                            results.append(True)
                except Exception as e:
                    print_colored(f"  ✗ SSL connection failed: {str(e)[:50]}", RED)
                    results.append(False)
            else:
                print_colored(f"  ✗ Cannot connect to {server}:{port}", RED)
                results.append(False)
    
    # Check for IONOS account
    ionos_email = env_vars.get("IONOS_EMAIL")
    ionos_password = env_vars.get("IONOS_PASSWORD")
    
    if ionos_email:
        # IONOS server settings
        server = "imap.ionos.de"
        port = 993
        use_ssl = True
        
        print_colored(f"\nTesting: IONOS Account", CYAN)
        print_colored(f"  Email: {ionos_email}", BLUE)
        print_colored(f"  Server: {server}:{port}", BLUE)
        print_colored(f"  SSL: {use_ssl}", BLUE)
        
        if not ionos_password or ionos_password == "your_ionos_password_here":
            print_colored(f"  ✗ Password not configured or placeholder", RED)
            results.append(False)
        else:
            # Test connection
            if test_socket_connection(server, port, timeout=10):
                print_colored(f"  ✓ Server is reachable", GREEN)
                
                # Test SSL
                try:
                    context = ssl.create_default_context()
                    with socket.create_connection((server, port), timeout=10) as sock:
                        with context.wrap_socket(sock, server_hostname=server) as ssock:
                            print_colored(f"  ✓ SSL connection successful", GREEN)
                            print_colored(f"  ✓ Ready for IMAP authentication", GREEN)
                            results.append(True)
                except Exception as e:
                    print_colored(f"  ✗ SSL connection failed: {str(e)[:50]}", RED)
                    results.append(False)
            else:
                print_colored(f"  ✗ Cannot connect to {server}:{port}", RED)
                results.append(False)
    
    if not results:
        print_colored("⊘ No email accounts configured", YELLOW)
        return None
    
    return results


def main():
    """Main test execution."""
    print_colored("\n" + "=" * 60, CYAN, bold=True)
    print_colored("  Paperless NGX - Simple Connection Test", CYAN, bold=True)
    print_colored("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"), CYAN)
    print_colored("=" * 60 + "\n", CYAN, bold=True)
    
    # Load environment variables
    print_colored("Loading .env configuration...", BLUE)
    env_vars = load_env()
    
    if not env_vars:
        print_colored("✗ No configuration found. Please create .env file", RED)
        sys.exit(1)
    
    print_colored(f"✓ Loaded {len(env_vars)} environment variables\n", GREEN)
    
    # Run tests
    results = {
        'paperless': test_paperless_api(env_vars),
        'ollama': test_ollama(env_vars),
        'openai': test_openai(env_vars),
        'email': test_email_accounts(env_vars)
    }
    
    # Summary
    print_header("Test Summary")
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for service, result in results.items():
        if result is True:
            print_colored(f"✓ {service.capitalize()}: Working", GREEN)
            success_count += 1
        elif result is False:
            print_colored(f"✗ {service.capitalize()}: Failed", RED)
            failed_count += 1
        elif result is None:
            print_colored(f"⊘ {service.capitalize()}: Not configured/disabled", YELLOW)
            skipped_count += 1
        elif isinstance(result, list):
            # Email accounts
            working = sum(1 for r in result if r)
            total = len(result)
            if working == total:
                print_colored(f"✓ Email: All {total} account(s) working", GREEN)
                success_count += 1
            elif working > 0:
                print_colored(f"⚠ Email: {working}/{total} account(s) working", YELLOW)
                success_count += 1
            else:
                print_colored(f"✗ Email: All accounts failed", RED)
                failed_count += 1
    
    print_colored(f"\nStatistics:", CYAN)
    print_colored(f"  Successful: {success_count}", GREEN)
    if failed_count > 0:
        print_colored(f"  Failed: {failed_count}", RED)
    if skipped_count > 0:
        print_colored(f"  Not configured: {skipped_count}", YELLOW)
    
    if failed_count == 0 and success_count > 0:
        print_colored("\n✓ All configured services are reachable!", GREEN, bold=True)
    elif failed_count > 0:
        print_colored(f"\n⚠ {failed_count} service(s) failed. Check configuration.", RED, bold=True)
    else:
        print_colored("\n⊘ No services properly configured.", YELLOW, bold=True)
    
    # Save results
    results_file = Path(__file__).parent / "test_results_simple.json"
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': {k: str(v) for k, v in results.items()}
        }, f, indent=2)
    print_colored(f"\nResults saved to: {results_file}", BLUE)


if __name__ == "__main__":
    main()