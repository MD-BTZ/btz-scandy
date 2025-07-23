# Scandy Instanz-Management

## Übersicht der verfügbaren Instanzen

### **Standard-Instanz (Hauptinstallation)**
- **Port**: 5000 (App), 27017 (MongoDB), 8081 (Mongo Express)
- **Container**: `scandy-app`, `scandy-mongodb`, `scandy-mongo-express`
- **Skripte**:
  - `./start_standard.sh` - Startet die Standard-Instanz
  - `./stop_standard.sh` - Stoppt die Standard-Instanz
  - `./status_standard.sh` - Zeigt Status der Standard-Instanz

### **Instance 2 (Zweite Installation)**
- **Port**: 5001 (App), 27018 (MongoDB), 8082 (Mongo Express)
- **Container**: `scandy-app-2`, `scandy-mongodb-2`, `scandy-mongo-express-2`
- **Skripte**:
  - `./start_instance2.sh` - Startet die zweite Instanz
  - `./stop_instance2.sh` - Stoppt die zweite Instanz
  - `./status_instance2.sh` - Zeigt Status der zweiten Instanz

### **Abteilungs-Instanzen**
- **BTZ**: Port 5003 (App), 27020 (MongoDB)
- **Werkstatt**: Port 5001 (App), 27018 (MongoDB)
- **Verwaltung**: Port 5002 (App), 27019 (MongoDB)
- **Skripte**:
  - `./start_all.sh` - Startet alle Abteilungs-Instanzen
  - `./stop_all.sh` - Stoppt alle Abteilungs-Instanzen

## Verwendung

### **Standard-Instanz starten:**
```bash
./start_standard.sh
```

### **Zweite Instanz starten:**
```bash
./start_instance2.sh
```

### **Alle Abteilungen starten:**
```bash
./start_all.sh
```

### **Status prüfen:**
```bash
# Standard-Instanz
./status_standard.sh

# Zweite Instanz
./status_instance2.sh

# Alle Container
docker compose ps
```

### **Stoppen:**
```bash
# Standard-Instanz
./stop_standard.sh

# Zweite Instanz
./stop_instance2.sh

# Alle Abteilungen
./stop_all.sh
```

## Wichtige Hinweise

### **Docker Compose Befehle**
Alle Skripte verwenden `docker compose` (ohne Bindestrich) für Server-Kompatibilität.

### **Ports**
- Jede Instanz verwendet andere Ports
- Keine Konflikte zwischen Instanzen
- Separate Datenbanken für jede Instanz

### **Container-Namen**
- Standard: `scandy-app`, `scandy-mongodb`, `scandy-mongo-express`
- Instance 2: `scandy-app-2`, `scandy-mongodb-2`, `scandy-mongo-express-2`
- Keine Namenskonflikte

### **Datenbanken**
- Standard: `scandy` (MongoDB)
- Instance 2: `scandy_instance2` (MongoDB)
- Separate Daten für jede Instanz

## Troubleshooting

### **Container-Name-Konflikt:**
```bash
# Alle Container stoppen
docker compose down
docker compose -f docker-compose-instance2.yml down

# Dann neu starten
./start_standard.sh
./start_instance2.sh
```

### **Port-Konflikt:**
```bash
# Prüfe welche Ports belegt sind
netstat -tulpn | grep :500

# Stoppe alle Instanzen
./stop_standard.sh
./stop_instance2.sh
./stop_all.sh
```

### **Docker Compose Fehler:**
```bash
# Verwende docker compose statt docker-compose
docker compose up -d
docker compose down
docker compose ps
``` 