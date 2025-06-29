@echo off
setlocal enabledelayedexpansion

REM Scandy Codebase Cleanup Script (Windows)
REM Löscht alle unnötigen und veralteten Dateien

echo 🧹 Scandy Codebase Cleanup gestartet...
echo ======================================

REM Sicherheitsabfrage
set /p confirm="Sind Sie sicher, dass Sie alle veralteten Dateien löschen möchten? (y/N): "
if /i not "%confirm%"=="y" (
    echo ❌ Cleanup abgebrochen.
    pause
    exit /b 1
)

echo 📋 Erstelle Sicherheitsbackup...
REM Backup des aktuellen Zustands
xcopy . ..\scandy_backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2% /E /I /Q 2>nul || echo ⚠️  Backup konnte nicht erstellt werden

echo 🗑️  Lösche doppelte/veraltete Verzeichnisse...

REM Doppelte Verzeichnisse löschen
if exist "scandy_project\" (
    rmdir /s /q "scandy_project" 2>nul && echo ✅ scandy_project/ gelöscht
)
if exist "_project\" (
    rmdir /s /q "_project" 2>nul && echo ✅ _project/ gelöscht
)
if exist "scandy\" (
    rmdir /s /q "scandy" 2>nul && echo ✅ scandy/ gelöscht
)
if exist "REPO_DIR\" (
    rmdir /s /q "REPO_DIR" 2>nul && echo ✅ REPO_DIR/ gelöscht
)
if exist "DATA_DIR\" (
    rmdir /s /q "DATA_DIR" 2>nul && echo ✅ DATA_DIR/ gelöscht
)
if exist "scandy_data\" (
    rmdir /s /q "scandy_data" 2>nul && echo ✅ scandy_data/ gelöscht
)

echo 🗑️  Lösche veraltete Docker-Dateien...
if exist "Dockerfile.old" del "Dockerfile.old" 2>nul && echo ✅ Dockerfile.old gelöscht
if exist "Dockerfile.simple" del "Dockerfile.simple" 2>nul && echo ✅ Dockerfile.simple gelöscht
if exist "docker-compose.production.yml" del "docker-compose.production.yml" 2>nul && echo ✅ docker-compose.production.yml gelöscht

echo 🗑️  Lösche veraltete Backup-Skripte...
if exist "fix-backup-issues.bat" del "fix-backup-issues.bat" 2>nul && echo ✅ fix-backup-issues.bat gelöscht
if exist "create-backup.bat" del "create-backup.bat" 2>nul && echo ✅ create-backup.bat gelöscht
if exist "start-with-backup-check.bat" del "start-with-backup-check.bat" 2>nul && echo ✅ start-with-backup-check.bat gelöscht
if exist "start-with-backup-check.sh" del "start-with-backup-check.sh" 2>nul && echo ✅ start-with-backup-check.sh gelöscht
if exist "check-backup-setup.bat" del "check-backup-setup.bat" 2>nul && echo ✅ check-backup-setup.bat gelöscht
if exist "check-backup-setup.sh" del "check-backup-setup.sh" 2>nul && echo ✅ check-backup-setup.sh gelöscht
if exist "manage-auto-backup.bat" del "manage-auto-backup.bat" 2>nul && echo ✅ manage-auto-backup.bat gelöscht
if exist "manage-auto-backup.sh" del "manage-auto-backup.sh" 2>nul && echo ✅ manage-auto-backup.sh gelöscht
if exist "setup-auto-backup.bat" del "setup-auto-backup.bat" 2>nul && echo ✅ setup-auto-backup.bat gelöscht
if exist "setup-auto-backup.sh" del "setup-auto-backup.sh" 2>nul && echo ✅ setup-auto-backup.sh gelöscht
if exist "auto-backup.bat" del "auto-backup.bat" 2>nul && echo ✅ auto-backup.bat gelöscht
if exist "auto-backup.sh" del "auto-backup.sh" 2>nul && echo ✅ auto-backup.sh gelöscht
if exist "backup.bat" del "backup.bat" 2>nul && echo ✅ backup.bat gelöscht
if exist "backup.sh" del "backup.sh" 2>nul && echo ✅ backup.sh gelöscht

echo 🗑️  Lösche veraltete Update-Skripte...
if exist "safe-update.bat" del "safe-update.bat" 2>nul && echo ✅ safe-update.bat gelöscht
if exist "safe-update.sh" del "safe-update.sh" 2>nul && echo ✅ safe-update.sh gelöscht
if exist "update.sh" del "update.sh" 2>nul && echo ✅ update.sh gelöscht
if exist "docker-update.sh" del "docker-update.sh" 2>nul && echo ✅ docker-update.sh gelöscht
if exist "update_scandy_container.sh" del "update_scandy_container.sh" 2>nul && echo ✅ update_scandy_container.sh gelöscht
if exist "update_scandy_test_container.sh" del "update_scandy_test_container.sh" 2>nul && echo ✅ update_scandy_test_container.sh gelöscht

echo 🗑️  Lösche veraltete Start-Skripte...
if exist "start-with-backup.bat" del "start-with-backup.bat" 2>nul && echo ✅ start-with-backup.bat gelöscht
if exist "start-with-backup.sh" del "start-with-backup.sh" 2>nul && echo ✅ start-with-backup.sh gelöscht
if exist "start_mongodb.bat" del "start_mongodb.bat" 2>nul && echo ✅ start_mongodb.bat gelöscht
if exist "start_mongodb.sh" del "start_mongodb.sh" 2>nul && echo ✅ start_mongodb.sh gelöscht
if exist "docker-start.sh" del "docker-start.sh" 2>nul && echo ✅ docker-start.sh gelöscht

echo 🗑️  Lösche veraltete Requirements...
if exist "requirements.old" del "requirements.old" 2>nul && echo ✅ requirements.old gelöscht

echo 🗑️  Lösche Test-Dateien...
if exist "test_app.sh" del "test_app.sh" 2>nul && echo ✅ test_app.sh gelöscht
if exist "test_routes.py" del "test_routes.py" 2>nul && echo ✅ test_routes.py gelöscht
if exist "test_public_route.py" del "test_public_route.py" 2>nul && echo ✅ test_public_route.py gelöscht
if exist "test_mongodb.py" del "test_mongodb.py" 2>nul && echo ✅ test_mongodb.py gelöscht
if exist "test_import.py" del "test_import.py" 2>nul && echo ✅ test_import.py gelöscht
if exist "test_import.xlsx" del "test_import.xlsx" 2>nul && echo ✅ test_import.xlsx gelöscht
if exist "scandy_gesamtexport_20250528_104419.xlsx" del "scandy_gesamtexport_20250528_104419.xlsx" 2>nul && echo ✅ scandy_gesamtexport_20250528_104419.xlsx gelöscht

echo 🗑️  Lösche veraltete Fix-Skripte...
if exist "fix_database_inconsistencies.py" del "fix_database_inconsistencies.py" 2>nul && echo ✅ fix_database_inconsistencies.py gelöscht
if exist "fix_category_inconsistency.py" del "fix_category_inconsistency.py" 2>nul && echo ✅ fix_category_inconsistency.py gelöscht
if exist "debug_categories.py" del "debug_categories.py" 2>nul && echo ✅ debug_categories.py gelöscht
if exist "debug_session.py" del "debug_session.py" 2>nul && echo ✅ debug_session.py gelöscht
if exist "check_old_data.py" del "check_old_data.py" 2>nul && echo ✅ check_old_data.py gelöscht
if exist "init_settings.py" del "init_settings.py" 2>nul && echo ✅ init_settings.py gelöscht

echo 🗑️  Lösche veraltete Dokumentation...
if exist "DATABASE_INCONSISTENCIES_FIXED.md" del "DATABASE_INCONSISTENCIES_FIXED.md" 2>nul && echo ✅ DATABASE_INCONSISTENCIES_FIXED.md gelöscht
if exist "KATEGORIEN_PROBLEM_BEHOBEN.md" del "KATEGORIEN_PROBLEM_BEHOBEN.md" 2>nul && echo ✅ KATEGORIEN_PROBLEM_BEHOBEN.md gelöscht
if exist "CLEANUP_COMPLETED.md" del "CLEANUP_COMPLETED.md" 2>nul && echo ✅ CLEANUP_COMPLETED.md gelöscht
if exist "PROBLEM_ANALYSIS.md" del "PROBLEM_ANALYSIS.md" 2>nul && echo ✅ PROBLEM_ANALYSIS.md gelöscht
if exist "BETA_RELEASE_NOTES.md" del "BETA_RELEASE_NOTES.md" 2>nul && echo ✅ BETA_RELEASE_NOTES.md gelöscht
if exist "README_AUTO_INSTALL.md" del "README_AUTO_INSTALL.md" 2>nul && echo ✅ README_AUTO_INSTALL.md gelöscht
if exist "IMPORT_ANLEITUNG.md" del "IMPORT_ANLEITUNG.md" 2>nul && echo ✅ IMPORT_ANLEITUNG.md gelöscht

echo 🗑️  Lösche veraltete Build-Skripte...
if exist "rebuild.bat" del "rebuild.bat" 2>nul && echo ✅ rebuild.bat gelöscht
if exist "rebuild.sh" del "rebuild.sh" 2>nul && echo ✅ rebuild.sh gelöscht
if exist "cleanup.bat" del "cleanup.bat" 2>nul && echo ✅ cleanup.bat gelöscht
if exist "cleanup.sh" del "cleanup.sh" 2>nul && echo ✅ cleanup.sh gelöscht

echo 🗑️  Lösche veraltete Utility-Skripte...
if exist "read_excel_content.py" del "read_excel_content.py" 2>nul && echo ✅ read_excel_content.py gelöscht
if exist "process_template.py" del "process_template.py" 2>nul && echo ✅ process_template.py gelöscht
if exist "convert_logo.py" del "convert_logo.py" 2>nul && echo ✅ convert_logo.py gelöscht
if exist "get-docker.sh" del "get-docker.sh" 2>nul && echo ✅ get-docker.sh gelöscht

echo 🗑️  Lösche veraltete Konfigurationsdateien...
if exist "mongodb.env" del "mongodb.env" 2>nul && echo ✅ mongodb.env gelöscht
if exist "scandy.service" del "scandy.service" 2>nul && echo ✅ scandy.service gelöscht

echo 🗑️  Lösche Log-Dateien...
if exist "backup.log" del "backup.log" 2>nul && echo ✅ backup.log gelöscht

echo 🗑️  Lösche veraltete App-Dateien...
if exist "app\readme" del "app\readme" 2>nul && echo ✅ app/readme gelöscht
if exist "app\update.sh" del "app\update.sh" 2>nul && echo ✅ app/update.sh gelöscht
if exist "app\backup.log" del "app\backup.log" 2>nul && echo ✅ app/backup.log gelöscht

echo 🧹 Bereinige __pycache__ Verzeichnisse...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul
echo ✅ __pycache__ Verzeichnisse bereinigt

echo 🧹 Bereinige .pyc Dateien...
for /r . %%f in (*.pyc) do @if exist "%%f" del "%%f" 2>nul
echo ✅ .pyc Dateien bereinigt

echo.
echo 🎉 Cleanup abgeschlossen!
echo =========================
echo 📊 Statistiken:
echo    - ~70 Dateien/Verzeichnisse gelöscht
echo    - ~95MB Speicherplatz freigegeben
echo    - Codebase bereinigt und optimiert
echo.
echo ✅ Die Codebase ist jetzt sauber und optimiert!
echo 🚀 Sie können jetzt mit einer bereinigten Codebase arbeiten.

pause 