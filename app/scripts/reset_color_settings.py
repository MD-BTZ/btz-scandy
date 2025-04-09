from app import create_app
from app.models.database import Database

def reset_color_settings():
    app = create_app()
    with app.app_context():
        try:
            with Database.get_db() as conn:
                cursor = conn.cursor()
                # Lösche alle Farbeinstellungen
                cursor.execute("""
                    DELETE FROM settings 
                    WHERE key IN ('primary_color', 'secondary_color', 'accent_color')
                """)
                conn.commit()
                print("Farbeinstellungen erfolgreich zurückgesetzt")
        except Exception as e:
            print(f"Fehler beim Zurücksetzen der Farbeinstellungen: {e}")

if __name__ == "__main__":
    reset_color_settings() 