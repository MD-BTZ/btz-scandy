@echo off
setlocal enabledelayedexpansion

echo 📦 Automatisches Scandy Backup
echo =============================
echo Zeit: %date% %time%
echo.

REM Prüfe ob Docker läuft
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker läuft nicht. Backup nicht möglich.
    echo Backup fehlgeschlagen: %date% %time% - Docker nicht verfügbar >> auto_backup.log
    exit /b 1
)

REM Finde Projekt-Verzeichnis
for /d %%i in (*_project) do (
    if exist "%%i\docker-compose.yml" (
        set PROJECT_DIR=%%i
        goto found_project
    )
)

echo ❌ Keine Scandy-Installation gefunden!
echo Backup fehlgeschlagen: %date% %time% - Keine Installation gefunden >> auto_backup.log
exit /b 1

:found_project
cd "%PROJECT_DIR%"

echo ✅ Projekt gefunden: %PROJECT_DIR%

REM Erstelle Backup-Verzeichnis
set BACKUP_DIR=backups\auto
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Erstelle Zeitstempel
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=!dt:~2,2!" & set "YYYY=!dt:~0,4!" & set "MM=!dt:~4,2!" & set "DD=!dt:~6,2!"
set "HH=!dt:~8,2!" & set "Min=!dt:~10,2!" & set "Sec=!dt:~12,2!"
set "TIMESTAMP=!YYYY!!MM!!DD!_!HH!!Min!!Sec!"

set BACKUP_NAME=auto_backup_!TIMESTAMP!
set BACKUP_PATH=%BACKUP_DIR%\%BACKUP_NAME%

echo 📅 Backup-Zeitstempel: !TIMESTAMP!
echo 📁 Backup-Pfad: %BACKUP_PATH%

REM Erstelle Backup-Verzeichnis
mkdir "%BACKUP_PATH%"

echo.
echo 🔄 Erstelle Datenbank-Backup...

REM MongoDB Backup
echo - MongoDB-Daten...
docker-compose exec -T scandy-mongodb mongodump --username admin --password scandy123 --authenticationDatabase admin --db scandy --archive > "%BACKUP_PATH%\mongodb_backup.archive" 2>nul
if errorlevel 1 (
    echo ⚠️  MongoDB-Backup fehlgeschlagen (Container läuft möglicherweise nicht)
    echo Backup fehlgeschlagen: %date% %time% - MongoDB-Backup fehlgeschlagen >> auto_backup.log
    exit /b 1
) else (
    echo ✅ MongoDB-Backup erstellt
)

echo.
echo 📁 Kopiere wichtige Dateien...

REM Kopiere wichtige Verzeichnisse (nur kritische Daten)
if exist "data\uploads" (
    echo - Upload-Dateien...
    xcopy "data\uploads" "%BACKUP_PATH%\uploads" /E /I /Y >nul
)

if exist "data\static" (
    echo - Statische Dateien...
    xcopy "data\static" "%BACKUP_PATH%\static" /E /I /Y >nul
)

echo.
echo 📋 Erstelle Backup-Info...

REM Erstelle Backup-Info
echo Automatisches Backup erstellt am: %date% %time% > "%BACKUP_PATH%\backup_info.txt"
echo Projekt: %PROJECT_DIR% >> "%BACKUP_PATH%\backup_info.txt"
echo Zeitstempel: !TIMESTAMP! >> "%BACKUP_PATH%\backup_info.txt"
echo Typ: Automatisches Backup >> "%BACKUP_PATH%\backup_info.txt"
echo. >> "%BACKUP_PATH%\backup_info.txt"
echo Enthaltene Daten: >> "%BACKUP_PATH%\backup_info.txt"
if exist "%BACKUP_PATH%\mongodb_backup.archive" echo - MongoDB-Datenbank >> "%BACKUP_PATH%\backup_info.txt"
if exist "%BACKUP_PATH%\uploads" echo - Upload-Dateien >> "%BACKUP_PATH%\backup_info.txt"
if exist "%BACKUP_PATH%\static" echo - Statische Dateien >> "%BACKUP_PATH%\backup_info.txt"

echo.
echo 📦 Erstelle komprimiertes Backup...

REM Erstelle ZIP-Archiv
powershell -Command "Compress-Archive -Path '%BACKUP_PATH%' -DestinationPath '%BACKUP_PATH%.zip' -Force"
if errorlevel 1 (
    echo ❌ Fehler beim Erstellen des ZIP-Archivs!
    echo Backup fehlgeschlagen: %date% %time% - ZIP-Erstellung fehlgeschlagen >> auto_backup.log
    exit /b 1
)

REM Lösche temporäres Verzeichnis
rmdir /s /q "%BACKUP_PATH%" 2>nul

echo.
echo ✅ Automatisches Backup erfolgreich erstellt!
echo 📁 Backup-Datei: %BACKUP_PATH%.zip

REM Logge erfolgreiches Backup
echo Backup erfolgreich: %date% %time% - %BACKUP_PATH%.zip >> auto_backup.log

REM Lösche alte automatische Backups (behalte nur die letzten 14)
echo.
echo 🧹 Bereinige alte automatische Backups...
set /a COUNT=0
for /f "delims=" %%f in ('dir /b /o-d "%BACKUP_DIR%\auto_backup_*.zip" 2^>nul') do (
    set /a COUNT+=1
    if !COUNT! gtr 14 (
        echo Lösche altes Backup: %%f
        del "%BACKUP_DIR%\%%f" 2>nul
    )
)

echo.
echo 📊 Backup-Statistik:
echo - Neue Backups: 1
echo - Behaltene Backups: 14 (7 Tage × 2x täglich)
echo - Gesamtgröße:
for %%A in ("%BACKUP_PATH%.zip") do echo   %%~zA Bytes

echo.
echo ✅ Automatisches Backup abgeschlossen!
exit /b 0 