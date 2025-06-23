@echo off

echo Rebuild Scandy Container...

docker-compose down
docker-compose build
docker-compose up -d

echo Rebuild abgeschlossen!
pause 