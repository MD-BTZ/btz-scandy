@echo off
set BACKUP_DIR=./scandy_testilol/backups
set TIMESTAMP=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP= =0

echo Erstelle Backup...

REM Erstelle Backup-Verzeichnis
if not exist "" mkdir ""

REM MongoDB Backup
echo Backup MongoDB...
docker exec scandy_technik-mongodb mongodump --out /tmp/backup
docker cp scandy_technik-mongodb:/tmp/backup "/mongodb_"

REM App-Daten Backup
echo Backup App-Daten...
powershell -Command "Compress-Archive -Path './scandy_testilol/uploads', './scandy_testilol/backups', './scandy_testilol/logs' -DestinationPath '/app_data_.zip'"

echo Backup erstellt: 
pause
