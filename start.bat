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

REM Starte Waitress über Python
python -m waitress --host=0.0.0.0 --port=5000 app.wsgi:application 