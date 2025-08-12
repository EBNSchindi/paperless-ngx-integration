#!/usr/bin/env python3
"""
Universeller Starter für Paperless NGX Integration
Funktioniert auf Windows, Linux und macOS
"""

import sys
import os
import platform
import subprocess
from pathlib import Path

# Farben für Terminal (funktioniert auf Windows 10+ und Linux/Mac)
if platform.system() == "Windows":
    os.system("color")  # Enable ANSI colors on Windows

GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_header():
    """Print application header."""
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}    Paperless NGX Integration System v1.0{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")

def setup_python_path():
    """Setup Python path for imports."""
    project_root = Path(__file__).parent
    src_path = project_root / "src"
    sys.path.insert(0, str(src_path))
    os.environ['PYTHONPATH'] = str(src_path) + os.pathsep + os.environ.get('PYTHONPATH', '')

def check_venv():
    """Check if running in virtual environment."""
    if sys.prefix == sys.base_prefix:
        print(f"{YELLOW}⚠️  Nicht in Virtual Environment!{RESET}")
        print(f"{YELLOW}   Empfohlen: {RESET}")
        if platform.system() == "Windows":
            print(f"   {GREEN}venv\\Scripts\\activate{RESET}")
        else:
            print(f"   {GREEN}source venv/bin/activate{RESET}")
        print()
        response = input("Trotzdem fortfahren? (j/n) [n]: ").lower()
        if response != 'j':
            sys.exit(0)

def check_env_file():
    """Check if .env file exists."""
    env_file = Path(".env")
    if not env_file.exists():
        print(f"{YELLOW}⚠️  .env Datei nicht gefunden!{RESET}")
        print(f"   Kopiere .env.example zu .env...")
        
        example_file = Path(".env.example")
        if example_file.exists():
            import shutil
            shutil.copy(example_file, env_file)
            print(f"{GREEN}✅ .env erstellt. Bitte konfigurieren!{RESET}")
            
            # Try to open in editor
            if platform.system() == "Windows":
                os.system(f"notepad {env_file}")
            else:
                editor = os.environ.get('EDITOR', 'nano')
                os.system(f"{editor} {env_file}")
        else:
            print(f"{RED}❌ .env.example nicht gefunden!{RESET}")
            sys.exit(1)

def check_dependencies():
    """Check and install missing dependencies."""
    print(f"{BLUE}🔍 Prüfe Dependencies...{RESET}")
    
    required = [
        'pythonjsonlogger',
        'structlog',
        'rich',
        'click',
        'rapidfuzz',
        'tenacity',
        'pydantic',
        'pydantic_settings',
        'dotenv',
        'imapclient',
        'litellm',
        'openai',
        'requests'
    ]
    
    missing = []
    for module in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        print(f"{YELLOW}📦 Installiere fehlende Pakete...{RESET}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print(f"{GREEN}✅ Installation abgeschlossen{RESET}")
    else:
        print(f"{GREEN}✅ Alle Dependencies vorhanden{RESET}")

def show_menu():
    """Show main menu and get user choice."""
    print(f"\n{BOLD}Hauptmenü:{RESET}\n")
    print(f"  {GREEN}1{RESET} → 🚀 Vereinfachtes 3-Punkt-Menü ({BOLD}empfohlen{RESET})")
    print(f"  {GREEN}2{RESET} → 📋 Vollständiges Hauptmenü (8 Optionen)")
    print(f"  {GREEN}3{RESET} → 🧪 Verbindungen testen")
    print(f"  {GREEN}4{RESET} → 📧 Email-Download (Workflow 1)")
    print(f"  {GREEN}5{RESET} → 🤖 Dokumente verarbeiten (Workflow 2)")
    print(f"  {GREEN}6{RESET} → 📊 Quality Scan (Workflow 3)")
    print(f"  {GREEN}7{RESET} → 🔄 Kompletter Durchlauf (1→2→3)")
    print(f"\n  {RED}0{RESET} → Beenden\n")
    
    choice = input(f"Ihre Wahl [1]: ").strip() or "1"
    return choice

def run_workflow(workflow_num):
    """Run a specific workflow."""
    try:
        from paperless_ngx.presentation.cli.simplified_menu import SimplifiedWorkflowCLI
        import asyncio
        
        cli = SimplifiedWorkflowCLI()
        
        if workflow_num == 1:
            asyncio.run(cli.workflow_1_email_fetch())
        elif workflow_num == 2:
            asyncio.run(cli.workflow_2_process_documents())
        elif workflow_num == 3:
            cli.workflow_3_quality_scan()
    except Exception as e:
        print(f"{RED}❌ Fehler: {e}{RESET}")
        import traceback
        traceback.print_exc()

def main():
    """Main entry point."""
    try:
        print_header()
        
        # Setup
        setup_python_path()
        check_venv()
        check_env_file()
        check_dependencies()
        
        # Show menu and process choice
        choice = show_menu()
        
        if choice == "0":
            print(f"\n{YELLOW}Auf Wiedersehen!{RESET}")
            sys.exit(0)
            
        elif choice == "1":
            # Simplified menu
            from paperless_ngx.presentation.cli.simplified_menu import SimplifiedWorkflowCLI
            cli = SimplifiedWorkflowCLI()
            workflow = cli.show_main_menu()
            if workflow > 0:
                run_workflow(workflow)
                
        elif choice == "2":
            # Full menu
            from paperless_ngx.presentation.cli.main import main as cli_main
            cli_main()
            
        elif choice == "3":
            # Test connections
            print(f"\n{BLUE}🧪 Teste Verbindungen...{RESET}")
            test_script = Path("tests/scripts/test_connections_simple.py")
            if test_script.exists():
                subprocess.run([sys.executable, str(test_script)])
            else:
                print(f"{RED}Test-Script nicht gefunden!{RESET}")
                
        elif choice == "4":
            run_workflow(1)
            
        elif choice == "5":
            run_workflow(2)
            
        elif choice == "6":
            run_workflow(3)
            
        elif choice == "7":
            # Complete workflow
            print(f"\n{BLUE}🔄 Führe kompletten Workflow aus...{RESET}")
            print(f"{YELLOW}Schritt 1/3: Email-Download{RESET}")
            run_workflow(1)
            print(f"{YELLOW}Schritt 2/3: Dokumentenverarbeitung{RESET}")
            run_workflow(2)
            print(f"{YELLOW}Schritt 3/3: Quality Scan{RESET}")
            run_workflow(3)
            print(f"{GREEN}✅ Workflow abgeschlossen!{RESET}")
            
        else:
            print(f"{RED}Ungültige Wahl!{RESET}")
            
        print(f"\n{GREEN}✅ Fertig!{RESET}\n")
        
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}⚠️  Abgebrochen durch Benutzer{RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{RED}❌ Fehler: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()