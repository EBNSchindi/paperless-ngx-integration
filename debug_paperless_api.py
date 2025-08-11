#!/usr/bin/env python3
"""
Debug script to test Paperless API connection with detailed diagnostics.
"""

import os
import urllib.request
import urllib.error
import json
from pathlib import Path

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def load_env():
    """Load .env file."""
    env_path = Path(__file__).parent / ".env"
    env_vars = {}
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Important: Remove quotes but keep the value as-is
                value = value.strip()
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                env_vars[key.strip()] = value
    
    return env_vars

def test_api():
    """Test Paperless API with detailed debugging."""
    env = load_env()
    
    api_url = env.get('PAPERLESS_BASE_URL')
    api_token = env.get('PAPERLESS_API_TOKEN')
    
    print(f"{BLUE}=== Paperless API Debug ==={RESET}\n")
    
    # Show configuration
    print(f"API URL: {api_url}")
    print(f"Token present: {'Yes' if api_token else 'No'}")
    
    if api_token:
        # Show token info (masked for security)
        print(f"Token length: {len(api_token)} characters")
        print(f"Token starts with: {api_token[:10]}...")
        print(f"Token ends with: ...{api_token[-10:]}")
        
        # Check if it's still placeholder
        if api_token == "your_paperless_api_token_here":
            print(f"{RED}ERROR: Token is still the placeholder!{RESET}")
            return
    
    print(f"\n{BLUE}Testing different endpoints...{RESET}\n")
    
    # Test different URL variations
    test_urls = [
        (api_url, "Original URL from .env"),
        (api_url.rstrip('/'), "URL without trailing slash"),
        (api_url.rstrip('/api') + '/api', "Ensure /api is at end"),
        (api_url.replace('/api', '') + '/api/documents/', "Direct documents endpoint"),
    ]
    
    headers_variations = [
        {'Authorization': f'Token {api_token}', 'Accept': 'application/json'},
        {'Authorization': f'token {api_token}', 'Accept': 'application/json'},  # lowercase
        {'Authorization': api_token, 'Accept': 'application/json'},  # without "Token"
    ]
    
    for url, description in test_urls:
        print(f"\n{YELLOW}Testing: {description}{RESET}")
        print(f"URL: {url}")
        
        for i, headers in enumerate(headers_variations, 1):
            auth_format = list(headers.keys())[0] + ": " + headers['Authorization'][:20] + "..."
            print(f"\n  Attempt {i}: {auth_format}")
            
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    print(f"  {GREEN}✓ SUCCESS! HTTP {response.status}{RESET}")
                    
                    # Read response
                    content = response.read().decode('utf-8')
                    try:
                        data = json.loads(content)
                        if 'count' in data:
                            print(f"  {GREEN}Documents count: {data['count']}{RESET}")
                        elif 'results' in data:
                            print(f"  {GREEN}Results found: {len(data['results'])}{RESET}")
                        else:
                            print(f"  {GREEN}Response received (keys: {list(data.keys())[:5]}){RESET}")
                    except:
                        print(f"  {GREEN}Response received (non-JSON or partial){RESET}")
                    
                    print(f"\n{GREEN}=== CONNECTION SUCCESSFUL ==={RESET}")
                    print(f"Working URL: {url}")
                    print(f"Working Auth: {auth_format}")
                    return
                    
            except urllib.error.HTTPError as e:
                print(f"  {RED}✗ HTTP {e.code}: {e.reason}{RESET}")
                if e.code == 401:
                    print(f"    Authentication failed - token might be invalid")
                elif e.code == 403:
                    print(f"    Forbidden - token might lack permissions")
                elif e.code == 404:
                    print(f"    Not found - URL might be wrong")
                    
            except urllib.error.URLError as e:
                print(f"  {RED}✗ Connection error: {str(e)}{RESET}")
            except Exception as e:
                print(f"  {RED}✗ Unexpected error: {str(e)}{RESET}")
    
    print(f"\n{RED}=== ALL ATTEMPTS FAILED ==={RESET}")
    print("\nPossible issues:")
    print("1. Token might be invalid or expired")
    print("2. Token might need to be regenerated in Paperless")
    print("3. API might be disabled in Paperless settings")
    print("4. URL format might be incorrect")
    print("\nPlease verify in Paperless NGX:")
    print(f"1. Go to {api_url.replace('/api', '')}/admin/")
    print("2. Check under 'Auth Tokens' that your token exists and is active")
    print("3. Try creating a new token if needed")

if __name__ == "__main__":
    test_api()