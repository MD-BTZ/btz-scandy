# Einfaches Multi-Platform Dockerfile für Scandy
# Fallback-Version für bessere Kompatibilität

FROM python:3.11-slim

# Installiere System-Abhängigkeiten
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    nodejs \
    npm \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Erstelle nicht-root Benutzer
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Kopiere Anwendungscode
COPY . .

# Installiere Python-Abhängigkeiten
RUN pip install --no-cache-dir --user -r requirements.txt

# Installiere Node.js Dependencies und baue CSS
RUN npm install && npm run build:css

# Erstelle notwendige Verzeichnisse
RUN mkdir -p /app/app/uploads /app/app/backups /app/app/logs /app/app/static /app/tmp && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Wechsle zu nicht-root Benutzer
USER appuser

# Füge Python-Pakete zum PATH hinzu
ENV PATH=/home/appuser/.local/bin:$PATH

# Setze Umgebungsvariablen
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_APP=app/wsgi.py

# Exponiere Port
EXPOSE 5000

# Health Check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Starte die Anwendung
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"] 