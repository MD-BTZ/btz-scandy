FROM python:3.9-slim

# Arbeitsverzeichnis im Container
WORKDIR /app

# System-Abhängigkeiten installieren
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# App von GitHub klonen
RUN git clone -b electron https://github.com/woschj/scandy.git .

# Python-Abhängigkeiten aus requirements.txt im Repository installieren
RUN pip install --no-cache-dir -r requirements.txt

# Port 5000 freigeben
EXPOSE 5000

# Umgebungsvariablen setzen
ENV FLASK_APP=app
ENV FLASK_ENV=development

# Stelle sicher, dass das Datenbankverzeichnis existiert
RUN mkdir -p app/database

# Anwendung starten
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"] 