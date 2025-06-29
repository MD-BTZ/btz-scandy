@echo off
setlocal enabledelayedexpansion

echo 🔧 Automatische Scandy Backups verwalten
echo ========================================

REM Prüfe Administrator-Rechte
net session >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Administrator-Rechte erforderlich!
    echo Bitte führen Sie dieses Script als Administrator aus.
    pause
    exit /b 1
)

echo ✅ Administrator-Rechte bestätigt

echo.
echo 📋 Verfügbare Aktionen:
echo 1. Status der automatischen Backups anzeigen
echo 2. Automatische Backups aktivieren/einrichten
echo 3. Automatische Backups deaktivieren
echo 4. Backup-Zeiten ändern
echo 5. Backup-Logs anzeigen
echo 6. Manuelles Backup erstellen
echo 7. Backup-Verzeichnis öffnen
echo 8. Beenden
echo.
set /p action="Wählen Sie eine Aktion (1-8): "

if "%action%"=="1" goto show_status
if "%action%"=="2" goto setup_backup
if "%action%"=="3" goto disable_backup
if "%action%"=="4" goto change_times
if "%action%"=="5" goto show_logs
if "%action%"=="6" goto manual_backup
if "%action%"=="7" goto open_backup_dir
if "%action%"=="8" goto end
echo Ungültige Auswahl.
goto end

:show_status
echo.
echo 📊 Status der automatischen Backups:
echo.
echo Windows Tasks:
schtasks /query /tn "Scandy Auto Backup Morning" /fo table 2>nul
if errorlevel 1 (
    echo ❌ Morgendlicher Task nicht gefunden
) else (
    echo ✅ Morgendlicher Task aktiv
)
echo.
schtasks /query /tn "Scandy Auto Backup Evening" /fo table 2>nul
if errorlevel 1 (
    echo ❌ Abendlicher Task nicht gefunden
) else (
    echo ✅ Abendlicher Task aktiv
)

REM Prüfe Konfigurationsdatei
if exist "auto_backup_config.txt" (
    echo.
    echo 📝 Konfiguration:
    type auto_backup_config.txt
) else (
    echo.
    echo ❌ Keine Konfigurationsdatei gefunden
)

REM Prüfe Backup-Verzeichnis
if exist "backups\auto" (
    echo.
    echo 📁 Backup-Verzeichnis: backups\auto
    echo Anzahl Backups:
    dir /b "backups\auto\auto_backup_*.zip" 2>nul | find /c /v ""
    if errorlevel 1 echo 0 Backups gefunden
    echo (Maximal 14 Backups - 7 Tage × 2x täglich)
) else (
    echo.
    echo ❌ Backup-Verzeichnis nicht gefunden
)

REM Prüfe Log-Datei
if exist "auto_backup.log" (
    echo.
    echo 📋 Letzte Log-Einträge:
    powershell -Command "Get-Content 'auto_backup.log' | Select-Object -Last 5"
) else (
    echo.
    echo ❌ Keine Log-Datei gefunden
)
goto end

:setup_backup
echo.
echo 🔄 Einrichtung automatischer Backups...
call setup-auto-backup.bat
goto end

:disable_backup
echo.
echo ⚠️  Automatische Backups deaktivieren...
echo.
set /p confirm="Sind Sie sicher? (j/n): "
if /i not "%confirm%"=="j" goto end

echo Lösche Windows Tasks...
schtasks /delete /tn "Scandy Auto Backup Morning" /f >nul 2>&1
schtasks /delete /tn "Scandy Auto Backup Evening" /f >nul 2>&1

echo ✅ Automatische Backups deaktiviert!
echo.
echo 💡 Hinweis: Bestehende Backups bleiben erhalten.
goto end

:change_times
echo.
echo ⏰ Backup-Zeiten ändern...
echo.
echo Aktuelle Zeiten:
schtasks /query /tn "Scandy Auto Backup Morning" /fo table 2>nul
schtasks /query /tn "Scandy Auto Backup Evening" /fo table 2>nul
echo.
echo Verfügbare Optionen:
echo 1. Morgens 06:00 und Abends 18:00
echo 2. Morgens 08:00 und Abends 20:00
echo 3. Benutzerdefiniert
echo.
set /p time_choice="Wählen Sie eine Option (1-3): "

if "%time_choice%"=="1" (
    set MORNING_TIME=06:00
    set EVENING_TIME=18:00
) else if "%time_choice%"=="2" (
    set MORNING_TIME=08:00
    set EVENING_TIME=20:00
) else if "%time_choice%"=="3" (
    set /p MORNING_TIME="Morgens Backup-Zeit (HH:MM): "
    set /p EVENING_TIME="Abends Backup-Zeit (HH:MM): "
) else (
    echo Ungültige Auswahl.
    goto end
)

echo.
echo 🔄 Aktualisiere Windows Tasks...

REM Lösche bestehende Tasks
schtasks /delete /tn "Scandy Auto Backup Morning" /f >nul 2>&1
schtasks /delete /tn "Scandy Auto Backup Evening" /f >nul 2>&1

REM Finde Projekt-Verzeichnis
for /d %%i in (*_project) do (
    if exist "%%i\docker-compose.yml" (
        set PROJECT_DIR=%%i
        goto update_tasks
    )
)
echo ❌ Keine Scandy-Installation gefunden!
goto end

:update_tasks
cd "%PROJECT_DIR%"
set SCRIPT_PATH=%CD%\auto-backup.bat

REM Erstelle neue Tasks
schtasks /create /tn "Scandy Auto Backup Morning" /tr "\"%SCRIPT_PATH%\"" /sc daily /st %MORNING_TIME% /ru "SYSTEM" /f
schtasks /create /tn "Scandy Auto Backup Evening" /tr "\"%SCRIPT_PATH%\"" /sc daily /st %EVENING_TIME% /ru "SYSTEM" /f

echo ✅ Backup-Zeiten aktualisiert!
echo - Morgens: %MORNING_TIME%
echo - Abends: %EVENING_TIME%
goto end

:show_logs
echo.
echo 📋 Backup-Logs anzeigen...
if exist "auto_backup.log" (
    echo.
    echo Letzte 20 Log-Einträge:
    echo =======================
    powershell -Command "Get-Content 'auto_backup.log' | Select-Object -Last 20"
    echo.
    echo Vollständige Log-Datei öffnen? (j/n):
    set /p open_log=""
    if /i "%open_log%"=="j" (
        notepad auto_backup.log
    )
) else (
    echo ❌ Keine Log-Datei gefunden!
)
goto end

:manual_backup
echo.
echo 📦 Manuelles Backup erstellen...
echo.
set /p confirm="Soll ein manuelles Backup erstellt werden? (j/n): "
if /i not "%confirm%"=="j" goto end

REM Finde Projekt-Verzeichnis
for /d %%i in (*_project) do (
    if exist "%%i\docker-compose.yml" (
        set PROJECT_DIR=%%i
        goto run_manual_backup
    )
)
echo ❌ Keine Scandy-Installation gefunden!
goto end

:run_manual_backup
cd "%PROJECT_DIR%"
echo Führe manuelles Backup aus...
call auto-backup.bat
goto end

:open_backup_dir
echo.
echo 📁 Backup-Verzeichnis öffnen...
if exist "backups\auto" (
    explorer "backups\auto"
) else (
    echo ❌ Backup-Verzeichnis nicht gefunden!
)
goto end

:end
echo.
pause 