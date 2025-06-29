# E-Mail-Konfiguration für Scandy

## Aktueller Status

Das E-Mail-System ist derzeit im **Entwicklungsmodus** konfiguriert. Das bedeutet:
- E-Mails werden nicht wirklich versendet
- Stattdessen werden sie in der Konsole/Docker-Logs ausgegeben
- Das System funktioniert vollständig, aber ohne echte E-Mail-Versendung

## E-Mails im Entwicklungsmodus testen

1. Erstellen Sie einen neuen Benutzer mit E-Mail-Adresse
2. Schauen Sie in die Docker-Logs: `docker-compose logs scandy-app`
3. Sie sehen dann eine Ausgabe wie:
```
============================================================
E-MAIL SIMULATION (Entwicklungsmodus)
============================================================
An: test@example.com
Betreff: Ihr Zugang zu Scandy
------------------------------------------------------------
Willkommen bei Scandy!

Ihr initiales Passwort lautet: ABC123
Bitte ändern Sie es nach dem ersten Login.

Viele Grüße
Ihr Scandy-Team
============================================================
```

## Für echte E-Mail-Versendung (Produktion)

### Option 1: Gmail SMTP (Empfohlen)

#### Schritt 1: 2-Faktor-Authentifizierung aktivieren

1. **Gehen Sie zu Ihren Google-Kontoeinstellungen:**
   - Besuchen Sie https://myaccount.google.com/
   - Klicken Sie auf "Sicherheit" in der linken Seitenleiste

2. **2-Schritt-Verifizierung aktivieren:**
   - Scrollen Sie zu "Bei Google anmelden"
   - Klicken Sie auf "2-Schritt-Verifizierung"
   - Folgen Sie den Anweisungen zur Aktivierung
   - Sie können SMS, Authenticator-App oder Sicherheitsschlüssel verwenden

#### Schritt 2: App-Passwort erstellen

**WICHTIG:** Das App-Passwort erscheint nur, wenn 2FA aktiviert ist!

1. **Gehen Sie zu App-Passwörtern:**
   - Besuchen Sie https://myaccount.google.com/security
   - Scrollen Sie zu "Bei Google anmelden"
   - Klicken Sie auf "App-Passwörter" (erscheint nur mit 2FA)

2. **App-Passwort generieren:**
   - Wählen Sie "App auswählen" → "Andere (benutzerdefinierten Namen)"
   - Geben Sie "Scandy" als Namen ein
   - Klicken Sie auf "Generieren"
   - **Kopieren Sie das 16-stellige Passwort** (z.B. "abcd efgh ijkl mnop")

#### Schritt 3: Docker Compose konfigurieren

Ändern Sie die `docker-compose.yml`:

```yaml
environment:
  # ... andere Einstellungen ...
  - MAIL_USERNAME=ihre-email@gmail.com
  - MAIL_PASSWORD=ihr-16-stelliges-app-passwort
  - MAIL_DEFAULT_SENDER=ihre-email@gmail.com
```

### Alternative: Gmail ohne 2FA (weniger sicher)

Falls Sie 2FA nicht aktivieren möchten:

1. **"Weniger sichere Apps" aktivieren:**
   - Gehen Sie zu https://myaccount.google.com/security
   - Scrollen Sie zu "Weniger sichere App-Zugriffe"
   - Aktivieren Sie "Weniger sichere Apps zulassen"

2. **Ihr normales Gmail-Passwort verwenden:**
   ```yaml
   environment:
     - MAIL_USERNAME=ihre-email@gmail.com
     - MAIL_PASSWORD=ihr-normales-gmail-passwort
     - MAIL_DEFAULT_SENDER=ihre-email@gmail.com
   ```

**⚠️ Warnung:** Diese Methode ist weniger sicher und wird von Google nicht empfohlen.

### Option 2: Andere SMTP-Server

Sie können auch andere SMTP-Server verwenden:
```yaml
environment:
  - MAIL_SERVER=smtp.ihr-provider.com
  - MAIL_PORT=587
  - MAIL_USE_TLS=true
  - MAIL_USERNAME=ihre-email@ihr-provider.com
  - MAIL_PASSWORD=ihr-passwort
  - MAIL_DEFAULT_SENDER=ihre-email@ihr-provider.com
```

### Option 3: .env-Datei (Sicherer)

1. Erstellen Sie eine `.env`-Datei im Projektverzeichnis:
   ```
   GMAIL_USERNAME=ihre-email@gmail.com
   GMAIL_APP_PASSWORD=ihr-app-passwort
   ```

2. Ändern Sie die docker-compose.yml:
   ```yaml
   environment:
     - MAIL_USERNAME=${GMAIL_USERNAME}
     - MAIL_PASSWORD=${GMAIL_APP_PASSWORD}
     - MAIL_DEFAULT_SENDER=${GMAIL_USERNAME}
   ```

## E-Mail-Funktionen

Das System unterstützt folgende E-Mail-Funktionen:

1. **Passwort-E-Mail bei Benutzererstellung**
   - Wird automatisch gesendet, wenn eine E-Mail-Adresse angegeben wird

2. **Passwort-Reset-E-Mail**
   - Über `/admin/reset_password` verfügbar

3. **Backup-E-Mail**
   - Kann beim Erstellen von Backups versendet werden

## Troubleshooting

### "App-Passwörter" nicht sichtbar
- **Stellen Sie sicher, dass 2-Faktor-Authentifizierung aktiviert ist**
- App-Passwörter erscheinen nur mit 2FA
- Warten Sie einige Minuten nach der 2FA-Aktivierung

### E-Mails werden nicht versendet
- Prüfen Sie die Docker-Logs: `docker-compose logs scandy-app`
- Stellen Sie sicher, dass die SMTP-Einstellungen korrekt sind
- Testen Sie die SMTP-Verbindung manuell

### Gmail-Fehler
- **Mit App-Passwort:** Stellen Sie sicher, dass 2FA aktiviert ist
- **Ohne App-Passwort:** Aktivieren Sie "Weniger sichere Apps"
- Prüfen Sie, ob das Passwort korrekt kopiert wurde (keine Leerzeichen)

### Firewall-Probleme
- Port 587 (TLS) oder 465 (SSL) muss ausgehend erlaubt sein
- Prüfen Sie Firmen-Firewall-Einstellungen

## Häufige Probleme

### "App-Passwörter" fehlt in Google-Einstellungen
**Lösung:** 2-Faktor-Authentifizierung muss aktiviert sein!

### "Anmeldung fehlgeschlagen" bei Gmail
**Lösung:** 
- App-Passwort korrekt kopiert? (16 Zeichen, keine Leerzeichen)
- 2FA aktiviert?
- "Weniger sichere Apps" aktiviert (falls ohne App-Passwort)?

### E-Mail wird nicht angezeigt
**Lösung:** 
- Prüfen Sie den Spam-Ordner
- Prüfen Sie die Docker-Logs für Fehlermeldungen
- Testen Sie mit einer anderen E-Mail-Adresse 