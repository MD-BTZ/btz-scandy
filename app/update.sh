#!/bin/bash

# Git-Repository aktualisieren
git fetch origin
git reset --hard origin/main

# Python-Abhängigkeiten installieren
pip install -r requirements.txt

# Neustart-Trigger setzen
mkdir -p tmp
touch tmp/needs_restart

echo "Update abgeschlossen"