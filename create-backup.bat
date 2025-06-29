@echo off
setlocal enabledelayedexpansion

echo 📦 Erstelle Backup vor Neuinstallation
echo =====================================

REM Prüfe ob DATA_DIR gesetzt ist
if not defined DATA_DIR (
    echo ❌ DATA_DIR nicht definiert!
    pause
    exit /b 1
)

echo 📁 Datenverzeichnis: %DATA_DIR%

REM Erstelle Backup-Verzeichnis
set BACKUP_DIR=%DATA_DIR%\backups
if not exist "%BACKUP_DIR%" (
    echo 📁 Erstelle Backup-Verzeichnis...
    mkdir "%BACKUP_DIR%"
)

REM Erstelle Zeitstempel
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=!dt:~2,2!" & set "YYYY=!dt:~0,4!" & set "MM=!dt:~4,2!" & set "DD=!dt:~6,2!"
set "HH=!dt:~8,2!" & set "Min=!dt:~10,2!" & set "Sec=!dt:~12,2!"
set "TIMESTAMP=!YYYY!!MM!!DD!_!HH!!Min!!Sec!"

set BACKUP_NAME=pre_install_backup_!TIMESTAMP!
set BACKUP_PATH=%BACKUP_DIR%\%BACKUP_NAME%

echo 📅 Backup-Zeitstempel: !TIMESTAMP!
echo 📁 Backup-Pfad: %BACKUP_PATH%

REM Prüfe ob Datenverzeichnis existiert
if not exist "%DATA_DIR%" (
    echo ❌ Datenverzeichnis existiert nicht: %DATA_DIR%
    pause
    exit /b 1
)

echo.
echo 🔄 Erstelle Backup...

REM Versuche Backup im Backup-Verzeichnis
echo Versuche Backup in: %BACKUP_PATH%.zip
powershell -Command "Compress-Archive -Path '%DATA_DIR%' -DestinationPath '%BACKUP_PATH%.zip' -Force"
if errorlevel 1 (
    echo ⚠️  Backup im Backup-Verzeichnis fehlgeschlagen.
    echo Versuche Backup im aktuellen Verzeichnis...
    
    REM Versuche Backup im aktuellen Verzeichnis
    set CURRENT_BACKUP=!BACKUP_NAME!.zip
    echo Versuche Backup in: %CD%\!CURRENT_BACKUP!
    powershell -Command "Compress-Archive -Path '%DATA_DIR%' -DestinationPath '!CURRENT_BACKUP!' -Force"
    if errorlevel 1 (
        echo ❌ Backup fehlgeschlagen! Mögliche Ursachen:
        echo - Unzureichende Berechtigungen
        echo - Speicherplatz voll
        echo - Datenverzeichnis ist leer oder beschädigt
        echo.
        echo 💡 Tipp: Erstellen Sie manuell ein Backup oder überspringen Sie diese Option.
        pause
        exit /b 1
    ) else (
        echo ✅ Backup erfolgreich erstellt: !CURRENT_BACKUP!
        echo 📁 Backup-Location: %CD%\!CURRENT_BACKUP!
    )
) else (
    echo ✅ Backup erfolgreich erstellt: %BACKUP_PATH%.zip
    echo 📁 Backup-Location: %BACKUP_PATH%.zip
)

echo.
echo 📊 Backup-Statistik:
if exist "%BACKUP_PATH%.zip" (
    for %%A in ("%BACKUP_PATH%.zip") do echo - Größe: %%~zA Bytes
    for %%A in ("%BACKUP_PATH%.zip") do echo - Pfad: %%~fA
) else if exist "!CURRENT_BACKUP!" (
    for %%A in ("!CURRENT_BACKUP!") do echo - Größe: %%~zA Bytes
    for %%A in ("!CURRENT_BACKUP!") do echo - Pfad: %%~fA
)

echo.
echo ✅ Backup abgeschlossen!
echo.
pause 