# 🎯 Model Switching Guide

## Quick Start: Modell wechseln

**JA, du kannst Modelle einfach in der .env wechseln!** Hier ist wie:

```bash
# In .env - einfach ändern:
OPENAI_MODEL=gpt-4o-mini        # Empfohlen für Produktion
OPENAI_MODEL=gpt-3.5-turbo      # Günstig und schnell
OPENAI_MODEL=gpt-4-turbo        # Beste Qualität
OPENAI_MODEL=gpt-4o             # Neuestes Modell
```

**Das war's! Kein Code ändern, kein Neustart nötig.**

## 📊 Verfügbare Modelle & Features

| Modell | JSON Format | Context Window | Kosten | Empfehlung |
|--------|------------|----------------|--------|------------|
| **gpt-4o** | ✅ Ja | 128k tokens | $5/$15 | Beste Balance |
| **gpt-4o-mini** | ✅ Ja | 128k tokens | $0.15/$0.60 | **⭐ EMPFOHLEN** |
| **gpt-4-turbo** | ✅ Ja | 128k tokens | $10/$30 | Höchste Qualität |
| **gpt-4-turbo-preview** | ✅ Ja | 128k tokens | $10/$30 | Experimentell |
| **gpt-3.5-turbo** | ✅ Ja | 16k tokens | $0.50/$1.50 | Budget-Option |
| **gpt-3.5-turbo-16k** | ✅ Ja | 16k tokens | $3/$4 | Große Dokumente |

*Kosten: $ pro Million Input/Output Tokens*

## ⚙️ Weitere Einstellungen (optional)

### 1. Temperature anpassen (Kreativität)
```bash
# In .env hinzufügen:
OPENAI_TEMPERATURE=0.1   # 0.0-1.0 (niedrig = präziser)
```

### 2. Max Tokens ändern
```bash
# In .env hinzufügen:
OPENAI_MAX_TOKENS=2000   # Maximale Antwortlänge
```

### 3. Context Window für große Dokumente
```python
# In metadata_extraction.py Zeile 48:
def _truncate_text_for_llm(self, text: str, max_chars: int = 40000):
    # Ändern zu:
    # max_chars: int = 100000  # Für gpt-4 Modelle mit 128k context
```

## 🚨 Wichtige Hinweise

### "gpt-5-nano" und "gpt-5-mini"
Diese Modelle **existieren nicht**! OpenAI hat keine GPT-5 Modelle veröffentlicht.
Falls du diese in .env siehst, ändere sie zu echten Modellen:

```bash
# FALSCH (funktioniert nicht richtig):
OPENAI_MODEL=gpt-5-nano  ❌

# RICHTIG:
OPENAI_MODEL=gpt-4o-mini  ✅
```

### JSON Response Format
Der Code erkennt automatisch, ob ein Modell JSON unterstützt:
- ✅ Unterstützt: gpt-4*, gpt-3.5-turbo* (automatisch aktiviert)
- ❌ Nicht unterstützt: Alte Modelle, Custom Models (automatisch deaktiviert)

### Fallback-Kette
```bash
# Provider-Reihenfolge in .env:
LLM_PROVIDER_ORDER=openai,ollama,openai_mini

# openai_mini verwendet automatisch gpt-4o-mini als Fallback
# Du musst nichts weiter konfigurieren!
```

## 🧪 Modell testen

```bash
# Test mit aktuellem Modell:
source venv/bin/activate
python3 -c "
from src.paperless_ngx.infrastructure.config.settings import get_settings
s = get_settings()
print(f'Aktuelles Modell: {s.openai_model}')
print(f'Temperature: {s.openai_temperature}')
print(f'Max Tokens: {s.openai_max_tokens}')
"

# Workflow 2 mit neuem Modell testen:
python -m paperless_ngx.presentation.cli.simplified_menu --workflow 2
```

## 💡 Empfehlungen nach Use Case

### Für Produktion (Beste Balance)
```bash
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.1
OPENAI_MAX_TOKENS=2000
```

### Für maximale Qualität
```bash
OPENAI_MODEL=gpt-4-turbo
OPENAI_TEMPERATURE=0.2
OPENAI_MAX_TOKENS=3000
```

### Für Budget-Betrieb
```bash
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.1
OPENAI_MAX_TOKENS=1500
```

### Für große Dokumente (>50 Seiten)
```bash
OPENAI_MODEL=gpt-4o        # 128k context window
OPENAI_TEMPERATURE=0.1
OPENAI_MAX_TOKENS=4000
```

## 🔧 Troubleshooting

### Problem: "Primary JSON extraction failed"
**Lösung**: Wechsel zu einem Modell mit JSON-Support (gpt-4o-mini, gpt-3.5-turbo)

### Problem: "Context window exceeded"
**Lösung**: 
1. Nutze Modell mit größerem Context (gpt-4o, gpt-4-turbo)
2. Oder erhöhe max_chars in metadata_extraction.py

### Problem: "Model not found"
**Lösung**: Prüfe Schreibweise! Exakte Namen verwenden:
- ✅ `gpt-4o-mini` (mit Bindestrich)
- ❌ `gpt4omini` (ohne Bindestriche)

## 📈 Kosten-Monitoring

```bash
# Kosten-Tracking ist eingebaut! Check die Logs:
grep "cost" logs/*.log

# Oder in Python:
from src.paperless_ngx.infrastructure.llm.litellm_client import get_llm_client
client = get_llm_client()
print(client.cost_tracker.get_total_cost())
```

---

**Zusammenfassung**: Ja, du kannst Modelle einfach in .env wechseln! Keine weiteren Einstellungen nötig. Der Code passt sich automatisch an.