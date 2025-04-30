# Entwicklerdokumentation

## Inhaltsverzeichnis

1. [Entwicklungsumgebung](#entwicklungsumgebung)
2. [Projektstruktur](#projektstruktur)
3. [Code-Standards](#code-standards)
4. [Datenbank-Schema](#datenbank-schema)
5. [Tests](#tests)
6. [Deployment](#deployment)
7. [Erweiterungen](#erweiterungen)

## Entwicklungsumgebung

### Voraussetzungen
- Python 3.x
- Git
- Virtualenv
- SQLite
- Node.js (für Frontend-Entwicklung)

### Setup
1. **Repository klonen**
   ```bash
   git clone <repository-url>
   cd scandy
   ```

2. **Virtuelle Umgebung erstellen**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   .\venv\Scripts\activate  # Windows
   ```

3. **Abhängigkeiten installieren**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Entwicklungstools
   ```

4. **Frontend-Setup**
   ```bash
   cd frontend
   npm install
   ```

### Entwicklungstools
- **IDE**: VS Code mit Python-Erweiterung
- **Linter**: flake8
- **Formatter**: black
- **Type Checking**: mypy
- **Tests**: pytest
- **Debugging**: pdb

## Projektstruktur

```
scandy/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models/
│   ├── routes/
│   ├── templates/
│   ├── static/
│   └── utils/
├── tests/
├── docs/
├── frontend/
├── scripts/
└── requirements.txt
```

### Wichtige Module

#### Backend
- **app/__init__.py**: Flask-Applikations-Factory
- **app/config.py**: Konfigurationsklassen
- **app/models/**: Datenbankmodelle
- **app/routes/**: API-Endpunkte
- **app/utils/**: Hilfsfunktionen

#### Frontend
- **frontend/src/**: Quellcode
- **frontend/public/**: Statische Dateien
- **frontend/components/**: React-Komponenten

## Code-Standards

### Python
- PEP 8 Konventionen
- Docstrings nach Google-Style
- Type Hints für Funktionen
- Unit Tests für alle Module

### JavaScript
- ESLint Konfiguration
- Prettier Formatierung
- React Hooks
- Functional Components

### Git
- Feature Branches
- Meaningful Commits
- Pull Request Reviews
- Semantic Versioning

## Datenbank-Schema

### Haupttabellen

#### Werkzeuge (tools)
```sql
CREATE TABLE tools (
    id INTEGER PRIMARY KEY,
    barcode TEXT UNIQUE,
    name TEXT NOT NULL,
    category TEXT,
    location TEXT,
    status TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Material (consumables)
```sql
CREATE TABLE consumables (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    quantity INTEGER DEFAULT 0,
    min_quantity INTEGER DEFAULT 0,
    location TEXT,
    unit TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Ausleihen (lendings)
```sql
CREATE TABLE lendings (
    id INTEGER PRIMARY KEY,
    tool_id INTEGER,
    worker_id INTEGER,
    start_date DATE,
    end_date DATE,
    status TEXT,
    condition TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(tool_id) REFERENCES tools(id),
    FOREIGN KEY(worker_id) REFERENCES workers(id)
);
```

#### Tickets (tickets)
```sql
CREATE TABLE tickets (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'open',
    priority TEXT DEFAULT 'medium',
    created_by INTEGER,
    assigned_to INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(created_by) REFERENCES users(id),
    FOREIGN KEY(assigned_to) REFERENCES users(id)
);
```

## Tests

### Unit Tests
```python
# Beispiel Test
def test_tool_creation():
    tool = Tool(barcode="123456", name="Hammer")
    assert tool.name == "Hammer"
    assert tool.status == "available"
```

### Integration Tests
```python
# Beispiel Test
def test_lending_process():
    tool = create_tool()
    worker = create_worker()
    lending = create_lending(tool, worker)
    assert lending.status == "active"
```

### Test-Ausführung
```bash
# Alle Tests
pytest

# Spezifische Tests
pytest tests/test_tools.py

# Mit Coverage
pytest --cov=app
```

## Deployment

### Entwicklung
```bash
# Entwicklungsserver
flask run --debug

# Frontend-Dev-Server
cd frontend
npm run dev
```

### Produktion
```bash
# Backend
gunicorn --workers 4 --bind 0.0.0.0:5000 wsgi:app

# Frontend
npm run build
```

### Docker
```bash
# Build
docker build -t scandy .

# Run
docker run -p 5000:5000 scandy
```

## Erweiterungen

### Neue Features
1. **Branch erstellen**
   ```bash
   git checkout -b feature/neue-funktion
   ```

2. **Entwicklung**
   - Tests schreiben
   - Code implementieren
   - Dokumentation aktualisieren

3. **Pull Request**
   - Branch pushen
   - Review anfordern
   - Tests durchlaufen

### API-Erweiterungen
1. **Neuer Endpunkt**
   ```python
   @api.route('/new-endpoint')
   def new_endpoint():
       return jsonify({"status": "success"})
   ```

2. **Versionierung**
   - Neue Version erstellen
   - Alte Versionen unterstützen
   - Dokumentation aktualisieren

### Datenbank-Migrationen
1. **Schema-Änderung**
   ```python
   # Migration erstellen
   alembic revision --autogenerate -m "description"
   ```

2. **Migration ausführen**
   ```bash
   alembic upgrade head
   ``` 