@echo off
echo Starte Scandy Docker-Container...
docker-compose up -d

echo Warte auf Container-Start...
timeout /t 10 /nobreak >nul

echo Container-Status:
docker-compose ps

echo.
echo ==========================================
echo Scandy ist verfügbar unter:
echo App: http://localhost:5005
echo Mongo Express: http://localhost:8085
echo MongoDB: localhost:27017
echo ==========================================
pause
