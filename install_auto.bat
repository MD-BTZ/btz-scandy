@echo off
setlocal enabledelayedexpansion

REM Feste Konfigurationswerte (keine Abfragen)
set CONTAINER_NAME=scandy
set APP_PORT=5000
set MONGO_PORT=27017
set MONGO_EXPRESS_PORT=8081
set MONGO_USER=admin
set MONGO_PASS=scandy123
set DATA_DIR=./scandy_data

echo ========================================
echo    Scandy Auto-Installer (Windows)
echo    Automatische Installation ohne Abfragen
echo ========================================

REM Prüfe Docker-Installation
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker ist nicht installiert. Bitte installieren Sie Docker zuerst.
    echo Installationsanleitung: https://docs.docker.com/get-docker/
    pause
    exit /b 1
)

REM Prüfe Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker Compose ist nicht installiert. Bitte installieren Sie Docker Compose zuerst.
    echo Installationsanleitung: https://docs.docker.com/compose/install/
    pause
    exit /b 1
)

REM Prüfe ob Docker läuft
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker läuft nicht. Bitte starten Sie Docker zuerst.
    pause
    exit /b 1
)

echo ✓ Docker ist installiert und läuft

REM Zeige Konfiguration
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

REM Erstelle Datenverzeichnisse
echo Erstelle Datenverzeichnisse...
if not exist "%DATA_DIR%\mongodb" mkdir "%DATA_DIR%\mongodb"
if not exist "%DATA_DIR%\uploads" mkdir "%DATA_DIR%\uploads"
if not exist "%DATA_DIR%\backups" mkdir "%DATA_DIR%\backups"
if not exist "%DATA_DIR%\logs" mkdir "%DATA_DIR%\logs"
if not exist "%DATA_DIR%\static" mkdir "%DATA_DIR%\static"

REM Kopiere statische Dateien
echo Kopiere statische Dateien...
if exist "app\static" (
    xcopy /E /I /Y app\static\* "%DATA_DIR%\static\" >nul 2>&1
) else (
    echo Statische Dateien nicht gefunden, überspringe...
)

REM Erstelle docker-compose.yml
echo Erstelle docker-compose.yml...
(
echo version: '3.8'
echo.
echo services:
echo   mongodb:
echo     image: mongo:7.0
echo     container_name: %CONTAINER_NAME%-mongodb
echo     restart: unless-stopped
echo     environment:
echo       MONGO_INITDB_ROOT_USERNAME: %MONGO_USER%
echo       MONGO_INITDB_ROOT_PASSWORD: %MONGO_PASS%
echo       MONGO_INITDB_DATABASE: scandy
echo     ports:
echo       - "%MONGO_PORT%:27017"
echo     volumes:
echo       - %DATA_DIR%/mongodb:/data/db
echo       - ./mongo-init:/docker-entrypoint-initdb.d
echo     networks:
echo       - scandy-network
echo     command: mongod --auth --bind_ip_all
echo     healthcheck:
echo       test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping'^)"]
echo       interval: 30s
echo       timeout: 10s
echo       retries: 3
echo       start_period: 40s
echo.
echo   mongo-express:
echo     image: mongo-express:1.0.0
echo     container_name: %CONTAINER_NAME%-mongo-express
echo     restart: unless-stopped
echo     environment:
echo       ME_CONFIG_MONGODB_ADMINUSERNAME: %MONGO_USER%
echo       ME_CONFIG_MONGODB_ADMINPASSWORD: %MONGO_PASS%
echo       ME_CONFIG_MONGODB_URL: mongodb://%MONGO_USER%:%MONGO_PASS%@mongodb:27017/
echo       ME_CONFIG_BASICAUTH_USERNAME: %MONGO_USER%
echo       ME_CONFIG_BASICAUTH_PASSWORD: %MONGO_PASS%
echo     ports:
echo       - "%MONGO_EXPRESS_PORT%:8081"
echo     depends_on:
echo       - mongodb
echo     networks:
echo       - scandy-network
echo.
echo   app:
echo     build: .
echo     container_name: %CONTAINER_NAME%-app
echo     restart: unless-stopped
echo     environment:
echo       - DATABASE_MODE=mongodb
echo       - MONGODB_URI=mongodb://%MONGO_USER%:%MONGO_PASS%@mongodb:27017/
echo       - MONGODB_DB=scandy
echo       - FLASK_ENV=production
echo       - SECRET_KEY=scandy-secret-key-fixed
echo       - SYSTEM_NAME=Scandy
echo       - TICKET_SYSTEM_NAME=Aufgaben
echo       - TOOL_SYSTEM_NAME=Werkzeuge
echo       - CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter
echo       - TZ=Europe/Berlin
echo     ports:
echo       - "%APP_PORT%:5000"
echo     volumes:
echo       - %DATA_DIR%/uploads:/app/app/uploads
echo       - %DATA_DIR%/backups:/app/app/backups
echo       - %DATA_DIR%/logs:/app/app/logs
echo       - %DATA_DIR%/static:/app/app/static
echo     depends_on:
echo       - mongodb
echo     networks:
echo       - scandy-network
echo     healthcheck:
echo       test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
echo       interval: 30s
echo       timeout: 10s
echo       retries: 3
echo       start_period: 60s
echo     logging:
echo       driver: "json-file"
echo       options:
echo         max-size: "10m"
echo         max-file: "3"
echo.
echo volumes:
echo   scandy_css_test-mongodb-data:
echo     driver: local
echo.
echo networks:
echo   scandy-network:
echo     driver: bridge
) > docker-compose.yml

REM Erstelle MongoDB Init-Skript
echo Erstelle MongoDB Init-Skript...
if not exist "mongo-init" mkdir mongo-init
(
echo // MongoDB Initialisierung
echo db = db.getSiblingDB('scandy'^);
echo.
echo // Erstelle Collections
echo db.createCollection('users'^);
echo db.createCollection('tools'^);
echo db.createCollection('consumables'^);
echo db.createCollection('workers'^);
echo db.createCollection('settings'^);
echo db.createCollection('tickets'^);
echo db.createCollection('lendings'^);
echo.
echo // Erstelle Indizes
echo db.users.createIndex({ "username": 1 }, { unique: true }^);
echo db.tools.createIndex({ "barcode": 1 }, { unique: true }^);
echo db.consumables.createIndex({ "barcode": 1 }, { unique: true }^);
echo db.workers.createIndex({ "barcode": 1 }, { unique: true }^);
echo db.tickets.createIndex({ "ticket_id": 1 }, { unique: true }^);
echo.
echo print('MongoDB Initialisierung abgeschlossen'^);
) > mongo-init\init.js

REM Container stoppen falls vorhanden
echo Stoppe vorhandene Container...
docker-compose down --volumes --remove-orphans >nul 2>&1

REM Entferne Container mit gleichen Namen falls vorhanden
echo Bereinige vorhandene Container...
docker rm -f %CONTAINER_NAME%-mongodb %CONTAINER_NAME%-app %CONTAINER_NAME%-mongo-express >nul 2>&1

REM Container bauen und starten
echo Baue und starte Container...
docker-compose up -d --build

REM Warte auf Container-Start
echo Warte auf Container-Start...
timeout /t 30 /nobreak >nul

REM Prüfe Container-Status
echo Prüfe Container-Status...
docker-compose ps

echo ========================================
echo    Installation abgeschlossen!
echo ========================================
echo Scandy-Anwendung: http://localhost:%APP_PORT%
echo MongoDB Express: http://localhost:%MONGO_EXPRESS_PORT%
echo MongoDB Express Login: %MONGO_USER% / %MONGO_PASS%
echo.
echo Nützliche Befehle:
echo   Container-Status: docker-compose ps
echo   Logs anzeigen: docker-compose logs -f
echo   Container stoppen: docker-compose down
echo   Container neu starten: docker-compose restart
echo ========================================

pause 