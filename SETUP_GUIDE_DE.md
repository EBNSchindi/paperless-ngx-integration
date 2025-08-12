# Paperless NGX Integration - Einrichtungsanleitung

## 🚀 Schnellstart für das 3-Punkte-Workflow-System

### 1. Voraussetzungen

- Python 3.9 oder höher
- Paperless NGX Installation (v1.17.0+)
- Entweder:
  - OpenAI API Key (empfohlen für Produktion)
  - Oder Ollama lokal installiert (kostenlos)

### 2. Installation

```bash
# Repository klonen
git clone <repository-url>
cd paperless-ngx-integration

# Python Virtual Environment erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate  # Windows

# Abhängigkeiten installieren
pip install -r requirements.txt

# Zusätzlich für besseres Tag-Matching
pip install rapidfuzz
```

### 3. Konfiguration (.env Datei)

Kopieren Sie die Beispiel-Konfiguration und passen Sie sie an:

```bash
cp .env.example .env
```

#### Wichtigste Einstellungen in .env:

```bash
# === PAPERLESS NGX ===
PAPERLESS_BASE_URL=http://192.168.178.76:8010/api  # Ihre Paperless URL
PAPERLESS_API_TOKEN=abc123def456  # Token aus Paperless Settings

# === LLM PROVIDER (wählen Sie eine Option) ===

# Option A: OpenAI (empfohlen - beste Qualität)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxx  # Ihr OpenAI API Key
OPENAI_MODEL=gpt-3.5-turbo  # oder gpt-4 für bessere Ergebnisse

# Option B: Ollama (lokal und kostenlos)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b  # oder qwen2.5, gemma2

# === EMAIL KONTEN (3 Konten konfiguriert) ===
# Gmail Konto 1 - Hauptgeschäft
EMAIL_ACCOUNT_1_NAME="Gmail Hauptgeschäft"
EMAIL_ACCOUNT_1_SERVER=imap.gmail.com
EMAIL_ACCOUNT_1_PORT=993
EMAIL_ACCOUNT_1_USERNAME=hauptgeschaeft@gmail.com
EMAIL_ACCOUNT_1_PASSWORD=abcd-efgh-ijkl-mnop  # App-spezifisches Passwort!

# Gmail Konto 2 - Buchhaltung
EMAIL_ACCOUNT_2_NAME="Gmail Buchhaltung"
EMAIL_ACCOUNT_2_SERVER=imap.gmail.com
EMAIL_ACCOUNT_2_PORT=993
EMAIL_ACCOUNT_2_USERNAME=buchhaltung@gmail.com
EMAIL_ACCOUNT_2_PASSWORD=wxyz-1234-5678-9abc  # App-spezifisches Passwort!

# IONOS Konto 3 - Geschäftlich
EMAIL_ACCOUNT_3_NAME="IONOS Geschäft"
EMAIL_ACCOUNT_3_SERVER=imap.ionos.de
EMAIL_ACCOUNT_3_PORT=993
EMAIL_ACCOUNT_3_USERNAME=info@ihre-domain.de
EMAIL_ACCOUNT_3_PASSWORD=IhrIONOSPasswort123  # Normales Passwort

# === GESCHÄFTSKONTEXT ===
# WICHTIG: Dies ist IMMER der Empfänger, NIE der Absender!
BUSINESS_NAME="Daniel Schindler / EBN Veranstaltungen und Consulting GmbH"
RECIPIENT_NAME="Daniel Schindler"

# === TAG-MATCHING EINSTELLUNGEN ===
TAG_SIMILARITY_THRESHOLD=0.95  # Verhindert falsche Vereinheitlichungen
```

### 4. Ollama einrichten (falls gewählt)

```bash
# Ollama installieren
curl -fsSL https://ollama.com/install.sh | sh

# Ollama starten
ollama serve

# Modell herunterladen (in neuem Terminal)
ollama pull llama3.1:8b  # ~4.7 GB

# Alternative Modelle (optional):
ollama pull qwen2.5:7b  # Sehr gut für Deutsch
ollama pull gemma2:9b   # Google's Modell
```

### 5. Gmail App-Passwort erstellen

1. Gehen Sie zu: https://myaccount.google.com/security
2. Aktivieren Sie 2-Faktor-Authentifizierung
3. Unter "2-Schritt-Verifizierung" → "App-Passwörter"
4. Erstellen Sie ein neues App-Passwort für "Mail"
5. Verwenden Sie dieses 16-stellige Passwort in der .env

### 6. Paperless API Token erhalten

1. Loggen Sie sich in Paperless NGX ein
2. Gehen Sie zu: Settings → Users & Groups
3. Klicken Sie auf Ihren Benutzer
4. Unter "Auth Token" → "Create Token"
5. Kopieren Sie den Token in die .env Datei

## 📊 Das 3-Punkte-Workflow-System verwenden

### Start des vereinfachten Menüs:

```bash
# Aktivieren Sie zuerst das Virtual Environment
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate  # Windows

# Starten Sie das 3-Punkte-Menü
python -m paperless_ngx.presentation.cli.simplified_menu
```

### Die 3 Workflows im Detail:

#### Workflow 1: Email-Dokumente abrufen
- **Zweck**: Lädt Rechnungen/Dokumente aus Email-Postfächern
- **Zeitraum**: Wählbar (z.B. letztes Quartal, letzte 3 Monate)
- **Output**: Dokumente organisiert nach Monat in `staging/2024-10/`, `staging/2024-11/`, etc.

#### Workflow 2: Dokumente verarbeiten & anreichern
- **Zweck**: Extrahiert Metadaten mit KI und matched Tags intelligent
- **Besonderheit**: 95% Tag-Threshold verhindert falsche Vereinheitlichungen
- **Beispiel**: "Telekommunikation" wird NICHT mit "Telekom" vereinheitlicht
- **Output**: Dokumente mit korrekten Metadaten in Paperless

#### Workflow 3: Quality Scan & Report
- **Zweck**: Prüft Dokumentenqualität im gewählten Zeitraum
- **Prüfungen**: Fehlende Tags, OCR-Probleme, fehlende Metadaten
- **Output**: CSV-Report mit konkreten Handlungsempfehlungen

## 🎯 Typischer Quartals-Workflow

```bash
# 1. Emails der letzten 3 Monate abrufen
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 1
> Wählen Sie: "Letzte 3 Monate"
> Wählen Sie: "Alle Email-Konten"

# 2. Dokumente verarbeiten und Metadaten extrahieren
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 2
> Quelle: "Staging-Verzeichnis"
> Monate: "alle"

# 3. Qualität prüfen
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 3
> Zeitraum: "Letztes Quartal"
> Export: "Ja" → quality_report_2024-10_2024-12.csv
```

## 🔧 Troubleshooting

### Problem: "Connection refused" zu Paperless
**Lösung**: Prüfen Sie die PAPERLESS_BASE_URL und stellen Sie sicher, dass Paperless läuft

### Problem: "Ollama not responding"
**Lösung**: 
```bash
# Ollama neu starten
ollama serve

# Prüfen ob Modell installiert ist
ollama list
```

### Problem: Gmail Authentication failed
**Lösung**: Verwenden Sie ein App-spezifisches Passwort, nicht Ihr normales Gmail-Passwort

### Problem: Tags werden falsch vereinheitlicht
**Lösung**: Prüfen Sie TAG_SIMILARITY_THRESHOLD=0.95 in .env (nicht niedriger setzen!)

### Problem: OpenAI API Key ungültig
**Lösung**: 
1. Prüfen Sie den Key auf https://platform.openai.com/api-keys
2. Stellen Sie sicher, dass Guthaben vorhanden ist
3. Key muss mit "sk-" beginnen

## 📝 Wichtige Geschäftsregeln

1. **Daniel Schindler/EBN ist IMMER Empfänger** - nie als Korrespondent speichern
2. **Tags präzise setzen** - "Telekommunikation" ist ein Thema, "Telekom" ist ein Anbieter
3. **3-7 Tags pro Dokument** - optimal für Auffindbarkeit
4. **Dateiformat**: YYYY-MM-DD_Absender_Dokumenttyp.pdf
5. **Beschreibung**: Maximal 128 Zeichen

## 🚀 Performance-Tipps

- **OpenAI GPT-3.5-turbo**: ~2-3 Sekunden pro Dokument, sehr zuverlässig
- **Ollama Llama3.1**: ~5-8 Sekunden pro Dokument, lokal und privat
- **Batch-Größe**: 10 Dokumente parallel (in .env anpassbar)
- **100+ Dokumente**: Kein Problem, einzelne Fehler stoppen nicht den Batch

## 📞 Support

Bei Problemen prüfen Sie:
1. Die Logs in `paperless.log`
2. Die Dokumentation in `docs/`
3. Die Test-Skripte in `test_connections.py`

Viel Erfolg mit der quartalsweisen Dokumentenverarbeitung!