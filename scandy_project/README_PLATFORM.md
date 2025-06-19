# Scandy - Plattformübergreifende Installation

## 🚀 Übersicht

Diese Version von Scandy wurde für maximale Kompatibilität auf allen Plattformen optimiert:

- ✅ **Windows** (10/11)
- ✅ **macOS** (Intel/Apple Silicon)
- ✅ **Linux** (Ubuntu, Debian, CentOS, etc.)

## 🔄 Entwicklung vs. Produktion

**Entwicklung (lokal):**
- Ports in der `docker-compose.yml` an `127.0.0.1` binden:
  ```yaml
  ports:
    - "127.0.0.1:5000:5000"
    - "127.0.0.1:27017:27017"
    - "127.0.0.1:8081:8081"
  ```
- Zugriff nur von deinem Rechner möglich (sicher für Entwicklung).

**Produktion/Serverbetrieb:**
- Ports **ohne** IP binden, damit die Dienste über die externe/Netzwerk-IP erreichbar sind:
  ```yaml
  ports:
    - "5000:5000"
    - "27017:27017"
    - "8081:8081"
  ```
- Zugriff im lokalen Netzwerk oder (bei Portfreigabe) auch von außen möglich.
- Aufruf im Browser: `http://<SERVER-IP>:5000`

**Tipp:**
- Für maximale Sicherheit in der Produktion: Firewall-Regeln setzen und ggf. HTTPS/Reverse Proxy nutzen.

## 🔧 Was wurde geändert?

### 1. Docker-Compose Optimierungen

**Explizite IPv4-Bindung (nur Entwicklung):**
```yaml
ports:
  - "127.0.0.1:5000:5000"  # Entwicklung
```
**Offene Ports (Produktion/Server):**
```yaml
ports:
  - "5000:5000"  # Produktion/Server
```

**IPv6-Unterstützung:**
```yaml
command: mongod --auth --bind_ip_all --ipv6
```

**Explizites Netzwerk-Subnetz:**
```yaml
networks:
  scandy-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### 2. Intelligente MongoDB-URI-Erkennung

Die Konfiguration erkennt automatisch die beste Verbindungsmethode:

1. **Umgebungsvariable** (höchste Priorität)
2. **Docker-Umgebung** (Container-Name)
3. **Plattformspezifische Fallbacks**

```python
def get_mongodb_uri():
    # 1. Prüfe Umgebungsvariable
    env_uri = os.environ.get('MONGODB_URI')
    if env_uri:
        return env_uri
    # 2. Prüfe Docker-Umgebung
    if os.environ.get('DATABASE_MODE') == 'mongodb':
        return 'mongodb://admin:admin@scandy-mongodb:27017/'
    # 3. Plattformspezifische Fallbacks
    return 'mongodb://localhost:27017/'  # Funktioniert überall
```

## 🚀 Installation

### Windows
```batch
# Verwende das plattformübergreifende Skript
start_cross_platform.bat

# Oder klassisch
start.bat
```

### Linux/macOS
```bash
# Mache das Skript ausführbar
chmod +x start_cross_platform.sh

# Starte
./start_cross_platform.sh

# Oder klassisch
./start.sh
```

### Docker Compose (alle Plattformen)
```bash
# Automatische Erkennung der besten Methode
docker-compose up -d --build

# Oder neue Syntax
docker compose up -d --build
```

## 🌐 Zugriff

Nach dem Start sind folgende URLs verfügbar:

| Service | URL | Alternative |
|---------|-----|-------------|
| **Scandy App** | http://localhost:5000 | http://<SERVER-IP>:5000 |
| **Mongo Express** | http://localhost:8081 | http://<SERVER-IP>:8081 |
| **MongoDB** | localhost:27017 | <SERVER-IP>:27017 |

## 🔍 Verbindungstests

Die Start-Skripte führen automatisch Verbindungstests durch:

1. **Docker-Installation** prüfen
2. **Docker Compose** Verfügbarkeit testen
3. **Container** starten
4. **Services** auf Erreichbarkeit testen
5. **Fallback-Mechanismen** bei Problemen

## 🛠️ Fehlerbehebung

### Problem: "localhost funktioniert, aber 127.0.0.1 nicht"

**Lösung:** Die neue Konfiguration verwendet explizite IPv4-Bindung für Entwicklung und offene Ports für Produktion.

### Problem: Docker Compose nicht gefunden

**Lösung:** Automatische Erkennung unterstützt beide Syntaxen:
- `docker-compose` (klassisch)
- `docker compose` (neu)

### Problem: Netzwerk-Konflikte

**Lösung:** Explizites Subnetz verhindert Konflikte:
```yaml
networks:
  scandy-network:
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

## 📊 Monitoring

### Container-Status prüfen
```bash
# Windows
docker-compose ps

# Linux/macOS
docker compose ps
```

### Logs anzeigen
```bash
# Alle Services
docker-compose logs

# Spezifischer Service
docker-compose logs scandy-app
docker-compose logs scandy-mongodb
```

### Health Checks
Die Container haben automatische Health Checks:
- **MongoDB:** Ping-Test alle 30s
- **App:** HTTP-Health-Check alle 30s

## 🔧 Konfiguration anpassen

### Umgebungsvariablen
```bash
# Windows
set MONGODB_URI=mongodb://localhost:27017/
set MONGODB_DB=scandy

# Linux/macOS
export MONGODB_URI=mongodb://localhost:27017/
export MONGODB_DB=scandy
```

### Docker Compose anpassen
```yaml
environment:
  - MONGODB_URI=mongodb://admin:admin@scandy-mongodb:27017/
  - MONGODB_DB=scandy
  - FLASK_ENV=production
```

## 🎯 Vorteile der neuen Lösung

1. **Plattformunabhängig:** Funktioniert auf Windows, macOS, Linux
2. **Robust:** Automatische Fallback-Mechanismen
3. **Intelligent:** Erkennt automatisch die beste Konfiguration
4. **Sicher:** Explizite IPv4-Bindung verhindert IPv6-Konflikte (Entwicklung), offene Ports für Serverbetrieb
5. **Monitoring:** Automatische Health Checks und Verbindungstests
6. **Debugging:** Detaillierte Logs und Fehlerbehandlung

## 📝 Bekannte Probleme und Lösungen

### Windows: WSL2-Probleme
```bash
# In WSL2: Verwende localhost statt 127.0.0.1
export MONGODB_URI=mongodb://localhost:27017/
```

### macOS: Docker Desktop
```bash
# Docker Desktop für Mac: localhost funktioniert am besten
# Keine spezielle Konfiguration nötig
```

### Linux: Firewall-Probleme
```bash
# Ports freigeben (falls nötig)
sudo ufw allow 5000
sudo ufw allow 27017
sudo ufw allow 8081
```

## 🚀 Nächste Schritte

1. **Start-Skript ausführen:** `./start_cross_platform.sh` oder `start_cross_platform.bat`
2. **Verbindungstests abwarten:** Automatische Prüfung aller Services
3. **Browser öffnen:** http://localhost:5000 oder http://<SERVER-IP>:5000
4. **Erste Anmeldung:** Admin-Account erstellen

Die Anwendung ist jetzt auf allen Plattformen und im Netzwerk zuverlässig verfügbar! 🎉 