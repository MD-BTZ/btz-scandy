@echo off
setlocal enabledelayedexpansion

REM Scandy Ein-Klick-Installation
REM MongoDB + App Container Setup

echo ========================================
echo    Scandy Ein-Klick-Installation
echo    MongoDB + App Container Setup
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

REM Container-Name Abfrage
set /p CONTAINER_NAME="Bitte geben Sie einen Namen für die Umgebung ein (Standard: scandy): "
if "%CONTAINER_NAME%"=="" set CONTAINER_NAME=scandy

REM App-Port Abfrage
set /p APP_PORT="Bitte geben Sie den Port für die App ein (Standard: 5000): "
if "%APP_PORT%"=="" set APP_PORT=5000

REM MongoDB-Port Abfrage
set /p MONGO_PORT="Bitte geben Sie den Port für MongoDB ein (Standard: 27017): "
if "%MONGO_PORT%"=="" set MONGO_PORT=27017

REM Mongo Express Port Abfrage
set /p MONGO_EXPRESS_PORT="Bitte geben Sie den Port für Mongo Express (Web-UI) ein (Standard: 8081): "
if "%MONGO_EXPRESS_PORT%"=="" set MONGO_EXPRESS_PORT=8081

echo ========================================
echo    Konfiguration:
echo ========================================
echo Container Name: %CONTAINER_NAME%
echo App Port: %APP_PORT%
echo MongoDB Port: %MONGO_PORT%
echo Mongo Express Port: %MONGO_EXPRESS_PORT%
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

REM Erstelle angepasste docker-compose.yml
echo Erstelle docker-compose.yml...
(
echo version: '3.8'
echo.
echo services:
echo   %CONTAINER_NAME%-mongodb:
echo     image: mongo:7.0
echo     container_name: %CONTAINER_NAME%-mongodb
echo     restart: unless-stopped
echo     environment:
echo       MONGO_INITDB_ROOT_USERNAME: admin
echo       MONGO_INITDB_ROOT_PASSWORD: scandy123
echo       MONGO_INITDB_DATABASE: scandy
echo     ports:
echo       - "%MONGO_PORT%:27017"
echo     volumes:
echo       - mongodb_data:/data/db
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
echo       ME_CONFIG_MONGODB_ADMINUSERNAME: admin
echo       ME_CONFIG_MONGODB_ADMINPASSWORD: scandy123
echo       ME_CONFIG_MONGODB_URL: mongodb://admin:scandy123@%CONTAINER_NAME%-mongodb:27017/
echo       ME_CONFIG_BASICAUTH_USERNAME: admin
echo       ME_CONFIG_BASICAUTH_PASSWORD: scandy123
echo     ports:
echo       - "%MONGO_EXPRESS_PORT%:8081"
echo     depends_on:
echo       %CONTAINER_NAME%-mongodb:
echo         condition: service_healthy
echo     networks:
echo       - %CONTAINER_NAME%-network
echo.
echo   %CONTAINER_NAME%-app:
echo     image: woschj/scandy:latest
echo     container_name: %CONTAINER_NAME%-app
echo     restart: unless-stopped
echo     environment:
echo       - DATABASE_MODE=mongodb
echo       - MONGODB_URI=mongodb://admin:scandy123@%CONTAINER_NAME%-mongodb:27017/
echo       - MONGODB_DB=scandy
echo       - FLASK_ENV=production
echo       - SECRET_KEY=scandy-secret-key-change-in-production
echo       - SYSTEM_NAME=Scandy
echo       - TICKET_SYSTEM_NAME=Aufgaben
echo       - TOOL_SYSTEM_NAME=Werkzeuge
echo       - CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter
echo       - TZ=Europe/Berlin
echo     ports:
echo       - "%APP_PORT%:5000"
echo     volumes:
echo       - app_uploads:/app/app/uploads
echo       - app_backups:/app/app/backups
echo       - app_logs:/app/app/logs
echo       - app_static:/app/app/static
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
echo     logging:
echo       driver: "json-file"
echo       options:
echo         max-size: "10m"
echo         max-file: "3"
echo.
echo volumes:
echo   mongodb_data:
echo     driver: local
echo   app_uploads:
echo     driver: local
echo   app_backups:
echo     driver: local
echo   app_logs:
echo     driver: local
echo   app_static:
echo     driver: local
echo.
echo networks:
echo   %CONTAINER_NAME%-network:
echo     driver: bridge
) > docker-compose.yml

REM Erstelle MongoDB Init-Skript
echo Erstelle MongoDB Init-Skript...
if not exist "mongo-init" mkdir "mongo-init"
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
) > mongo-init\init.js

REM Erstelle Verwaltungsskripte
echo Erstelle Verwaltungsskripte...

REM Start-Skript
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

REM Stop-Skript
(
echo @echo off
echo echo Stoppe Scandy Docker-Container...
echo docker-compose down
echo.
echo echo Container gestoppt.
echo pause
) > stop.bat

REM Update-Skript
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
echo REM Starte Container
echo docker-compose up -d
echo.
echo echo Update abgeschlossen!
echo pause
) > update.bat

REM Backup-Skript
(
echo @echo off
echo set BACKUP_DIR=./backups
echo for /f "tokens=2 delims==" %%a in ^('wmic OS Get localdatetime /value'^) do set "dt=%%a"
echo set "YY=!dt:~2,2!" ^& set "YYYY=!dt:~0,4!" ^& set "MM=!dt:~4,2!" ^& set "DD=!dt:~6,2!"
echo set "HH=!dt:~8,2!" ^& set "Min=!dt:~10,2!" ^& set "Sec=!dt:~12,2!"
echo set "TIMESTAMP=!YYYY!!MM!!DD!_!HH!!Min!!Sec!"
echo.
echo echo Erstelle Backup...
echo.
echo REM Erstelle Backup-Verzeichnis
echo if not exist "!BACKUP_DIR!" mkdir "!BACKUP_DIR!"
echo.
echo REM MongoDB Backup
echo echo Backup MongoDB...
echo docker exec %CONTAINER_NAME%-mongodb mongodump --out /tmp/backup
echo docker cp %CONTAINER_NAME%-mongodb:/tmp/backup "!BACKUP_DIR!\mongodb_!TIMESTAMP!"
echo.
echo REM App-Daten Backup
echo echo Backup App-Daten...
echo powershell -Command "Compress-Archive -Path '%DATA_DIR%\uploads', '%DATA_DIR%\backups', '%DATA_DIR%\logs' -DestinationPath '!BACKUP_DIR!\app_data_!TIMESTAMP!.zip'"
echo.
echo echo Backup erstellt: !BACKUP_DIR!
echo pause
) > backup.bat

REM Baue und starte Container
echo Baue und starte Container...
docker-compose down --volumes --remove-orphans
docker-compose up -d

echo ========================================
echo Installation abgeschlossen!
echo Die Anwendung ist unter http://localhost:%APP_PORT% erreichbar
echo Container-Name: %CONTAINER_NAME%
echo MongoDB Port: %MONGO_PORT%
echo Mongo Express Port: %MONGO_EXPRESS_PORT%
echo ========================================
echo.
echo Verwaltung:
echo   Starten: start.bat
echo   Stoppen: stop.bat
echo   Update:  update.bat
echo   Backup:  backup.bat

pause 