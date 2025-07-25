#!/bin/bash

# Scandy Update Skript
echo "Aktualisiere Scandy..."

# Stoppe Service
sudo systemctl stop scandy.service

# Aktiviere Virtual Environment
source venv/bin/activate

# Update Python-Pakete
pip install -r requirements.txt --upgrade

# Starte Service
sudo systemctl start scandy.service

echo "Scandy aktualisiert"
