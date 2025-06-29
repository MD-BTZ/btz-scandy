# Scandy - Entwickler-Dokumentation

## 📋 Übersicht

Scandy ist eine Flask-basierte Webanwendung zur Verwaltung von Werkzeugen, Verbrauchsmaterialien und Aufgaben. Das System verwendet MongoDB als Datenbank und ist in Docker-Containern deploybar.

## 🏗️ Projektstruktur

```
Scandy neu/
├── app/                          # Hauptanwendung
│   ├── __init__.py              # Flask-App-Initialisierung
│   ├── config/                  # Konfiguration
│   ├── models/                  # Datenmodelle
│   ├── routes/                  # Flask-Routen
│   ├── static/                  # Statische Dateien (CSS, JS, Bilder)
│   ├── templates/               # Jinja2-Templates
│   └── utils/                   # Hilfsfunktionen
├── docker-compose.yml           # Docker-Compose-Konfiguration
├── Dockerfile                   # Multi-Platform-Dockerfile
├── requirements.txt             # Python-Abhängigkeiten
└── README.md                    # Hauptdokumentation
```

## 🚀 Schnellstart für Entwickler

### Voraussetzungen
- Docker und Docker Compose
- Git
- Code-Editor (VS Code empfohlen)

### Installation
```bash
# Repository klonen
git clone <repository-url>
cd "Scandy neu"

# Container starten
docker-compose up -d

# Anwendung ist verfügbar unter: http://localhost:5000
```

### Erste Einrichtung
1. Öffne http://localhost:5000
2. Folge dem Setup-Assistenten
3. Erstelle den ersten Admin-Benutzer
4. Melde dich an und konfiguriere die Systemeinstellungen

## 🔧 Entwicklungsumgebung

### Code-Struktur

#### Flask-App (`app/__init__.py`)
- **Hauptfunktion**: `create_app()` - Erstellt und konfiguriert die Flask-Anwendung
- **Initialisierung**: MongoDB, Flask-Login, Session-Management, Blueprints
- **Health Check**: `/health` - Endpoint für Container-Monitoring

#### Routen (`app/routes/`)
- **auth.py**: Authentifizierung (Login, Logout, Setup, Profil)
- **admin.py**: Admin-Funktionen (Dashboard, Benutzerverwaltung, Backups)
- **tickets.py**: Ticket-System (Aufgabenverwaltung)
- **tools.py**: Werkzeugverwaltung
- **workers.py**: Mitarbeiterverwaltung
- **consumables.py**: Verbrauchsmaterialverwaltung
- **lending.py**: Ausleihsystem

#### Datenmodelle (`app/models/`)
- **mongodb_models.py**: MongoDB-Modelle und Datenbankoperationen
- **user.py**: Benutzer-Modell für Flask-Login
- **tool.py**: Werkzeug-Modell

#### Utilities (`app/utils/`)
- **database_helpers.py**: Hilfsfunktionen für Datenbankoperationen
- **auth_utils.py**: Authentifizierungs-Hilfsfunktionen
- **email_utils.py**: E-Mail-Funktionalität
- **backup_manager.py**: Backup-System
- **decorators.py**: Flask-Dekoratoren für Berechtigungen

### Datenbank-Schema

#### Collections
- **users**: Benutzerkonten
- **tools**: Werkzeuge
- **workers**: Mitarbeiter
- **consumables**: Verbrauchsmaterialien
- **tickets**: Aufgaben/Tickets
- **lendings**: Ausleihvorgänge
- **settings**: Systemeinstellungen
- **backups**: Backup-Metadaten

### Berechtigungssystem

#### Rollen
- **admin**: Vollzugriff auf alle Funktionen
- **mitarbeiter**: Erweiterte Rechte (Benutzerverwaltung, aber keine Admin-Bearbeitung)
- **anwender**: Grundlegende Funktionen

#### Dekoratoren
- `@login_required`: Benutzer muss angemeldet sein
- `@admin_required`: Nur Admins
- `@mitarbeiter_required`: Admins und Mitarbeiter

## 🛠️ Entwicklung

### Code-Standards

#### Python
- **Docstrings**: Alle Funktionen müssen Docstrings haben
- **Typisierung**: Wo möglich Type Hints verwenden
- **Fehlerbehandlung**: Try/Except mit aussagekräftigen Fehlermeldungen
- **Logging**: Strukturiertes Logging für Debugging

#### JavaScript
- **Toast-Funktionen**: Verwende `window.showToast()` für Nutzerfeedback
- **Keine Console-Logs**: Im Produktivcode keine Debug-Ausgaben
- **Error Handling**: Try/Catch für alle async-Operationen

#### Templates (Jinja2)
- **Konsistente Einrückung**: 2 Leerzeichen
- **Sprechende Variablennamen**: Klare, beschreibende Namen
- **Kommentare**: Komplexe Logik kommentieren

### Neue Features entwickeln

#### 1. Route hinzufügen
```python
# In der entsprechenden routes/datei.py
@bp.route('/neue-funktion', methods=['GET', 'POST'])
@login_required  # oder andere Berechtigung
def neue_funktion():
    """
    Beschreibung der Funktion.
    
    Args:
        Keine
        
    Returns:
        Template oder JSON-Response
    """
    # Implementierung
    pass
```

#### 2. Template erstellen
```html
<!-- In templates/verzeichnis/template.html -->
{% extends "base.html" %}

{% block content %}
<!-- Template-Inhalt -->
{% endblock %}
```

#### 3. JavaScript hinzufügen
```javascript
// In static/js/datei.js
document.addEventListener('DOMContentLoaded', () => {
    // Initialisierung
});

async function neueFunktion() {
    try {
        // Implementierung
    } catch (error) {
        showToast('error', 'Fehler: ' + error.message);
    }
}
```

### Debugging

#### Logs anzeigen
```bash
# Alle Container-Logs
docker-compose logs

# Nur App-Logs
docker-compose logs scandy-app

# Live-Logs
docker-compose logs -f scandy-app
```

#### Datenbank-Zugriff
```bash
# MongoDB Express (Web-Interface)
# http://localhost:8081

# Direkter MongoDB-Zugriff
docker-compose exec scandy-mongodb mongosh
```

#### Code-Änderungen
- Container automatisch neu starten bei Code-Änderungen
- Bei Konfigurationsänderungen: `docker-compose restart`

## 🧪 Testing

### Manuelle Tests
1. **Login/Logout**: Verschiedene Benutzerrollen testen
2. **CRUD-Operationen**: Erstellen, Lesen, Aktualisieren, Löschen
3. **Berechtigungen**: Zugriff mit verschiedenen Rollen prüfen
4. **Formulare**: Validierung und Fehlerbehandlung
5. **Responsive Design**: Verschiedene Bildschirmgrößen

### Automatisierte Tests
```bash
# Tests ausführen (falls vorhanden)
python -m pytest tests/

# Coverage-Report
python -m pytest --cov=app tests/
```

## 📦 Deployment

### Produktionsumgebung
```bash
# Produktions-Build
docker-compose -f docker-compose.prod.yml up -d

# Umgebungsvariablen setzen
export FLASK_ENV=production
export MONGODB_URI=mongodb://prod-mongodb:27017/scandy
```

### Backup/Restore
```bash
# Backup erstellen
docker-compose exec scandy-app python -c "
from app.utils.backup_manager import BackupManager
bm = BackupManager()
bm.create_backup()
"

# Backup wiederherstellen
# Über Admin-Interface oder direkt über MongoDB
```

## 🔍 Troubleshooting

### Häufige Probleme

#### Container startet nicht
```bash
# Logs prüfen
docker-compose logs scandy-app

# Container neu bauen
docker-compose build --no-cache
docker-compose up -d
```

#### Datenbankverbindung fehlschlägt
```bash
# MongoDB-Container prüfen
docker-compose ps scandy-mongodb

# MongoDB-Logs
docker-compose logs scandy-mongodb
```

#### E-Mails funktionieren nicht
- SMTP-Einstellungen in `docker-compose.yml` prüfen
- Gmail App-Passwort konfiguriert?
- Firewall-Einstellungen?

### Debug-Modus aktivieren
```python
# In app/config/config.py
DEBUG = True
```

## 📚 Nützliche Links

- [Flask Dokumentation](https://flask.palletsprojects.com/)
- [MongoDB Dokumentation](https://docs.mongodb.com/)
- [Docker Dokumentation](https://docs.docker.com/)
- [Jinja2 Template Engine](https://jinja.palletsprojects.com/)

## 🤝 Beitragen

### Pull Request erstellen
1. Feature-Branch erstellen: `git checkout -b feature/neue-funktion`
2. Änderungen implementieren
3. Tests schreiben/ausführen
4. Code-Review durchführen
5. Pull Request erstellen

### Code-Review Checkliste
- [ ] Docstrings vorhanden und aktuell
- [ ] Fehlerbehandlung implementiert
- [ ] Logging hinzugefügt
- [ ] Tests geschrieben
- [ ] Keine Debug-Ausgaben im Produktivcode
- [ ] Berechtigungen korrekt gesetzt

## 📞 Support

Bei Fragen oder Problemen:
1. Dokumentation durchsuchen
2. Issues im Repository prüfen
3. Neues Issue erstellen mit:
   - Beschreibung des Problems
   - Schritte zur Reproduktion
   - Logs und Screenshots
   - Umgebung (OS, Browser, etc.)

---

**Letzte Aktualisierung**: Juni 2025
**Version**: 1.0.0 