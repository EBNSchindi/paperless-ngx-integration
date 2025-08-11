# Migration Notes - Clean Architecture Implementation

**Date**: 2025-08-08
**Action**: Aggressive cleanup und Migration zu Clean Architecture

## Was wurde gelöscht

### Entfernte Verzeichnisse:
- `api/` - Alter API-Code (migriert nach `src/paperless_ngx/infrastructure/api/`)
- `config/` - Alte Konfiguration (migriert nach `src/paperless_ngx/infrastructure/config/`)
- `llm/` - Alte LLM-Integration (migriert nach `src/paperless_ngx/infrastructure/llm/`)
- `filters/` - Alte Filter (migriert nach `src/paperless_ngx/domain/utilities/`)
- `venv/` - Windows Virtual Environment (150MB, nicht benötigt auf Linux)
- `research/` - Temporäre Forschungsnotizen
- `test_api.py` - Alter Test (Tests jetzt in `src/paperless_ngx/tests/`)
- `AGENT_LOG.md` - Veraltetes Agent-Log

## Neue Struktur

Alle Funktionalitäten wurden erhalten und verbessert in der neuen Clean Architecture:

```
src/paperless_ngx/
├── domain/              # Geschäftslogik und Entitäten
├── application/         # Use Cases und Services
├── infrastructure/      # Externe Integrationen
│   ├── api/            # Paperless API Client
│   ├── email/          # E-Mail Integration
│   ├── llm/            # LLM Integration
│   └── config/         # Konfiguration
└── presentation/        # CLI und UI
```

## Verwendung

1. **Dependencies installieren**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Credentials konfigurieren**:
   ```bash
   cp .env.example .env
   nano .env  # Ihre Credentials eintragen
   ```

3. **Anwendung starten**:
   ```bash
   python run.py
   # oder direkt:
   python -m src.paperless_ngx.presentation.cli.main --help
   ```

## Migrations-Vorteile

- Saubere Trennung der Verantwortlichkeiten
- Bessere Testbarkeit
- Verbesserte Wartbarkeit
- Klare Dependency Injection
- Domain-Driven Design Prinzipien

Alle vorherigen Funktionen sind erhalten, aber besser organisiert.