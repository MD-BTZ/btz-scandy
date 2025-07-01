#!/usr/bin/env python3
"""
Sicherheitsupdate-Skript für Scandy
Aktualisiert alle kritischen Abhängigkeiten auf sichere Versionen
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Führt einen Befehl aus und gibt Status zurück"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} erfolgreich")
            return True
        else:
            print(f"❌ {description} fehlgeschlagen: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Fehler bei {description}: {e}")
        return False

def main():
    print("🔒 Scandy Sicherheitsupdate gestartet")
    print("=" * 50)
    
    # Prüfe ob wir in der richtigen Umgebung sind
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt nicht gefunden. Bitte im Projektverzeichnis ausführen.")
        sys.exit(1)
    
    # Aktualisiere Python-Abhängigkeiten
    print("\n📦 Python-Abhängigkeiten aktualisieren:")
    run_command("pip install --upgrade pip", "Pip aktualisieren")
    run_command("pip install -r requirements.txt --upgrade", "Requirements aktualisieren")
    
    # Aktualisiere npm-Abhängigkeiten
    if os.path.exists("package.json"):
        print("\n📦 Node.js-Abhängigkeiten aktualisieren:")
        run_command("npm install -g npm@latest", "NPM aktualisieren")
        run_command("npm install", "NPM-Abhängigkeiten installieren")
        run_command("npm audit fix", "NPM-Sicherheitslücken beheben")
        run_command("npm run build:css", "CSS neu kompilieren")
    
    # Prüfe auf verbleibende Sicherheitslücken
    print("\n🔍 Sicherheitsprüfung:")
    run_command("pip list --outdated", "Veraltete Python-Pakete anzeigen")
    
    if os.path.exists("package.json"):
        run_command("npm audit", "NPM-Sicherheitsprüfung")
    
    print("\n✅ Sicherheitsupdate abgeschlossen!")
    print("\n💡 Nächste Schritte:")
    print("1. Testen Sie die Anwendung lokal")
    print("2. Bauen Sie das Docker-Image neu: docker build -t woschj/scandy:main .")
    print("3. Pushen Sie das neue Image: docker push woschj/scandy:main")

if __name__ == "__main__":
    main() 