#!/bin/bash

# Konfiguration
SERVER="btz-admin@10.42.0.189"
ARCHIV="scandy_deploy.tar.gz"
TEMP_DIR="/tmp/scandy_test_install"
TARGET_DIR="/opt/scandy_test"
TEST_PORT=5001

echo "Starte Installation der Testumgebung..."

# Verzeichnis vorbereiten
echo "Bereite Verzeichnisse auf dem Server vor..."
ssh $SERVER "mkdir -p $TEMP_DIR && sudo chown btz-admin:btz-admin $TEMP_DIR && chmod 755 $TEMP_DIR && mkdir -p $TARGET_DIR"

# Archiv kopieren
echo "Kopiere Archiv auf den Server..."
scp $ARCHIV $SERVER:$TEMP_DIR

# Remote-Installation ausführen
echo "Starte Remote-Installation..."
ssh $SERVER << EOF
    # Verzeichnis leeren falls es schon existiert
    rm -rf $TARGET_DIR/*
    
    # Archiv entpacken
    tar -xzf $TEMP_DIR/$ARCHIV -C $TARGET_DIR
    
    # Berechtigungen anpassen
    sudo chown -R btz-admin:btz-admin $TARGET_DIR
    sudo chmod -R 755 $TARGET_DIR
    
    # Verzeichnisse erstellen
    mkdir -p $TARGET_DIR/database $TARGET_DIR/backups $TARGET_DIR/logs $TARGET_DIR/tmp
    
    # Startskript ausführbar machen
    chmod +x $TARGET_DIR/docker-start.sh
    
    # Secret Key generieren falls nicht vorhanden
    if [ ! -f $TARGET_DIR/.env ]; then
        echo "Generiere neue .env Datei..."
        echo "SECRET_KEY=\$(openssl rand -hex 32)" > $TARGET_DIR/.env
    fi
    
    # Docker-Compose-Datei für Testumgebung anpassen
    sed -i "s/\"5000:5000\"/\"$TEST_PORT:5000\"/" $TARGET_DIR/docker-compose.yml
    sed -i "s/container_name: scandy/container_name: scandy_test/" $TARGET_DIR/docker-compose.yml
    
    # Docker-Container bauen und starten
    cd $TARGET_DIR
    sudo docker compose up -d --build
    
    echo "Installation der Testumgebung abgeschlossen!"
EOF

echo "Installation der Testumgebung abgeschlossen. Die Anwendung sollte unter http://10.42.0.189:$TEST_PORT erreichbar sein."
echo "Überprüfen Sie den Container-Status mit: ssh $SERVER 'sudo docker ps | grep scandy_test'" 