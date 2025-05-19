@echo off
echo Prüfe auf laufende Prozesse auf Port 5000...

REM Finde und beende Prozesse auf Port 5000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000"') do (
    if not "%%a"=="" (
        if not "%%a"=="0" (
            echo Beende Prozess mit PID: %%a
            taskkill /F /PID %%a 2>nul
            if errorlevel 1 (
                echo Prozess konnte nicht beendet werden, fahre trotzdem fort...
            )
        )
    )
)

REM Warte kurz
timeout /t 2 /nobreak > nul

REM Aktiviere die virtuelle Umgebung
call venv\Scripts\activate.bat

REM Setze PYTHONPATH
set PYTHONPATH=%CD%

REM Starte die Anwendung direkt über Python
python -c "from app import create_app; app = create_app(); from waitress import serve; serve(app, host='0.0.0.0', port=5000)" 