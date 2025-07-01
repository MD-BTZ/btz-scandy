# E-Mail-Konfiguration für Scandy

## Neue Weboberfläche für E-Mail-Einstellungen

Scandy bietet jetzt eine benutzerfreundliche Weboberfläche zur Konfiguration des E-Mail-Systems. Sie können die E-Mail-Einstellungen direkt in der Anwendung verwalten, ohne die Docker Compose Datei zu bearbeiten.

### Zugriff auf E-Mail-Einstellungen

1. **Anmelden** als Administrator
2. **Admin-Menü** öffnen (Hamburger-Menü oben rechts)
3. **E-Mail-Einstellungen** auswählen

### E-Mail-Einstellungen konfigurieren

#### 1. E-Mail-System aktivieren
- Aktivieren Sie das Kontrollkästchen "E-Mail-System aktivieren"
- Ohne Aktivierung werden E-Mails nur in der Konsole ausgegeben (Entwicklungsmodus)

#### 2. SMTP-Einstellungen
- **SMTP-Server**: z.B. `smtp.gmail.com`, `smtp.office365.com`
- **SMTP-Port**: `587` (TLS) oder `465` (SSL)
- **TLS verwenden**: Aktivieren für sichere Verbindungen (empfohlen)

#### 3. Anmeldedaten
- **E-Mail-Adresse**: Ihre E-Mail-Adresse für SMTP
- **Passwort/App-Passwort**: Ihr Passwort oder App-Passwort
- **Absender-E-Mail**: E-Mail-Adresse, die als Absender angezeigt wird

#### 4. Einstellungen speichern
- Klicken Sie auf "Einstellungen speichern"
- Die Konfiguration wird sofort aktiviert
- Kein Neustart der Anwendung erforderlich

#### 5. E-Mail-Test
- Klicken Sie auf "E-Mail-Test senden"
- Eine Test-E-Mail wird an Ihre Absender-Adresse gesendet
- Überprüfen Sie, ob die E-Mail ankommt

## Unterstützte E-Mail-Anbieter

### Gmail (Empfohlen)
1. **2-Faktor-Authentifizierung aktivieren**
   - Gehen Sie zu https://myaccount.google.com/security
   - Aktivieren Sie "2-Schritt-Verifizierung"

2. **App-Passwort erstellen**
   - Gehen Sie zu https://myaccount.google.com/security
   - Klicken Sie auf "App-Passwörter"
   - Wählen Sie "Andere (benutzerdefinierten Namen)"
   - Geben Sie "Scandy" als Namen ein
   - Kopieren Sie das 16-stellige Passwort

3. **Einstellungen in Scandy**
   - SMTP-Server: `smtp.gmail.com`
   - Port: `587`
   - TLS: Aktiviert
   - E-Mail-Adresse: Ihre Gmail-Adresse
   - Passwort: Das 16-stellige App-Passwort

### Office 365
1. **Einstellungen in Scandy**
   - SMTP-Server: `smtp.office365.com`
   - Port: `587`
   - TLS: Aktiviert
   - E-Mail-Adresse: Ihre Office 365-Adresse
   - Passwort: Ihr normales Passwort oder App-Passwort

### Andere Anbieter
- Prüfen Sie die SMTP-Einstellungen Ihres E-Mail-Anbieters
- Verwenden Sie die entsprechenden Server- und Port-Einstellungen

## E-Mail-Funktionen

Das System unterstützt folgende E-Mail-Funktionen:

1. **Passwort-E-Mail bei Benutzererstellung**
   - Wird automatisch gesendet, wenn eine E-Mail-Adresse angegeben wird

2. **Passwort-Reset-E-Mail**
   - Über `/admin/reset_password` verfügbar

3. **Backup-E-Mail**
   - Kann beim Erstellen von Backups versendet werden

4. **E-Mail-Test**
   - Über die E-Mail-Einstellungen verfügbar

## Troubleshooting

### E-Mail-Test fehlgeschlagen
- **Prüfen Sie die SMTP-Einstellungen**
- **Gmail**: Stellen Sie sicher, dass 2FA aktiviert ist und ein App-Passwort verwendet wird
- **Office 365**: Prüfen Sie, ob das Passwort korrekt ist
- **Firewall**: Port 587 oder 465 muss ausgehend erlaubt sein

### E-Mails werden nicht versendet
- **E-Mail-System aktiviert**: Stellen Sie sicher, dass das E-Mail-System aktiviert ist
- **Anmeldedaten**: Prüfen Sie E-Mail-Adresse und Passwort
- **SMTP-Server**: Stellen Sie sicher, dass der Server korrekt ist
- **Logs prüfen**: Schauen Sie in die Anwendungs-Logs für Fehlermeldungen

### Gmail-spezifische Probleme
- **"App-Passwörter" nicht sichtbar**: 2-Faktor-Authentifizierung muss aktiviert sein
- **"Anmeldung fehlgeschlagen"**: App-Passwort korrekt kopiert? (16 Zeichen, keine Leerzeichen)

## Fallback auf Umgebungsvariablen

Falls keine E-Mail-Konfiguration in der Datenbank gespeichert ist, verwendet Scandy weiterhin die Umgebungsvariablen aus der Docker Compose Datei:

```yaml
environment:
  - MAIL_SERVER=smtp.gmail.com
  - MAIL_PORT=587
  - MAIL_USE_TLS=true
  - MAIL_USERNAME=ihre-email@gmail.com
  - MAIL_PASSWORD=ihr-app-passwort
  - MAIL_DEFAULT_SENDER=ihre-email@gmail.com
```

## Sicherheit

- **Passwörter werden verschlüsselt** in der Datenbank gespeichert
- **TLS-Verschlüsselung** wird für alle SMTP-Verbindungen verwendet
- **App-Passwörter** werden für Gmail empfohlen
- **Regelmäßige Überprüfung** der E-Mail-Einstellungen empfohlen

## Migration von Docker Compose

Wenn Sie bereits E-Mail-Einstellungen in der Docker Compose Datei haben:

1. **E-Mail-Einstellungen in Scandy öffnen**
2. **Einstellungen aus Docker Compose übertragen**
3. **E-Mail-Test durchführen**
4. **Einstellungen speichern**
5. **Docker Compose E-Mail-Einstellungen entfernen** (optional)

Die Weboberfläche bietet eine benutzerfreundlichere und flexiblere Möglichkeit zur E-Mail-Konfiguration. 