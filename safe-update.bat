@echo off
setlocal enabledelayedexpansion

echo 🔄 Sicheres Scandy Update
echo =========================

REM Prüfe ob Docker läuft
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker läuft nicht. Bitte starten Sie Docker zuerst.
    pause
    exit /b 1
)

echo ✓ Docker ist verfügbar

REM Finde alle Scandy-Projekte
echo 🔍 Suche Scandy-Installationen...
set FOUND_PROJECTS=0

for /d %%i in (*_project) do (
    if exist "%%i\docker-compose.yml" (
        echo 📁 Gefunden: %%i
        set /a FOUND_PROJECTS+=1
        set PROJECT_DIR=%%i
    )
)

if %FOUND_PROJECTS%==0 (
    echo ❌ Keine Scandy-Installation gefunden!
    echo 💡 Führen Sie zuerst install.bat aus.
    pause
    exit /b 1
)

if %FOUND_PROJECTS%==1 (
    echo ✅ Verwende Projekt: %PROJECT_DIR%
) else (
    echo ⚠️  Mehrere Projekte gefunden. Bitte wählen Sie eines:
    for /d %%i in (*_project) do (
        if exist "%%i\docker-compose.yml" (
            echo - %%i
        )
    )
    set /p PROJECT_DIR="Projekt-Verzeichnis: "
    if not exist "%PROJECT_DIR%\docker-compose.yml" (
        echo ❌ Ungültiges Projekt-Verzeichnis!
        pause
        exit /b 1
    )
)

cd "%PROJECT_DIR%"

echo.
echo 📋 Update-Optionen:
echo 1. Sicheres Update (empfohlen) - Backup + Update
echo 2. Schnelles Update - Nur App-Container
echo 3. Vollständiges Update - Alle Container
echo 4. Abbrechen
echo.
set /p update_choice="Wählen Sie eine Option (1-4): "

if "%update_choice%"=="1" goto safe_update
if "%update_choice%"=="2" goto quick_update
if "%update_choice%"=="3" goto full_update
if "%update_choice%"=="4" goto cancel
echo Ungültige Auswahl.
goto cancel

:safe_update
echo 🔄 Sicheres Update wird durchgeführt...
echo.

echo 📦 Erstelle Backup...
call backup.bat
if errorlevel 1 (
    echo ❌ Backup fehlgeschlagen! Update abgebrochen.
    pause
    exit /b 1
)
echo ✅ Backup erfolgreich!

echo.
echo 🔄 Stoppe Container...
docker-compose down

echo.
echo 📥 Lade neue Images...
docker-compose pull

echo.
echo 🏗️  Baue App-Container neu...
docker-compose build --no-cache scandy-app

echo.
echo 🚀 Starte Container...
docker-compose up -d

echo.
echo ✅ Sicheres Update abgeschlossen!
echo 📋 Container-Status:
docker-compose ps
goto end

:quick_update
echo 🔄 Schnelles Update wird durchgeführt...
echo.

echo 🔄 Stoppe App-Container...
docker-compose stop scandy-app

echo.
echo 📥 Lade neues App-Image...
docker-compose pull scandy-app

echo.
echo 🏗️  Baue App-Container neu...
docker-compose build --no-cache scandy-app

echo.
echo 🚀 Starte App-Container...
docker-compose up -d scandy-app

echo.
echo ✅ Schnelles Update abgeschlossen!
echo 📋 Container-Status:
docker-compose ps
goto end

:full_update
echo 🔄 Vollständiges Update wird durchgeführt...
echo.

echo ⚠️  WARNUNG: Dies stoppt alle Container und lädt alle Images neu!
set /p confirm="Sind Sie sicher? (j/n): "
if /i not "%confirm%"=="j" goto cancel

echo.
echo 🔄 Stoppe alle Container...
docker-compose down

echo.
echo 📥 Lade alle Images neu...
docker-compose pull

echo.
echo 🏗️  Baue alle Container neu...
docker-compose build --no-cache

echo.
echo 🚀 Starte alle Container...
docker-compose up -d

echo.
echo ✅ Vollständiges Update abgeschlossen!
echo 📋 Container-Status:
docker-compose ps
goto end

:cancel
echo Update abgebrochen.
goto end

:end
echo.
echo 📋 Nächste Schritte:
echo - Prüfen Sie die Anwendung: http://localhost:5000
echo - Prüfen Sie die Logs: docker-compose logs
echo - Bei Problemen: troubleshoot.bat
echo.
pause 