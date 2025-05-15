#!/bin/bash

ARCHIV="$1"
CONTAINER="scandy-test"
APP_DIR="/app"

if [ -z "$ARCHIV" ]; then
  echo "Bitte gib den Namen des App-Archivs als Argument an!"
  echo "Beispiel: ./update_scandy_test_container.sh scandy_build_20250430_1520.tar.gz"
  exit 1
fi

echo "Kopiere $ARCHIV in den Container..."
docker cp "$ARCHIV" $CONTAINER:/tmp/

echo "Entpacke Archiv im Container..."
docker exec $CONTAINER bash -c "tar -xzf /tmp/$(basename $ARCHIV) -C $APP_DIR --strip-components=1"

echo "Entferne Archiv aus dem Container..."
docker exec $CONTAINER rm /tmp/$(basename $ARCHIV)

echo "Starte App-Prozess im Container neu..."
docker restart $CONTAINER

echo "Fertig! Die App wurde im Test-Container aktualisiert." 