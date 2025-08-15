# Workflow 2 Fehler und Lösungen

## Identifizierte Probleme

### 1. Context Window Exceeded
**Problem**: Große Dokumente (>100k Zeichen) überschreiten das Token-Limit von GPT-3.5
**Lösung**: Text-Truncating implementiert in `metadata_extraction.py`
- Automatisches Kürzen auf 30.000 Zeichen
- Behält 70% vom Anfang und 25% vom Ende
- Fügt Marker "[... DOKUMENT GEKÜRZT ...]" ein

### 2. Ollama Connection Refused
**Problem**: Ollama als Fallback konfiguriert, aber nicht installiert
**Lösungen**:

Option A: Ollama installieren
```bash
# Installation
curl -fsSL https://ollama.com/install.sh | sh
# Model herunterladen
ollama pull llama3.1:8b
# Service starten
ollama serve
```

Option B: Ollama deaktivieren in .env
```bash
OLLAMA_ENABLED=false
# oder LLM_PROVIDER_ORDER ohne ollama:
LLM_PROVIDER_ORDER=openai,anthropic
```

### 3. BaseApplicationException Double Error  
**Problem**: `error_code` wurde doppelt übergeben
**Lösung**: Fix in `custom_exceptions.py` implementiert

## Empfohlene .env Anpassungen

```bash
# LLM Provider Konfiguration
LLM_PROVIDER_ORDER=openai,anthropic  # Ollama entfernt wenn nicht installiert
OPENAI_ENABLED=true
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_MAX_TOKENS=2000  # Konservativ für große Dokumente

# Optional: GPT-4 für große Dokumente
# OPENAI_MODEL=gpt-4-turbo-preview  # Größeres Context Window (128k)

# Ollama nur wenn installiert
OLLAMA_ENABLED=false  # Auf true setzen wenn Ollama läuft
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Context Window Fallback (für zukünftige LiteLLM Updates)
LITELLM_CONTEXT_WINDOW_FALLBACK=true
```

## Test des Fixes

```bash
# Workflow 2 erneut ausführen
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 2

# Oder direkt mit problematischem Dokument
python run.py --process-document 500
```

## Monitoring

Die Logs zeigen jetzt:
- "Text truncated from X to Y characters" bei großen Dokumenten
- Bessere Fehlerbehandlung bei LLM-Fehlern
- Kein Absturz mehr bei fehlenden Fallback-Providern