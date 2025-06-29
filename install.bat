@echo off
setlocal enabledelayedexpansion

echo 🚀 Scandy Installation (Windows)
echo =================================

REM Prüfe Docker
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker läuft nicht. Bitte starten Sie Docker zuerst.
    pause
    exit /b 1
)

echo ✅ Docker ist verfügbar

REM Konfiguration
set CONTAINER_NAME=scandy
set APP_PORT=5000
set MONGO_PORT=27017
set MONGO_EXPRESS_PORT=8081
set MONGO_USER=admin
set MONGO_PASS=scandy123
set DATA_DIR=./scandy_data

echo ========================================
echo    Konfiguration:
echo ========================================
echo Container Name: %CONTAINER_NAME%
echo App Port: %APP_PORT%
echo MongoDB Port: %MONGO_PORT%
echo Mongo Express Port: %MONGO_EXPRESS_PORT%
echo Datenverzeichnis: %DATA_DIR%
echo ========================================

REM Prüfe bestehende Installation
if exist "%DATA_DIR%\mongodb" (
    echo ⚠️  Bestehende Installation gefunden!
    echo Optionen: 1=Abbrechen, 2=Backup+Neu, 3=Überschreiben
    set /p choice="Wählen Sie (1-3): "
    if "%choice%"=="1" exit /b 0
    if "%choice%"=="2" (
        echo Erstelle Backup...
        if not exist "%DATA_DIR%\backups" mkdir "%DATA_DIR%\backups"
    )
    if "%choice%"=="3" (
        echo Lösche alte Daten...
        rmdir /s /q "%DATA_DIR%" 2>nul
    )
)

REM Erstelle Projektverzeichnis
set PROJECT_DIR=%CONTAINER_NAME%_project
if not exist "%PROJECT_DIR%" mkdir "%PROJECT_DIR%"
cd "%PROJECT_DIR%"

REM Erstelle Datenverzeichnisse
if not exist "%DATA_DIR%\mongodb" mkdir "%DATA_DIR%\mongodb"
if not exist "%DATA_DIR%\uploads" mkdir "%DATA_DIR%\uploads"
if not exist "%DATA_DIR%\backups" mkdir "%DATA_DIR%\backups"
if not exist "%DATA_DIR%\logs" mkdir "%DATA_DIR%\logs"
if not exist "%DATA_DIR%\static" mkdir "%DATA_DIR%\static"

REM Kopiere statische Dateien
if exist "..\app\static" xcopy "..\app\static\*" "%DATA_DIR%\static\" /E /I /Y

REM Erstelle docker-compose.yml
(
echo version: '3.8'
echo.
echo services:
echo   %CONTAINER_NAME%-mongodb:
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
echo       - %CONTAINER_NAME%-network
echo     command: mongod --auth --bind_ip_all
echo     healthcheck:
echo       test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping'^)"]
echo       interval: 30s
echo       timeout: 10s
echo       retries: 3
echo       start_period: 40s
echo.
echo   %CONTAINER_NAME%-mongo-express:
echo     image: mongo-express:1.0.0
echo     container_name: %CONTAINER_NAME%-mongo-express
echo     restart: unless-stopped
echo     environment:
echo       ME_CONFIG_MONGODB_ADMINUSERNAME: %MONGO_USER%
echo       ME_CONFIG_MONGODB_ADMINPASSWORD: %MONGO_PASS%
echo       ME_CONFIG_MONGODB_URL: mongodb://%MONGO_USER%:%MONGO_PASS%@%CONTAINER_NAME%-mongodb:27017/
echo       ME_CONFIG_BASICAUTH_USERNAME: %MONGO_USER%
echo       ME_CONFIG_BASICAUTH_PASSWORD: %MONGO_PASS%
echo     ports:
echo       - "%MONGO_EXPRESS_PORT%:8081"
echo     depends_on:
echo       %CONTAINER_NAME%-mongodb:
echo         condition: service_healthy
echo     networks:
echo       - %CONTAINER_NAME%-network
echo.
echo   %CONTAINER_NAME%-app:
echo     build:
echo       context: .
echo       dockerfile: Dockerfile
echo     container_name: %CONTAINER_NAME%-app
echo     restart: unless-stopped
echo     environment:
echo       - DATABASE_MODE=mongodb
echo       - MONGODB_URI=mongodb://%MONGO_USER%:%MONGO_PASS%@%CONTAINER_NAME%-mongodb:27017/
echo       - MONGODB_DB=scandy
echo       - FLASK_ENV=production
echo       - SECRET_KEY=scandy-secret-key-production
echo       - SYSTEM_NAME=Scandy
echo       - TICKET_SYSTEM_NAME=Aufgaben
echo       - TOOL_SYSTEM_NAME=Werkzeuge
echo       - CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter
echo       - CONTAINER_NAME=%CONTAINER_NAME%
echo       - TZ=Europe/Berlin
echo     ports:
echo       - "%APP_PORT%:5000"
echo     volumes:
echo       - %DATA_DIR%/uploads:/app/app/uploads
echo       - %DATA_DIR%/backups:/app/app/backups
echo       - %DATA_DIR%/logs:/app/app/logs
echo       - %DATA_DIR%/static:/app/app/static
echo     depends_on:
echo       %CONTAINER_NAME%-mongodb:
echo         condition: service_healthy
echo     networks:
echo       - %CONTAINER_NAME%-network
echo     healthcheck:
echo       test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
echo       interval: 30s
echo       timeout: 10s
echo       retries: 3
echo       start_period: 60s
echo.
echo volumes:
echo   %CONTAINER_NAME%-mongodb-data:
echo     driver: local
echo.
echo networks:
echo   %CONTAINER_NAME%-network:
echo     driver: bridge
) > docker-compose.yml

REM Kopiere Dateien
copy "..\Dockerfile" . >nul
copy "..\requirements.txt" . >nul
copy "..\package.json" . >nul
if exist "..\tailwind.config.js" copy "..\tailwind.config.js" . >nul
if exist "..\postcss.config.js" copy "..\postcss.config.js" . >nul
if exist "..\.dockerignore" copy "..\.dockerignore" . >nul

REM Kopiere App
xcopy "..\app" "app\" /E /I /Y >nul

REM Erstelle MongoDB Init
if not exist "mongo-init" mkdir "mongo-init"
(
echo db = db.getSiblingDB^('scandy'^);
echo db.createCollection^('tools'^);
echo db.createCollection^('consumables'^);
echo db.createCollection^('workers'^);
echo db.createCollection^('lendings'^);
echo db.createCollection^('users'^);
echo db.createCollection^('tickets'^);
echo db.createCollection^('settings'^);
echo db.createCollection^('system_logs'^);
echo db.tools.createIndex^({ "barcode": 1 }, { unique: true }^);
echo db.tools.createIndex^({ "deleted": 1 }^);
echo db.tools.createIndex^({ "status": 1 }^);
echo db.consumables.createIndex^({ "barcode": 1 }, { unique: true }^);
echo db.consumables.createIndex^({ "deleted": 1 }^);
echo db.workers.createIndex^({ "barcode": 1 }, { unique: true }^);
echo db.workers.createIndex^({ "deleted": 1 }^);
echo db.lendings.createIndex^({ "tool_barcode": 1 }^);
echo db.lendings.createIndex^({ "worker_barcode": 1 }^);
echo db.lendings.createIndex^({ "returned_at": 1 }^);
echo db.users.createIndex^({ "username": 1 }, { unique: true }^);
echo db.users.createIndex^({ "email": 1 }, { sparse: true }^);
echo db.tickets.createIndex^({ "created_at": 1 }^);
echo db.tickets.createIndex^({ "status": 1 }^);
echo db.tickets.createIndex^({ "assigned_to": 1 }^);
echo print^('MongoDB für Scandy initialisiert!'^);
) > mongo-init\init.js

REM Erstelle Management-Scripts
(
echo @echo off
echo echo Starte Scandy...
echo docker-compose up -d
echo timeout /t 10 /nobreak ^>nul
echo docker-compose ps
echo echo.
echo echo Scandy: http://localhost:%APP_PORT%
echo echo Mongo Express: http://localhost:%MONGO_EXPRESS_PORT%
echo pause
) > start.bat

(
echo @echo off
echo echo Stoppe Scandy...
echo docker-compose down
echo pause
) > stop.bat

(
echo @echo off
echo echo Update Scandy...
echo docker-compose down
echo docker-compose pull
echo docker-compose build --no-cache
echo docker-compose up -d
echo pause
) > update.bat

REM Baue und starte
echo 🏗️  Baue Container...
docker-compose build --no-cache

if errorlevel 1 (
    echo ⚠️  Standard-Build fehlgeschlagen, verwende einfache Version...
    if exist "..\Dockerfile.simple" (
        copy "..\Dockerfile.simple" "Dockerfile" >nul
        docker-compose build --no-cache
    )
)

if errorlevel 1 (
    echo ❌ Build fehlgeschlagen!
    pause
    exit /b 1
)

echo ✅ Build erfolgreich!

echo 🚀 Starte Container...
docker-compose up -d

echo ⏳ Warte auf Start...
timeout /t 15 /nobreak >nul

echo ========================================
echo ✅ Installation abgeschlossen!
echo ========================================
echo Scandy: http://localhost:%APP_PORT%
echo Mongo Express: http://localhost:%MONGO_EXPRESS_PORT%
echo ========================================
echo.
echo 📋 Scripts:
echo - start.bat: Container starten
echo - stop.bat: Container stoppen
echo - update.bat: System aktualisieren
echo ========================================

echo.
echo 🔄 Richte automatische Backups ein...
echo Erstelle Backup-Script...
(
echo @echo off
echo setlocal enabledelayedexpansion
echo set BACKUP_DIR=%DATA_DIR%\backups
echo for /f "tokens=2 delims==" %%a in ^('wmic OS Get localdatetime /value'^) do set "dt=%%a"
echo set "YY=!dt:~2,2!" ^& set "YYYY=!dt:~0,4!" ^& set "MM=!dt:~4,2!" ^& set "DD=!dt:~6,2!"
echo set "HH=!dt:~8,2!" ^& set "Min=!dt:~10,2!" ^& set "Sec=!dt:~12,2!"
echo set "TIMESTAMP=!YYYY!!MM!!DD!_!HH!!Min!!Sec!"
echo.
echo echo Erstelle Backup...
echo if not exist "!BACKUP_DIR!" mkdir "!BACKUP_DIR!"
echo docker exec %CONTAINER_NAME%-mongodb mongodump --out /tmp/backup
echo docker cp %CONTAINER_NAME%-mongodb:/tmp/backup "!BACKUP_DIR!\mongodb_!TIMESTAMP!"
echo powershell -Command "Compress-Archive -Path '%DATA_DIR%\uploads', '%DATA_DIR%\backups', '%DATA_DIR%\logs' -DestinationPath '!BACKUP_DIR!\app_data_!TIMESTAMP!.zip'"
echo echo Backup erstellt: !BACKUP_DIR!
) > backup.bat

echo ✅ Automatische Backups eingerichtet!
echo 💡 Backups werden bei jedem Start erstellt
echo.

pause 