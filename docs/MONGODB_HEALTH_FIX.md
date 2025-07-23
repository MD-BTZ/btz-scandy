# MongoDB Health-Check Verbesserungen

## Problem

Bei der Installation auf Servern kam die Meldung:
```
Installation fehlgeschlagen weil der MongoDB scandy Container unhealthy ist
```

**Ursache:** MongoDB braucht länger zum Starten, aber das Installationsskript bricht zu früh ab.

## Lösung

### 1. Verbesserte Wartezeiten

**Vorher:**
- Container-Start: 12 × 5s = 60s
- Health-Check: 15 × 6s = 90s
- **Gesamt:** ~2.5 Minuten

**Jetzt:**
- Container-Start: 30 × 10s = 5 Minuten
- Health-Check: 60 × 10s = 10 Minuten
- Zusätzliche Wartezeit: 30s
- **Gesamt:** ~15 Minuten

### 2. Verbesserte Health-Check-Konfiguration

**Docker Compose Health-Check:**
```yaml
healthcheck:
  test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
  interval: 30s      # Vorher: 10s
  timeout: 30s       # Vorher: 10s
  retries: 10        # Vorher: 15
  start_period: 60s  # Vorher: 30s
```

### 3. Bessere Fehlerbehandlung

**Neue Features:**
- ✅ **Container-Status prüfen** vor Health-Check
- ✅ **Unhealthy-Status erkennen** und Logs anzeigen
- ✅ **Detaillierte Logs** bei Problemen
- ✅ **Graceful Fallback** wenn Health-Check fehlschlägt

## Verwendung

### Neue Installation

```bash
# Installation mit verbesserten Health-Checks
./install_multi_instance.sh -n verwaltung -p 5001 -m 27018 -e 8082
```

### Debug bei Problemen

```bash
# MongoDB Debug-Tool
./debug_mongodb.sh

# Container-Logs anzeigen
docker logs scandy-mongodb-verwaltung -f

# Health-Status prüfen
docker inspect scandy-mongodb-verwaltung | grep -A 10 "Health"
```

## Troubleshooting

### MongoDB startet nicht

1. **Debug-Tool verwenden:**
   ```bash
   ./debug_mongodb.sh
   ```

2. **Container-Logs prüfen:**
   ```bash
   docker logs scandy-mongodb-verwaltung --tail 20
   ```

3. **Port-Konflikte prüfen:**
   ```bash
   lsof -i :27018
   ```

4. **Volume-Probleme:**
   ```bash
   docker volume ls | grep mongodb
   docker volume rm mongodb_data_verwaltung
   ```

### Health-Check schlägt fehl

1. **Mehr Zeit geben:**
   ```bash
   # Installation fortsetzen
   cd verwaltung
   ./manage.sh start
   ```

2. **Manueller Health-Check:**
   ```bash
   docker exec scandy-mongodb-verwaltung mongosh --eval "db.adminCommand('ping')"
   ```

3. **Container neu starten:**
   ```bash
   docker restart scandy-mongodb-verwaltung
   ```

### Installation bricht ab

1. **Manuell fortsetzen:**
   ```bash
   cd verwaltung
   docker compose up -d
   ```

2. **Health-Check überspringen:**
   ```bash
   # Container starten ohne Health-Check
   docker compose up -d mongodb-verwaltung
   sleep 120  # 2 Minuten warten
   docker compose up -d
   ```

## Server-spezifische Anpassungen

### Langsame Server

Für sehr langsame Server können Sie die Wartezeiten erhöhen:

```bash
# Manuell installieren mit mehr Zeit
./install_multi_instance.sh -n verwaltung -p 5001 -m 27018 -e 8082

# Nach Installation mehr Zeit geben
sleep 300  # 5 Minuten warten
cd verwaltung
./manage.sh start
```

### Ressourcen-Probleme

```bash
# Docker-Ressourcen prüfen
docker system df
docker stats

# Nicht benötigte Container/Images löschen
docker system prune -f
```

## Monitoring

### Health-Check-Status überwachen

```bash
# Alle MongoDB Container
docker ps --filter "name=scandy-mongodb" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Health-Status aller Container
for container in $(docker ps --filter "name=scandy-mongodb" --format "{{.Names}}"); do
    echo "$container: $(docker inspect -f '{{.State.Health.Status}}' $container)"
done
```

### Log-Monitoring

```bash
# Live-Logs aller MongoDB Container
for container in $(docker ps --filter "name=scandy-mongodb" --format "{{.Names}}"); do
    echo "=== $container ==="
    docker logs $container --tail 5
done
```

## Best Practices

1. **Geduld haben:** MongoDB braucht Zeit zum Starten
2. **Ressourcen prüfen:** Genug RAM/CPU für MongoDB
3. **Ports planen:** Keine Konflikte zwischen Instanzen
4. **Volumes sauber halten:** Regelmäßige Bereinigung
5. **Monitoring:** Health-Checks überwachen

## Technische Details

### Health-Check-Parameter

- **interval:** Wie oft geprüft wird (30s)
- **timeout:** Maximale Prüfzeit (30s)
- **retries:** Anzahl Versuche (10)
- **start_period:** Wartezeit vor ersten Checks (60s)

### MongoDB-Start-Prozess

1. **Container startet** (0s)
2. **MongoDB initialisiert** (30-60s)
3. **Datenbank erstellt** (60-120s)
4. **Health-Check aktiv** (120s+)
5. **Bereit für Verbindungen** (150s+) 