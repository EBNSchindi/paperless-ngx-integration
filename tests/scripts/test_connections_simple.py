#!/usr/bin/env python3
"""
Einfacher Verbindungstest für Paperless NGX Integration.
Testet alle konfigurierten Verbindungen ohne externe Dependencies.
"""

import os
import sys
import json
import imaplib
import ssl
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import urllib.request
import urllib.error

# Farben für Terminal-Ausgabe
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Druckt eine formatierte Überschrift."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_test(name: str, success: bool, message: str = ""):
    """Druckt ein Testergebnis."""
    status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if success else f"{Colors.RED}✗ FAIL{Colors.RESET}"
    print(f"  {status} {name}")
    if message:
        print(f"        {Colors.YELLOW}{message}{Colors.RESET}")

def load_env_file(env_path: Path) -> Dict[str, str]:
    """Lädt Umgebungsvariablen aus .env Datei."""
    env_vars = {}
    if not env_path.exists():
        print(f"{Colors.RED}FEHLER: .env Datei nicht gefunden!{Colors.RESET}")
        print(f"Bitte erstellen Sie eine .env Datei basierend auf .env.example")
        return env_vars
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    env_vars[key.strip()] = value
    
    return env_vars

def test_paperless_connection(env: Dict[str, str]) -> Dict[str, Any]:
    """Testet die Verbindung zu Paperless NGX."""
    result = {
        'name': 'Paperless NGX API',
        'status': False,
        'message': '',
        'details': {}
    }
    
    base_url = env.get('PAPERLESS_BASE_URL', '').rstrip('/')
    api_token = env.get('PAPERLESS_API_TOKEN', '')
    
    if not base_url or not api_token:
        result['message'] = "URL oder Token fehlt in .env"
        return result
    
    try:
        # Test API endpoint
        test_url = f"{base_url}/documents/"
        req = urllib.request.Request(test_url)
        req.add_header('Authorization', f'Token {api_token}')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                result['status'] = True
                result['message'] = f"Verbunden mit {base_url}"
                # Try to parse response
                try:
                    data = json.loads(response.read().decode())
                    result['details']['document_count'] = data.get('count', 0)
                except:
                    pass
    except urllib.error.HTTPError as e:
        result['message'] = f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        result['message'] = f"Verbindungsfehler: {e.reason}"
    except Exception as e:
        result['message'] = str(e)
    
    return result

def test_email_account(env: Dict[str, str], account_num: int) -> Dict[str, Any]:
    """Testet eine Email-Verbindung."""
    prefix = f"EMAIL_ACCOUNT_{account_num}_"
    
    result = {
        'name': env.get(f'{prefix}NAME', f'Email Account {account_num}'),
        'status': False,
        'message': '',
        'details': {}
    }
    
    server = env.get(f'{prefix}SERVER', '')
    port = int(env.get(f'{prefix}PORT', '993'))
    username = env.get(f'{prefix}USERNAME', '')
    password = env.get(f'{prefix}PASSWORD', '')
    
    if not all([server, username, password]):
        result['message'] = "Konfiguration unvollständig"
        return result
    
    result['details']['server'] = server
    result['details']['username'] = username
    
    try:
        # Create SSL context
        context = ssl.create_default_context()
        
        # Connect to IMAP server
        imap = imaplib.IMAP4_SSL(server, port, ssl_context=context)
        
        # Try to login
        imap.login(username, password)
        
        # Get folder list to verify connection
        status, folders = imap.list()
        if status == 'OK':
            result['status'] = True
            result['message'] = f"Erfolgreich verbunden"
            result['details']['folder_count'] = len(folders)
            
            # Check for INBOX
            status, data = imap.select('INBOX', readonly=True)
            if status == 'OK':
                result['details']['inbox_messages'] = int(data[0])
        
        imap.logout()
        
    except imaplib.IMAP4.error as e:
        result['message'] = f"IMAP Fehler: {str(e)}"
        if 'AUTHENTICATIONFAILED' in str(e):
            if 'gmail' in server.lower():
                result['message'] += " (App-Passwort erforderlich!)"
    except Exception as e:
        result['message'] = f"Verbindungsfehler: {str(e)}"
    
    return result

def test_llm_provider(env: Dict[str, str]) -> Dict[str, Any]:
    """Testet die LLM Provider Konfiguration."""
    result = {
        'name': 'LLM Provider',
        'status': False,
        'message': '',
        'details': {}
    }
    
    provider = env.get('LLM_PROVIDER', 'openai').lower()
    result['details']['configured_provider'] = provider
    
    if provider == 'openai':
        api_key = env.get('OPENAI_API_KEY', '')
        model = env.get('OPENAI_MODEL', 'gpt-3.5-turbo')
        
        if not api_key or api_key.startswith('sk-your'):
            result['message'] = "OpenAI API Key nicht konfiguriert"
            result['details']['fallback'] = 'Ollama wird als Fallback verwendet'
        else:
            # Basic validation of API key format
            if api_key.startswith('sk-') and len(api_key) > 20:
                result['status'] = True
                result['message'] = f"OpenAI konfiguriert (Modell: {model})"
                result['details']['priority'] = 'OpenAI → Ollama (Fallback)'
            else:
                result['message'] = "OpenAI API Key Format ungültig"
    
    elif provider == 'ollama':
        base_url = env.get('OLLAMA_BASE_URL', 'http://localhost:11434')
        model = env.get('OLLAMA_MODEL', 'llama3.1:8b')
        
        # Try to connect to Ollama
        try:
            req = urllib.request.Request(f"{base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    result['status'] = True
                    result['message'] = f"Ollama läuft (Modell: {model})"
                    result['details']['priority'] = 'Ollama (lokal)'
        except:
            result['message'] = "Ollama nicht erreichbar (ist 'ollama serve' gestartet?)"
    
    else:
        result['message'] = f"Unbekannter Provider: {provider}"
    
    return result

def test_tag_matching_config(env: Dict[str, str]) -> Dict[str, Any]:
    """Testet die Tag-Matching Konfiguration."""
    result = {
        'name': 'Tag-Matching Konfiguration',
        'status': True,
        'message': '',
        'details': {}
    }
    
    threshold = float(env.get('TAG_SIMILARITY_THRESHOLD', '0.95'))
    prevent_false = env.get('ENABLE_FALSE_POSITIVE_PREVENTION', 'true').lower() == 'true'
    
    result['details']['similarity_threshold'] = f"{threshold:.0%}"
    result['details']['false_positive_prevention'] = prevent_false
    
    if threshold < 0.95:
        result['status'] = False
        result['message'] = f"Warnung: Threshold {threshold:.0%} < 95% kann zu falschen Vereinheitlichungen führen!"
    else:
        result['message'] = f"Korrekt konfiguriert (95% Threshold)"
    
    # Check business context
    business_name = env.get('BUSINESS_NAME', '')
    if 'Daniel Schindler' in business_name or 'EBN' in business_name:
        result['details']['business_context'] = '✓ Daniel/EBN als Empfänger konfiguriert'
    else:
        result['details']['business_context'] = '⚠ Business-Kontext prüfen'
    
    return result

def main():
    """Hauptfunktion für Verbindungstests."""
    print_header("Paperless NGX Integration - Verbindungstest")
    
    # Load environment
    env_path = Path('.env')
    env = load_env_file(env_path)
    
    if not env:
        sys.exit(1)
    
    print(f"Umgebung geladen: {len(env)} Variablen\n")
    
    all_results = []
    
    # Test Paperless
    print(f"{Colors.BOLD}1. Paperless NGX Verbindung{Colors.RESET}")
    result = test_paperless_connection(env)
    print_test(result['name'], result['status'], result['message'])
    if result['details'].get('document_count') is not None:
        print(f"        Dokumente in Paperless: {result['details']['document_count']}")
    all_results.append(result)
    
    # Test LLM Provider Priority
    print(f"\n{Colors.BOLD}2. LLM Provider Priorität{Colors.RESET}")
    result = test_llm_provider(env)
    print_test(result['name'], result['status'], result['message'])
    if result['details'].get('priority'):
        print(f"        Priorität: {result['details']['priority']}")
    all_results.append(result)
    
    # Test Email Accounts
    print(f"\n{Colors.BOLD}3. Email Konten (3 konfiguriert){Colors.RESET}")
    for i in range(1, 4):
        result = test_email_account(env, i)
        if result['name'] != f'Email Account {i}':  # Only test if configured
            print_test(result['name'], result['status'], result['message'])
            if result['status'] and result['details'].get('inbox_messages') is not None:
                print(f"        Nachrichten in INBOX: {result['details']['inbox_messages']}")
            all_results.append(result)
    
    # Test Tag Matching Config
    print(f"\n{Colors.BOLD}4. Tag-Matching Einstellungen{Colors.RESET}")
    result = test_tag_matching_config(env)
    print_test(result['name'], result['status'], result['message'])
    for key, value in result['details'].items():
        print(f"        {key}: {value}")
    all_results.append(result)
    
    # Summary
    print_header("Zusammenfassung")
    
    passed = sum(1 for r in all_results if r['status'])
    failed = len(all_results) - passed
    
    print(f"Getestet: {len(all_results)} Verbindungen")
    print(f"{Colors.GREEN}Erfolgreich: {passed}{Colors.RESET}")
    print(f"{Colors.RED}Fehlgeschlagen: {failed}{Colors.RESET}")
    
    if failed > 0:
        print(f"\n{Colors.YELLOW}Fehlgeschlagene Tests:{Colors.RESET}")
        for r in all_results:
            if not r['status']:
                print(f"  - {r['name']}: {r['message']}")
    
    # Check LLM priority specifically
    print(f"\n{Colors.BOLD}LLM Provider Priorität:{Colors.RESET}")
    provider = env.get('LLM_PROVIDER', 'openai').lower()
    if provider == 'openai':
        if env.get('OPENAI_API_KEY', '').startswith('sk-') and len(env.get('OPENAI_API_KEY', '')) > 20:
            print(f"  {Colors.GREEN}✓{Colors.RESET} OpenAI wird als primärer Provider verwendet")
            print(f"  {Colors.BLUE}→{Colors.RESET} Ollama wird nur als Fallback verwendet")
        else:
            print(f"  {Colors.YELLOW}⚠{Colors.RESET} OpenAI konfiguriert aber API Key fehlt")
            print(f"  {Colors.BLUE}→{Colors.RESET} Ollama wird automatisch verwendet")
    else:
        print(f"  {Colors.BLUE}ℹ{Colors.RESET} Ollama als primärer Provider konfiguriert")
    
    # Save results to JSON
    results_file = Path('connection_test_results.json')
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': len(all_results),
                'passed': passed,
                'failed': failed
            },
            'results': all_results
        }, f, indent=2)
    
    print(f"\n{Colors.BLUE}Ergebnisse gespeichert in:{Colors.RESET} {results_file}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())