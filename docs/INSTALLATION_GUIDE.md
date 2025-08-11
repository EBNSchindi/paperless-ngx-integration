# Paperless NGX API Integration - Installationsanleitung

## Inhaltsverzeichnis
- [Systemanforderungen](#systemanforderungen)
- [Python-Umgebung einrichten](#python-umgebung-einrichten)
- [Abhängigkeiten installieren](#abhängigkeiten-installieren)
- [Konfigurationsdateien einrichten](#konfigurationsdateien-einrichten)
- [Paperless NGX API-Token generieren](#paperless-ngx-api-token-generieren)
- [Ollama Installation und Setup](#ollama-installation-und-setup)
- [OpenAI API Setup (Optional)](#openai-api-setup-optional)
- [Email-Konten konfigurieren](#email-konten-konfigurieren)
- [Installation testen](#installation-testen)
- [Häufige Installationsprobleme](#häufige-installationsprobleme)

## Systemanforderungen

### Mindestanforderungen

- **Betriebssystem**: Windows 10/11, Linux (Ubuntu 20.04+), macOS 12+
- **Python**: Version 3.9 oder höher
- **RAM**: Mindestens 4 GB (8 GB empfohlen für Ollama)
- **Festplatte**: 10 GB freier Speicherplatz
- **Netzwerk**: Stabile Internetverbindung
- **Paperless NGX**: Version 1.17.0 oder höher

### Zusätzliche Software

- **Git**: Für Code-Verwaltung (optional)
- **Ollama**: Für lokale LLM-Verarbeitung
- **Text-Editor**: VS Code, PyCharm oder ähnlich

## Python-Umgebung einrichten

### 1. Python installieren

#### Windows
```powershell
# Python von python.org herunterladen und installieren
# Oder mit winget:
winget install Python.Python.3.11

# Version prüfen
python --version
```

#### Linux (Ubuntu/Debian)
```bash
# Python installieren
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# Version prüfen
python3 --version
```

#### macOS
```bash
# Mit Homebrew
brew install python@3.11

# Version prüfen
python3 --version
```

### 2. Virtuelle Umgebung erstellen

#### Windows
```powershell
# Ins Projektverzeichnis wechseln
cd "C:\Path\To\Paperless NGX - API-Datenverarbeitung"

# Virtuelle Umgebung erstellen
python -m venv venv

# Aktivieren
venv\Scripts\activate
```

#### Linux/macOS
```bash
# Ins Projektverzeichnis wechseln
cd "/path/to/Paperless NGX - API-Datenverarbeitung"

# Virtuelle Umgebung erstellen
python3 -m venv venv

# Aktivieren
source venv/bin/activate
```

## Abhängigkeiten installieren

### 1. Requirements installieren

```bash
# Virtuelle Umgebung muss aktiviert sein!
pip install -r requirements.txt
```

### 2. Zusätzliche Pakete für erweiterte Funktionen

```bash
# Für Tag-Analyse (Fuzzy Matching)
pip install rapidfuzz

# Für Datenverarbeitung
pip install pandas

# Für Fortschrittsanzeigen
pip install tqdm

# Für bessere Konsolen-Ausgabe
pip install rich
```

### 3. Vollständige requirements.txt

```txt
# Core Dependencies
requests>=2.31.0
python-dotenv>=1.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# E-Mail Processing
imapclient>=3.0.0
email-validator>=2.0.0

# AI/LLM Integration
openai>=1.0.0
litellm>=1.0.0

# Utilities
python-dateutil>=2.8.0
typing-extensions>=4.5.0
rapidfuzz>=3.0.0
pandas>=2.0.0
tqdm>=4.65.0

# Development Dependencies
pytest>=7.0.0
pytest-asyncio>=0.21.0
black>=23.0.0
flake8>=6.0.0

# Optional Features
watchdog>=3.0.0
rich>=13.0.0
structlog>=24.0.0
```

## Konfigurationsdateien einrichten

### 1. .env Datei erstellen

Erstellen Sie eine `.env` Datei im Projektverzeichnis:

```bash
# Paperless NGX Konfiguration
PAPERLESS_API_URL=http://192.168.178.76:8010/api
PAPERLESS_API_TOKEN=your-paperless-api-token-here

# Ollama Konfiguration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TIMEOUT=120

# OpenAI Konfiguration (Fallback)
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-3.5-turbo

# Email Konfiguration - Gmail Account 1
GMAIL1_IMAP_SERVER=imap.gmail.com
GMAIL1_IMAP_PORT=993
GMAIL1_EMAIL=your.email1@gmail.com
GMAIL1_PASSWORD=your-app-specific-password1
GMAIL1_FOLDER=INBOX

# Email Konfiguration - Gmail Account 2
GMAIL2_IMAP_SERVER=imap.gmail.com
GMAIL2_IMAP_PORT=993
GMAIL2_EMAIL=your.email2@gmail.com
GMAIL2_PASSWORD=your-app-specific-password2
GMAIL2_FOLDER=INBOX

# Email Konfiguration - IONOS
IONOS_IMAP_SERVER=imap.ionos.de
IONOS_IMAP_PORT=993
IONOS_EMAIL=your.email@yourdomain.de
IONOS_PASSWORD=your-ionos-password
IONOS_FOLDER=INBOX

# Verarbeitungseinstellungen
MIN_OCR_TEXT_LENGTH=50
QUALITY_SCAN_OUTPUT_DIR=./reports/quality_scans
TAG_SIMILARITY_THRESHOLD=0.85
QUARTERLY_PROCESSING_BATCH_SIZE=10

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/paperless_ngx.log
```

### 2. Verzeichnisstruktur erstellen

```bash
# Erstelle notwendige Verzeichnisse
mkdir -p reports/quality_scans
mkdir -p logs
mkdir -p data/email_state
mkdir -p data/attachments
```

## Paperless NGX API-Token generieren

### 1. In Paperless NGX einloggen

1. Öffnen Sie Paperless NGX im Browser: `http://192.168.178.76:8010`
2. Melden Sie sich mit Ihren Admin-Zugangsdaten an

### 2. API-Token erstellen

1. Navigieren Sie zu **Einstellungen** → **Benutzer & Gruppen**
2. Klicken Sie auf Ihren Benutzernamen
3. Scrollen Sie zu **API-Token**
4. Klicken Sie auf **Token generieren**
5. Kopieren Sie den generierten Token
6. Fügen Sie den Token in die `.env` Datei ein:
   ```
   PAPERLESS_API_TOKEN=generated-token-here
   ```

### 3. Token testen

```bash
# Test mit curl
curl -H "Authorization: Token your-token-here" \
     http://192.168.178.76:8010/api/documents/

# Oder mit Python
python test_connections.py
```

## Ollama Installation und Setup

### 1. Ollama installieren

#### Windows
```powershell
# Download von https://ollama.ai/download/windows
# Installer ausführen

# Oder mit winget
winget install Ollama.Ollama
```

#### Linux
```bash
# Installation mit curl
curl -fsSL https://ollama.ai/install.sh | sh

# Service starten
sudo systemctl start ollama
```

#### macOS
```bash
# Mit Homebrew
brew install ollama

# Service starten
ollama serve
```

### 2. LLM-Modell herunterladen

```bash
# Llama 3.1 8B Modell herunterladen (empfohlen)
ollama pull llama3.1:8b

# Alternative: Kleineres Modell für schwächere Hardware
ollama pull llama2:7b

# Verfügbare Modelle anzeigen
ollama list
```

### 3. Ollama testen

```bash
# Test ob Ollama läuft
curl http://localhost:11434/api/tags

# Test mit Python-Script
python llm/ollama_test.py
```

### 4. Ollama-Konfiguration optimieren

```bash
# Für bessere Performance (Linux/macOS)
export OLLAMA_NUM_PARALLEL=2
export OLLAMA_MAX_LOADED_MODELS=1

# Windows (PowerShell)
$env:OLLAMA_NUM_PARALLEL = 2
$env:OLLAMA_MAX_LOADED_MODELS = 1
```

## OpenAI API Setup (Optional)

OpenAI wird nur als Fallback verwendet, wenn Ollama nicht verfügbar ist.

### 1. API-Key erstellen

1. Gehen Sie zu https://platform.openai.com/api-keys
2. Melden Sie sich an oder erstellen Sie ein Konto
3. Klicken Sie auf **Create new secret key**
4. Kopieren Sie den Key (wird nur einmal angezeigt!)
5. Fügen Sie ihn in die `.env` Datei ein:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```

### 2. Nutzungslimits setzen (empfohlen)

1. Gehen Sie zu **Usage limits** im OpenAI Dashboard
2. Setzen Sie ein monatliches Budget (z.B. $10)
3. Aktivieren Sie Email-Benachrichtigungen

## Email-Konten konfigurieren

### Gmail konfigurieren

#### 1. App-spezifisches Passwort erstellen

1. Gehen Sie zu https://myaccount.google.com/security
2. Aktivieren Sie 2-Faktor-Authentifizierung (falls nicht aktiv)
3. Klicken Sie auf **2-Step Verification** → **App passwords**
4. Wählen Sie **Mail** und **Other (Custom name)**
5. Geben Sie einen Namen ein: "Paperless NGX"
6. Kopieren Sie das generierte Passwort
7. Fügen Sie es in die `.env` Datei ein

#### 2. IMAP aktivieren

1. Öffnen Sie Gmail → Einstellungen → **Alle Einstellungen anzeigen**
2. Gehen Sie zum Tab **Weiterleitung und POP/IMAP**
3. Aktivieren Sie **IMAP-Zugriff**
4. Speichern Sie die Änderungen

### IONOS/1&1 konfigurieren

```env
# IONOS IMAP-Einstellungen
IONOS_IMAP_SERVER=imap.ionos.de
IONOS_IMAP_PORT=993
IONOS_EMAIL=ihre.email@ihre-domain.de
IONOS_PASSWORD=ihr-email-passwort
```

### Andere Email-Provider

| Provider | IMAP Server | Port | SSL |
|----------|------------|------|-----|
| Outlook | outlook.office365.com | 993 | Ja |
| Yahoo | imap.mail.yahoo.com | 993 | Ja |
| GMX | imap.gmx.net | 993 | Ja |
| Web.de | imap.web.de | 993 | Ja |

## Installation testen

### 1. Grundlegender Verbindungstest

```bash
# Aktiviere virtuelle Umgebung
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS

# Teste alle Verbindungen
python test_connections.py
```

Erwartete Ausgabe:
```
Testing connections...
✓ Paperless API: Connected
✓ Ollama: Online (llama3.1:8b)
✓ OpenAI: Ready
✓ Gmail Account 1: Connected
✓ Gmail Account 2: Connected
✓ IONOS: Connected
```

### 2. Hauptanwendung testen

```bash
# Starte die Anwendung
python run.py

# Wähle Option 8 (Verbindungen testen)
```

### 3. CLI-Funktionen testen

```bash
# Email-Verbindungen testen
python run.py --test-email-connections

# Dry-run für Email-Abruf
python run.py --fetch-email-attachments --dry-run
```

## Häufige Installationsprobleme

### Problem: "ModuleNotFoundError: No module named 'requests'"

**Lösung**:
```bash
# Virtuelle Umgebung aktivieren
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS

# Requirements neu installieren
pip install -r requirements.txt
```

### Problem: "Connection refused" zu Paperless API

**Lösung**:
1. Prüfen Sie ob Paperless läuft
2. Verifizieren Sie die URL in `.env`
3. Firewall-Einstellungen prüfen
4. Ping-Test: `ping 192.168.178.76`

### Problem: "Ollama not responding"

**Lösung**:
```bash
# Ollama Service neu starten
ollama serve  # In separatem Terminal

# Oder als System-Service (Linux)
sudo systemctl restart ollama
```

### Problem: "Gmail authentication failed"

**Lösung**:
1. Verwenden Sie App-spezifische Passwörter, nicht Ihr normales Passwort
2. Prüfen Sie ob IMAP aktiviert ist
3. Überprüfen Sie die 2-Faktor-Authentifizierung
4. Testen Sie mit: `python -m paperless_ngx.cli --test-email-connections`

### Problem: "OpenAI API key invalid"

**Lösung**:
1. Prüfen Sie den API-Key in `.env`
2. Stellen Sie sicher, dass der Key mit `sk-` beginnt
3. Überprüfen Sie Ihr OpenAI-Guthaben
4. Testen Sie mit: `python -c "import openai; print(openai.__version__)"`

### Problem: "Permission denied" beim Erstellen von Verzeichnissen

**Lösung (Linux/macOS)**:
```bash
# Mit sudo ausführen
sudo mkdir -p reports/quality_scans logs data

# Berechtigungen setzen
sudo chown -R $USER:$USER reports logs data
```

### Problem: "SSL certificate verify failed"

**Lösung**:
```bash
# Zertifikate aktualisieren
pip install --upgrade certifi

# Oder SSL-Verifikation temporär deaktivieren (nicht empfohlen!)
export PYTHONHTTPSVERIFY=0  # Linux/macOS
set PYTHONHTTPSVERIFY=0  # Windows
```

## Post-Installation

### 1. Erste Schritte

1. Führen Sie einen Verbindungstest durch (Option 8)
2. Rufen Sie Email-Anhänge ab (Option 1) im Dry-Run-Modus
3. Verarbeiten Sie ein einzelnes Test-Dokument (Option 5)
4. Führen Sie einen Qualitäts-Scan durch (Option 2)

### 2. Performance-Optimierung

```bash
# Für große Dokumentenmengen
export PAPERLESS_BATCH_SIZE=50  # Statt 10
export OLLAMA_TIMEOUT=300  # Statt 120

# Parallelverarbeitung aktivieren
export PAPERLESS_PARALLEL_WORKERS=4
```

### 3. Backup-Strategie

```bash
# Backup der Konfiguration
cp .env .env.backup

# Backup der Verarbeitungsstände
tar -czf backup_$(date +%Y%m%d).tar.gz data/ logs/ reports/
```

## Weitere Hilfe

- **Dokumentation**: Siehe USER_MANUAL.md für Bedienungsanleitung
- **API-Referenz**: Siehe API_REFERENCE.md für technische Details
- **Logs prüfen**: `tail -f logs/paperless_ngx.log`
- **Debug-Modus**: `LOG_LEVEL=DEBUG python run.py`

---

*Letzte Aktualisierung: Januar 2025*
*Version: 1.0.0*