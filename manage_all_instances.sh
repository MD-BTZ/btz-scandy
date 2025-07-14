#!/bin/bash

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Funktionen
show_help() {
    echo "========================================"
    echo "Scandy Multi-Instance Manager"
    echo "========================================"
    echo
    echo "Verwendung: ./manage_all_instances.sh [BEFEHL] [INSTANCE]"
    echo
    echo "Befehle:"
    echo "  list                    - Alle Instances auflisten"
    echo "  status [INSTANCE]       - Status aller oder einer Instance"
    echo "  start [INSTANCE]        - Alle oder eine Instance starten"
    echo "  stop [INSTANCE]         - Alle oder eine Instance stoppen"
    echo "  restart [INSTANCE]      - Alle oder eine Instance neustarten"
    echo "  logs [INSTANCE]         - Logs aller oder einer Instance"
    echo "  update [INSTANCE]       - Alle oder eine Instance aktualisieren"
    echo "  install NAME [OPTIONS]  - Neue Instance installieren"
    echo "  help                    - Diese Hilfe anzeigen"
    echo
    echo "Beispiele:"
    echo "  ./manage_all_instances.sh list"
    echo "  ./manage_all_instances.sh status"
    echo "  ./manage_all_instances.sh start verwaltung"
    echo "  ./manage_all_instances.sh install werkstatt -p 8080"
}

# Finde alle Scandy-Instances
find_instances() {
    local instances=()
    
    # Suche nach docker-compose.yml Dateien mit Scandy-Konfiguration
    local compose_files=$(find / -name "docker-compose.yml" -type f 2>/dev/null | grep -E "(scandy|verwaltung|werkstatt|btz)" | head -10)
    
    for file in $compose_files; do
        local dir=$(dirname "$file")
        if [ -f "$dir/.env" ]; then
            local instance_name=$(grep "DEPARTMENT=" "$dir/.env" | cut -d'=' -f2 2>/dev/null)
            if [ -n "$instance_name" ]; then
                instances+=("$instance_name:$dir")
            fi
        fi
    done
    
    echo "${instances[@]}"
}

# Zeige alle Instances
list_instances() {
    echo -e "${BLUE}🔍 Suche nach Scandy-Instances...${NC}"
    
    local instances=($(find_instances))
    
    if [ ${#instances[@]} -eq 0 ]; then
        echo -e "${YELLOW}⚠️  Keine Scandy-Instances gefunden${NC}"
        return
    fi
    
    echo -e "${GREEN}✅ Gefundene Instances:${NC}"
    echo ""
    
    for instance_info in "${instances[@]}"; do
        local instance_name=$(echo "$instance_info" | cut -d':' -f1)
        local instance_dir=$(echo "$instance_info" | cut -d':' -f2)
        
        # Prüfe Status
        local status="gestoppt"
        if docker ps --format "table {{.Names}}" | grep -q "scandy-app-$instance_name"; then
            status="läuft"
        fi
        
        # Hole Port-Informationen
        local web_port=$(grep "WEB_PORT=" "$instance_dir/.env" | cut -d'=' -f2 2>/dev/null || echo "unbekannt")
        
        echo -e "${BLUE}📋 $instance_name${NC}"
        echo "   Verzeichnis: $instance_dir"
        echo "   Status: $status"
        echo "   Web-Port: $web_port"
        echo ""
    done
}

# Führe Befehl für alle oder eine spezifische Instance aus
execute_for_instances() {
    local command="$1"
    local target_instance="$2"
    local instances=($(find_instances))
    
    if [ ${#instances[@]} -eq 0 ]; then
        echo -e "${YELLOW}⚠️  Keine Scandy-Instances gefunden${NC}"
        return
    fi
    
    for instance_info in "${instances[@]}"; do
        local instance_name=$(echo "$instance_info" | cut -d':' -f1)
        local instance_dir=$(echo "$instance_info" | cut -d':' -f2)
        
        # Wenn eine spezifische Instance angegeben wurde, überspringe andere
        if [ -n "$target_instance" ] && [ "$instance_name" != "$target_instance" ]; then
            continue
        fi
        
        echo -e "${BLUE}🔧 Führe '$command' für $instance_name aus...${NC}"
        echo "   Verzeichnis: $instance_dir"
        
        # Wechsle ins Verzeichnis und führe Befehl aus
        cd "$instance_dir"
        
        case "$command" in
            start)
                docker compose up -d
                ;;
            stop)
                docker compose down
                ;;
            restart)
                docker compose restart
                ;;
            status)
                docker compose ps
                ;;
            logs)
                docker compose logs --tail=20
                ;;
            update)
                docker compose down
                docker compose build --no-cache
                docker compose up -d
                ;;
        esac
        
        echo ""
    done
}

# Installiere neue Instance
install_instance() {
    local instance_name="$1"
    shift
    
    if [ -z "$instance_name" ]; then
        echo -e "${RED}❌ ERROR: Instance-Name erforderlich!${NC}"
        echo "Verwendung: ./manage_all_instances.sh install NAME [OPTIONS]"
        exit 1
    fi
    
    echo -e "${BLUE}🚀 Installiere neue Instance: $instance_name${NC}"
    
    # Erstelle Installationsverzeichnis
    local install_dir="./$instance_name"
    
    # Parse zusätzliche Optionen
    local install_options=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            -p|--port)
                install_options="$install_options -p $2"
                shift 2
                ;;
            -m|--mongodb-port)
                install_options="$install_options -m $2"
                shift 2
                ;;
            -e|--express-port)
                install_options="$install_options -e $2"
                shift 2
                ;;
            -f|--force)
                install_options="$install_options -f"
                shift
                ;;
            *)
                echo -e "${RED}❌ Unbekannte Option: $1${NC}"
                exit 1
                ;;
        esac
    done
    
    # Führe Installation aus
    echo "Installationsverzeichnis: $install_dir"
    echo "Optionen: $install_options"
    echo ""
    
    # Erstelle Verzeichnis und wechsle hinein
    mkdir -p "$install_dir"
    cd "$install_dir"
    
    # Kopiere Installationsskript falls vorhanden
    if [ -f "../install_unified.sh" ]; then
        cp "../install_unified.sh" .
        chmod +x install_unified.sh
        ./install_unified.sh -n "$instance_name" $install_options
    else
        echo -e "${RED}❌ ERROR: install_unified.sh nicht gefunden!${NC}"
        exit 1
    fi
}

# Hauptlogik
case "$1" in
    list)
        list_instances
        ;;
    status)
        execute_for_instances "status" "$2"
        ;;
    start)
        execute_for_instances "start" "$2"
        ;;
    stop)
        execute_for_instances "stop" "$2"
        ;;
    restart)
        execute_for_instances "restart" "$2"
        ;;
    logs)
        execute_for_instances "logs" "$2"
        ;;
    update)
        execute_for_instances "update" "$2"
        ;;
    install)
        shift
        install_instance "$@"
        ;;
    help|*)
        show_help
        ;;
esac 