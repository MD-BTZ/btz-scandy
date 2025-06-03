# Verwende Python 3.11 als Basis-Image
FROM python:3.11-slim

# Installiere System-Abhängigkeiten
RUN apt-get update && apt-get install -y \
    git \
    nodejs \
    npm \
    pandoc \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Setze das Arbeitsverzeichnis
WORKDIR /app

# Klone das Repository
RUN git clone https://github.com/woschj/scandy2.git /app

# Kopiere Requirements
COPY requirements.txt .

# Installiere Python-Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere Anwendungscode
COPY . .

# Setze Umgebungsvariablen
ENV FLASK_APP=app
ENV FLASK_ENV=production

# Installiere Node.js-Abhängigkeiten und kompiliere Tailwind CSS
RUN npm install && npm run build:css

# Erstelle notwendige Verzeichnisse
RUN mkdir -p /app/database /app/uploads /app/backups

# Setze Berechtigungen
RUN chmod -R 777 /app/database /app/uploads /app/backups

# Exponiere den Port
EXPOSE 5000

# Starte die Anwendung
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"] 