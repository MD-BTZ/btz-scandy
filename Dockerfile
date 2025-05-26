# Verwende Python 3.11 als Basis-Image
FROM python:3.11-slim

# Installiere Git und andere benötigte Pakete
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Setze das Arbeitsverzeichnis
WORKDIR /app

# Klone das Repository
RUN git clone https://github.com/woschj/scandy2.git /app

# Installiere die Python-Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt

# Erstelle notwendige Verzeichnisse
RUN mkdir -p /app/database /app/uploads /app/backups

# Setze Berechtigungen
RUN chmod -R 777 /app/database /app/uploads /app/backups

# Exponiere den Port
EXPOSE 5000

# Starte die Anwendung
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"] 