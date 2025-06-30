@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Scandy Komplette Installation
echo ========================================
echo Dieses Skript installiert Scandy komplett neu:
echo - Scandy App
echo - MongoDB Datenbank
echo - Mongo Express ^(Datenbank-Verwaltung^)
echo ========================================
echo.

REM Prüfe ob Docker installiert ist
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Docker ist nicht installiert oder nicht verfügbar!
    echo Bitte installiere Docker und starte es neu.
    pause
    exit /b 1
)

REM Prüfe ob Docker läuft
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Docker läuft nicht!
    echo Bitte starte Docker und versuche es erneut.
    pause
    exit /b 1
)

echo ✅ Docker gefunden. Starte komplette Installation...
echo.

REM Prüfe ob bereits eine Installation existiert
if exist "docker-compose.yml" (
    echo ⚠️  Bestehende Installation gefunden!
    echo.
    echo Optionen:
    echo 1 = Abbrechen
    echo 2 = Komplett neu installieren ^(ALLE Daten gehen verloren!^)
    echo 3 = Nur App neu installieren ^(Daten bleiben erhalten^)
    echo.
    set /p choice="Wählen Sie (1-3): "
    if "!choice!"=="1" (
        echo Installation abgebrochen.
        pause
        exit /b 0
    ) else if "!choice!"=="2" (
        echo ⚠️  KOMPLETT NEU INSTALLIEREN - ALLE DATEN GEHEN VERLOREN!
        set /p confirm="Sind Sie sicher? (j/N): "
        if /i not "!confirm!"=="j" (
            echo Installation abgebrochen.
            pause
            exit /b 0
        )
        echo 🔄 Komplett neu installieren...
        docker-compose down -v
        docker system prune -f
        docker volume prune -f
        if exist "data" rmdir /s /q data
        if exist "backups" rmdir /s /q backups
        if exist "logs" rmdir /s /q logs
    ) else if "!choice!"=="3" (
        echo 🔄 Nur App neu installieren...
        echo Führe update.bat aus...
        call update.bat
        exit /b 0
    ) else (
        echo Ungültige Auswahl. Installation abgebrochen.
        pause
        exit /b 1
    )
)

REM Erstelle Datenverzeichnisse
echo 📁 Erstelle Datenverzeichnisse...
if not exist "data" mkdir data
if not exist "data\backups" mkdir data\backups
if not exist "data\logs" mkdir data\logs
if not exist "data\static" mkdir data\static
if not exist "data\uploads" mkdir data\uploads
if not exist "backups" mkdir backups
if not exist "logs" mkdir logs

REM Stoppe laufende Container falls vorhanden
echo 🛑 Stoppe laufende Container...
docker-compose down -v >nul 2>&1

REM Entferne alte Images
echo 🗑️  Entferne alte Images...
for /f "tokens=3" %%i in ('docker images ^| findstr scandy') do docker rmi -f %%i >nul 2>&1
for /f "tokens=3" %%i in ('docker images ^| findstr mongo') do docker rmi -f %%i >nul 2>&1

REM Baue und starte alle Container
echo 🔨 Baue und starte alle Container...
docker-compose up -d --build

if %errorlevel% neq 0 (
    echo ❌ ERROR: Fehler beim Bauen der Container!
    echo Versuche es mit einfachem Build...
    docker-compose build --no-cache
    docker-compose up -d
)

if %errorlevel% neq 0 (
    echo ❌ ERROR: Installation fehlgeschlagen!
    pause
    exit /b 1
)

echo.
echo ⏳ Warte auf Start aller Services...
timeout /t 20 /nobreak >nul

REM Prüfe Container-Status
echo 🔍 Prüfe Container-Status...
docker-compose ps

REM Prüfe ob alle Container laufen
echo.
echo 🔍 Prüfe Service-Verfügbarkeit...
timeout /t 5 /nobreak >nul

REM Prüfe MongoDB
docker-compose exec -T scandy-mongodb mongosh --eval "db.adminCommand('ping')" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ MongoDB läuft
) else (
    echo ⚠️  MongoDB startet noch...
)

REM Prüfe Mongo Express
curl -s http://localhost:8081 >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Mongo Express läuft
) else (
    echo ⚠️  Mongo Express startet noch...
)

REM Prüfe Scandy App
curl -s http://localhost:5000 >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Scandy App läuft
) else (
    echo ⚠️  Scandy App startet noch...
)

echo.
echo ========================================
echo ✅ KOMPLETTE INSTALLATION ABGESCHLOSSEN!
echo ========================================
echo.
echo 🎉 Alle Services sind installiert und verfügbar:
echo.
echo 🌐 Web-Anwendungen:
echo - Scandy App:     http://localhost:5000
echo - Mongo Express:  http://localhost:8081
echo.
echo 🔐 Standard-Zugangsdaten:
echo - Benutzer: admin
echo - Passwort: admin123
echo.
echo 📊 Datenbank-Zugang ^(Mongo Express^):
echo - Benutzer: admin
echo - Passwort: scandy123
echo.
echo 📁 Datenverzeichnisse:
echo - Backups: .\backups\
echo - Logs:    .\logs\
echo - Uploads: .\data\uploads\
echo.
echo 🔧 Nützliche Befehle:
echo - Status aller Container: docker-compose ps
echo - Logs anzeigen:         docker-compose logs -f
echo - Stoppen:               docker-compose down
echo - Neustart:              docker-compose restart
echo - Nur App updaten:       update.bat
echo.
echo ⚠️  WICHTIG: Für Updates verwenden Sie update.bat
echo    Das schont die Datenbank und ist schneller!
echo.
echo ========================================
pause 