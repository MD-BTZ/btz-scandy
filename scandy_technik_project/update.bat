@echo off
echo Update Scandy Docker-Container...

REM Stoppe Container
docker-compose down

REM Pull neueste Images
docker-compose pull

REM Baue App neu
docker-compose build --no-cache

REM Starte Container
docker-compose up -d

echo Update abgeschlossen
pause
