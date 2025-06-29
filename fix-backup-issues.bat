@echo off
setlocal enabledelayedexpansion

echo 🔧 Backup-Probleme beheben
echo =========================

echo.
echo 📋 Häufige Backup-Probleme und Lösungen:
echo.
echo 1. Berechtigungsprobleme
echo    - Führen Sie das Script als Administrator aus
echo    - Prüfen Sie Schreibrechte im Zielverzeichnis
echo.
echo 2. Speicherplatz voll
echo    - Löschen Sie alte Dateien
echo    - Prüfen Sie verfügbaren Speicherplatz
echo.
echo 3. PowerShell-Probleme
echo    - Prüfen Sie PowerShell-Execution-Policy
echo    - Verwenden Sie alternative Backup-Methoden
echo.

REM Prüfe PowerShell-Execution-Policy
echo 🔍 Prüfe PowerShell-Execution-Policy...
powershell -Command "Get-ExecutionPolicy" >nul 2>&1
if errorlevel 1 (
    echo ❌ PowerShell-Execution-Policy blockiert!
    echo 💡 Lösung: PowerShell als Administrator öffnen und ausführen:
    echo    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
) else (
    echo ✅ PowerShell-Execution-Policy ist korrekt
)

REM Prüfe verfügbaren Speicherplatz
echo.
echo 🔍 Prüfe verfügbaren Speicherplatz...
for /f "tokens=3" %%a in ('dir /-c 2^>nul ^| find "bytes free"') do set FREE_SPACE=%%a
echo Verfügbarer Speicherplatz: %FREE_SPACE% Bytes

REM Prüfe Schreibrechte im aktuellen Verzeichnis
echo.
echo 🔍 Prüfe Schreibrechte...
echo Test > test_write.tmp 2>nul
if exist "test_write.tmp" (
    del test_write.tmp >nul 2>&1
    echo ✅ Schreibrechte im aktuellen Verzeichnis OK
) else (
    echo ❌ Keine Schreibrechte im aktuellen Verzeichnis!
    echo 💡 Führen Sie das Script als Administrator aus
)

echo.
echo 💡 Alternative Backup-Methoden:
echo 1. Manuelles Kopieren der Datenverzeichnisse
echo 2. Verwendung von 7-Zip oder WinRAR
echo 3. Robocopy für Datei-Kopien
echo.
echo 📞 Bei weiteren Problemen:
echo - Prüfen Sie die Windows-Ereignisanzeige
echo - Dokumentieren Sie die Fehlermeldungen
echo - Erstellen Sie ein Issue mit Screenshots
echo.
pause 