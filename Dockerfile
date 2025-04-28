# Verwende Python 3.9 als Basis-Image
FROM python:3.9-slim

# Setze Arbeitsverzeichnis
WORKDIR /app

# Installiere Systemabhängigkeiten
RUN apt-get update && apt-get install -y \
    build-essential \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Kopiere Requirements-Datei
COPY requirements.txt .

# Installiere Python-Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere Anwendungsdateien
COPY . .

# Erstelle notwendige Verzeichnisse
RUN mkdir -p /app/backups /app/venv

# Setze Umgebungsvariablen
ENV FLASK_APP=app.wsgi:application
ENV FLASK_ENV=production
ENV DATABASE_URL=sqlite:////app/database/inventory.db

# Exponiere Port 5000
EXPOSE 5000

# Starte die Anwendung mit Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app.wsgi:application"] 