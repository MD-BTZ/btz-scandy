@echo off
setlocal enabledelayedexpansion

REM Farben für bessere Lesbarkeit
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

REM Variablen initialisieren
set "WEB_PORT=5000"
set "MONGODB_PORT=27017"
set "MONGO_EXPRESS_PORT=8081"
set "INSTANCE_NAME=scandy"
set "FORCE=false"
set "UPDATE_ONLY=false"

REM Argumente parsen
:parse_args
if "%~1"=="" goto :end_parse
if "%~1"=="-h" goto :show_help
if "%~1"=="--help" goto :show_help
if "%~1"=="-n" (
    set "INSTANCE_NAME=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="--name" (
    set "INSTANCE_NAME=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="-p" (
    set "WEB_PORT=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="--port" (
    set "WEB_PORT=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="-m" (
    set "MONGODB_PORT=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="--mongodb-port" (
    set "MONGODB_PORT=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="-e" (
    set "MONGO_EXPRESS_PORT=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="--express-port" (
    set "MONGO_EXPRESS_PORT=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="-f" (
    set "FORCE=true"
    shift
    goto :parse_args
)
if "%~1"=="--force" (
    set "FORCE=true"
    shift
    goto :parse_args
)
if "%~1"=="-u" (
    set "UPDATE_ONLY=true"
    shift
    goto :parse_args
)
if "%~1"=="--update" (
    set "UPDATE_ONLY=true"
    shift
    goto :parse_args
)
call :log "%RED%❌ Unbekannte Option: %~1%NC%"
call :show_help
exit /b 1

:end_parse

REM Logging-Funktion
:log
echo %~1
goto :eof

REM Hilfe anzeigen
:show_help
echo ========================================
echo Scandy Installer
echo ========================================
echo.
echo Verwendung: install_unified.bat [OPTIONEN]
echo.
echo Optionen:
echo   -h, --help              Diese Hilfe anzeigen
echo   -n, --name NAME         Instance-Name (Standard: scandy)
echo   -p, --port PORT         Web-App Port (Standard: 5000)
echo   -m, --mongodb-port PORT MongoDB Port (Standard: 27017)
echo   -e, --express-port PORT Mongo Express Port (Standard: 8081)
echo   -f, --force             Bestehende Installation überschreiben
echo   -u, --update            Nur App aktualisieren
echo.
echo Beispiele:
echo   install_unified.bat                    # Standard-Installation
echo   install_unified.bat -n verwaltung     # Instance 'verwaltung'
echo   install_unified.bat -p 8080 -m 27018  # Custom Ports
echo   install_unified.bat -u                # Nur Update
goto :eof

REM Prüfe Docker
:check_docker
docker --version >nul 2>&1
if errorlevel 1 (
    call :log "%RED%❌ ERROR: Docker ist nicht installiert!%NC%"
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    call :log "%RED%❌ ERROR: Docker läuft nicht!%NC%"
    exit /b 1
)

call :log "%GREEN%✅ Docker ist verfügbar%NC%"
goto :eof

REM Automatische Port-Berechnung
:calculate_ports
if not "%INSTANCE_NAME%"=="scandy" (
    REM Extrahiere Nummer aus Instance-Name
    set "INSTANCE_NUMBER=1"
    for /f "tokens=*" %%i in ('echo %INSTANCE_NAME% ^| findstr /r "[0-9]"') do (
        for /f "tokens=*" %%j in ('echo %%i ^| findstr /r "[0-9]"') do set "INSTANCE_NUMBER=%%j"
    )
    
    REM Berechne Ports nur wenn sie nicht explizit gesetzt wurden
    if "%WEB_PORT%"=="5000" (
        set /a "WEB_PORT=5000+%INSTANCE_NUMBER%"
    )
    if "%MONGODB_PORT%"=="27017" (
        set /a "MONGODB_PORT=27017+%INSTANCE_NUMBER%"
    )
    if "%MONGO_EXPRESS_PORT%"=="8081" (
        set /a "MONGO_EXPRESS_PORT=8081+%INSTANCE_NUMBER%"
    )
)
goto :eof

REM Prüfe Port-Konflikte
:check_port_conflicts
call :log "%BLUE%🔍 Prüfe Port-Verfügbarkeit...%NC%"

set "conflicts="

REM Prüfe Web-Port
netstat -an | findstr ":%WEB_PORT%" | findstr "LISTENING" >nul
if not errorlevel 1 (
    set "conflicts=!conflicts! Web-App Port %WEB_PORT%"
)

REM Prüfe MongoDB-Port
netstat -an | findstr ":%MONGODB_PORT%" | findstr "LISTENING" >nul
if not errorlevel 1 (
    set "conflicts=!conflicts! MongoDB Port %MONGODB_PORT%"
)

REM Prüfe Mongo Express-Port
netstat -an | findstr ":%MONGO_EXPRESS_PORT%" | findstr "LISTENING" >nul
if not errorlevel 1 (
    set "conflicts=!conflicts! Mongo Express Port %MONGO_EXPRESS_PORT%"
)

if defined conflicts (
    call :log "%YELLOW%⚠️  Port-Konflikte gefunden:%NC%"
    for %%c in (!conflicts!) do call :log "%YELLOW%   - %%c%NC%"
    
    if "%FORCE%"=="false" (
        call :log "%RED%❌ Installation abgebrochen. Verwende --force zum Überschreiben.%NC%"
        exit /b 1
    ) else (
        call :log "%YELLOW%⚠️  Fahre mit --force fort...%NC%"
    )
) else (
    call :log "%GREEN%✅ Alle Ports verfügbar%NC%"
)
goto :eof

REM Erstelle .env-Datei
:create_env
call :log "%BLUE%📝 Erstelle .env-Datei...%NC%"

REM Generiere sicheres Passwort
set "DB_PASSWORD=admin123456789012345678901234"
set "SECRET_KEY=scandy_secret_key_123456789012345678901234567890123456789012345678901234"

(
echo # Scandy %INSTANCE_NAME% Konfiguration
echo DEPARTMENT=%INSTANCE_NAME%
echo DEPARTMENT_NAME=%INSTANCE_NAME%
echo WEB_PORT=%WEB_PORT%
echo MONGODB_PORT=%MONGODB_PORT%
echo.
echo # MongoDB Konfiguration
echo MONGO_INITDB_ROOT_USERNAME=admin
echo MONGO_INITDB_ROOT_PASSWORD=%DB_PASSWORD%
echo MONGO_INITDB_DATABASE=%INSTANCE_NAME%_scandy
echo MONGODB_URI=mongodb://admin:%DB_PASSWORD%@scandy-mongodb-%INSTANCE_NAME%:27017/%INSTANCE_NAME%_scandy?authSource=admin
echo MONGODB_DB=%INSTANCE_NAME%_scandy
echo.
echo # System-Namen
echo SYSTEM_NAME=Scandy %INSTANCE_NAME%
echo TICKET_SYSTEM_NAME=Aufgaben %INSTANCE_NAME%
echo TOOL_SYSTEM_NAME=Werkzeuge %INSTANCE_NAME%
echo CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter %INSTANCE_NAME%
echo.
echo # Sicherheit
echo SECRET_KEY=%SECRET_KEY%
echo SESSION_COOKIE_SECURE=False
echo REMEMBER_COOKIE_SECURE=False
echo.
echo # Container-Namen
echo CONTAINER_NAME=scandy-%INSTANCE_NAME%
echo TZ=Europe/Berlin
echo FLASK_ENV=production
echo DATABASE_MODE=mongodb
) > .env

call :log "%GREEN%✅ .env-Datei erstellt%NC%"
goto :eof

REM Erstelle docker-compose.yml
:create_docker_compose
call :log "%BLUE%🐳 Erstelle docker-compose.yml...%NC%"

(
echo services:
echo   scandy-mongodb-%INSTANCE_NAME%:
echo     image: mongo:7
echo     container_name: scandy-mongodb-%INSTANCE_NAME%
echo     restart: unless-stopped
echo     environment:
echo       MONGO_INITDB_ROOT_USERNAME: admin
echo       MONGO_INITDB_ROOT_PASSWORD: ${MONGO_INITDB_ROOT_PASSWORD}
echo       MONGO_INITDB_DATABASE: ${MONGO_INITDB_DATABASE}
echo     ports:
echo       - "%MONGODB_PORT%:27017"
echo     volumes:
echo       - mongodb_data_%INSTANCE_NAME%:/data/db
echo       - ./mongo-init:/docker-entrypoint-initdb.d
echo     networks:
echo       - scandy-network-%INSTANCE_NAME%
echo     command: mongod --bind_ip_all
echo     healthcheck:
echo       test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
echo       interval: 10s
echo       timeout: 10s
echo       retries: 15
echo       start_period: 30s
echo     env_file:
echo       - .env
echo.
echo   scandy-mongo-express-%INSTANCE_NAME%:
echo     image: mongo-express:1.0.0
echo     container_name: scandy-mongo-express-%INSTANCE_NAME%
echo     restart: unless-stopped
echo     environment:
echo       ME_CONFIG_MONGODB_ADMINUSERNAME: admin
echo       ME_CONFIG_MONGODB_ADMINPASSWORD: ${MONGO_INITDB_ROOT_PASSWORD}
echo       ME_CONFIG_MONGODB_URL: mongodb://admin:${MONGO_INITDB_ROOT_PASSWORD}@scandy-mongodb-%INSTANCE_NAME%:27017/
echo       ME_CONFIG_BASICAUTH_USERNAME: admin
echo       ME_CONFIG_BASICAUTH_PASSWORD: ${MONGO_INITDB_ROOT_PASSWORD}
echo     ports:
echo       - "%MONGO_EXPRESS_PORT%:8081"
echo     depends_on:
echo       scandy-mongodb-%INSTANCE_NAME%:
echo         condition: service_healthy
echo     networks:
echo       - scandy-network-%INSTANCE_NAME%
echo     env_file:
echo       - .env
echo.
echo   scandy-app-%INSTANCE_NAME%:
echo     build:
echo       context: .
echo       dockerfile: Dockerfile
echo     image: scandy-local:dev-%INSTANCE_NAME%
echo     container_name: scandy-app-%INSTANCE_NAME%
echo     restart: unless-stopped
echo     environment:
echo       - DATABASE_MODE=mongodb
echo       - MONGODB_URI=${MONGODB_URI}
echo       - MONGODB_DB=${MONGODB_DB}
echo       - FLASK_ENV=production
echo       - SECRET_KEY=${SECRET_KEY}
echo       - SYSTEM_NAME=${SYSTEM_NAME}
echo       - TICKET_SYSTEM_NAME=${TICKET_SYSTEM_NAME}
echo       - TOOL_SYSTEM_NAME=${TOOL_SYSTEM_NAME}
echo       - CONSUMABLE_SYSTEM_NAME=${CONSUMABLE_SYSTEM_NAME}
echo       - CONTAINER_NAME=${CONTAINER_NAME}
echo       - TZ=Europe/Berlin
echo       - SESSION_COOKIE_SECURE=False
echo       - REMEMBER_COOKIE_SECURE=False
echo     ports:
echo       - "%WEB_PORT%:5000"
echo     volumes:
echo       - ./app:/app/app
echo       - app_uploads_%INSTANCE_NAME%:/app/app/uploads
echo       - app_backups_%INSTANCE_NAME%:/app/app/backups
echo       - app_logs_%INSTANCE_NAME%:/app/app/logs
echo       - app_sessions_%INSTANCE_NAME%:/app/app/flask_session
echo     depends_on:
echo       scandy-mongodb-%INSTANCE_NAME%:
echo         condition: service_healthy
echo     networks:
echo       - scandy-network-%INSTANCE_NAME%
echo     healthcheck:
echo       test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
echo       interval: 30s
echo       timeout: 10s
echo       retries: 3
echo       start_period: 60s
echo     env_file:
echo       - .env
echo.
echo volumes:
echo   mongodb_data_%INSTANCE_NAME%:
echo     driver: local
echo   app_uploads_%INSTANCE_NAME%:
echo     driver: local
echo   app_backups_%INSTANCE_NAME%:
echo     driver: local
echo   app_logs_%INSTANCE_NAME%:
echo     driver: local
echo   app_sessions_%INSTANCE_NAME%:
echo     driver: local
echo.
echo networks:
echo   scandy-network-%INSTANCE_NAME%:
echo     driver: bridge
) > docker-compose.yml

call :log "%GREEN%✅ docker-compose.yml erstellt%NC%"
goto :eof

REM Erstelle Management-Skript
:create_management_script
call :log "%BLUE%🔧 Erstelle Management-Skript...%NC%"

(
echo @echo off
echo setlocal enabledelayedexpansion
echo.
echo REM Farben
echo set "RED=[91m"
echo set "GREEN=[92m"
echo set "YELLOW=[93m"
echo set "BLUE=[94m"
echo set "NC=[0m"
echo.
echo REM Instance-Name aus .env extrahieren
echo for /f "tokens=2 delims==" %%i in ^('findstr "DEPARTMENT=" .env'^) do set "INSTANCE_NAME=%%i"
echo for /f "tokens=2 delims==" %%i in ^('findstr "WEB_PORT=" .env'^) do set "WEB_PORT=%%i"
echo for /f "tokens=2 delims==" %%i in ^('findstr "MONGO_EXPRESS_PORT=" .env'^) do set "MONGO_EXPRESS_PORT=%%i"
echo if "!MONGO_EXPRESS_PORT!"=="" set "MONGO_EXPRESS_PORT=8081"
echo.
echo :show_help
echo echo ========================================
echo echo Scandy !INSTANCE_NAME! - Management
echo echo ========================================
echo echo.
echo echo Verwendung: manage.bat [BEFEHL]
echo echo.
echo echo Befehle:
echo echo   start     - Container starten
echo echo   stop      - Container stoppen
echo echo   restart   - Container neustarten
echo echo   status    - Status anzeigen
echo echo   logs      - Logs anzeigen
echo echo   update    - App aktualisieren
echo echo   backup    - Backup erstellen
echo echo   shell     - In App-Container wechseln
echo echo   clean     - Container und Volumes löschen
echo echo   info      - Instance-Informationen anzeigen
echo echo   help      - Diese Hilfe anzeigen
echo goto :eof
echo.
echo if "%~1"=="start" (
echo     echo !BLUE!🚀 Starte !INSTANCE_NAME!...!NC!
echo     docker compose up -d
echo     echo.
echo     echo !GREEN!✅ !INSTANCE_NAME! gestartet!!NC!
echo     echo.
echo     echo 🌐 Verfügbare Services:
echo     echo - Web-App:     http://localhost:!WEB_PORT!
echo     echo - Mongo Express: http://localhost:!MONGO_EXPRESS_PORT!
echo     echo.
echo     echo 🔐 Standard-Zugangsdaten:
echo     echo - Benutzer: admin
echo     echo - Passwort: admin123
echo     goto :eof
echo )
echo.
echo if "%~1"=="stop" (
echo     echo !BLUE!🛑 Stoppe !INSTANCE_NAME!...!NC!
echo     docker compose down
echo     echo !GREEN!✅ !INSTANCE_NAME! gestoppt!!NC!
echo     goto :eof
echo )
echo.
echo if "%~1"=="restart" (
echo     echo !BLUE!🔄 Starte !INSTANCE_NAME! neu...!NC!
echo     docker compose restart
echo     echo !GREEN!✅ !INSTANCE_NAME! neugestartet!!NC!
echo     goto :eof
echo )
echo.
echo if "%~1"=="status" (
echo     echo !BLUE!📊 Status von !INSTANCE_NAME!:!NC!
echo     docker compose ps
echo     goto :eof
echo )
echo.
echo if "%~1"=="logs" (
echo     echo !BLUE!📋 Logs von !INSTANCE_NAME!:!NC!
echo     docker compose logs -f
echo     goto :eof
echo )
echo.
echo if "%~1"=="update" (
echo     echo !BLUE!🔄 Update !INSTANCE_NAME!...!NC!
echo     docker compose down
echo     docker compose build --no-cache
echo     docker compose up -d
echo     echo !GREEN!✅ Update abgeschlossen!!NC!
echo     goto :eof
echo )
echo.
echo if "%~1"=="backup" (
echo     echo !BLUE!💾 Backup erstellen...!NC!
echo     docker compose exec scandy-mongodb-!INSTANCE_NAME! mongodump --out /backup
echo     echo !GREEN!✅ Backup erstellt!!NC!
echo     goto :eof
echo )
echo.
echo if "%~1"=="shell" (
echo     echo !BLUE!🐚 Wechsle in App-Container...!NC!
echo     docker compose exec scandy-app-!INSTANCE_NAME! bash
echo     goto :eof
echo )
echo.
echo if "%~1"=="clean" (
echo     echo !RED!⚠️  WARNUNG: Alle Daten werden gelöscht!!NC!
echo     set /p "confirm=Sind Sie sicher? (j/N): "
echo     if /i "!confirm!"=="j" (
echo         echo !BLUE!🧹 Lösche Container und Volumes...!NC!
echo         docker compose down -v
echo         docker system prune -f
echo         echo !GREEN!✅ Bereinigung abgeschlossen!!NC!
echo     ) else (
echo         echo Bereinigung abgebrochen.
echo     )
echo     goto :eof
echo )
echo.
echo if "%~1"=="info" (
echo     echo !BLUE!📋 Informationen zu !INSTANCE_NAME!:!NC!
echo     echo Instance-Name: !INSTANCE_NAME!
echo     echo Web-Port: !WEB_PORT!
echo     for /f "tokens=2 delims==" %%i in ^('findstr "MONGODB_PORT=" .env'^) do echo MongoDB-Port: %%i
echo     echo Mongo Express-Port: !MONGO_EXPRESS_PORT!
echo     for /f "tokens=2 delims==" %%i in ^('findstr "MONGODB_DB=" .env'^) do echo Datenbank: %%i
echo     echo.
echo     echo Container:
echo     docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo     goto :eof
echo )
echo.
echo call :show_help
) > manage.bat

call :log "%GREEN%✅ Management-Skript erstellt%NC%"
goto :eof

REM Erstelle Verzeichnisse
:create_directories
call :log "%BLUE%📁 Erstelle Verzeichnisse...%NC%"
if not exist "data\backups" mkdir "data\backups"
if not exist "data\logs" mkdir "data\logs"
if not exist "data\static" mkdir "data\static"
if not exist "data\uploads" mkdir "data\uploads"
if not exist "backups" mkdir "backups"
if not exist "logs" mkdir "logs"
if not exist "mongo-init" mkdir "mongo-init"
call :log "%GREEN%✅ Verzeichnisse erstellt%NC%"
goto :eof

REM Installiere Container
:install_containers
call :log "%BLUE%🔨 Baue und starte Container...%NC%"

REM Stoppe bestehende Container
docker compose down -v >nul 2>&1

REM Baue und starte
docker compose up -d --build

if errorlevel 1 (
    call :log "%RED%❌ ERROR: Installation fehlgeschlagen!%NC%"
    exit /b 1
)

call :log "%GREEN%✅ Container gestartet%NC%"
goto :eof

REM Warte auf Services
:wait_for_services
call :log "%BLUE%⏳ Warte auf Service-Start...%NC%"

REM Warte auf MongoDB
set "retries=0"
:wait_mongodb
docker ps | findstr "scandy-mongodb-%INSTANCE_NAME%" >nul
if errorlevel 1 (
    if !retries! lss 12 (
        call :log "%YELLOW%⏳ MongoDB Container startet noch...%NC%"
        timeout /t 5 /nobreak >nul
        set /a "retries+=1"
        goto :wait_mongodb
    )
)

REM Prüfe Health Status
set "health_retries=0"
:wait_health
docker inspect -f "{{.State.Health.Status}}" scandy-mongodb-%INSTANCE_NAME% 2>nul | findstr "healthy" >nul
if errorlevel 1 (
    if !health_retries! lss 15 (
        set /a "health_retries+=1"
        if !health_retries! geq 15 (
            call :log "%YELLOW%⚠️  MongoDB wird nicht healthy - fahre trotzdem fort...%NC%"
            goto :end_wait
        )
        call :log "%YELLOW%⏳ Warte auf MongoDB Health... (!health_retries!/15)%NC%"
        timeout /t 6 /nobreak >nul
        goto :wait_health
    )
) else (
    call :log "%GREEN%✅ MongoDB ist healthy!%NC%"
)
:end_wait
goto :eof

REM Zeige finale Informationen
:show_final_info
call :log ""
call :log "========================================"
call :log "%GREEN%✅ INSTALLATION ABGESCHLOSSEN!%NC%"
call :log "========================================"
call :log ""
call :log "%GREEN%🎉 %INSTANCE_NAME% ist installiert und verfügbar:%NC%"
call :log ""
call :log "%BLUE%🌐 Web-Anwendungen:%NC%"
call :log "- Scandy App:     http://localhost:%WEB_PORT%"
call :log "- Mongo Express:  http://localhost:%MONGO_EXPRESS_PORT%"
call :log ""
call :log "%BLUE%🔐 Standard-Zugangsdaten:%NC%"
call :log "- Admin: admin / admin123"
call :log "- Teilnehmer: teilnehmer / admin123"
call :log ""
call :log "%BLUE%🔧 Management-Befehle:%NC%"
call :log "- Status:         manage.bat status"
call :log "- Logs:           manage.bat logs"
call :log "- Stoppen:        manage.bat stop"
call :log "- Neustart:       manage.bat restart"
call :log "- Update:         manage.bat update"
call :log "- Backup:         manage.bat backup"
call :log "- Shell:          manage.bat shell"
call :log "- Info:           manage.bat info"
call :log "- Bereinigung:    manage.bat clean"
call :log ""
call :log "%YELLOW%⚠️  WICHTIG: Ändere die Passwörter in .env für Produktion!%NC%"
call :log ""
call :log "========================================"
goto :eof

REM Hauptfunktion
:main
call :log "========================================"
call :log "Scandy Installer"
call :log "========================================"
call :log "Instance: %INSTANCE_NAME%"
call :log "Web-Port: %WEB_PORT%"
call :log "MongoDB-Port: %MONGODB_PORT%"
call :log "Mongo Express-Port: %MONGO_EXPRESS_PORT%"
call :log "========================================"
call :log ""

REM Prüfe Docker
call :check_docker

REM Update-Modus
if "%UPDATE_ONLY%"=="true" (
    call :log "%BLUE%🔄 Update-Modus: Nur App aktualisieren...%NC%"
    if exist "docker-compose.yml" (
        docker compose down
        docker compose build --no-cache
        docker compose up -d
        call :log "%GREEN%✅ Update abgeschlossen!%NC%"
    ) else (
        call :log "%RED%❌ Keine bestehende Installation gefunden!%NC%"
        exit /b 1
    )
    goto :end
)

REM Berechne Ports
call :calculate_ports

REM Prüfe Port-Konflikte
call :check_port_conflicts

REM Prüfe bestehende Installation
if exist "docker-compose.yml" (
    if "%FORCE%"=="false" (
        call :log "%YELLOW%⚠️  Bestehende Installation gefunden!%NC%"
        call :log ""
        call :log "Optionen:"
        call :log "1 = Abbrechen"
        call :log "2 = Komplett neu installieren (ALLE Daten gehen verloren!)"
        call :log "3 = Nur App neu installieren (Daten bleiben erhalten)"
        call :log ""
        set /p "choice=Wählen Sie (1-3): "
        
        if "!choice!"=="1" (
            call :log "Installation abgebrochen."
            goto :end
        )
        if "!choice!"=="2" (
            call :log "%RED%⚠️  KOMPLETT NEU INSTALLIEREN - ALLE DATEN GEHEN VERLOREN!%NC%"
            set /p "confirm=Sind Sie sicher? (j/N): "
            if /i not "!confirm!"=="j" (
                call :log "Installation abgebrochen."
                goto :end
            )
            call :log "%BLUE%🔄 Komplett neu installieren...%NC%"
            docker compose down -v
            docker system prune -f
            if exist "data" rmdir /s /q "data"
            if exist "backups" rmdir /s /q "backups"
            if exist "logs" rmdir /s /q "logs"
        )
        if "!choice!"=="3" (
            call :log "%BLUE%🔄 Nur App neu installieren...%NC%"
            docker compose down
            docker compose build --no-cache
            docker compose up -d
            call :log "%GREEN%✅ Update abgeschlossen!%NC%"
            goto :end
        )
        call :log "Ungültige Auswahl. Installation abgebrochen."
        exit /b 1
    )
)

REM Erstelle Verzeichnisse
call :create_directories

REM Erstelle Konfigurationsdateien
call :create_env
call :create_docker_compose
call :create_management_script

REM Installiere Container
call :install_containers

REM Warte auf Services
call :wait_for_services

REM Zeige finale Informationen
call :show_final_info

:end
pause

REM Starte Hauptfunktion
call :main 