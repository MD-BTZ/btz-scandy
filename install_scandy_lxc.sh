#!/bin/bash
set -e

# Farben
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}==== Scandy LXC-Installationsskript ====${NC}"

# 1. System aktualisieren
apt update && apt upgrade -y

# 2. Basis-Pakete installieren (ohne mongodb)
apt install -y python3 python3-pip python3-venv git nginx curl gnupg lsb-release

# 3. Offizielles MongoDB-Repository hinzufügen (Version 7.x, focal-Workaround für noble)
UBUNTU_CODENAME=$(lsb_release -cs)
MONGO_REPO_CODENAME=$UBUNTU_CODENAME
if [ "$UBUNTU_CODENAME" = "noble" ]; then
    echo -e "${GREEN}Ubuntu 24.04 erkannt – focal-Repo für MongoDB wird verwendet!${NC}"
    MONGO_REPO_CODENAME="focal"
fi

# GPG-Key robust laden
if ! curl -fsSL https://pgp.mongodb.com/server-7.0.asc -o /tmp/server-7.0.asc; then
    echo "Fehler: Konnte den MongoDB GPG-Key nicht herunterladen! Prüfe Internet und DNS."
    exit 1
fi
gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg /tmp/server-7.0.asc

# Repo eintragen
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu $MONGO_REPO_CODENAME/mongodb-org/7.0 multiverse" > /etc/apt/sources.list.d/mongodb-org-7.0.list
apt update
apt install -y mongodb-org

# 4. Benutzer und Verzeichnis anlegen
useradd -m -s /bin/bash scandy || true
mkdir -p /opt/scandy
chown scandy:scandy /opt/scandy

# 5. Code ins Zielverzeichnis kopieren (wenn nicht schon dort)
if [ "$PWD" != "/opt/scandy" ]; then
    cp -r . /opt/scandy/
    chown -R scandy:scandy /opt/scandy
fi
cd /opt/scandy

# 6. Python-Umgebung einrichten
sudo -u scandy python3 -m venv /opt/scandy/venv
sudo -u scandy /opt/scandy/venv/bin/pip install --upgrade pip
sudo -u scandy /opt/scandy/venv/bin/pip install -r /opt/scandy/requirements.txt

# 7. MongoDB einrichten
systemctl enable mongod
systemctl start mongod

# 8. .env-Datei anlegen (ggf. anpassen)
cat > /opt/scandy/.env <<EOF
MONGODB_URI=mongodb://localhost:27017/scandy
MONGODB_DB=scandy
SECRET_KEY=$(openssl rand -hex 32)
FLASK_ENV=production
EOF
chown scandy:scandy /opt/scandy/.env

# 9. Systemd-Service für Scandy anlegen
cat > /etc/systemd/system/scandy.service <<EOF
[Unit]
Description=Scandy Flask App
After=network.target mongod.service

[Service]
User=scandy
Group=scandy
WorkingDirectory=/opt/scandy
Environment=PATH=/opt/scandy/venv/bin
EnvironmentFile=/opt/scandy/.env
ExecStart=/opt/scandy/venv/bin/gunicorn --bind 127.0.0.1:5000 app.wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable scandy
systemctl restart scandy

# 10. Nginx als Reverse Proxy einrichten
cat > /etc/nginx/sites-available/scandy <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /opt/scandy/app/static;
        expires 30d;
    }
}
EOF

ln -sf /etc/nginx/sites-available/scandy /etc/nginx/sites-enabled/scandy
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx

# 11. Abschluss
IP=$(hostname -I | awk '{print $1}')
echo -e "${GREEN}==== Installation abgeschlossen! ====${NC}"
echo -e "Scandy läuft jetzt unter: http://$IP/" 