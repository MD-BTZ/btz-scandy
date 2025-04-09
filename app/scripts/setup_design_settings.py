from app import create_app
from app.models.database import Database

def setup_design_settings():
    app = create_app()
    with app.app_context():
        try:
            with Database.get_db() as conn:
                cursor = conn.cursor()
                # Setze BTZ-Blau als Standard
                settings = {
                    'primary_color': '220 35% 45%',
                    'secondary_color': '220 35% 35%',
                    'accent_color': '220 35% 55%'
                }
                
                # Lösche alte Einstellungen
                cursor.execute("DELETE FROM settings WHERE key LIKE '%color%'")
                
                # Füge neue Standardeinstellungen hinzu
                for key, value in settings.items():
                    cursor.execute("""
                        INSERT INTO settings (key, value)
                        VALUES (?, ?)
                    """, (key, value))
                    
                conn.commit()
                print("Design-Einstellungen erfolgreich initialisiert")
        except Exception as e:
            print(f"Fehler beim Einrichten der Design-Einstellungen: {e}")

if __name__ == "__main__":
    setup_design_settings()