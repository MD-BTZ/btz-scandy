# Admin-E-Mail-Problem beheben

## Problem

Die Fehlermeldung "Administrator hat keine E-Mail angegeben" tritt auf, wenn:

1. Der Admin-Benutzer keine E-Mail-Adresse in seinem Profil hat
2. Die E-Mail-Einstellungen nicht korrekt konfiguriert sind
3. Die E-Mail-Konfiguration nicht gespeichert werden kann

## Ursachen

### 1. Admin-Benutzer ohne E-Mail-Adresse

Bei der Erstellung des Admin-Benutzers wurde keine E-Mail-Adresse angegeben oder das Feld ist leer.

### 2. Session-Probleme beim Speichern

Session-Konflikte in Multi-Instance-Setups können das Speichern von E-Mail-Einstellungen verhindern.

### 3. Datenbank-Verbindungsprobleme

MongoDB-Verbindungsprobleme können das Speichern von Benutzerdaten verhindern.

## Lösungen

### 1. Admin-E-Mail über Profil-Seite setzen

```bash
# Gehen Sie zur Profil-Seite
http://localhost:5000/auth/profile

# Geben Sie eine E-Mail-Adresse ein
# Klicken Sie auf 'Speichern'
```

### 2. Admin-E-Mail über Benutzerverwaltung setzen

```bash
# Gehen Sie zur Benutzerverwaltung
http://localhost:5000/admin/manage_users

# Klicken Sie auf den Admin-Benutzer zum Bearbeiten
# Geben Sie eine E-Mail-Adresse ein
# Klicken Sie auf 'Speichern'
```

### 3. E-Mail-Einstellungen konfigurieren

```bash
# Gehen Sie zu den E-Mail-Einstellungen
http://localhost:5000/admin/email_settings

# Konfigurieren Sie SMTP-Einstellungen:
# - SMTP-Server: smtp.gmail.com
# - Port: 587
# - TLS: Aktiviert
# - E-Mail-Adresse: Ihre E-Mail
# - Passwort: App-Passwort

# Klicken Sie auf 'Einstellungen speichern'
# Klicken Sie auf 'Test-E-Mail senden'
```

### 4. Manueller Fix über Datenbank

```bash
# Haupt-Instanz
docker exec scandy-mongodb-scandy mongosh --eval "db.users.updateOne({role: 'admin'}, {\$set: {email: 'admin@example.com'}})"

# Verwaltung-Instanz
docker exec scandy-mongodb-verwaltung mongosh --eval "db.users.updateOne({role: 'admin'}, {\$set: {email: 'admin@example.com'}})"

# Test-Instanz
docker exec scandy-mongodb-test_isolated mongosh --eval "db.users.updateOne({role: 'admin'}, {\$set: {email: 'admin@example.com'}})"
```

### 5. Debug-Skript ausführen

```bash
# Führen Sie das Fix-Skript aus
./fix_admin_email.sh
```

## E-Mail-Konfiguration

### Gmail-Konfiguration

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

### Office 365-Konfiguration

- SMTP-Server: `smtp.office365.com`
- Port: `587`
- TLS: Aktiviert
- E-Mail-Adresse: Office 365-Adresse
- Passwort: Normales Passwort oder App-Passwort

## Troubleshooting

### 1. Session-Probleme beheben

```bash
# Sessions bereinigen
./cleanup_sessions.sh

# Container neu starten
./manage.sh restart
```

### 2. Datenbank-Probleme beheben

```bash
# MongoDB-Status prüfen
./debug_mongodb.sh

# Container neu starten
docker compose restart mongodb-scandy
```

### 3. E-Mail-Konfiguration testen

```bash
# Test-E-Mail senden
curl -X POST http://localhost:5000/admin/email_settings \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "action=test&mail_server=smtp.gmail.com&mail_port=587&mail_use_tls=on&mail_username=your@email.com&mail_password=yourpassword&test_email=test@example.com"
```

### 4. Logs prüfen

```bash
# App-Logs prüfen
docker logs scandy-app-scandy -f

# MongoDB-Logs prüfen
docker logs scandy-mongodb-scandy -f
```

## Häufige Fehler

### 1. "Admin-Benutzer hat keine E-Mail-Adresse"

**Lösung**: E-Mail-Adresse für Admin-Benutzer setzen

```bash
# Über Profil-Seite
http://localhost:5000/auth/profile

# Oder über Datenbank
docker exec scandy-mongodb-scandy mongosh --eval "db.users.updateOne({role: 'admin'}, {\$set: {email: 'admin@example.com'}})"
```

### 2. "E-Mail-Konfiguration konnte nicht gespeichert werden"

**Lösung**: Session-Probleme beheben

```bash
# Sessions bereinigen
./cleanup_sessions.sh

# Container neu starten
./manage.sh restart
```

### 3. "SMTP-Verbindung fehlgeschlagen"

**Lösung**: E-Mail-Konfiguration prüfen

```bash
# SMTP-Einstellungen prüfen
http://localhost:5000/admin/email_settings

# App-Passwort für Gmail erstellen
# https://myaccount.google.com/security
```

### 4. "Test-E-Mail konnte nicht versendet werden"

**Lösung**: E-Mail-Konfiguration testen

```bash
# Test-E-Mail senden
http://localhost:5000/admin/email_settings
# Klicken Sie auf "Test-E-Mail senden"
```

## Prävention

### 1. Admin-E-Mail beim Setup setzen

Stellen Sie sicher, dass beim ersten Setup eine E-Mail-Adresse für den Admin-Benutzer angegeben wird.

### 2. E-Mail-Konfiguration dokumentieren

Dokumentieren Sie die E-Mail-Konfiguration für alle Instanzen.

### 3. Regelmäßige Tests

Führen Sie regelmäßig E-Mail-Tests durch, um Probleme früh zu erkennen.

### 4. Backup der E-Mail-Konfiguration

Erstellen Sie Backups der E-Mail-Konfiguration.

## Monitoring

### 1. E-Mail-Status prüfen

```bash
# Admin-E-Mail prüfen
docker exec scandy-mongodb-scandy mongosh --eval "db.users.find({role: 'admin'}, {username: 1, email: 1}).pretty()"

# E-Mail-Einstellungen prüfen
docker exec scandy-mongodb-scandy mongosh --eval "db.settings.find({key: /^email_/}).pretty()"
```

### 2. E-Mail-Logs prüfen

```bash
# App-Logs nach E-Mail-Fehlern durchsuchen
docker logs scandy-app-scandy | grep -i email

# MongoDB-Logs prüfen
docker logs scandy-mongodb-scandy | grep -i error
```

## Fazit

Das Admin-E-Mail-Problem kann durch das Setzen einer E-Mail-Adresse für den Admin-Benutzer und die korrekte Konfiguration der E-Mail-Einstellungen behoben werden. Die bereitgestellten Skripte und Anleitungen sollten alle häufigen Probleme lösen. 