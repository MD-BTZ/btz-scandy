@echo off
setlocal enabledelayedexpansion

echo 🚀 Scandy mit Backup-Prüfung starten
echo ====================================

REM Finde Projekt-Verzeichnis
for /d %%i in (*_project) do (
    if exist "%%i\docker-compose.yml" (
        set PROJECT_DIR=%%i
        goto found_project
    )
)

echo ❌ Keine Scandy-Installation gefunden!
echo Führen Sie zuerst install.bat aus.
pause
exit /b 1

:found_project
cd "%PROJECT_DIR%"

echo ✅ Projekt gefunden: %PROJECT_DIR%

REM Starte Container
echo.
echo 🔄 Starte Scandy Container...
docker-compose up -d

if errorlevel 1 (
    echo ❌ Fehler beim Starten der Container!
    pause
    exit /b 1
)

echo.
echo ✅ Container erfolgreich gestartet!
echo.
echo 📋 Container-Status:
docker-compose ps

echo.
echo 🌐 Scandy ist verfügbar unter: http://localhost:5000
echo.

REM Prüfe automatische Backups
echo 🔍 Prüfe automatische Backup-Einrichtung...
call check-backup-setup.bat

echo.
echo ✅ Scandy ist bereit!
echo.
pause 