# Multi-Instance Setup Beispiele

## Beispiel 1: Werkstatt + Verwaltung

```bash
# Erste Instanz: Werkstatt
./install_working.sh -n werkstatt -p 5000 -m 27017 -e 8081

# Zweite Instanz: Verwaltung  
./install_working.sh -n verwaltung -p 5001 -m 27018 -e 8082
```

**Ergebnis:**
- Werkstatt: http://localhost:5000 (MongoDB: 27017, Express: 8081)
- Verwaltung: http://localhost:5001 (MongoDB: 27018, Express: 8082)

## Beispiel 2: Automatische Port-Berechnung

```bash
# Instance-Namen mit Nummern = automatische Port-Berechnung
./install_working.sh -n instance1  # Ports: 5001, 27018, 8082
./install_working.sh -n instance2  # Ports: 5002, 27019, 8083
./install_working.sh -n instance3  # Ports: 5003, 27020, 8084
```

## Beispiel 3: Custom Ports

```bash
# Spezifische Ports für jede Instanz
./install_working.sh -n produktions -p 8080 -m 27020 -e 9090
./install_working.sh -n test -p 8081 -m 27021 -e 9091
./install_working.sh -n demo -p 8082 -m 27022 -e 9092
```

## Verzeichnis-Struktur

Jede Instanz erhält ein eigenes Verzeichnis:

```
/Users/woschj/Downloads/Scandy2/
├── .env                    # Haupt-Instanz
├── docker-compose.yml
├── manage.sh
├── verwaltung/            # Zweite Instanz
│   ├── .env
│   ├── docker-compose.yml
│   └── manage.sh
└── werkstatt/            # Dritte Instanz
    ├── .env
    ├── docker-compose.yml
    └── manage.sh
```

## Management

Jede Instanz hat ihr eigenes Management-Skript:

```bash
# Haupt-Instanz verwalten
./manage.sh start

# Verwaltung-Instanz verwalten
cd verwaltung
./manage.sh start

# Werkstatt-Instanz verwalten  
cd werkstatt
./manage.sh start
```

## Port-Übersicht

| Instanz | Web-App | MongoDB | Mongo Express |
|---------|---------|---------|---------------|
| scandy  | 5000    | 27017   | 8081          |
| verwaltung | 5001  | 27018   | 8082          |
| werkstatt | 5002   | 27019   | 8083          |

## Wichtige Hinweise

1. **Port-Konflikte vermeiden**: Jede Instanz braucht eindeutige Ports
2. **Ressourcen**: Mehrere Instanzen = mehr RAM/CPU-Verbrauch
3. **Backups**: Jede Instanz hat eigene Backups
4. **Updates**: Instanzen können unabhängig aktualisiert werden
5. **Netzwerke**: Jede Instanz hat isoliertes Docker-Netzwerk 