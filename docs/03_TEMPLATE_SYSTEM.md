# Template-System für Docker Compose

## Übersicht

Das Template-System ermöglicht es, Docker Compose Konfigurationen dynamisch basierend auf Benutzereingaben zu generieren. Dies löst das Problem, dass feste Werte in der `docker-compose.yml` nicht mit den tatsächlichen Benutzereingaben übereinstimmen.

## Dateien

### 1. `docker-compose.template.yml`
Template-Datei mit Platzhaltern, die durch tatsächliche Werte ersetzt werden.

**Platzhalter:**
- `{{CONTAINER_NAME}}` - Name der Container-Umgebung
- `{{APP_PORT}}` - Port für die Flask-Anwendung
- `{{MONGO_PORT}}` - Port für MongoDB
- `{{MONGO_EXPRESS_PORT}}` - Port für Mongo Express
- `{{MONGO_USER}}` - MongoDB Admin Benutzername
- `{{MONGO_PASS}}` - MongoDB Admin Passwort
- `{{DATA_DIR}}` - Datenverzeichnis
- `{{RANDOM_KEY}}` - Zufällig generierter Schlüssel

### 2. `process_template.py`
Python-Skript zur Verarbeitung des Templates.

**Verwendung:**
```bash
python process_template.py <container_name> [app_port] [mongo_port] [mongo_express_port] [mongo_user] [mongo_pass] [data_dir]
```

**Beispiel:**
```bash
python process_template.py scandy_prod 5000 27017 8081 admin scandy123 ./scandy_data
```

### 3. `install_docker_template.bat`
Installationsskript, das das Template-System verwendet.

## Vorteile

1. **Flexibilität**: Benutzer können beliebige Namen, Ports und Verzeichnisse wählen
2. **Wartbarkeit**: Ein zentrales Template für alle Konfigurationen
3. **Konsistenz**: Alle generierten Dateien folgen dem gleichen Muster
4. **Fehlervermeidung**: Keine manuellen Anpassungen der docker-compose.yml nötig

## Workflow

1. **Benutzer führt `install_docker_template.bat` aus**
2. **Skript fragt Konfigurationswerte ab**
3. **Template-Dateien werden kopiert**
4. **`process_template.py` ersetzt Platzhalter**
5. **Generierte `docker-compose.yml` wird erstellt**
6. **Container werden gebaut und gestartet**

## Beispiel

**Benutzereingaben:**
- Container Name: `scandy_technik`
- App Port: `5001`
- MongoDB Port: `27018`
- Mongo Express Port: `8082`
- MongoDB User: `admin`
- MongoDB Pass: `admin123`
- Datenverzeichnis: `./scandy_technik_data`

**Generierte docker-compose.yml:**
```yaml
services:
  scandy_technik-mongodb:
    container_name: scandy_technik-mongodb
    ports:
      - "27018:27017"
    # ... weitere Konfiguration
```

## Migration von bestehenden Installationen

Für bestehende Installationen mit manuell erstellten `docker-compose.yml` Dateien:

1. **Backup erstellen**
2. **Neues Template-System verwenden**
3. **Alte Installation stoppen**
4. **Neue Installation mit korrekten Werten starten**

## Troubleshooting

### Problem: Template-Datei nicht gefunden
**Lösung:** Stellen Sie sicher, dass `docker-compose.template.yml` im Projektverzeichnis liegt.

### Problem: Python-Skript fehlgeschlagen
**Lösung:** Überprüfen Sie die Python-Installation und die Syntax der Befehlszeilenargumente.

### Problem: Container starten nicht
**Lösung:** Überprüfen Sie die generierte `docker-compose.yml` auf korrekte Werte. 