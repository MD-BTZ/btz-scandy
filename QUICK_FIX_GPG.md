# Schnelle Behebung der GPG-Berechtigungsprobleme

## Problem
```
gpg: '/usr/share/keyrings/mongodb-server-7.0.gpg' kann nicht erzeugt werden: Keine Berechtigung
gpg: Keine gültigen OpenPGP-Daten gefunden.
gpg: Entfernen der ASCII-Hülle ist fehlgeschlagen: Keine Berechtigung
```

## Lösung 1: Automatisches Fix-Script

```bash
# Script ausführbar machen
chmod +x fix_gpg_permissions.sh

# GPG-Probleme beheben
sudo ./fix_gpg_permissions.sh
```

## Lösung 2: Manuelle Schritte

Falls das automatische Script nicht funktioniert, führen Sie diese Schritte manuell aus:

### Schritt 1: Berechtigungen korrigieren
```bash
# Als Root ausführen
sudo su

# Temporäre Verzeichnisse korrigieren
chmod 1777 /tmp
chmod 1777 /var/tmp
chown root:root /tmp
chown root:root /var/tmp

# GPG-Verzeichnis korrigieren
mkdir -p /usr/share/keyrings
chmod 755 /usr/share/keyrings
chown root:root /usr/share/keyrings

# APT-Verzeichnis korrigieren
mkdir -p /etc/apt/sources.list.d
chmod 755 /etc/apt/sources.list.d
chown root:root /etc/apt/sources.list.d
```

### Schritt 2: Vorhandene GPG-Keys löschen
```bash
# Vorhandene Keys löschen
rm -f /usr/share/keyrings/mongodb-server-7.0.gpg
rm -f /etc/apt/sources.list.d/mongodb-org-7.0.list
```

### Schritt 3: GPG-Key manuell herunterladen und importieren
```bash
# Temporäres Verzeichnis erstellen
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# GPG-Key herunterladen
curl -fsSL https://pgp.mongodb.com/server-7.0.asc -o server-7.0.asc

# GPG-Key importieren
gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg server-7.0.asc

# Berechtigungen setzen
chmod 644 /usr/share/keyrings/mongodb-server-7.0.gpg
chown root:root /usr/share/keyrings/mongodb-server-7.0.gpg

# Aufräumen
cd /
rm -rf "$TEMP_DIR"
```

### Schritt 4: Repository erstellen
```bash
# Für Linux Mint 22.x (noble)
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu noble/mongodb-org/7.0 multiverse" > /etc/apt/sources.list.d/mongodb-org-7.0.list

# System aktualisieren
apt update
```

### Schritt 5: MongoDB installieren
```bash
# MongoDB installieren
apt install -y mongodb-org

# MongoDB starten
systemctl enable mongod
systemctl start mongod
```

## Lösung 3: Alternative - Manuelles Installationsscript

Falls die obigen Schritte nicht funktionieren:

```bash
# Manuelles Installationsscript verwenden
chmod +x manual_mongodb_install.sh
sudo ./manual_mongodb_install.sh
```

## Überprüfung

Nach der Behebung können Sie überprüfen, ob alles funktioniert:

```bash
# GPG-Key überprüfen
ls -la /usr/share/keyrings/mongodb-server-7.0.gpg

# Repository testen
apt update

# MongoDB-Status prüfen
systemctl status mongod
```

## Häufige Probleme

### Problem: "Keine Berechtigung" trotz sudo
```bash
# Als Root-Benutzer wechseln
sudo su -

# Dann die Befehle ausführen
```

### Problem: GPG-Key ist ungültig
```bash
# GPG-Key neu herunterladen
curl -fsSL https://pgp.mongodb.com/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg
```

### Problem: Repository-Fehler
```bash
# Repository-Datei neu erstellen
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu noble/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
```

## Support

Falls alle Lösungen fehlschlagen:

1. Führen Sie das Troubleshooting-Script aus: `sudo ./troubleshoot_mongodb.sh`
2. Prüfen Sie die System-Logs: `sudo journalctl -xe`
3. Stellen Sie sicher, dass Sie Root-Rechte haben: `sudo su -` 