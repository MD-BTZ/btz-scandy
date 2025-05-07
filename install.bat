@echo off
setlocal

echo Installiere Scandy...

REM --- Python & Pip --- 
echo [1/4] Ueberpruefe Python und Pip...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo FEHLER: Python ist nicht im PATH gefunden. Bitte installieren Sie Python 3 und fuegen Sie es zum PATH hinzu.
    goto :eof
)
where pip >nul 2>nul
if %errorlevel% neq 0 (
    echo FEHLER: pip ist nicht im PATH gefunden. Bitte stellen Sie sicher, dass pip mit Python installiert wurde.
    goto :eof
)

REM --- Virtuelle Umgebung --- 
echo [2/4] Erstelle virtuelle Umgebung (venv)...
python -m venv venv

REM --- Python-Abhaengigkeiten --- 
echo [3/4] Installiere Python-Abhaengigkeiten aus requirements.txt...
call venv\Scripts\activate.bat
pip install -r requirements.txt

REM --- Node.js, npm & Tailwind CSS --- 
echo [4/4] Richte Tailwind CSS ein...
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo WARNUNG: Node.js nicht gefunden.
    echo Tailwind CSS benoetigt Node.js und npm zum Kompilieren der Stylesheets.
    echo Bitte installieren Sie Node.js von der offiziellen Webseite (https://nodejs.org/) und stellen Sie sicher, dass es im PATH ist.
    echo Nach der Installation fuehren Sie bitte manuell folgende Befehle in der Eingabeaufforderung im Projektverzeichnis aus:
    echo 1. npm install
    echo 2. npm run build:css
    echo Installation wird fortgesetzt, aber CSS wird möglicherweise nicht korrekt generiert.
    goto :skip_npm
)
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo WARNUNG: npm nicht gefunden.
    echo Bitte stellen Sie sicher, dass npm korrekt mit Node.js installiert wurde.
    echo Führen Sie nach der Behebung manuell folgende Befehle in der Eingabeaufforderung im Projektverzeichnis aus:
    echo 1. npm install
    echo 2. npm run build:css
    echo Installation wird fortgesetzt, aber CSS wird möglicherweise nicht korrekt generiert.
    goto :skip_npm
)

echo Installiere npm-Abhaengigkeiten (tailwindcss, daisyui)...
npm install
echo Generiere CSS-Datei mit Tailwind...
npm run build:css

:skip_npm
call venv\Scripts\deactivate.bat

echo ------------------------------------
echo Scandy Installation abgeschlossen!
echo.
echo So starten Sie die Anwendung:
echo 1. Aktivieren Sie die virtuelle Umgebung: venv\Scripts\activate.bat
echo 2. Starten Sie den Server: start.bat
echo ------------------------------------

endlocal 