@echo off
setlocal enabledelayedexpansion

echo 🔍 Prüfe automatische Backup-Einrichtung
echo ========================================

REM Prüfe Administrator-Rechte
net session >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Hinweis: Administrator-Rechte erforderlich für automatische Backups
    echo    Sie können Backups manuell einrichten mit: setup-auto-backup.bat
    goto end
)

REM Finde Projekt-Verzeichnis
for /d %%i in (*_project) do (
    if exist "%%i\docker-compose.yml" (
        set PROJECT_DIR=%%i
        goto found_project
    )
)

echo ❌ Keine Scandy-Installation gefunden!
goto end

:found_project
cd "%PROJECT_DIR%"

echo ✅ Projekt gefunden: %PROJECT_DIR%

REM Prüfe ob automatische Backups bereits eingerichtet sind
schtasks /query /tn "Scandy Auto Backup Morning" >nul 2>&1
if errorlevel 1 (
    echo ❌ Automatische Backups nicht eingerichtet
    echo.
    echo 🔄 Möchten Sie automatische Backups jetzt einrichten?
    echo - Morgens 06:00 und Abends 18:00
    echo - 14 Backups werden automatisch behalten (7 Tage)
    echo.
    set /p setup_backup="Automatische Backups einrichten? (j/n): "
    if /i "%setup_backup%"=="j" (
        echo.
        echo 🔄 Richte automatische Backups ein...
        call setup-auto-backup.bat
    ) else (
        echo.
        echo 💡 Sie können Backups später einrichten mit:
        echo    setup-auto-backup.bat
    )
) else (
    echo ✅ Automatische Backups sind eingerichtet!
    echo.
    echo 📋 Backup-Status:
    schtasks /query /tn "Scandy Auto Backup Morning" /fo table
    echo.
    schtasks /query /tn "Scandy Auto Backup Evening" /fo table
    echo.
    echo 💡 Backup-Verwaltung: manage-auto-backup.bat
)

:end
echo.
pause 