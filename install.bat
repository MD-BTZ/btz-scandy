@echo off
echo ========================================
echo Scandy Installation - Windows
echo ========================================
echo.

REM Prüfe ob Docker installiert ist
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker ist nicht installiert oder nicht verfügbar!
    echo Bitte installiere Docker Desktop und starte es neu.
    pause
    exit /b 1
)

echo Docker gefunden. Starte Installation...
echo.

REM Stoppe laufende Container
echo Stoppe laufende Container...
docker-compose down

REM Lösche alte Images (optional)
echo Lösche alte Images...
docker-compose down --rmi all

REM Baue und starte Container
echo Baue und starte Container...
docker-compose up -d --build

if %errorlevel% neq 0 (
    echo ERROR: Fehler beim Bauen der Container!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation abgeschlossen!
echo ========================================
echo.
echo Die Scandy-App ist jetzt verfügbar unter:
echo - Web-App: http://localhost:5000
echo - Mongo Express: http://localhost:8081
echo.
echo Standard-Zugangsdaten:
echo - Benutzer: admin
echo - Passwort: admin123
echo.
echo Container-Status prüfen:
echo docker-compose ps
echo.
echo Logs anzeigen:
echo docker-compose logs -f
echo.
pause 