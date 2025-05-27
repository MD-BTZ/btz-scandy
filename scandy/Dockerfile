FROM python:3.11-slim

# Installiere System-Abhängigkeiten
RUN apt-get update && apt-get install -y \
    git \
    nodejs \
    npm \
    curl \
    build-essential \
    libsqlite3-dev \
    zip \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Erstelle nicht-root Benutzer
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Klone das Repository
RUN git clone https://github.com/woschj/scandy2.git /app

# Installiere Python-Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt docker

# Installiere und baue CSS
RUN npm install && npm run build:css

# Erstelle notwendige Verzeichnisse
RUN mkdir -p /app/database /app/uploads /app/backups /app/logs /app/tmp
RUN chmod -R 777 /app/database /app/uploads /app/backups /app/logs /app/tmp

# Setze Berechtigungen für das Update-Skript
RUN chmod +x /app/update.sh

# Wechsle zu nicht-root Benutzer
USER appuser

EXPOSE 5000

# Starte Gunicorn mit mehreren Workers
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--reload", "--reload-extra-file", "tmp/needs_restart", "--log-level", "debug", "app.wsgi:application"]
