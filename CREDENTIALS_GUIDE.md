# 📋 Credentials Konfiguration - Komplettanleitung

## 🎯 Übersicht
**ALLE Credentials kommen in EINE Datei: `.env`**

## 🚀 Schnellstart

1. **Kopieren Sie die Vorlage:**
```bash
cp .env.example .env
```

2. **Öffnen Sie .env:**
```bash
nano .env
```

3. **Tragen Sie Ihre Daten ein (siehe unten)**

---

## 📧 E-Mail Konfiguration

### Gmail (2 Konten)
```ini
# Gmail Konto 1
GMAIL1_EMAIL=ihre.email1@gmail.com
GMAIL1_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # 16-stelliges App-Passwort!

# Gmail Konto 2
GMAIL2_EMAIL=ihre.email2@gmail.com
GMAIL2_APP_PASSWORD=yyyy-yyyy-yyyy-yyyy  # 16-stelliges App-Passwort!
```

**⚠️ WICHTIG: Gmail App-Passwort erstellen:**
1. Gehen Sie zu: https://myaccount.google.com/apppasswords
2. 2-Faktor-Authentifizierung MUSS aktiviert sein!
3. Klicken Sie auf "App auswählen" → "Mail"
4. Klicken Sie auf "Gerät auswählen" → "Anderes"
5. Geben Sie einen Namen ein (z.B. "Paperless NGX")
6. Klicken Sie auf "Generieren"
7. **Kopieren Sie das 16-stellige Passwort** (Format: xxxx-xxxx-xxxx-xxxx)
8. Verwenden Sie DIESES Passwort in .env, NICHT Ihr normales Gmail-Passwort!

### IONOS Mail
```ini
# IONOS Konto
IONOS_EMAIL=ihre.email@ihre-domain.de
IONOS_PASSWORD=ihr_ionos_passwort
```

**IONOS Einstellungen:**
- Server: `imap.ionos.de`
- Port: 993 (SSL/TLS)
- Verwenden Sie Ihr normales IONOS E-Mail-Passwort

---

## 📄 Paperless NGX API

```ini
# Paperless NGX
PAPERLESS_URL=http://192.168.178.76:8010/api
PAPERLESS_API_TOKEN=xxxxxxxxxxxxxxxxxxxxx
```

**Token erstellen:**
1. Loggen Sie sich in Paperless NGX ein
2. Gehen Sie zu: Einstellungen → API Token
3. Klicken Sie auf "Token erstellen"
4. Kopieren Sie den generierten Token
5. Fügen Sie ihn in .env ein

---

## 🤖 KI/AI APIs

### OpenAI (für GPT Modelle)
```ini
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
```

**API Key erstellen:**
1. Gehen Sie zu: https://platform.openai.com/api-keys
2. Klicken Sie auf "Create new secret key"
3. Kopieren Sie den Key (beginnt mit `sk-`)
4. Fügen Sie ihn in .env ein

### Ollama (Lokal)
```ini
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

---

## 📁 Sonstige Einstellungen

```ini
# E-Mail Download Ordner
EMAIL_DOWNLOAD_DIR=./downloads/email_attachments

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/paperless.log

# Verarbeitung
EMAIL_CHECK_INTERVAL=300  # Sekunden (5 Minuten)
MAX_RETRIES=3
TIMEOUT=30
```

---

## ✅ Vollständiges .env Beispiel

```ini
# === E-MAIL KONTEN ===
GMAIL1_EMAIL=max.mustermann@gmail.com
GMAIL1_APP_PASSWORD=abcd-efgh-ijkl-mnop

GMAIL2_EMAIL=firma.gmbh@gmail.com
GMAIL2_APP_PASSWORD=qrst-uvwx-yzab-cdef

IONOS_EMAIL=info@meine-firma.de
IONOS_PASSWORD=mein_sicheres_passwort

# === PAPERLESS NGX ===
PAPERLESS_URL=http://192.168.178.76:8010/api
PAPERLESS_API_TOKEN=a1b2c3d4e5f6g7h8i9j0

# === KI/AI ===
OPENAI_API_KEY=sk-proj-1234567890abcdefghij
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# === VERZEICHNISSE ===
EMAIL_DOWNLOAD_DIR=./downloads/email_attachments
LOG_FILE=./logs/paperless.log

# === SETTINGS ===
LOG_LEVEL=INFO
EMAIL_CHECK_INTERVAL=300
MAX_RETRIES=3
TIMEOUT=30
```

---

## 🔒 Sicherheitshinweise

1. **NIEMALS .env in Git committen!** (ist in .gitignore)
2. **Verwenden Sie starke, einzigartige Passwörter**
3. **Rotieren Sie API Keys regelmäßig**
4. **Für Gmail: NUR App-Passwörter verwenden**
5. **Teilen Sie .env niemals mit anderen**

---

## 🐛 Fehlerbehebung

### Gmail funktioniert nicht
- ✅ 2-Faktor-Authentifizierung aktiviert?
- ✅ App-Passwort verwendet (nicht normales Passwort)?
- ✅ Korrekte Formatierung (xxxx-xxxx-xxxx-xxxx)?

### IONOS funktioniert nicht
- ✅ IMAP in IONOS aktiviert?
- ✅ Richtiger Server (imap.ionos.de)?
- ✅ Port 993 mit SSL/TLS?

### Paperless NGX Verbindung fehlgeschlagen
- ✅ Ist Paperless NGX erreichbar?
- ✅ Token korrekt kopiert?
- ✅ URL mit /api am Ende?

### OpenAI API Fehler
- ✅ Gültiger API Key?
- ✅ Guthaben vorhanden?
- ✅ Rate Limits beachtet?

---

## 📞 Support

Bei Problemen prüfen Sie:
1. Diese Anleitung nochmal genau
2. Die Logs in `./logs/`
3. Die Fehlermeldungen beim Start