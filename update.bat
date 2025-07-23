@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Scandy App Update
echo ========================================
echo Dieses Skript aktualisiert NUR die Scandy-App:
echo - ✅ Scandy App wird aktualisiert
echo - 🔒 MongoDB bleibt unverändert
echo - 🔒 Mongo Express bleibt unverändert
echo - 💾 Alle Daten bleiben erhalten
echo - 🔐 .env-Einstellungen bleiben erhalten
echo ========================================
echo.

REM Prüfe ob Docker installiert ist
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Docker ist nicht installiert oder nicht verfügbar!
    pause
    exit /b 1
)

REM Prüfe ob Docker läuft
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Docker läuft nicht!
    pause
    exit /b 1
)

REM Prüfe ob .env existiert, falls nicht erstelle sie
if not exist ".env" (
    echo 📝 Erstelle .env-Datei aus env.example...
    copy env.example .env >nul
    echo ✅ .env-Datei erstellt!
    echo ⚠️  Bitte passe die Werte in .env an deine Umgebung an!
    echo.
)

REM Sichere .env-Datei vor dem Update
if exist ".env" (
    echo 💾 Sichere .env-Datei...
    copy .env .env.backup >nul
    echo ✅ .env gesichert als .env.backup
)

REM Prüfe ob docker-compose.yml existiert
if not exist "docker-compose.yml" (
    echo ❌ ERROR: docker-compose.yml nicht gefunden!
    echo Bitte führen Sie zuerst install.bat aus.
    pause
    exit /b 1
)

echo 🔍 Prüfe bestehende Installation...
docker compose ps

echo.
echo ⚠️  WARNUNG: Dieses Update betrifft NUR die Scandy-App!
echo    MongoDB und Mongo Express bleiben unverändert.
echo    Alle Daten bleiben erhalten.
echo    .env-Einstellungen bleiben erhalten.
echo.

set /p confirm="Möchten Sie fortfahren? (j/N): "
if /i not "!confirm!"=="j" (
    echo Update abgebrochen.
    pause
    exit /b 0
)

echo.
echo 🔄 Starte App-Update...

REM Stoppe nur die App-Container
echo 🛑 Stoppe App-Container...
docker compose stop scandy-app >nul 2>&1

REM Entferne nur die App-Container
echo 🗑️  Entferne alte App-Container...
docker compose rm -f scandy-app >nul 2>&1

REM Entferne alte App-Images
echo 🗑️  Entferne alte App-Images...
for /f "tokens=3" %%i in ('docker images ^| findstr scandy-local') do docker rmi -f %%i >nul 2>&1

REM Baue nur die App neu
echo 🔨 Baue neue App-Version...
docker compose build --no-cache scandy-app

if %errorlevel% neq 0 (
    echo ❌ Fehler beim Bauen der App!
    echo Versuche es mit einfachem Build...
    docker compose build scandy-app
)

if %errorlevel% neq 0 (
    echo ❌ App-Update fehlgeschlagen!
    pause
    exit /b 1
)

REM Starte nur die App
echo 🚀 Starte neue App-Version...
docker compose up -d scandy-app

if %errorlevel% neq 0 (
    echo ❌ Fehler beim Starten der App!
    pause
    exit /b 1
)

echo.
echo ⏳ Warte auf App-Start...
timeout /t 10 /nobreak >nul

REM Prüfe App-Status
echo 🔍 Prüfe App-Status...
docker compose ps scandy-app

REM Prüfe App-Logs
echo.
echo 📋 Letzte App-Logs:
docker compose logs --tail=10 scandy-app

REM Prüfe ob App läuft
echo.
echo 🔍 Prüfe App-Verfügbarkeit...
timeout /t 5 /nobreak >nul

curl -s http://localhost:5000 >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Scandy App läuft erfolgreich
) else (
    echo ⚠️  Scandy App startet noch...
    echo    Bitte warten Sie einen Moment und prüfen Sie:
    echo    docker compose logs scandy-app
)

echo.
echo ========================================
echo ✅ APP-UPDATE ABGESCHLOSSEN!
echo ========================================
echo.
echo 🎉 Die Scandy-App wurde erfolgreich aktualisiert!
echo.
echo 🌐 Verfügbare Services:
echo - Scandy App:     http://localhost:5000 ✅ AKTUALISIERT
echo - Mongo Express:  http://localhost:8081 🔒 UNVERÄNDERT
echo.
echo 💾 Datenbank-Status:
echo - MongoDB:        🔒 Unverändert ^(Daten erhalten^)
echo - Mongo Express:  🔒 Unverändert ^(Daten erhalten^)
echo.
echo 🔐 Konfiguration:
echo - .env-Datei:     🔒 Unverändert ^(Einstellungen erhalten^)
echo - Backup:         .env.backup ^(falls benötigt^)
echo.
echo 🔧 Nützliche Befehle:
echo - App-Logs:       docker compose logs -f scandy-app
echo - App-Status:     docker compose ps scandy-app
echo - App-Neustart:   docker compose restart scandy-app
echo - Alle Container: docker compose ps
echo.
echo 📁 Datenverzeichnisse ^(unverändert^):
echo - Backups: .\backups\
echo - Logs:    .\logs\
echo - Uploads: .\data\uploads\
echo.
echo ========================================
pause 