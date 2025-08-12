# Test-Anleitung für Paperless NGX Integration

## 🚀 Schnelltest (5 Minuten)

### 1. Verbindungstest
```bash
# Test alle Verbindungen
python tests/scripts/test_connections_simple.py

# Oder spezifisch:
python tests/scripts/test_all_connections.py
```

### 2. Simplified Workflow testen
```bash
# Interaktives Menü
python -m paperless_ngx.presentation.cli.simplified_menu

# Oder direkt:
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 1  # Email fetch
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 2  # Process & enrich
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 3  # Quality scan
```

## 📧 Email-Download Test (Workflow 1)

### Schritt 1: Email-Accounts konfigurieren
```bash
# Kopiere .env.example zu .env
cp .env.example .env

# Bearbeite .env mit deinen Email-Credentials:
nano .env  # oder dein bevorzugter Editor
```

**Wichtige Einstellungen für Email-Test:**
```env
# Email Account 1 (Gmail)
EMAIL_ACCOUNT_1_NAME="Gmail Test"
EMAIL_ACCOUNT_1_SERVER=imap.gmail.com
EMAIL_ACCOUNT_1_USERNAME=deine@gmail.com
EMAIL_ACCOUNT_1_PASSWORD=app-specific-password  # NICHT normales Passwort!

# Email Account 2 (Optional)
EMAIL_ACCOUNT_2_NAME="IONOS Test"  
EMAIL_ACCOUNT_2_SERVER=imap.ionos.de
EMAIL_ACCOUNT_2_USERNAME=info@deine-domain.de
EMAIL_ACCOUNT_2_PASSWORD=dein-ionos-passwort
```

### Schritt 2: Email-Verbindung testen
```bash
# Teste Email-Verbindungen
python tests/scripts/test_connections_simple.py

# Erwartete Ausgabe:
# ✅ Gmail Test: Verbindung erfolgreich
# ✅ IONOS Test: Verbindung erfolgreich
```

### Schritt 3: Email-Downloads durchführen
```bash
# Interaktiv mit Workflow 1
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 1

# Wähle Zeitraum: z.B. "2024-12" oder "Last Month"
```

**Ergebnis prüfen:**
```bash
# Downloads prüfen
ls -la staging/
ls -la staging/2024-12/  # oder dein gewählter Monat

# Sollte PDF-Dateien enthalten
```

## 🤖 LLM & Paperless Test (Workflow 2)

### Schritt 1: LLM-Provider konfigurieren
```env
# In .env - LLM Provider Order
LLM_PROVIDER_ORDER=openai,ollama

# OpenAI (empfohlen für Tests)
OPENAI_ENABLED=true
OPENAI_API_KEY=sk-dein-openai-key

# Ollama (optional, lokal)
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
```

### Schritt 2: Paperless NGX konfigurieren
```env
# Paperless NGX
PAPERLESS_BASE_URL=https://dein-paperless.domain.com/api
PAPERLESS_API_TOKEN=dein-paperless-token
```

### Schritt 3: LLM-Verbindung testen
```bash
# Test LLM-Providers
python -c "
from src.paperless_ngx.infrastructure.llm.litellm_client import get_llm_client
client = get_llm_client()
health = client.health_check()
print('LLM Health:', health)
"
```

### Schritt 4: Paperless-Verbindung testen
```bash
# Test Paperless API
python -c "
from src.paperless_ngx.infrastructure.paperless.api_client import PaperlessApiClient
client = PaperlessApiClient()
docs = client.get_documents(page_size=1)
print('Paperless Verbindung: ✅ OK - ', docs['count'], 'Dokumente')
"
```

### Schritt 5: Metadaten-Extraktion testen
```bash
# Workflow 2: Dokumente verarbeiten
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 2

# Wähle:
# - Source: "paperless" (bestehende Dokumente)
# - Date Range: z.B. "2024-12"
```

**Erwartetes Ergebnis:**
- LLM analysiert OCR-Text
- Extrahiert: Absender, Dokumenttyp, Tags, Beschreibung
- **WICHTIG**: Beschreibung wird als **Notizen** in Paperless gespeichert
- Smart Tag-Matching mit 95% Threshold

## 🔍 Quality Scan Test (Workflow 3)

```bash
# Workflow 3: Quality Scan
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 3

# Generiert CSV-Report in ./reports/
```

## 📊 Ausführlicher Test (July 2025 Workflows)

```bash
# Umfassende Integration Tests
python tests/scripts/test_july_2025_simple.py

# Erwartete Ausgabe:
# ✅ Workflow 1: Email Fetch (6/6 Tests)
# ✅ Workflow 2: Document Processing (6/6 Tests) 
# ✅ Workflow 3: Quality Scan (6/6 Tests)
# 📊 Gesamtergebnis: 18/18 Tests bestanden
```

## 🚨 Fehlerbehebung

### Email-Verbindung schlägt fehl
```bash
# Gmail: App-spezifisches Passwort verwenden!
# 1. Google Account → Sicherheit → 2-Faktor-Authentifizierung
# 2. App-Passwörter → Neues App-Passwort generieren
# 3. Dieses Passwort in .env verwenden

# IONOS: Normales Passwort verwenden
# Port 993 für SSL, Port 143 für TLS
```

### LLM-Verbindung schlägt fehl
```bash
# OpenAI API Key prüfen:
curl -H "Authorization: Bearer sk-your-key" https://api.openai.com/v1/models

# Ollama lokal starten:
ollama serve
ollama pull llama3.1:8b
```

### Paperless API schlägt fehl
```bash
# Token prüfen:
curl -H "Authorization: Token dein-token" https://dein-paperless.domain.com/api/documents/

# Netzwerk prüfen:
ping dein-paperless.domain.com
```

## 📈 Erfolgs-Indikatoren

### ✅ Email-Download erfolgreich:
- Dateien in `staging/YYYY-MM/`
- Console zeigt: "✓ Gmail: 5 Dokumente gespeichert"

### ✅ LLM-Verarbeitung erfolgreich:
- Console zeigt: "LLM-Analyse: Dokument.pdf..."
- Console zeigt: "Tag-Match: 'Rechnung' → 'Rechnungen' (98%)"
- **Notizen-Feld** in Paperless ist gefüllt!

### ✅ Quality Scan erfolgreich:
- CSV-Report in `reports/quality_report_YYYY-MM.csv`
- Console zeigt Statistiken

## 🎯 Spezifischer Test für Notizen-Feld

```bash
# 1. Nimm ein Dokument in Paperless (merke dir die ID)
DOCUMENT_ID=123

# 2. Führe Workflow 2 aus und verarbeite dieses Dokument

# 3. Prüfe danach das Notizen-Feld:
python -c "
from src.paperless_ngx.infrastructure.paperless.api_client import PaperlessApiClient
client = PaperlessApiClient()
doc = client.get_document($DOCUMENT_ID)
print('Notizen:', doc.get('notes', 'LEER!'))
"
```

**Erwartung**: Das Notizen-Feld enthält die LLM-generierte Beschreibung!

## 📞 Support

Bei Problemen:
1. Prüfe `ERROR_LOG.md` 
2. Setze `LOG_LEVEL=DEBUG` in `.env`
3. Führe Tests mit `--verbose` aus