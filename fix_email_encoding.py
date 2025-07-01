#!/usr/bin/env python3
"""
Script zur Diagnose und Behebung des E-Mail-Encoding-Problems
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.mongodb_database import mongodb
from app.utils.email_utils import get_email_config, test_email_config

def diagnose_email_problem():
    print("=== DIAGNOSE: E-Mail-Encoding-Problem ===\n")
    
    # 1. Prüfe aktuelle E-Mail-Konfiguration
    print("1. Aktuelle E-Mail-Konfiguration:")
    config = get_email_config()
    if config:
        print(f"   - Aktiviert: {config.get('enabled', False)}")
        print(f"   - SMTP-Server: {config.get('mail_server', 'Nicht gesetzt')}")
        print(f"   - Port: {config.get('mail_port', 'Nicht gesetzt')}")
        print(f"   - TLS: {config.get('mail_use_tls', 'Nicht gesetzt')}")
        print(f"   - Benutzername: {config.get('mail_username', 'Nicht gesetzt')}")
        print(f"   - Passwort: {'Gesetzt' if config.get('mail_password') else 'Nicht gesetzt'}")
        print(f"   - Authentifizierung: {config.get('use_auth', True)}")
    else:
        print("   ❌ Keine E-Mail-Konfiguration gefunden!")
        return
    
    print()
    
    # 2. Teste E-Mail-Konfiguration
    print("2. E-Mail-Konfiguration testen:")
    if config and config.get('enabled') and config.get('mail_username') and config.get('mail_password'):
        success, message = test_email_config(config)
        if success:
            print(f"   ✅ E-Mail-Test erfolgreich: {message}")
        else:
            print(f"   ❌ E-Mail-Test fehlgeschlagen: {message}")
    else:
        print("   ⚠️  E-Mail-Konfiguration unvollständig - Test übersprungen")
    
    print()
    
    # 3. Prüfe Datenbank-E-Mail-Konfiguration
    print("3. Datenbank-E-Mail-Konfiguration:")
    db_config = mongodb.find_one('email_config', {'_id': 'email_config'})
    if db_config:
        print("   ✅ E-Mail-Konfiguration in Datenbank gefunden")
        print(f"   - Aktiviert: {db_config.get('enabled', False)}")
        print(f"   - Server: {db_config.get('mail_server', 'Nicht gesetzt')}")
        print(f"   - Benutzername: {db_config.get('mail_username', 'Nicht gesetzt')}")
    else:
        print("   ❌ Keine E-Mail-Konfiguration in Datenbank gefunden")
    
    print()
    
    # 4. Empfehlungen
    print("4. Empfehlungen zur Behebung:")
    if not config or not config.get('enabled'):
        print("   - Aktivieren Sie das E-Mail-System in den Admin-Einstellungen")
    if not config or not config.get('mail_username') or not config.get('mail_password'):
        print("   - Konfigurieren Sie SMTP-Anmeldedaten in den E-Mail-Einstellungen")
    if config and config.get('enabled') and config.get('mail_username') and config.get('mail_password'):
        print("   - Das Encoding-Problem wurde in der E-Mail-Utils behoben")
        print("   - Starten Sie die Anwendung neu, um die Änderungen zu aktivieren")
    
    print("\n=== DIAGNOSE ABGESCHLOSSEN ===")

if __name__ == "__main__":
    diagnose_email_problem() 