@echo off
setlocal

REM Verzeichnisse erstellen
mkdir scandy_data\mongodb 2>nul
mkdir scandy_data\uploads 2>nul
mkdir scandy_data\backups 2>nul
mkdir scandy_data\logs 2>nul
mkdir scandy_data\static 2>nul

REM Statische Dateien kopieren
xcopy /E /I /Y app\static\* scandy_data\static\

REM Container stoppen und neu erstellen
docker-compose down --volumes --remove-orphans
docker-compose up -d --build

echo Installation abgeschlossen. Die Anwendung ist unter http://localhost:5000 erreichbar.

endlocal 