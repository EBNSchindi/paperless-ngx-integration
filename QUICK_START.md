# 🚀 Quick Start Guide

> **Plattform-Support**: Windows 10/11 ✅ | Linux ✅ | macOS ✅  
> **Python-Version**: 3.8+ erforderlich  
> **Letztes Update**: 2025-08-12

## ⚡ 5-Minuten-Setup

### Windows
```powershell
# 1. Repository klonen
git clone https://github.com/EBNSchindi/paperless-ngx-integration.git
cd paperless-ngx-integration

# 2. Virtual Environment erstellen & aktivieren
python -m venv venv
venv\Scripts\activate

# 3. Dependencies installieren
pip install -r requirements.txt

# 4. Konfiguration (WICHTIG!)
copy .env.example .env
notepad .env  # ← Paperless URL & API Token eintragen!

# 5. UTF-8 für Windows aktivieren
set PYTHONUTF8=1

# 6. STARTEN 🚀
python start.py
```

### Linux/macOS
```bash
# 1. Repository klonen
git clone https://github.com/EBNSchindi/paperless-ngx-integration.git
cd paperless-ngx-integration

# 2. Virtual Environment erstellen & aktivieren
python3 -m venv venv
source venv/bin/activate

# 3. Dependencies installieren
pip install -r requirements.txt

# 4. Konfiguration (WICHTIG!)
cp .env.example .env
nano .env  # ← Paperless URL & API Token eintragen!

# 5. STARTEN 🚀
python3 start.py
```

## 🎯 Der 3-Punkt-Workflow

Nach dem Setup stehen dir 3 Hauptworkflows zur Verfügung:

### 1️⃣ Email-Dokumente abrufen
```bash
python start.py --workflow 1
```
- Holt Anhänge aus allen konfigurierten Email-Konten
- Organisiert Dateien nach Monat (YYYY-MM)
- Erkennt automatisch PDF-Dokumente

### 2️⃣ Dokumente verarbeiten & anreichern
```bash
python start.py --workflow 2
```
- Extrahiert OCR-Text aus Paperless
- Analysiert mit LLM (OpenAI/Ollama)
- Matched Tags intelligent (95% Threshold)
- Aktualisiert Metadaten in Paperless

### 3️⃣ Quality Scan & Report
```bash
python start.py --workflow 3
```
- Prüft Dokumente auf fehlende Metadaten
- Identifiziert Probleme mit Tags/OCR
- Generiert CSV-Report mit Empfehlungen

## 🎨 Interaktives Menü

Ohne Parameter startet das interaktive Menü:

```bash
python start.py  # Windows
python3 start.py # Linux/macOS
```

```
╔════════════════════════════════════════╗
║     Paperless NGX Integration          ║
║        Simplified Workflow              ║
╚════════════════════════════════════════╝

1. 📥 Email-Dokumente abrufen
2. 🔄 Dokumente verarbeiten & anreichern
3. 📊 Quality Scan & Report
4. 🚀 Alle Workflows nacheinander
5. 🔧 Verbindungen testen
6. ❌ Beenden

Wähle Option (1-6):
```

## ⚠️ Häufige Probleme & Lösungen

### Windows: "Python nicht gefunden"
```powershell
# Python von python.org installieren
# Dann in PowerShell als Admin:
winget install Python.Python.3.12
```

### Linux: "pip: command not found"
```bash
sudo apt update
sudo apt install python3-pip python3-venv
```

### Alle Systeme: "ModuleNotFoundError"
```bash
# Virtual Environment aktiviert?
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Dependencies installieren
pip install -r requirements.txt
```

### ".env Datei fehlt"
```bash
# Template kopieren
cp .env.example .env

# Minimal-Konfiguration:
PAPERLESS_BASE_URL=http://192.168.1.100:8000/api
PAPERLESS_API_TOKEN=dein-api-token-hier
OPENAI_API_KEY=sk-...  # Oder Ollama nutzen
```

## 🔍 Verbindungen testen

**Immer zuerst testen:**
```bash
python start.py
# → Option 5: Verbindungen testen
```

Erfolgreiche Ausgabe:
```
✅ Paperless NGX: Verbunden (447 Dokumente)
✅ OpenAI: Verfügbar (GPT-3.5)
✅ Email: 3 Konten konfiguriert
✅ Dateisystem: Schreibrechte OK
```

## 💡 Pro-Tipps

1. **Windows UTF-8**: Permanent aktivieren
   ```powershell
   [System.Environment]::SetEnvironmentVariable('PYTHONUTF8', '1', 'User')
   ```

2. **Linux Alias**: Schnellzugriff einrichten
   ```bash
   echo "alias paperless='cd ~/paperless-ngx-integration && source venv/bin/activate && python3 start.py'" >> ~/.bashrc
   ```

3. **Automatisierung**: Cron/Task Scheduler
   ```bash
   # Linux Cron (täglich um 2 Uhr)
   0 2 * * * cd /home/user/paperless-ngx-integration && venv/bin/python start.py --workflow 1,2,3
   ```

## 📚 Weiterführende Dokumentation

- **[Vollständige Installation](docs/setup/)** - Detaillierte Platform-Guides
- **[Workflows erklärt](docs/user-guide/WORKFLOWS.md)** - Was passiert im Detail
- **[API Referenz](docs/API_REFERENCE.md)** - Für Entwickler
- **[FAQ](docs/user-guide/FAQ.md)** - Häufige Fragen

---

**🎉 Fertig!** Du bist startklar. Bei Problemen → [docs/setup/TROUBLESHOOTING.md](docs/setup/TROUBLESHOOTING.md)