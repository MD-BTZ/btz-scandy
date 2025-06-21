@echo off
setlocal

echo ========================================
echo    Scandy Cleanup-Skript (Windows)
echo    Entfernt alle Container und Daten
echo ========================================

REM Container stoppen und entfernen
echo Stoppe und entferne Container...
docker-compose down --volumes --remove-orphans >nul 2>&1

REM Entferne Container mit Scandy-Namen
echo Entferne Scandy-Container...
docker rm -f scandy-mongodb scandy-app scandy-mongo-express >nul 2>&1
docker rm -f scandyneu-app >nul 2>&1

REM Entferne Images
echo Entferne Scandy-Images...
docker rmi scandyneu-app:latest >nul 2>&1

REM Entferne Netzwerke
echo Entferne Scandy-Netzwerke...
docker network rm scandyneu_scandy-network >nul 2>&1
docker network rm scandy_scandy-network >nul 2>&1

REM Entferne Volumes
echo Entferne Scandy-Volumes...
docker volume rm scandy_css_test-mongodb-data >nul 2>&1

REM Entferne Datenverzeichnisse (optional)
set /p remove_data="Möchten Sie auch die Datenverzeichnisse entfernen? (j/n): "
if /i "%remove_data%"=="j" (
    echo Entferne Datenverzeichnisse...
    if exist scandy_data rmdir /s /q scandy_data
    if exist backups rmdir /s /q backups
    if exist logs rmdir /s /q logs
)

echo ========================================
echo    Cleanup abgeschlossen!
echo ========================================
echo Alle Scandy-Container und Daten wurden entfernt.
echo Sie können jetzt eine neue Installation durchführen.
echo ========================================

pause 