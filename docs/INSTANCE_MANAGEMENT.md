# Scandy Instance Management

## Übersicht

Das neue Instance-Management-System ermöglicht es, beliebig viele Scandy-Instanzen mit einem einzigen Skript zu erstellen und zu verwalten.

## Einziges Setup-Skript

### `setup_instance.sh`

Das universelle Setup-Skript fragt nach dem Namen und Ports und erstellt eine vollständig isolierte Instanz.

```bash
./setup_instance.sh
```

### Interaktive Konfiguration

Das Skript fragt nach:

1. **Instance-Name** (z.B. 'verwaltung', 'produktion', 'test')
2. **Ports** (automatisch berechnet oder manuell angepasst)

### Automatische Port-Berechnung

Basierend auf dem Instance-Namen werden Ports automatisch berechnet:

| Instance-Name | Web-Port | MongoDB-Port | Mongo Express |
|---------------|----------|--------------|---------------|
| verwaltung | 5001 | 27018 | 8082 |
| produktion | 5002 | 27019 | 8083 |
| test | 5003 | 27020 | 8084 |

## Einziges Management-Skript

### `manage.sh`

Jede Instanz erhält ein einziges Management-Skript mit allen notwendigen Befehlen.

```bash
# Starten
./manage.sh start

# Stoppen
./manage.sh stop

# Status prüfen
./manage.sh status

# Logs anzeigen
./manage.sh logs

# Update
./manage.sh update

# Backup erstellen
./manage.sh backup

# In Container wechseln
./manage.sh shell

# Hilfe anzeigen
./manage.sh help
```

## Verzeichnisstruktur

```
scandy-[name]/
├── app/                    # Scandy-Anwendung
├── .env                    # Instance-Konfiguration
├── docker-compose.yml      # Docker-Compose für diese Instance
├── manage.sh              # Einziges Management-Skript
├── README.md              # Instance-spezifische Dokumentation
└── mongo-init/            # MongoDB-Initialisierung
```

## Beispiel-Installationen

### Verwaltung
```bash
./setup_instance.sh
# Name: verwaltung
# Ports: 5001, 27018, 8082
```

### Produktion
```bash
./setup_instance.sh
# Name: produktion
# Ports: 5002, 27019, 8083
```

### Test
```bash
./setup_instance.sh
# Name: test
# Ports: 5003, 27020, 8084
```

## Vorteile des neuen Systems

### ✅ **Vereinfachung**
- Nur ein Setup-Skript für alle Instanzen
- Nur ein Management-Skript pro Instanz
- Keine Verwirrung durch multiple Skripte

### ✅ **Flexibilität**
- Beliebig viele Instanzen möglich
- Automatische Port-Berechnung
- Manuelle Port-Anpassung möglich

### ✅ **Isolation**
- Jede Instanz hat eigene Datenbank
- Eigene Container-Namen
- Eigene Netzwerke
- Eigene Volumes

### ✅ **Benutzerfreundlichkeit**
- Interaktive Konfiguration
- Automatische Port-Berechnung
- Klare Dokumentation pro Instanz

## Migration von alten Skripten

### Alte Skripte entfernen
```bash
rm setup_instance2.sh setup_instance2_server.sh setup_instance3.sh
```

### Neue Instanzen erstellen
```bash
./setup_instance.sh
```

## Sicherheitshinweise

### Passwörter ändern
Jede Instanz erhält Standard-Passwörter, die geändert werden sollten:

```bash
# In der .env-Datei der jeweiligen Instanz
MONGO_INITDB_ROOT_PASSWORD=neuesPasswort123
SECRET_KEY=neuerSecretKey123456789
```

### Port-Konflikte vermeiden
- Prüfe vor der Installation, ob Ports frei sind
- Verwende unterschiedliche Ports für verschiedene Instanzen

## Troubleshooting

### Port bereits in Verwendung
```bash
# Prüfe verwendete Ports
netstat -tulpn | grep :5001
netstat -tulpn | grep :27018
```

### Container-Name bereits vergeben
```bash
# Liste alle Container
docker ps -a

# Entferne alte Container
docker rm -f scandy-app-verwaltung
```

### Datenbank-Konflikte
```bash
# Prüfe MongoDB-Verbindungen
docker exec -it scandy-mongodb-verwaltung mongosh
```

## Best Practices

### Naming Convention
- Verwende beschreibende Namen: 'verwaltung', 'produktion', 'test'
- Vermeide Sonderzeichen und Leerzeichen
- Verwende Kleinbuchstaben

### Port-Management
- Verwende automatische Port-Berechnung
- Dokumentiere verwendete Ports
- Prüfe Port-Verfügbarkeit vor Installation

### Backup-Strategie
- Regelmäßige Backups mit `./manage.sh backup`
- Separate Backup-Verzeichnisse pro Instanz
- Teste Backup-Wiederherstellung

### Monitoring
- Überwache Container-Status mit `./manage.sh status`
- Prüfe Logs mit `./manage.sh logs`
- Setze Health-Checks ein 