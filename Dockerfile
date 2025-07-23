# Einfaches Dockerfile für Scandy
FROM python:3.11-slim

# Installiere System-Abhängigkeiten
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Kopiere nur die notwendigen Dateien
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY package*.json ./
COPY tailwind.config.js ./
COPY postcss.config.js ./

# Kopiere das app-Verzeichnis
COPY app ./app

WORKDIR /app

# Aktualisiere npm und installiere Abhängigkeiten
RUN npm install --silent
RUN npm update --silent
RUN npm audit fix --silent || true
RUN npm run build:css

# Erstelle notwendige Verzeichnisse
RUN mkdir -p /app/app/uploads /app/app/backups /app/app/logs /app/app/static /app/tmp

# Setze Umgebungsvariablen
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_APP=app/wsgi.py

# Exponiere Port
EXPOSE 5000

# Health Check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Starte die Anwendung mit Gunicorn (Produktions-WSGI-Server)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "--max-requests", "1000", "--max-requests-jitter", "100", "app.wsgi:application"] 