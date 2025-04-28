#!/bin/bash

# Konfiguration
SERVER="btz-admin@10.42.0.189"
ARCHIV="scandy.tar.gz"
TEMP_DIR="/tmp/scandy_install"

echo "Starte Installation..."

# Archiv kopieren
echo "Kopiere Archiv auf den Server..."
scp $ARCHIV $SERVER:$TEMP_DIR

# Remote-Installation ausführen
echo "Starte Remote-Installation..."
ssh $SERVER << 'ENDSSH'
    # Berechtigungen anpassen
    sudo chown -R btz-admin:btz-admin $TEMP_DIR
    sudo chmod -R 755 $TEMP_DIR

    # Archiv entpacken
    tar -xzf $TEMP_DIR/$ARCHIV -C $TEMP_DIR

    # Startskript ausführbar machen
    chmod +x $TEMP_DIR/start.sh

    # Container starten
    cd $TEMP_DIR
    ./start.sh
ENDSSH

echo "Installation abgeschlossen. Bitte überprüfen Sie die Anwendung unter http://10.42.0.189:5000" 