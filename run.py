#!/usr/bin/env python3
"""
Paperless NGX API Data Processing - Haupteinstiegspunkt

Dieses Script bietet einen einfachen Weg, die Anwendung vom Root-Verzeichnis aus zu starten.
Alle Funktionalitäten sind in src/paperless_ngx/ implementiert nach Clean Architecture Prinzipien.
"""

import sys
import os
from pathlib import Path

# Füge src Verzeichnis zum Python-Pfad hinzu
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def main():
    """Haupteinstiegspunkt für die Anwendung."""
    print("Paperless NGX API Data Processing")
    print("=" * 50)
    
    # Import der CLI aus der neuen Struktur
    try:
        from paperless_ngx.presentation.cli.main import main as cli_main
        cli_main()
    except ImportError as e:
        print(f"Fehler beim Import der Anwendung: {e}")
        print("\nStellen Sie sicher, dass Sie die Dependencies installiert haben:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Anwendungsfehler: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()