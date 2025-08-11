# Paperless NGX API Integration - Benutzerhandbuch

## Inhaltsverzeichnis
- [Schnellstart](#schnellstart)
- [Hauptmenü Übersicht](#hauptmenü-übersicht)
- [Detaillierte Funktionsbeschreibungen](#detaillierte-funktionsbeschreibungen)
- [Arbeitsabläufe](#arbeitsabläufe)
- [Geschäftsregeln](#geschäftsregeln)
- [Fehlerbehebung](#fehlerbehebung)
- [Häufig gestellte Fragen (FAQ)](#häufig-gestellte-fragen-faq)

## Schnellstart

### 1. Anwendung starten

```bash
# Virtuelle Umgebung aktivieren (Windows)
venv\Scripts\activate

# Anwendung starten
python run.py
```

### 2. Hauptfunktionen

Die Anwendung bietet 8 Hauptfunktionen über ein interaktives Menü:

1. **Email-Anhänge abrufen**: Lädt Dokumente aus konfigurierten Email-Konten
2. **Qualitäts-Scan**: Prüft alle Dokumente auf OCR-Fehler und fehlende Metadaten
3. **Quartalsverarbeitung**: Verarbeitet Dokumente des letzten Quartals neu
4. **Stapelverarbeitung**: Verarbeitet mehrere Dokumente gleichzeitig
5. **Einzeldokument verarbeiten**: Verarbeitet ein spezifisches Dokument
6. **Tag-Analyse**: Analysiert und vereinheitlicht Tags
7. **Berichte generieren**: Erstellt detaillierte Verarbeitungsberichte
8. **Verbindungen testen**: Prüft alle System-Verbindungen

## Hauptmenü Übersicht

```
╔════════════════════════════════════════════════════╗
║     Paperless NGX - Erweiterte Verarbeitung       ║
╠════════════════════════════════════════════════════╣
║  1. Email-Anhänge abrufen                         ║
║  2. Kompletter Qualitäts-Scan                     ║
║  3. Quartalsweise Verarbeitung                    ║
║  4. Stapelverarbeitung von Dokumenten             ║
║  5. Einzeldokument verarbeiten                    ║
║  6. Tag-Analyse und Bereinigung                   ║
║  7. Berichte generieren                           ║
║  8. Verbindungen testen                           ║
║                                                    ║
║  0. Beenden                                        ║
╚════════════════════════════════════════════════════╝
```

## Detaillierte Funktionsbeschreibungen

### Option 1: Email-Anhänge abrufen

**Zweck**: Lädt Dokumente aus konfigurierten Email-Konten (GMAIL1, GMAIL2, IONOS)

**Verwendung**:
```bash
python run.py --fetch-email-attachments
```

**Optionen**:
- `--email-account NAME`: Nur von spezifischem Konto abrufen
- `--since-days N`: Nur Emails der letzten N Tage
- `--since-date YYYY-MM-DD`: Nur Emails nach diesem Datum
- `--dry-run`: Zeigt was heruntergeladen würde ohne es zu tun

**Beispiel**:
```bash
# Emails der letzten 7 Tage von Gmail Account 1
python run.py --fetch-email-attachments --email-account "Gmail Account 1" --since-days 7
```

### Option 2: Kompletter Qualitäts-Scan

**Zweck**: Prüft alle Dokumente in Paperless auf Qualitätsprobleme

**Was wird geprüft**:
- OCR-Text vorhanden und > 50 Zeichen
- Korrespondent zugewiesen
- Dokumenttyp festgelegt
- Tags vorhanden
- Metadaten vollständig

**Ausgabe**: CSV-Datei mit Zeitstempel
```
reports/quality_scans/quality_scan_2025-01-15_14-30-00.csv
```

**CSV-Inhalt**:
- `document_id`: Dokument-ID in Paperless
- `title`: Dokumenttitel
- `ocr_status`: success/failed/empty
- `missing_fields`: Liste fehlender Felder
- `needs_reprocessing`: true/false
- `error_details`: Detaillierte Fehlerbeschreibung

### Option 3: Quartalsweise Verarbeitung

**Zweck**: Verarbeitet alle Dokumente des letzten abgeschlossenen Quartals neu

**Ablauf**:
1. Ermittelt automatisch das letzte abgeschlossene Quartal
2. Lädt alle Dokumente aus diesem Zeitraum
3. Extrahiert Metadaten neu mit LLM
4. Vereinheitlicht Tags (Singular statt Plural)
5. Aktualisiert Dokumente in Paperless

**Beispiel-Quartale**:
- Q1: Januar - März
- Q2: April - Juni
- Q3: Juli - September
- Q4: Oktober - Dezember

### Option 4: Stapelverarbeitung

**Zweck**: Verarbeitet mehrere Dokumente gleichzeitig

**Eingabe-Optionen**:
- Datumsbereich: Von-Bis Datum
- Dokumenten-IDs: Kommagetrennte Liste
- Filter: Nach Korrespondent oder Tags

**Features**:
- Fortschrittsanzeige mit Prozentbalken
- Parallelverarbeitung für bessere Performance
- Fehlertoleranz (einzelne Fehler stoppen nicht die gesamte Verarbeitung)
- Zusammenfassungsbericht am Ende

### Option 5: Einzeldokument verarbeiten

**Zweck**: Verarbeitet ein einzelnes Dokument mit detailliertem Feedback

**Eingabe**: Dokument-ID aus Paperless

**Ablauf**:
1. Dokument aus Paperless laden
2. OCR-Text extrahieren
3. Metadaten mit LLM anreichern
4. Validierung der Metadaten
5. Dokument in Paperless aktualisieren

**Anzeige**:
- Aktuelle Metadaten
- Extrahierte neue Metadaten
- Validierungsergebnisse
- Update-Status

### Option 6: Tag-Analyse und Bereinigung

**Zweck**: Findet und vereinheitlicht ähnliche Tags

**Funktionen**:
- **Ähnlichkeitsanalyse**: Findet Tags mit >85% Ähnlichkeit
- **Automatische Vorschläge**: 
  - Rechnung + Rechnungen → Rechnung
  - Steuer + Steuern → Steuer
- **Manuelle Bestätigung**: Jede Zusammenführung muss bestätigt werden
- **Batch-Verarbeitung**: Mehrere Tags gleichzeitig bearbeiten

**Ausgabe**: Tag-Analyse-Bericht mit:
- Gefundene Duplikate
- Vorgeschlagene Zusammenführungen
- Durchgeführte Änderungen

### Option 7: Berichte generieren

**Zweck**: Erstellt verschiedene Auswertungen

**Verfügbare Berichte**:
1. **Tagesbericht**: Verarbeitete Dokumente heute
2. **Wochenbericht**: Letzte 7 Tage Aktivität
3. **Monatsbericht**: Monatsübersicht mit Statistiken
4. **Fehleranalyse**: Alle Fehler der letzten 30 Tage
5. **Performance-Report**: Verarbeitungszeiten und Durchsatz

**Formate**:
- CSV für Excel-Import
- JSON für technische Auswertung
- HTML für Präsentation

### Option 8: Verbindungen testen

**Zweck**: Prüft alle Systemverbindungen

**Was wird getestet**:
- ✅ Paperless API (http://192.168.178.76:8010/api)
- ✅ Ollama LLM (localhost:11434)
- ✅ OpenAI API (Fallback)
- ✅ Email-Konten (GMAIL1, GMAIL2, IONOS)

**Ausgabe**:
```
Verbindungstests:
[✓] Paperless API: Verbunden (87 Dokumente)
[✓] Ollama: Online (llama3.1:8b)
[✓] OpenAI: Bereit (GPT-3.5-turbo)
[✓] Gmail Account 1: 23 neue Emails
[✓] Gmail Account 2: 5 neue Emails
[✓] IONOS: 12 neue Emails
```

## Arbeitsabläufe

### Workflow 1: Tägliche Dokumentverarbeitung

1. **Morgens**: Email-Anhänge abrufen (Option 1)
2. **Verarbeitung**: Stapelverarbeitung neuer Dokumente (Option 4)
3. **Qualitätskontrolle**: Qualitäts-Scan durchführen (Option 2)
4. **Nachbearbeitung**: Fehlerhafte Dokumente einzeln bearbeiten (Option 5)
5. **Abschluss**: Tagesbericht generieren (Option 7)

### Workflow 2: Quartalsabschluss

1. **Tag-Bereinigung**: Tag-Analyse durchführen (Option 6)
2. **Quartalsverarbeitung**: Alle Dokumente neu verarbeiten (Option 3)
3. **Qualitätssicherung**: Kompletter Qualitäts-Scan (Option 2)
4. **Dokumentation**: Quartalsbericht erstellen (Option 7)

### Workflow 3: Problembehandlung

1. **Diagnose**: Verbindungen testen (Option 8)
2. **Fehlersuche**: Fehleranalyse-Bericht (Option 7)
3. **Korrektur**: Betroffene Dokumente einzeln verarbeiten (Option 5)
4. **Validierung**: Qualitäts-Scan der korrigierten Dokumente (Option 2)

## Geschäftsregeln

### Wichtige Regeln für die Metadatenextraktion

1. **Empfänger-Regel**: 
   - Daniel Schindler / EBN Veranstaltungen und Consulting GmbH ist IMMER der Empfänger
   - Diese werden NIEMALS als Absender/Korrespondent eingetragen

2. **Korrespondent-Bestimmung**:
   - Korrespondent = Absender des Dokuments
   - Bei Rechnungen: Das Unternehmen, das die Rechnung stellt
   - Bei Briefen: Der Absender des Briefs

3. **Dokumenttyp-Klassifizierung** (Deutsch):
   - Rechnung
   - Vertrag
   - Korrespondenz
   - Steuerunterlagen
   - Versicherungsunterlagen
   - Bankunterlagen
   - Bestellung
   - Lieferschein
   - Mahnung
   - Angebot

4. **Dateinamens-Format**:
   ```
   YYYY-MM-DD_Absender_Dokumenttyp
   Beispiel: 2025-01-15_Telekom_Rechnung
   ```

5. **Tag-Regeln**:
   - 3-7 deutsche Schlüsselwörter
   - Singular bevorzugt (Rechnung statt Rechnungen)
   - Substantive großgeschrieben
   - Keine Sonderzeichen außer Bindestrich

6. **Beschreibungs-Regeln**:
   - Maximal 128 Zeichen
   - Prägnante Zusammenfassung auf Deutsch
   - Keine vertraulichen Informationen

## Fehlerbehebung

### Problem: "Keine Verbindung zu Paperless API"

**Lösung**:
1. Prüfen Sie die Netzwerkverbindung
2. Verifizieren Sie die API-URL: `http://192.168.178.76:8010/api`
3. Prüfen Sie den API-Token in der Konfiguration
4. Testen Sie mit Option 8 (Verbindungen testen)

### Problem: "OCR-Text leer oder zu kurz"

**Lösung**:
1. Dokument in Paperless manuell neu verarbeiten
2. OCR-Einstellungen in Paperless prüfen
3. Dokumentqualität überprüfen (Scan-Auflösung)
4. Alternative OCR-Engine in Paperless aktivieren

### Problem: "LLM antwortet nicht"

**Lösung**:
1. Ollama-Status prüfen: `ollama list`
2. Ollama neu starten: `ollama serve`
3. Fallback zu OpenAI wird automatisch aktiviert
4. API-Keys in .env-Datei prüfen

### Problem: "Falscher Korrespondent zugewiesen"

**Lösung**:
1. Geschäftsregeln prüfen (Daniel/EBN niemals als Absender)
2. Dokument mit Option 5 einzeln neu verarbeiten
3. Validierung aktivieren für kritische Dokumente
4. Manuelle Korrektur in Paperless

### Problem: "Tags werden nicht vereinheitlicht"

**Lösung**:
1. Ähnlichkeitsschwelle anpassen (Standard: 85%)
2. Tag-Analyse mit Option 6 durchführen
3. Manuelle Tag-Zuordnung in Paperless
4. Tag-Mapping-Regeln erweitern

## Häufig gestellte Fragen (FAQ)

### F: Wie oft sollte ich Email-Anhänge abrufen?
**A**: Empfohlen: 2-3x täglich oder nach Bedarf. Die Anwendung merkt sich bereits verarbeitete Emails.

### F: Was bedeutet "OCR-Status: failed"?
**A**: Der OCR-Text ist leer oder unter 50 Zeichen. Das Dokument sollte in Paperless neu verarbeitet werden.

### F: Kann ich mehrere Quartale gleichzeitig verarbeiten?
**A**: Nein, aus Performance-Gründen wird immer nur ein Quartal verarbeitet. Führen Sie die Funktion mehrmals aus.

### F: Werden Originaldokumente verändert?
**A**: Nein, nur die Metadaten in Paperless werden aktualisiert. Die PDF-Dateien bleiben unverändert.

### F: Was passiert bei einem Fehler während der Stapelverarbeitung?
**A**: Einzelne Fehler werden protokolliert, die Verarbeitung läuft weiter. Am Ende erhalten Sie einen Fehlerbericht.

### F: Wie kann ich die LLM-Kosten kontrollieren?
**A**: Ollama läuft lokal ohne Kosten. OpenAI wird nur als Fallback verwendet. Kosten werden im Log angezeigt.

### F: Kann ich eigene Dokumenttypen hinzufügen?
**A**: Ja, in Paperless können Sie neue Dokumenttypen anlegen. Diese werden automatisch erkannt.

### F: Wie lange dauert ein kompletter Qualitäts-Scan?
**A**: Je nach Anzahl der Dokumente: 100 Dokumente ≈ 2-3 Minuten, 1000 Dokumente ≈ 20-30 Minuten.

### F: Werden gelöschte Emails erneut verarbeitet?
**A**: Nein, die Anwendung merkt sich die Message-IDs bereits verarbeiteter Emails.

### F: Kann ich die Verarbeitung unterbrechen?
**A**: Ja, mit Strg+C. Bereits verarbeitete Dokumente bleiben erhalten.

## Support und weitere Hilfe

Bei weiteren Fragen oder Problemen:
1. Prüfen Sie die Logs in `logs/paperless_ngx.log`
2. Konsultieren Sie die API-Dokumentation (API_REFERENCE.md)
3. Überprüfen Sie die Konfiguration in `.env`
4. Führen Sie die Verbindungstests aus (Option 8)

---

*Letzte Aktualisierung: Januar 2025*
*Version: 1.0.0*