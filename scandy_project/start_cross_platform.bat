@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo Scandy - Plattformübergreifender Start
echo ==========================================
echo.

REM Prüfe Docker-Installation
echo [1/5] Prüfe Docker-Installation...
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker ist nicht installiert oder nicht verfügbar
    echo Bitte installieren Sie Docker Desktop: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo ✅ Docker ist verfügbar

REM Prüfe Docker-Compose
echo [2/5] Prüfe Docker Compose...
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose ist nicht verfügbar
    echo Versuche mit 'docker compose' (neue Syntax)...
    docker compose version >nul 2>&1
    if errorlevel 1 (
        echo ❌ Docker Compose ist nicht verfügbar
        pause
        exit /b 1
    ) else (
        set DOCKER_COMPOSE_CMD=docker compose
    )
) else (
    set DOCKER_COMPOSE_CMD=docker-compose
)
echo ✅ Docker Compose ist verfügbar

REM Stoppe bestehende Container
echo [3/5] Stoppe bestehende Container...
%DOCKER_COMPOSE_CMD% down >nul 2>&1
echo ✅ Bestehende Container gestoppt

REM Starte Container
echo [4/5] Starte Scandy-Container...
%DOCKER_COMPOSE_CMD% up -d --build
if errorlevel 1 (
    echo ❌ Fehler beim Starten der Container
    echo.
    echo Versuche alternative Start-Methode...
    docker-compose up -d --build
    if errorlevel 1 (
        echo ❌ Container konnten nicht gestartet werden
        pause
        exit /b 1
    )
)
echo ✅ Container gestartet

REM Warte auf Container-Start
echo [5/5] Warte auf Container-Start...
timeout /t 15 /nobreak >nul

REM Teste Verbindungen
echo.
echo ==========================================
echo Verbindungstests
echo ==========================================

REM Teste MongoDB
echo Teste MongoDB-Verbindung...
curl -s http://127.0.0.1:27017 >nul 2>&1
if errorlevel 1 (
    echo ⚠️  MongoDB nicht direkt erreichbar (normal in Docker)
) else (
    echo ✅ MongoDB ist erreichbar
)

REM Teste App
echo Teste Scandy-App...
curl -s http://127.0.0.1:5000 >nul 2>&1
if errorlevel 1 (
    echo ⚠️  App noch nicht bereit, warte...
    timeout /t 10 /nobreak >nul
    curl -s http://127.0.0.1:5000 >nul 2>&1
    if errorlevel 1 (
        echo ❌ App ist nicht erreichbar
        echo Prüfe Logs mit: %DOCKER_COMPOSE_CMD% logs scandy-app
    ) else (
        echo ✅ App ist erreichbar
    )
) else (
    echo ✅ App ist erreichbar
)

REM Teste Mongo Express
echo Teste Mongo Express...
curl -s http://127.0.0.1:8081 >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Mongo Express noch nicht bereit
) else (
    echo ✅ Mongo Express ist erreichbar
)

echo.
echo ==========================================
echo Scandy ist verfügbar unter:
echo ==========================================
echo.
echo 🌐 Hauptanwendung: http://localhost:5000
echo 🌐 Hauptanwendung: http://127.0.0.1:5000
echo.
echo 📊 Mongo Express: http://localhost:8081
echo 📊 Mongo Express: http://127.0.0.1:8081
echo.
echo 🗄️  MongoDB: localhost:27017
echo 🗄️  MongoDB: 127.0.0.1:27017
echo.
echo ==========================================
echo Container-Status:
echo ==========================================
%DOCKER_COMPOSE_CMD% ps
echo.
echo ==========================================
echo Nützliche Befehle:
echo ==========================================
echo Container stoppen: %DOCKER_COMPOSE_CMD% down
echo Logs anzeigen: %DOCKER_COMPOSE_CMD% logs
echo App-Logs: %DOCKER_COMPOSE_CMD% logs scandy-app
echo MongoDB-Logs: %DOCKER_COMPOSE_CMD% logs scandy-mongodb
echo.
pause 