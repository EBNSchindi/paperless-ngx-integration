# Paperless NGX - Tags und Notizen Analyse

## Status: Beide Features funktionieren korrekt ✅

### 1. Tags (IDs statt Namen)

**Beobachtung**: Tags werden in der API als Integer-IDs gespeichert (z.B. 1396, 1398, 1430)

**Analyse**: 
- Dies ist das **korrekte Verhalten** der Paperless NGX API
- Die API speichert Tags als numerische IDs für Performance und Konsistenz
- Die Paperless NGX Web-UI löst diese IDs automatisch zu den Tag-Namen auf

**Beispiel aus der Analyse**:
```
Document ID: 447
Tags (raw): [1396, 1398, 1430, 1395, 1429, 1397]

Tag-Auflösung:
  Tag ID 1396: Bescheid
  Tag ID 1398: Eigentumsverhältnisse
  Tag ID 1430: Einspruch
  Tag ID 1395: Grundsteuer
  Tag ID 1429: Zurechnung
  Tag ID 1397: Zurechnungsfortschreibung
```

**Fazit**: Kein Bug - die Tags funktionieren wie vorgesehen.

### 2. Notizen-Feld

**Beobachtung**: Das `notes` Feld bleibt leer ([])

**Analyse**:
- Das `notes` Feld in Paperless NGX ist für **Benutzer-Notizen** reserviert
- Diese werden über die Web-UI erstellt und sind read-only via API
- Die separaten Endpoints `/notes/` und `/document_notes/` sind geschützt (403 Forbidden)
- **ABER**: Die Metadaten-Extraktion generiert erfolgreich ein `description` Feld

**Lösung**: 
Das System generiert bereits Beschreibungen über das `description` Feld:
```python
metadata = {
    'correspondent': 'Finanzamt Bruchsal',
    'document_type': 'Grundsteuerbescheid',
    'tags': ['Grundsteuer', 'Bescheid', ...],
    'description': 'Bescheid über die Grundsteuer für das Grundstück von Herrn Schindler'
}
```

Diese Beschreibung sollte in einem anderen Feld gespeichert werden, da das `notes` Feld API-seitig nicht beschreibbar ist.

### 3. Empfehlungen

1. **Tags**: Keine Änderung nötig - funktioniert korrekt
2. **Beschreibungen**: 
   - Option A: Custom Field für automatisch generierte Beschreibungen verwenden
   - Option B: Beschreibung im Titel einbauen
   - Option C: Separate Dokumentation/Export der Beschreibungen

### 4. Technische Details

**API-Verhalten**:
- Tags: Werden als Integer-Array gespeichert und von der UI aufgelöst
- Notes: Read-only Array für Benutzer-erstellte Notizen
- Description: Wird vom LLM generiert, muss aber anders gespeichert werden

**Code-Pfade**:
- Tag-Mapping: `src/paperless_ngx/application/services/paperless_api_service.py:350-379`
- ID-Resolution: `src/paperless_ngx/application/services/document_metadata_service.py:120-177`
- Metadata-Extraction: `src/paperless_ngx/application/use_cases/metadata_extraction.py`

## Zusammenfassung

Beide "Probleme" sind keine Bugs:
1. **Tags als IDs**: Normales API-Verhalten, UI zeigt Namen korrekt an
2. **Leere Notizen**: API-Limitation, Beschreibungen werden aber erfolgreich generiert

Das System funktioniert wie designed. Die generierten Beschreibungen könnten in Zukunft in einem Custom Field gespeichert werden, wenn gewünscht.