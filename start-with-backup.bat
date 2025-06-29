@echo off
setlocal enabledelayedexpansion

echo 🚀 Starte Scandy mit automatischem Backup...
echo ==========================================

REM Prüfe ob wir im Projektverzeichnis sind
if not exist "docker-compose.yml" (
    echo ❌ ERROR: docker-compose.yml nicht gefunden!
    echo Bitte führen Sie dieses Script im Projektverzeichnis aus.
    pause
    exit /b 1
)

REM Erstelle Backup vor dem Start
echo 📦 Erstelle Backup vor dem Start...
if exist "backup.bat" (
    call backup.bat
    echo ✅ Backup erstellt
) else (
    echo ⚠️  Backup-Script nicht gefunden, überspringe Backup
)

echo.
echo 🚀 Starte Container...
docker-compose up -d

echo.
echo ⏳ Warte auf Container-Start...
timeout /t 15 /nobreak >nul

echo.
echo 📊 Container-Status:
docker-compose ps

echo.
echo ==========================================
echo ✅ Scandy gestartet!
echo ==========================================
echo Scandy: http://localhost:5000
echo Mongo Express: http://localhost:8081
echo ==========================================
echo.
pause 