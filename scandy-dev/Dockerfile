FROM python:3.11-slim

# Installiere Git und Node.js
RUN apt-get update && apt-get install -y \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Klone das Repository
RUN git clone https://github.com/woschj/scandy2.git /app

# Installiere Python-Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt

# Installiere und baue CSS
RUN npm install && npm run build:css

# Erstelle notwendige Verzeichnisse
RUN mkdir -p /app/database /app/uploads /app/backups
RUN chmod -R 777 /app/database /app/uploads /app/backups

# Setze Berechtigungen für das Update-Skript
RUN chmod +x /app/update.sh

EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0"]
