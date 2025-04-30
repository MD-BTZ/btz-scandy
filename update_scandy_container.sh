#!/bin/bash

ARCHIV="$1"
CONTAINER="scandy"
APP_DIR="/app"

if [ -z "$ARCHIV" ]; then
  echo "Bitte gib den Namen des App-Archivs als Argument an!"
  echo "Beispiel: ./update_scandy_container.sh scandy_build_20250430_1520.tar.gz"
  exit 1
fi

echo "Kopiere $ARCHIV in den Container..."
docker cp "$ARCHIV" $CONTAINER:/tmp/

echo "Entpacke Archiv im Container (ohne Datenbank-Verzeichnis zu überschreiben)..."
docker exec $CONTAINER bash -c "tar --exclude='database' -xzf /tmp/$(basename $ARCHIV) -C $APP_DIR --strip-components=1"

echo "Entferne Archiv aus dem Container..."
docker exec $CONTAINER rm /tmp/$(basename $ARCHIV)

echo "Starte App-Prozess im Container neu..."
docker restart $CONTAINER

echo "Fertig! Die App wurde im Container aktualisiert." 