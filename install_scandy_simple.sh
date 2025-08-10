#!/usr/bin/env bash
set -euo pipefail

# Einfache Native-Installation für Scandy (Ubuntu/Debian)
# - Keine Interaktion
# - Nutzt lokalen MongoDB-Server (127.0.0.1:27017)
# - Installiert in /opt/scandy

log_info()    { echo -e "[INFO]    $*"; }
log_success() { echo -e "[SUCCESS] $*"; }
log_warn()    { echo -e "[WARN]    $*"; }
log_error()   { echo -e "[ERROR]   $*"; }

require_root() {
  if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    log_error "Bitte als root ausführen (sudo)."; exit 1
  fi
}

detect_apt() {
  if command -v apt >/dev/null 2>&1; then
    echo apt
  else
    log_error "Dieses einfache Script unterstützt nur Debian/Ubuntu (apt)."
    exit 1
  fi
}

install_packages() {
  local PKG=python3-venv
  log_info "Installiere Systempakete..."
  apt update -y >/dev/null
  apt install -y python3 python3-venv python3-pip git curl gnupg lsb-release $PKG >/dev/null
  log_success "Systempakete installiert"
}

ensure_mongodb() {
  if ! command -v mongod >/dev/null 2>&1; then
    log_info "Installiere MongoDB..."
    curl -fsSL https://pgp.mongodb.com/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg
    echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/7.0 multiverse" > /etc/apt/sources.list.d/mongodb-org-7.0.list
    apt update -y >/dev/null
    apt install -y mongodb-org >/dev/null
  fi
  systemctl enable mongod >/dev/null 2>&1 || true
  systemctl restart mongod || systemctl start mongod || true
  # Kurzes Warten, bis 27017 lauscht
  for i in {1..20}; do
    if ss -H -ltn 2>/dev/null | awk '{print $4}' | grep -q ":27017$"; then
      log_success "MongoDB läuft auf 127.0.0.1:27017"
      return
    fi
    sleep 1
  done
  log_warn "MongoDB lauscht nicht auf 27017. Prüfe 'systemctl status mongod'."
}

configure_mongo_auth() {
  log_info "Prüfe MongoDB-Authentifizierung..."
  local CONF=/etc/mongod.conf
  local ADMIN_USER=admin
  local APP_USER=scandy_app
  local ADMIN_PW APP_PW

  # sichere Passwörter (ohne Here-Doc, robust ohne Python)
  ADMIN_PW=$(head -c 32 /dev/urandom | base64 | tr -d '=+/' | cut -c1-24)
  APP_PW=$(head -c 32 /dev/urandom | base64 | tr -d '=+/' | cut -c1-24)

  # Wenn authorization bereits enabled ist, überspringen wir das Anlegen (keine Credentials bekannt)
  if grep -qE '^\s*security:\s*$' "$CONF" && grep -qE '^\s*authorization:\s*enabled\s*$' "$CONF"; then
    log_info "MongoDB authorization ist bereits aktiviert – überspringe User-Provisioning."
  else
    log_info "Erstelle MongoDB-User (ohne Auth aktiv)..."
    # Admin-User anlegen (root)
    mongosh --quiet --eval "db.getSiblingDB('admin').createUser({user: '$ADMIN_USER', pwd: '$ADMIN_PW', roles: [{role: 'root', db: 'admin'}]})" || true
    # App-User mit readWrite auf scandy, in admin-DB verwaltet
    mongosh --quiet --eval "db.getSiblingDB('admin').createUser({user: '$APP_USER', pwd: '$APP_PW', roles: [{role: 'readWrite', db: 'scandy'}]})" || true

    # Authorization aktivieren
    if ! grep -qE '^\s*security:\s*$' "$CONF"; then
      printf "\nsecurity:\n  authorization: enabled\n" >> "$CONF"
    else
      if grep -qE '^\s*authorization:' "$CONF"; then
        sed -i "s/^\s*authorization:.*/  authorization: enabled/" "$CONF"
      else
        sed -i "/^\s*security:\s*$/a\\  authorization: enabled" "$CONF"
      fi
    fi
    systemctl restart mongod || true
    log_success "MongoDB-Authentifizierung aktiviert"

    # .env mit App-User-Credentials befüllen
    sed -i "s#^MONGODB_URI=.*#MONGODB_URI=mongodb://$APP_USER:$APP_PW@localhost:27017/scandy?authSource=admin#" /opt/scandy/.env || true
  fi
}

setup_app_tree() {
  log_info "Richte /opt/scandy ein..."
  mkdir -p /opt/scandy
  # Code kopieren (ohne venv/__pycache__)
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete --exclude 'venv' --exclude '__pycache__' --exclude '*.pyc' ./ /opt/scandy/
  else
    cp -r . /opt/scandy/
    rm -rf /opt/scandy/venv /opt/scandy/__pycache__ || true
    find /opt/scandy -name "*.pyc" -delete 2>/dev/null || true
  fi
  chown -R scandy:scandy /opt/scandy 2>/dev/null || true
  log_success "Code nach /opt/scandy kopiert"
}

setup_venv() {
  log_info "Erstelle Virtualenv..."
  rm -rf /opt/scandy/venv || true
  sudo -u scandy bash -lc 'python3 -m venv /opt/scandy/venv' 2>/dev/null || python3 -m venv /opt/scandy/venv
  log_info "Installiere Python-Abhängigkeiten..."
  /opt/scandy/venv/bin/pip install --upgrade pip --no-warn-script-location >/dev/null
  /opt/scandy/venv/bin/pip install -r /opt/scandy/requirements.txt --no-warn-script-location
  log_success "Python-Umgebung bereit"
}

write_env() {
  log_info "Schreibe /opt/scandy/.env (minimal)..."
  local ENV=/opt/scandy/.env
  if [ ! -f "$ENV" ]; then
    local SECRET=$(python3 - <<'PY'
import secrets; print(secrets.token_urlsafe(48))
PY
)
    cat > "$ENV" <<EOF
WEB_PORT=5001
MONGODB_PORT=27017
MONGODB_DB=scandy
MONGODB_URI=mongodb://admin:admin@localhost:27017/scandy?authSource=admin
SECRET_KEY=$SECRET
SESSION_COOKIE_SECURE=false
REMEMBER_COOKIE_SECURE=false
FLASK_ENV=production
EOF
    log_success ".env erstellt"
  else
    log_info ".env existiert – unverändert übernommen"
  fi
}

create_systemd_unit() {
  log_info "Erzeuge systemd-Unit..."
  cat > /etc/systemd/system/scandy.service << 'EOF'
[Unit]
Description=Scandy Application - scandy
After=network.target mongod.service

[Service]
Type=simple
User=scandy
Group=scandy
WorkingDirectory=/opt/scandy
Environment=PATH=/opt/scandy/venv/bin
EnvironmentFile=-/opt/scandy/.env
ExecStart=/opt/scandy/venv/bin/gunicorn --bind 0.0.0.0:${WEB_PORT} --workers 4 app.wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable scandy >/dev/null 2>&1 || true
  log_success "systemd-Unit geschrieben"
}

open_firewall() {
  if command -v ufw >/dev/null 2>&1 && ufw status | grep -q 'Status: active'; then
    if ! ufw status | grep -q '5001/tcp.*ALLOW'; then
      yes | ufw allow 5001/tcp >/dev/null 2>&1 || true
      log_info "UFW: Port 5001 freigegeben"
    fi
  fi
}

start_services() {
  log_info "Starte Dienste..."
  systemctl restart mongod || systemctl start mongod || true
  systemctl restart scandy || systemctl start scandy || true
  # Port-Wartecheck
  for i in {1..60}; do
    if ss -H -ltn | grep -q ':5001 '; then
      log_success "App lauscht auf Port 5001"
      return
    fi
    sleep 2
  done
  log_warn "Port 5001 lauscht nicht. Prüfe 'journalctl -u scandy -f'."
}

main() {
  require_root
  detect_apt >/dev/null
  install_packages
  ensure_mongodb
  setup_app_tree
  setup_venv
  write_env
  configure_mongo_auth
  create_systemd_unit
  open_firewall
  start_services

  echo
  log_success "Installation abgeschlossen."
  echo "Web-App:   http://<SERVER-IP>:5001"
  echo "Logs:      journalctl -u scandy -f"
}

main "$@"


