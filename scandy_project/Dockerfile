# Multi-Stage Build für optimierte Größe
FROM node:18-alpine AS frontend-builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY app/static/css/input.css ./app/static/css/
RUN npm run build:css

# Python Builder Stage
FROM python:3.11-slim AS python-builder

WORKDIR /app

# Installiere nur Build-Abhängigkeiten
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Kopiere und installiere Python-Abhängigkeiten
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final Stage
FROM python:3.11-slim AS final

# Installiere nur Runtime-Abhängigkeiten
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Erstelle nicht-root Benutzer
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Kopiere Python-Pakete vom Builder
COPY --from=python-builder /root/.local /home/appuser/.local

# Kopiere CSS vom Frontend-Builder
COPY --from=frontend-builder /app/app/static/css/main.css ./app/static/css/

# Kopiere Anwendungscode
COPY . .

# Erstelle notwendige Verzeichnisse
RUN mkdir -p /app/app/uploads /app/app/backups /app/app/logs /app/app/static /app/tmp && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Wechsle zu nicht-root Benutzer
USER appuser

# Füge Python-Pakete zum PATH hinzu
ENV PATH=/home/appuser/.local/bin:$PATH

# Exponiere Port
EXPOSE 5000

# Health Check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Starte die Anwendung
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"] 