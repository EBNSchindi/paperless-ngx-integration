# 🚀 Quick Start Guide

## Installation & Start (Alle Systeme)

### Windows
```powershell
# 1. Virtual Environment erstellen
python -m venv venv

# 2. Dependencies installieren
venv\Scripts\activate
pip install -r requirements.txt

# 3. Konfiguration
copy .env.example .env
notepad .env  # Credentials eintragen!

# 4. STARTEN
start.bat
# oder direkt:
python start.py
```

### Linux/Mac
```bash
# 1. Virtual Environment erstellen
python3 -m venv venv

# 2. Dependencies installieren
source venv/bin/activate
pip install -r requirements.txt

# 3. Konfiguration
cp .env.example .env
nano .env  # Credentials eintragen!

# 4. STARTEN
./start.sh
# oder direkt:
python3 start.py
```

## 🎯 Universelle Starter

Wir haben **EINEN** universellen Starter für alle Systeme:

| Datei | System | Beschreibung |
|-------|--------|--------------|
| `start.py` | Alle | Hauptstarter (Python) |
| `start.bat` | Windows | Windows-Wrapper |
| `start.sh` | Linux/Mac | Unix-Wrapper |

### Direktstart ohne Menü

```bash
# Windows
python start.py --workflow 1  # Email-Download
python start.py --workflow 2  # Dokumente verarbeiten
python start.py --workflow 3  # Quality Scan

# Linux/Mac
./start.sh --workflow 1  # Email-Download
./start.sh --workflow 2  # Dokumente verarbeiten
./start.sh --workflow 3  # Quality Scan
```

## ⚙️ Was macht der Starter?

1. **Prüft Virtual Environment** - Warnt wenn nicht aktiviert
2. **Prüft .env Datei** - Erstellt aus Template wenn fehlt
3. **Installiert Dependencies** - Automatisch wenn nötig
4. **Zeigt Menü** - 7 Optionen zur Auswahl
5. **Cross-Platform** - Funktioniert überall gleich

## 📋 Menü-Optionen

1. **Vereinfachtes 3-Punkt-Menü** (empfohlen)
2. **Vollständiges Hauptmenü** (8 Optionen)
3. **Verbindungen testen**
4. **Email-Download** (Workflow 1)
5. **Dokumente verarbeiten** (Workflow 2)
6. **Quality Scan** (Workflow 3)
7. **Kompletter Durchlauf** (alle 3 Workflows)

## 🔧 Troubleshooting

### "Module not found"
```bash
pip install -r requirements.txt
```

### "Virtual Environment nicht gefunden"
```bash
# Windows
python -m venv venv

# Linux/Mac
python3 -m venv venv
```

### ".env nicht konfiguriert"
```bash
# Kopiere Template und editiere
cp .env.example .env
```

## 💡 Tipps

- **Immer in venv arbeiten!** Der Starter warnt dich
- **Erst .env konfigurieren!** Sonst keine Verbindungen
- **Option 3 zum Testen** - Prüft alle Verbindungen
- **Option 7 für Komplett-Durchlauf** - Alle 3 Workflows

## 🎯 Schnelltest

```bash
# Windows
start.bat
# → Wähle Option 3 (Verbindungen testen)

# Linux/Mac
./start.sh
# → Wähle Option 3 (Verbindungen testen)
```

---

**Das war's!** Mit `start.py` / `start.bat` / `start.sh` läuft alles. 🚀