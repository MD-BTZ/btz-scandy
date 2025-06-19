@echo off
REM MongoDB-Startskript für Scandy (Windows)

echo === Scandy MongoDB Setup ===

REM Prüfe ob Docker installiert ist
docker --version >nul 2>&1
if errorlevel 1 (
    echo Docker ist nicht installiert. Bitte installieren Sie Docker Desktop zuerst.
    pause
    exit /b 1
)

REM Prüfe ob Docker läuft
docker info >nul 2>&1
if errorlevel 1 (
    echo Docker läuft nicht. Bitte starten Sie Docker Desktop zuerst.
    pause
    exit /b 1
)

echo Docker ist verfügbar.

REM Stoppe existierende Container
echo Stoppe existierende MongoDB-Container...
docker stop scandy-mongodb >nul 2>&1
docker rm scandy-mongodb >nul 2>&1

REM Starte MongoDB-Container
echo Starte MongoDB-Container...
docker run -d ^
  --name scandy-mongodb ^
  -p 27017:27017 ^
  -e MONGO_INITDB_ROOT_USERNAME=admin ^
  -e MONGO_INITDB_ROOT_PASSWORD=scandy123 ^
  -e MONGO_INITDB_DATABASE=scandy ^
  mongo:7.0

REM Warte bis MongoDB bereit ist
echo Warte auf MongoDB...
timeout /t 10 /nobreak >nul

REM Teste MongoDB-Verbindung
echo Teste MongoDB-Verbindung...
docker exec scandy-mongodb mongosh --eval "db.adminCommand('ping')" >nul 2>&1
if errorlevel 1 (
    echo ✗ MongoDB-Verbindung fehlgeschlagen
    pause
    exit /b 1
) else (
    echo ✓ MongoDB ist bereit!
)

REM Starte MongoDB Express (optional)
set /p start_express="Möchten Sie MongoDB Express (Web-Interface) starten? (y/n): "
if /i "%start_express%"=="y" (
    echo Starte MongoDB Express...
    docker stop scandy-mongo-express >nul 2>&1
    docker rm scandy-mongo-express >nul 2>&1
    
    docker run -d ^
      --name scandy-mongo-express ^
      -p 8081:8081 ^
      -e ME_CONFIG_MONGODB_ADMINUSERNAME=admin ^
      -e ME_CONFIG_MONGODB_ADMINPASSWORD=scandy123 ^
      -e ME_CONFIG_MONGODB_URL=mongodb://admin:scandy123@scandy-mongodb:27017/ ^
      -e ME_CONFIG_BASICAUTH_USERNAME=admin ^
      -e ME_CONFIG_BASICAUTH_PASSWORD=scandy123 ^
      --network host ^
      mongo-express:1.0.0
    
    echo ✓ MongoDB Express gestartet: http://localhost:8081
    echo   Benutzername: admin
    echo   Passwort: scandy123
)

REM Setze Umgebungsvariablen
echo.
echo === Umgebungsvariablen ===
echo Setzen Sie folgende Umgebungsvariablen:
echo.
echo set DATABASE_MODE=mongodb
echo set MONGODB_URI=mongodb://admin:scandy123@localhost:27017/
echo set MONGODB_DB=scandy
echo.
echo Oder erstellen Sie eine .env Datei:
echo.
echo DATABASE_MODE=mongodb
echo MONGODB_URI=mongodb://admin:scandy123@localhost:27017/
echo MONGODB_DB=scandy
echo.

REM Starte Scandy-Anwendung
set /p start_scandy="Möchten Sie Scandy mit MongoDB starten? (y/n): "
if /i "%start_scandy%"=="y" (
    echo Starte Scandy-Anwendung...
    
    REM Setze Umgebungsvariablen für diesen Prozess
    set DATABASE_MODE=mongodb
    set MONGODB_URI=mongodb://admin:scandy123@localhost:27017/
    set MONGODB_DB=scandy
    
    REM Starte Flask-Anwendung
    python -m flask run --host=0.0.0.0 --port=5000
)

echo.
echo === MongoDB Setup abgeschlossen ===
echo MongoDB läuft auf: localhost:27017
echo Datenbank: scandy
echo Benutzer: admin
echo Passwort: scandy123
pause 