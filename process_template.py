#!/usr/bin/env python3
"""
Template-Verarbeitung für docker-compose.yml
Ersetzt Platzhalter in der Template-Datei mit tatsächlichen Werten
"""

import sys
import os
import random
import string
import subprocess
import shutil

def generate_random_key(length=8):
    """Generiert einen zufälligen Schlüssel"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def process_template(template_file, output_file, variables):
    """Verarbeitet das Template und ersetzt Platzhalter"""
    try:
        # Template lesen
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Platzhalter ersetzen
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            content = content.replace(placeholder, str(value))
        
        # Ausgabedatei schreiben
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ Template verarbeitet: {output_file}")
        return True
        
    except Exception as e:
        print(f"✗ Fehler beim Verarbeiten des Templates: {e}")
        return False

def setup_css_build():
    """Richtet CSS-Build ein"""
    try:
        # Prüfe ob Node.js und npm verfügbar sind
        if not shutil.which('node') or not shutil.which('npm'):
            print("⚠️  Node.js/npm nicht gefunden. Versuche Fallback...")
            return copy_existing_css()
        
        # Stelle sicher, dass die Verzeichnisstruktur existiert
        css_dir = "app/static/css"
        os.makedirs(css_dir, exist_ok=True)
        
        # Kopiere input.css falls nicht vorhanden
        input_css = os.path.join(css_dir, "input.css")
        if not os.path.exists(input_css):
            source_input_css = os.path.join("..", css_dir, "input.css")
            if os.path.exists(source_input_css):
                shutil.copy2(source_input_css, input_css)
                print("✓ input.css kopiert")
            else:
                print("⚠️  input.css nicht gefunden")
                return copy_existing_css()
        
        # Installiere npm-Abhängigkeiten
        print("📦 Installiere npm-Abhängigkeiten...")
        npm_install = subprocess.run(['npm', 'install'], capture_output=True, text=True)
        if npm_install.returncode != 0:
            print(f"⚠️  npm install fehlgeschlagen: {npm_install.stderr}")
            return copy_existing_css()
        
        # Generiere CSS
        print("🎨 Generiere CSS...")
        npm_build = subprocess.run(['npm', 'run', 'build:css'], capture_output=True, text=True)
        if npm_build.returncode != 0:
            print(f"⚠️  CSS-Generierung fehlgeschlagen: {npm_build.stderr}")
            return copy_existing_css()
        
        # Prüfe ob die CSS-Dateien tatsächlich generiert wurden
        if not os.path.exists(os.path.join(css_dir, "main.css")):
            print("⚠️  Keine CSS-Dateien gefunden nach der Generierung. Versuche Fallback...")
            return copy_existing_css()
            
        print("✓ CSS erfolgreich generiert")
        return True
        
    except Exception as e:
        print(f"⚠️  CSS-Setup fehlgeschlagen: {e}")
        return copy_existing_css()

def copy_existing_css():
    """Kopiert bestehende CSS-Dateien"""
    try:
        # Mögliche Quellverzeichnisse für CSS-Dateien
        source_dirs = [
            "../app/static/css",  # Relatives Verzeichnis
            "app/static/css",     # Lokales Verzeichnis
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "../app/static/css")  # Absoluter Pfad
        ]
        
        target_css_dir = "app/static/css"
        css_copied = False
        
        # Versuche jedes mögliche Quellverzeichnis
        for source_dir in source_dirs:
            if os.path.exists(source_dir) and os.path.isdir(source_dir):
                # Stelle sicher, dass das Zielverzeichnis existiert
                os.makedirs(target_css_dir, exist_ok=True)
                
                # Kopiere alle CSS-Dateien
                for file in os.listdir(source_dir):
                    if file.endswith('.css'):
                        source_file = os.path.join(source_dir, file)
                        target_file = os.path.join(target_css_dir, file)
                        shutil.copy2(source_file, target_file)
                        print(f"✓ CSS-Datei kopiert: {file}")
                        css_copied = True
                
                if css_copied:
                    print(f"✓ CSS-Dateien erfolgreich kopiert aus {source_dir}")
                    return True
        
        if not css_copied:
            print("⚠️  Keine CSS-Dateien in den Quellverzeichnissen gefunden")
            return False
            
    except Exception as e:
        print(f"⚠️  Fehler beim Kopieren der CSS-Dateien: {e}")
        return False

def copy_application_files():
    """Kopiert Anwendungsdateien"""
    try:
        # Kopiere app-Verzeichnis
        if os.path.exists('../app'):
            # Erstelle eine Liste von Dateien/Verzeichnissen, die übersprungen werden sollen
            ignore_patterns = shutil.ignore_patterns('*.pyc', '__pycache__', '*.log')
            shutil.copytree('../app', 'app', dirs_exist_ok=True, ignore=ignore_patterns)
            print("✓ App-Verzeichnis kopiert")
        
        # Kopiere Konfigurationsdateien
        files_to_copy = [
            'requirements.txt',
            'package.json',
            'tailwind.config.js',
            'postcss.config.js',  # Wichtig für Tailwind
            'input.css'  # Kopiere auch input.css in das Hauptverzeichnis
        ]
        
        for file in files_to_copy:
            source_file = f'../{file}'
            if os.path.exists(source_file):
                shutil.copy2(source_file, '.')
                print(f"✓ {file} kopiert")
            else:
                print(f"⚠️  {file} nicht gefunden")
        
        return True
        
    except Exception as e:
        print(f"✗ Fehler beim Kopieren der Dateien: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Verwendung: python process_template.py <container_name> [app_port] [mongo_port] [mongo_express_port] [mongo_user] [mongo_pass] [data_dir]")
        sys.exit(1)
    
    # Standardwerte
    container_name = sys.argv[1]
    app_port = sys.argv[2] if len(sys.argv) > 2 else "5000"
    mongo_port = sys.argv[3] if len(sys.argv) > 3 else "27017"
    mongo_express_port = sys.argv[4] if len(sys.argv) > 4 else "8081"
    mongo_user = sys.argv[5] if len(sys.argv) > 5 else "admin"
    mongo_pass = sys.argv[6] if len(sys.argv) > 6 else "scandy123"
    data_dir = sys.argv[7] if len(sys.argv) > 7 else "./scandy_data"
    
    # Variablen für Template
    variables = {
        'CONTAINER_NAME': container_name,
        'APP_PORT': app_port,
        'MONGO_PORT': mongo_port,
        'MONGO_EXPRESS_PORT': mongo_express_port,
        'MONGO_USER': mongo_user,
        'MONGO_PASS': mongo_pass,
        'DATA_DIR': data_dir,
        'RANDOM_KEY': generate_random_key()
    }
    
    # Template verarbeiten
    template_file = "docker-compose.template.yml"
    output_file = "docker-compose.yml"
    
    if not os.path.exists(template_file):
        print(f"✗ Template-Datei nicht gefunden: {template_file}")
        sys.exit(1)
    
    if process_template(template_file, output_file, variables):
        print("✓ Docker Compose Datei erfolgreich erstellt!")
        print(f"Container Name: {container_name}")
        print(f"App Port: {app_port}")
        print(f"MongoDB Port: {mongo_port}")
        print(f"Mongo Express Port: {mongo_express_port}")
        print(f"Datenverzeichnis: {data_dir}")
        
        # Kopiere Anwendungsdateien
        if copy_application_files():
            # Setup CSS-Build
            setup_css_build()
        else:
            print("⚠️  Anwendungsdateien konnten nicht kopiert werden")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main() 