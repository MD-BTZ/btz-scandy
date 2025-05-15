#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Installiere Scandy Testumgebung..."

# Prüfe ob Docker installiert ist
if ! command -v docker >/dev/null 2>&1; then
    echo "FEHLER: Docker ist nicht installiert. Bitte installieren Sie Docker zuerst." >&2
    exit 1
fi

# Erstelle Dockerfile für die Testumgebung
cat > Dockerfile.test << 'EOL'
FROM python:3.9-slim

WORKDIR /app

# Installiere Node.js, npm und SSH-Server
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    openssh-server \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# SSH-Konfiguration
RUN mkdir /var/run/sshd
RUN echo 'root:scandy' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

# Erstelle einen Entwickler-User
RUN useradd -m -s /bin/bash developer && \
    echo "developer:scandy" | chpasswd && \
    echo "developer ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Kopiere die Anwendungsdateien
COPY . .

# Setze Berechtigungen
RUN chown -R developer:developer /app

# Installiere Python-Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt

# Installiere npm-Abhängigkeiten und baue CSS
RUN npm install && npm run build:css

# Setze Umgebungsvariablen
ENV FLASK_APP=app
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0
ENV PORT=5001
ENV DATABASE_PATH=scandy_test.db

# Exponiere die Ports
EXPOSE 5001
EXPOSE 22

# Starte SSH und Gunicorn
COPY start-services.sh /start-services.sh
RUN chmod +x /start-services.sh
CMD ["/start-services.sh"]
EOL

# Erstelle Start-Skript für die Services
cat > start-services.sh << 'EOL'
#!/bin/bash
service ssh start
gunicorn --bind 0.0.0.0:5001 --workers 4 "app:create_app()"
EOL

# Erstelle docker-compose.yml für die Testumgebung
cat > docker-compose.test.yml << 'EOL'
version: '3'
services:
  scandy-test:
    build:
      context: .
      dockerfile: Dockerfile.test
    container_name: scandy-test
    ports:
      - "5001:5001"
      - "2223:22"
    volumes:
      - ./scandy_test.db:/app/scandy_test.db
    restart: unless-stopped
EOL

# Baue und starte den Container
echo "Baue und starte den Docker-Container für die Testumgebung..."
docker compose -f docker-compose.test.yml up -d --build

echo "------------------------------------"
echo "Scandy Testumgebung Installation abgeschlossen!"
echo ""
echo "Die Testumgebung ist jetzt verfügbar unter:"
echo "http://localhost:5001"
echo ""
echo "SSH-Zugang:"
echo "Host: localhost"
echo "Port: 2223"
echo "User: developer"
echo "Passwort: scandy"
echo ""
echo "Um den Container zu stoppen:"
echo "docker compose -f docker-compose.test.yml down"
echo "------------------------------------" 