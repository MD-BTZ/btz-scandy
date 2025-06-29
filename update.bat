@echo off
echo ========================================
echo Scandy Update - Windows
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

echo Docker gefunden. Starte Update...
echo.

REM Stoppe nur den App-Container
echo Stoppe App-Container...
docker-compose stop scandy-app

REM Lösche nur das App-Image
echo Lösche altes App-Image...
docker-compose down --rmi local

REM Baue und starte nur den App-Container neu
echo Baue und starte App-Container neu...
docker-compose up -d --build scandy-app

if %errorlevel% neq 0 (
    echo ERROR: Fehler beim Update des App-Containers!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Update abgeschlossen!
echo ========================================
echo.
echo Die Scandy-App wurde erfolgreich aktualisiert.
echo MongoDB-Daten bleiben unberührt.
echo.
echo Die App ist verfügbar unter:
echo - Web-App: http://localhost:5000
echo.
echo Container-Status prüfen:
echo docker-compose ps
echo.
echo App-Logs anzeigen:
echo docker-compose logs -f scandy-app
echo.
pause 