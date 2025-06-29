@echo off
setlocal enabledelayedexpansion

echo 🔄 Einrichtung automatischer Scandy Backups
echo ===========================================

REM Prüfe Administrator-Rechte
net session >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Administrator-Rechte erforderlich!
    echo Bitte führen Sie dieses Script als Administrator aus.
    pause
    exit /b 1
)

echo ✅ Administrator-Rechte bestätigt

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

REM Erstelle vollständigen Pfad zum auto-backup.bat
set SCRIPT_PATH=%CD%\auto-backup.bat
echo 📁 Script-Pfad: %SCRIPT_PATH%

REM Prüfe ob auto-backup.bat existiert
if not exist "%SCRIPT_PATH%" (
    echo ❌ auto-backup.bat nicht gefunden!
    echo Kopiere auto-backup.bat in das Projektverzeichnis...
    copy "..\auto-backup.bat" "%SCRIPT_PATH%" >nul
    if errorlevel 1 (
        echo ❌ Fehler beim Kopieren von auto-backup.bat!
        pause
        exit /b 1
    )
)

echo.
echo 📋 Backup-Zeitplan konfigurieren:
echo.
echo Verfügbare Optionen:
echo 1. Morgens 06:00 und Abends 18:00 (empfohlen)
echo 2. Morgens 08:00 und Abends 20:00
echo 3. Benutzerdefiniert
echo.
set /p schedule_choice="Wählen Sie eine Option (1-3): "

if "%schedule_choice%"=="1" (
    set MORNING_TIME=06:00
    set EVENING_TIME=18:00
) else if "%schedule_choice%"=="2" (
    set MORNING_TIME=08:00
    set EVENING_TIME=20:00
) else if "%schedule_choice%"=="3" (
    echo.
    set /p MORNING_TIME="Morgens Backup-Zeit (HH:MM): "
    set /p EVENING_TIME="Abends Backup-Zeit (HH:MM): "
) else (
    echo Ungültige Auswahl. Verwende Standard-Zeiten.
    set MORNING_TIME=06:00
    set EVENING_TIME=18:00
)

echo.
echo ⏰ Backup-Zeiten:
echo - Morgens: %MORNING_TIME%
echo - Abends: %EVENING_TIME%

echo.
echo 🔄 Erstelle Windows Tasks...

REM Lösche bestehende Tasks (falls vorhanden)
schtasks /delete /tn "Scandy Auto Backup Morning" /f >nul 2>&1
schtasks /delete /tn "Scandy Auto Backup Evening" /f >nul 2>&1

REM Erstelle morgendlichen Task
echo Erstelle morgendlichen Backup-Task...
schtasks /create /tn "Scandy Auto Backup Morning" /tr "\"%SCRIPT_PATH%\"" /sc daily /st %MORNING_TIME% /ru "SYSTEM" /f
if errorlevel 1 (
    echo ❌ Fehler beim Erstellen des morgendlichen Tasks!
    pause
    exit /b 1
)

REM Erstelle abendlichen Task
echo Erstelle abendlichen Backup-Task...
schtasks /create /tn "Scandy Auto Backup Evening" /tr "\"%SCRIPT_PATH%\"" /sc daily /st %EVENING_TIME% /ru "SYSTEM" /f
if errorlevel 1 (
    echo ❌ Fehler beim Erstellen des abendlichen Tasks!
    pause
    exit /b 1
)

echo.
echo ✅ Windows Tasks erfolgreich erstellt!

echo.
echo 📋 Task-Status prüfen...
schtasks /query /tn "Scandy Auto Backup Morning" /fo table
echo.
schtasks /query /tn "Scandy Auto Backup Evening" /fo table

echo.
echo 📁 Backup-Verzeichnis erstellen...
if not exist "backups\auto" mkdir "backups\auto"

echo.
echo 📝 Erstelle Konfigurationsdatei...
echo Automatische Backups konfiguriert am: %date% %time% > auto_backup_config.txt
echo Projekt: %PROJECT_DIR% >> auto_backup_config.txt
echo Script-Pfad: %SCRIPT_PATH% >> auto_backup_config.txt
echo Morgens: %MORNING_TIME% >> auto_backup_config.txt
echo Abends: %EVENING_TIME% >> auto_backup_config.txt
echo Windows Tasks: >> auto_backup_config.txt
echo - Scandy Auto Backup Morning >> auto_backup_config.txt
echo - Scandy Auto Backup Evening >> auto_backup_config.txt

echo.
echo ✅ Automatische Backups erfolgreich eingerichtet!
echo.
echo 📋 Zusammenfassung:
echo - Morgens Backup: %MORNING_TIME%
echo - Abends Backup: %EVENING_TIME%
echo - Backup-Verzeichnis: backups\auto
echo - Log-Datei: auto_backup.log
echo - Konfiguration: auto_backup_config.txt
echo.
echo 💡 Tipps:
echo - Backups werden automatisch alle 7 Tage bereinigt (14 Backups behalten)
echo - Prüfen Sie auto_backup.log für Backup-Status
echo - Bei Problemen: troubleshoot.bat ausführen
echo.
pause 