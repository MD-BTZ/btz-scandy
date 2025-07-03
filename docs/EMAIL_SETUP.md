# E-Mail-Konfiguration für Scandy

## Weboberfläche für E-Mail-Einstellungen

Die E-Mail-Einstellungen können über die Weboberfläche konfiguriert werden.

### Zugriff auf E-Mail-Einstellungen

1. Als Administrator anmelden
2. Admin-Menü öffnen (Hamburger-Menü oben rechts)
3. E-Mail-Einstellungen auswählen

### E-Mail-Einstellungen konfigurieren

#### 1. E-Mail-System aktivieren
- Kontrollkästchen "E-Mail-System aktivieren" aktivieren
- Ohne Aktivierung werden E-Mails nur in der Konsole ausgegeben

#### 2. SMTP-Einstellungen
- **SMTP-Server**: z.B. `smtp.gmail.com`, `smtp.office365.com`
- **SMTP-Port**: `587` (TLS) oder `465` (SSL)
- **TLS verwenden**: Aktivieren für sichere Verbindungen

#### 3. Anmeldedaten
- **E-Mail-Adresse**: E-Mail-Adresse für SMTP
- **Passwort/App-Passwort**: Passwort oder App-Passwort
- **Absender-E-Mail**: E-Mail-Adresse, die als Absender angezeigt wird

#### 4. Einstellungen speichern
- "Einstellungen speichern" klicken
- Konfiguration wird sofort aktiviert

#### 5. E-Mail-Test
- "E-Mail-Test senden" klicken
- Test-E-Mail wird an die Absender-Adresse gesendet

## Unterstützte E-Mail-Anbieter

### Gmail
1. **2-Faktor-Authentifizierung aktivieren**
   - https://myaccount.google.com/security
   - "2-Schritt-Verifizierung" aktivieren

2. **App-Passwort erstellen**
   - https://myaccount.google.com/security
   - "App-Passwörter" klicken
   - "Andere (benutzerdefinierten Namen)" wählen
   - "Scandy" als Namen eingeben
   - 16-stelliges Passwort kopieren

3. **Einstellungen in Scandy**
   - SMTP-Server: `smtp.gmail.com`
   - Port: `587`
   - TLS: Aktiviert
   - E-Mail-Adresse: Gmail-Adresse
   - Passwort: 16-stelliges App-Passwort

### Office 365
- SMTP-Server: `smtp.office365.com`
- Port: `587`
- TLS: Aktiviert
- E-Mail-Adresse: Office 365-Adresse
- Passwort: Normales Passwort oder App-Passwort

## E-Mail-Funktionen

- Passwort-E-Mail bei Benutzererstellung
- Passwort-Reset-E-Mail über `/admin/reset_password`
- Backup-E-Mail beim Erstellen von Backups
- E-Mail-Test über die E-Mail-Einstellungen

## Troubleshooting

### E-Mail-Test fehlgeschlagen
- SMTP-Einstellungen prüfen
- Gmail: 2FA aktiviert und App-Passwort verwenden
- Office 365: Passwort korrekt?
- Firewall: Port 587 oder 465 ausgehend erlauben

### E-Mails werden nicht versendet
- E-Mail-System aktiviert?
- Anmeldedaten korrekt?
- SMTP-Server korrekt?
- Anwendungs-Logs für Fehlermeldungen prüfen

### Gmail-spezifische Probleme
- "App-Passwörter" nicht sichtbar: 2FA muss aktiviert sein
- "Anmeldung fehlgeschlagen": App-Passwort korrekt kopiert?

## Fallback auf Umgebungsvariablen

Falls keine E-Mail-Konfiguration in der Datenbank gespeichert ist, werden die Umgebungsvariablen aus der Docker Compose Datei verwendet:

```yaml
environment:
  - MAIL_SERVER=smtp.gmail.com
  - MAIL_PORT=587
  - MAIL_USE_TLS=true
  - MAIL_USERNAME=ihre-email@gmail.com
  - MAIL_PASSWORD=ihr-app-passwort
  - MAIL_DEFAULT_SENDER=ihre-email@gmail.com
```

## Migration von Docker Compose

Bei bestehenden E-Mail-Einstellungen in der Docker Compose Datei:

1. E-Mail-Einstellungen in Scandy öffnen
2. Einstellungen aus Docker Compose übertragen
3. E-Mail-Test durchführen
4. Einstellungen speichern
5. Docker Compose E-Mail-Einstellungen entfernen (optional) 