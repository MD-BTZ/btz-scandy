@echo off
setlocal enabledelayedexpansion

REM Scandy Docker-Installer (Vollständig) - Windows Version
REM MongoDB + App Container Setup

echo ========================================
echo    Scandy Docker-Installer (Vollständig)
echo    MongoDB + App Container Setup
echo ========================================

REM Prüfe Docker-Installation
docker --version >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Docker ist nicht installiert. Bitte installieren Sie Docker Desktop zuerst.
    echo Installationsanleitung: https://docs.docker.com/desktop/install/windows/
    pause
    exit /b 1
)

REM Prüfe Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Docker Compose ist nicht installiert. Bitte installieren Sie Docker Compose zuerst.
    echo Installationsanleitung: https://docs.docker.com/compose/install/
    pause
    exit /b 1
)

REM Prüfe ob Docker läuft
docker info >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Docker läuft nicht. Bitte starten Sie Docker Desktop zuerst.
    pause
    exit /b 1
)

echo ✓ Docker ist installiert und läuft

REM Container-Name Abfrage
:container_name_loop
set /p CONTAINER_NAME="Bitte geben Sie einen Namen für die Umgebung ein (z.B. scandy_prod): "
if "%CONTAINER_NAME%"=="" (
    echo Der Name darf nicht leer sein.
    goto container_name_loop
)

REM Konvertiere zu Kleinbuchstaben und ersetze ungültige Zeichen
set CONTAINER_NAME=%CONTAINER_NAME: =%
set CONTAINER_NAME=%CONTAINER_NAME:ä=a%
set CONTAINER_NAME=%CONTAINER_NAME:ö=o%
set CONTAINER_NAME=%CONTAINER_NAME:ü=u%
set CONTAINER_NAME=%CONTAINER_NAME:ß=s%
set CONTAINER_NAME=%CONTAINER_NAME:Ä=A%
set CONTAINER_NAME=%CONTAINER_NAME:Ö=O%
set CONTAINER_NAME=%CONTAINER_NAME:Ü=U%

REM App-Port Abfrage
set /p APP_PORT="Bitte geben Sie den Port für die App ein (Standard: 5000): "
if "%APP_PORT%"=="" set APP_PORT=5000

REM MongoDB-Port Abfrage
set /p MONGO_PORT="Bitte geben Sie den Port für MongoDB ein (Standard: 27017): "
if "%MONGO_PORT%"=="" set MONGO_PORT=27017

REM Mongo Express Port Abfrage
set /p MONGO_EXPRESS_PORT="Bitte geben Sie den Port für Mongo Express (Web-UI) ein (Standard: 8081): "
if "%MONGO_EXPRESS_PORT%"=="" set MONGO_EXPRESS_PORT=8081

REM MongoDB Credentials
set /p MONGO_USER="MongoDB Admin Benutzername (Standard: admin): "
if "%MONGO_USER%"=="" set MONGO_USER=admin

set /p MONGO_PASS="MongoDB Admin Passwort (Standard: scandy123): "
if "%MONGO_PASS%"=="" set MONGO_PASS=scandy123

REM Datenverzeichnis
set /p DATA_DIR="Datenverzeichnis (Standard: ./scandy_data): "
if "%DATA_DIR%"=="" set DATA_DIR=./scandy_data

echo ========================================
echo    Konfiguration:
echo ========================================
echo Container Name: %CONTAINER_NAME%
echo App Port: %APP_PORT%
echo MongoDB Port: %MONGO_PORT%
echo Mongo Express Port: %MONGO_EXPRESS_PORT%
echo MongoDB User: %MONGO_USER%
echo Datenverzeichnis: %DATA_DIR%
echo ========================================

set /p confirm="Möchten Sie mit der Installation fortfahren? (j/n): "
if /i not "%confirm%"=="j" (
    echo Installation abgebrochen.
    pause
    exit /b 0
)

REM Erstelle Projektverzeichnis
set PROJECT_DIR=%CONTAINER_NAME%_project
if not exist "%PROJECT_DIR%" mkdir "%PROJECT_DIR%"
cd "%PROJECT_DIR%"

echo Erstelle Projektverzeichnis: %PROJECT_DIR%

REM Kopiere Template-Dateien
echo Kopiere Template-Dateien...
copy "..\docker-compose.template.yml" "." >nul
copy "..\process_template.py" "." >nul

REM Verarbeite Template
echo Verarbeite Template...
python process_template.py %CONTAINER_NAME% %APP_PORT% %MONGO_PORT% %MONGO_EXPRESS_PORT% %MONGO_USER% %MONGO_PASS% %DATA_DIR%

if errorlevel 1 (
    echo FEHLER: Template-Verarbeitung fehlgeschlagen!
    pause
    exit /b 1
)

REM Erstelle Dockerfile
echo Erstelle Dockerfile...
(
echo FROM python:3.11-slim
echo.
echo # Installiere System-Abhängigkeiten
echo RUN apt-get update ^&^& apt-get install -y \
echo     git \
echo     nodejs \
echo     npm \
echo     curl \
echo     build-essential \
echo     zip \
echo     unzip \
echo     ^&^& rm -rf /var/lib/apt/lists/*
echo.
echo # Erstelle nicht-root Benutzer
echo RUN useradd -m -u 1000 appuser
echo.
echo WORKDIR /app
echo.
echo # Kopiere Requirements zuerst für besseres Caching
echo COPY requirements.txt .
echo.
echo # Installiere Python-Abhängigkeiten
echo RUN pip install --no-cache-dir -r requirements.txt
echo.
echo # Kopiere den Rest der Anwendung
echo COPY . .
echo.
echo # Installiere und baue CSS
echo RUN npm install ^&^& npm run build:css
echo.
echo # Erstelle notwendige Verzeichnisse und setze Berechtigungen
echo RUN mkdir -p /app/app/uploads /app/app/backups /app/app/logs /app/app/static /app/tmp ^&^& \
echo     chown -R appuser:appuser /app ^&^& \
echo     chmod -R 755 /app
echo.
echo # Wechsle zu nicht-root Benutzer
echo USER appuser
echo.
echo # Exponiere Port
echo EXPOSE 5000
echo.
echo # Health Check
echo HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
echo     CMD curl -f http://localhost:5000/health ^|^| exit 1
echo.
echo # Starte die Anwendung
echo CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]
) > Dockerfile

REM Erstelle MongoDB Init-Skript
echo Erstelle MongoDB Init-Skript...
if not exist "mongo-init" mkdir mongo-init
(
echo // MongoDB Initialisierung für Scandy
echo db = db.getSiblingDB^('scandy'^);
echo.
echo // Erstelle Collections
echo db.createCollection^('tools'^);
echo db.createCollection^('consumables'^);
echo db.createCollection^('workers'^);
echo db.createCollection^('lendings'^);
echo db.createCollection^('users'^);
echo db.createCollection^('tickets'^);
echo db.createCollection^('settings'^);
echo db.createCollection^('system_logs'^);
echo.
echo // Erstelle Indizes
echo db.tools.createIndex^({ "barcode": 1 }, { unique: true }^);
echo db.tools.createIndex^({ "deleted": 1 }^);
echo db.tools.createIndex^({ "status": 1 }^);
echo.
echo db.consumables.createIndex^({ "barcode": 1 }, { unique: true }^);
echo db.consumables.createIndex^({ "deleted": 1 }^);
echo.
echo db.workers.createIndex^({ "barcode": 1 }, { unique: true }^);
echo db.workers.createIndex^({ "deleted": 1 }^);
echo.
echo db.lendings.createIndex^({ "tool_barcode": 1 }^);
echo db.lendings.createIndex^({ "worker_barcode": 1 }^);
echo db.lendings.createIndex^({ "returned_at": 1 }^);
echo.
echo db.users.createIndex^({ "username": 1 }, { unique: true }^);
echo db.users.createIndex^({ "email": 1 }, { sparse: true }^);
echo.
echo db.tickets.createIndex^({ "created_at": 1 }^);
echo db.tickets.createIndex^({ "status": 1 }^);
echo db.tickets.createIndex^({ "assigned_to": 1 }^);
echo.
echo print^('MongoDB für Scandy initialisiert!'^);
) > mongo-init/init.js

REM Erstelle .dockerignore
echo Erstelle .dockerignore...
(
echo .git
echo .gitignore
echo README.md
echo docs/
echo *.md
echo venv/
echo __pycache__/
echo *.pyc
echo *.pyo
echo *.pyd
echo .Python
echo env/
echo pip-log.txt
echo pip-delete-this-directory.txt
echo .tox/
echo .coverage
echo .coverage.*
echo .cache
echo nosetests.xml
echo coverage.xml
echo *.cover
echo *.log
echo .git
echo .mypy_cache
echo .pytest_cache
echo .hypothesis
echo .DS_Store
echo Thumbs.db
) > .dockerignore

REM Erstelle Start-Skript
echo Erstelle Start-Skript...
(
echo @echo off
echo echo Starte Scandy Docker-Container...
echo docker-compose up -d
echo.
echo echo Warte auf Container-Start...
echo timeout /t 10 /nobreak ^>nul
echo.
echo echo Container-Status:
echo docker-compose ps
echo.
echo echo.
echo echo ==========================================
echo echo Scandy ist verfügbar unter:
echo echo App: http://localhost:%APP_PORT%
echo echo Mongo Express: http://localhost:%MONGO_EXPRESS_PORT%
echo echo MongoDB: localhost:%MONGO_PORT%
echo echo ==========================================
echo pause
) > start.bat

REM Erstelle Stop-Skript
echo Erstelle Stop-Skript...
(
echo @echo off
echo echo Stoppe Scandy Docker-Container...
echo docker-compose down
echo.
echo echo Container gestoppt.
echo pause
) > stop.bat

REM Erstelle Update-Skript
echo Erstelle Update-Skript...
(
echo @echo off
echo echo Update Scandy Docker-Container...
echo.
echo REM Stoppe Container
echo docker-compose down
echo.
echo REM Pull neueste Images
echo docker-compose pull
echo.
echo REM Baue App neu
echo docker-compose build --no-cache
echo.
echo REM Starte Container
echo docker-compose up -d
echo.
echo echo Update abgeschlossen!
echo pause
) > update.bat

REM Erstelle Backup-Skript
echo Erstelle Backup-Skript...
(
echo @echo off
echo set BACKUP_DIR=%DATA_DIR%/backups
echo set TIMESTAMP=%%date:~-4,4%%%%date:~-10,2%%%%date:~-7,2%%_%%time:~0,2%%%%time:~3,2%%%%time:~6,2%%
echo set TIMESTAMP=!TIMESTAMP: =0!
echo.
echo echo Erstelle Backup...
echo.
echo REM Erstelle Backup-Verzeichnis
echo if not exist "!BACKUP_DIR!" mkdir "!BACKUP_DIR!"
echo.
echo REM MongoDB Backup
echo echo Backup MongoDB...
echo docker exec %CONTAINER_NAME%-mongodb mongodump --out /tmp/backup
echo docker cp %CONTAINER_NAME%-mongodb:/tmp/backup "!BACKUP_DIR!/mongodb_!TIMESTAMP!"
echo.
echo REM App-Daten Backup
echo echo Backup App-Daten...
echo powershell -Command "Compress-Archive -Path '%DATA_DIR%/uploads', '%DATA_DIR%/backups', '%DATA_DIR%/logs' -DestinationPath '!BACKUP_DIR!/app_data_!TIMESTAMP!.zip'"
echo.
echo echo Backup erstellt: !BACKUP_DIR!
echo pause
) > backup.bat

REM Erstelle Datenverzeichnisse
echo Erstelle Datenverzeichnisse...
if not exist "%DATA_DIR%/mongodb" mkdir "%DATA_DIR%/mongodb"
if not exist "%DATA_DIR%/uploads" mkdir "%DATA_DIR%/uploads"
if not exist "%DATA_DIR%/backups" mkdir "%DATA_DIR%/backups"
if not exist "%DATA_DIR%/logs" mkdir "%DATA_DIR%/logs"
if not exist "%DATA_DIR%/static" mkdir "%DATA_DIR%/static"

REM Kopiere aktuelle Anwendung
echo Kopiere Anwendung...
REM Das Template-System übernimmt das Kopieren und CSS-Build

REM Baue und starte Container
echo Baue Docker-Container...
docker-compose build

echo Starte Container...
docker-compose up -d

REM Warte auf Container-Start
echo Warte auf Container-Start...
timeout /t 15 /nobreak >nul

REM Zeige Status
echo Container-Status:
docker-compose ps

echo ========================================
echo    Installation abgeschlossen!
echo ========================================
echo Scandy ist verfügbar unter:
echo App: http://localhost:%APP_PORT%
echo Mongo Express: http://localhost:%MONGO_EXPRESS_PORT%
echo MongoDB: localhost:%MONGO_PORT%
echo.
echo Verfügbare Skripte:
echo start.bat - Container starten
echo stop.bat - Container stoppen
echo update.bat - Container aktualisieren
echo backup.bat - Backup erstellen
echo.
echo Daten werden gespeichert in: %DATA_DIR%
echo ========================================
pause 