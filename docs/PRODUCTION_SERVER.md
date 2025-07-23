# Produktionsserver-Konfiguration

## Problem
Die Anwendung verwendet den Flask-Entwicklungsserver, was zu folgender Warnung führt:
```
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
```

## Warum ist das wichtig?

### Flask-Entwicklungsserver (aktuell)
- ❌ **Nicht für Produktion** gedacht
- ❌ **Performance-Limitationen** (nur ein Thread)
- ❌ **Sicherheitsrisiken** (Debug-Modus, unsichere Konfiguration)
- ❌ **Nicht für hohe Last** ausgelegt
- ❌ **Keine Worker-Prozesse**

### Produktions-WSGI-Server (empfohlen)
- ✅ **Für Produktion** optimiert
- ✅ **Multi-Worker** Unterstützung
- ✅ **Bessere Performance** und Skalierbarkeit
- ✅ **Sicherheitsfeatures**
- ✅ **Stabilität** bei hoher Last

## Lösungsoptionen

### Option 1: Gunicorn (Empfohlen für Linux)

#### Vorteile:
- **Hochperformant** und stabil
- **Multi-Worker** Unterstützung
- **Automatische Worker-Verwaltung**
- **Umfassende Konfigurationsoptionen**

#### Konfiguration:
```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "--max-requests", "1000", "--max-requests-jitter", "100", "--preload", "app.wsgi:application"]
```

#### Parameter-Erklärung:
- `--bind 0.0.0.0:5000`: Bindet an alle Interfaces, Port 5000
- `--workers 4`: 4 Worker-Prozesse (empfohlen: 2-4 × CPU-Kerne)
- `--timeout 120`: 120 Sekunden Timeout für Requests
- `--max-requests 1000`: Worker wird nach 1000 Requests neu gestartet
- `--max-requests-jitter 100`: Zufälliger Jitter für Worker-Restarts
- `--preload`: Lädt die App vor dem Fork der Worker

### Option 2: Waitress (Empfohlen für Windows)

#### Vorteile:
- **Windows-kompatibel**
- **Einfach zu konfigurieren**
- **Keine externen Abhängigkeiten**
- **Gute Performance**

#### Konfiguration:
```python
from waitress import serve
serve(application, host='0.0.0.0', port=5000, threads=4)
```

### Option 3: Uvicorn (Für ASGI)

#### Vorteile:
- **Moderne ASGI-Unterstützung**
- **Sehr hohe Performance**
- **WebSocket-Unterstützung**

#### Konfiguration:
```dockerfile
CMD ["uvicorn", "app.wsgi:application", "--host", "0.0.0.0", "--port", "5000", "--workers", "4"]
```

## Implementierung

### 1. Dockerfile aktualisiert
```dockerfile
# Vorher (Entwicklungsserver)
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]

# Nachher (Produktionsserver)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "--max-requests", "1000", "--max-requests-jitter", "100", "--preload", "app.wsgi:application"]
```

### 2. WSGI-Datei verbessert
```python
if __name__ == '__main__':
    # Für Entwicklung: Flask-Entwicklungsserver
    # Für Produktion: Verwende Gunicorn oder Waitress
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--dev':
        # Entwicklungsserver
        application.run(host='0.0.0.0', port=5000, debug=False)
    else:
        # Produktionsserver (Waitress als Fallback)
        try:
            from waitress import serve
            print("Starting with Waitress production server...")
            serve(application, host='0.0.0.0', port=5000, threads=4)
        except ImportError:
            print("Waitress not available, falling back to Flask development server...")
            application.run(host='0.0.0.0', port=5000, debug=False)
```

## Deployment-Optionen

### Option A: Gunicorn verwenden
```bash
# Container neu bauen
docker-compose build

# Container starten
docker-compose up -d
```

### Option B: Waitress verwenden (Fallback)
```dockerfile
# In Dockerfile kommentieren:
# CMD ["gunicorn", ...]
CMD ["python", "app/wsgi.py"]
```

### Option C: Entwicklungsserver (nur für Tests)
```bash
# Mit --dev Flag
python app/wsgi.py --dev
```

## Performance-Vergleich

### Flask-Entwicklungsserver
- **Requests/Sekunde**: ~100-500
- **Worker**: 1 (Single-threaded)
- **Memory**: Niedrig
- **CPU**: Niedrig

### Gunicorn (4 Worker)
- **Requests/Sekunde**: ~1000-5000
- **Worker**: 4 (Multi-process)
- **Memory**: Höher (4 × App-Memory)
- **CPU**: Effizienter genutzt

### Waitress (4 Threads)
- **Requests/Sekunde**: ~800-3000
- **Worker**: 1 Prozess, 4 Threads
- **Memory**: Mittlerer Verbrauch
- **CPU**: Gut genutzt

## Monitoring und Logging

### Gunicorn-Logs
```bash
# Logs anzeigen
docker-compose logs -f scandy-app

# Worker-Status
docker-compose exec scandy-app ps aux
```

### Health Check
```bash
# Health Check
curl http://localhost:5000/health

# Worker-Status
curl http://localhost:5000/admin/debug/backup-info
```

## Empfehlungen

### Für Produktionsumgebungen:
1. **Gunicorn** verwenden (Linux)
2. **4 Worker** für typische Server
3. **Monitoring** einrichten
4. **Logs** überwachen

### Für Entwicklung:
1. **Flask-Entwicklungsserver** mit `--dev` Flag
2. **Debug-Modus** aktiviert
3. **Auto-Reload** für Code-Änderungen

### Für Windows:
1. **Waitress** als primärer Server
2. **Gunicorn** als Alternative (falls verfügbar)

## Troubleshooting

### Problem: Gunicorn startet nicht
```bash
# Logs prüfen
docker-compose logs scandy-app

# Manuell testen
docker-compose exec scandy-app gunicorn --bind 0.0.0.0:5000 app.wsgi:application
```

### Problem: Worker sterben ab
```bash
# Memory-Limit erhöhen
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "300", "--max-requests", "500", "app.wsgi:application"]
```

### Problem: Performance-Probleme
```bash
# Worker-Anzahl anpassen
# Empfohlen: 2-4 × CPU-Kerne
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "8", "--timeout", "120", "app.wsgi:application"]
```

## Fazit

Die Umstellung auf einen Produktions-WSGI-Server ist **wichtig** für:
- **Bessere Performance**
- **Höhere Stabilität**
- **Sicherheit**
- **Skalierbarkeit**

**Empfehlung**: Verwenden Sie Gunicorn für Linux-Produktionsumgebungen und Waitress als Fallback oder für Windows. 