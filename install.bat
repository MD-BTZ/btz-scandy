@echo off
echo Starte Installation...

REM Prüfe ob Python installiert ist
python --version >nul 2>&1
if errorlevel 1 (
    echo Python ist nicht installiert. Bitte installieren Sie Python 3.x
    exit /b 1
)

REM Erstelle virtuelle Umgebung, falls sie nicht existiert
if not exist venv (
    python -m venv venv
)

REM Aktiviere virtuelle Umgebung
call venv\Scripts\activate.bat

REM Aktualisiere pip
python -m pip install --upgrade pip

REM Installiere Abhängigkeiten
pip install -r requirements.txt

REM Installiere wichtige Abhängigkeiten explizit
pip install flask
pip install waitress
pip install flask-login
pip install flask-sqlalchemy
pip install flask-wtf
pip install werkzeug
pip install sqlalchemy
pip install wtforms
pip install python-dotenv
pip install bcrypt
pip install pillow
pip install python-barcode
pip install requests
pip install flask-compress
pip install flask-session
pip install openpyxl
pip install apscheduler

REM Erstelle notwendige Verzeichnisse
if not exist app\database mkdir app\database
if not exist app\logs mkdir app\logs
if not exist app\uploads mkdir app\uploads
if not exist app\flask_session mkdir app\flask_session

echo Installation abgeschlossen. Starten Sie die Anwendung mit 'start.bat' 