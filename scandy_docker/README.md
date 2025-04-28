# Scandy Docker Installation

## Voraussetzungen
- Docker
- Docker Compose
- Bash Shell

## Installation

1. Entpacken Sie das Archiv:
```bash
tar -xzf scandy_docker.tar.gz
cd scandy_docker
```

2. Machen Sie das Startskript ausführbar:
```bash
chmod +x docker-start.sh
```

3. Starten Sie die Anwendung:
```bash
./docker-start.sh
```

## Verzeichnisstruktur
- `Dockerfile` - Docker-Konfiguration
- `docker-compose.yml` - Container-Konfiguration
- `docker-start.sh` - Startskript
- `.dockerignore` - Auszuschließende Dateien
- `requirements.txt` - Python-Abhängigkeiten
- `app_structure.md` - Dokumentation

## Wichtige Hinweise
- Die Anwendung läuft standardmäßig auf Port 5000
- Die Datenbank wird im Verzeichnis `database` gespeichert
- Backups werden im Verzeichnis `backups` gespeichert
- Logs werden im Verzeichnis `logs` gespeichert

## Fehlerbehebung
Bei Problemen:
1. Prüfen Sie die Logs: `docker-compose logs`
2. Überprüfen Sie die Container: `docker ps`
3. Starten Sie die Container neu: `docker-compose restart`

## Sicherheit
- Der Secret Key wird automatisch generiert
- Die Datenbank ist nur im Container zugänglich
- Externe Verbindungen sind auf Port 5000 beschränkt 