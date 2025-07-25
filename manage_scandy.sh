#!/bin/bash

# Scandy Management Skript
case "$1" in
    start)
        echo "Starte Scandy..."
        sudo systemctl start scandy.service
        ;;
    stop)
        echo "Stoppe Scandy..."
        sudo systemctl stop scandy.service
        ;;
    restart)
        echo "Starte Scandy neu..."
        sudo systemctl restart scandy.service
        ;;
    status)
        echo "Scandy Status:"
        sudo systemctl status scandy.service
        ;;
    logs)
        echo "Scandy Logs:"
        sudo journalctl -u scandy.service -f
        ;;
    backup)
        echo "Erstelle Backup..."
        ./backup_scandy.sh
        ;;
    update)
        echo "Update Scandy..."
        ./update_scandy.sh
        ;;
    *)
        echo "Verwendung: $0 {start|stop|restart|status|logs|backup|update}"
        exit 1
        ;;
esac
