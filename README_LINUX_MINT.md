# Scandy Linux Mint Installation

## Schnellstart

1. **Repository klonen**
   ```bash
   git clone <repository-url>
   cd scandy
   ```

2. **Skripte ausführbar machen**
   ```bash
   chmod +x install_linux_mint.sh
   chmod +x uninstall_linux_mint.sh
   ```

3. **Installation starten**
   ```bash
   # Empfohlen: Mit sudo für bessere Berechtigungen
   sudo ./install_linux_mint.sh
   
   # Oder ohne sudo (falls Berechtigungsprobleme auftreten)
   ./install_linux_mint.sh
   ```

## Was wird installiert?

- **Python 3** mit Virtual Environment
- **MongoDB 7.0** Datenbank
- **Node.js 18** für CSS-Build
- **Nginx** (optional) als Reverse Proxy
- **UFW** Firewall
- **Systemd Service** für automatischen Start

## Verwaltung

```bash
# Status prüfen
./manage_scandy.sh status

# Logs anzeigen
./manage_scandy.sh logs

# Backup erstellen
./manage_scandy.sh backup

# Update durchführen
./manage_scandy.sh update
```

## Deinstallation

```bash
./uninstall_linux_mint.sh
```

## Dokumentation

Siehe `INSTALL_LINUX_MINT.md` für detaillierte Anweisungen.

## Support

Bei Problemen:
1. Prüfen Sie die Logs: `./manage_scandy.sh logs`
2. Prüfen Sie den Status: `./manage_scandy.sh status`
3. Erstellen Sie ein Backup vor Änderungen 