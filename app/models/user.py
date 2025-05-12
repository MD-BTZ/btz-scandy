from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.database import Database
import logging

logger = logging.getLogger(__name__)

class User(UserMixin):
    """Benutzermodell für Flask-Login und Datenbankinteraktion."""

    def __init__(self, id, username, password_hash, role, is_active, email=None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role # admin, mitarbeiter, anwender
        self._db_is_active = bool(is_active) # Intern speichern
        self.email = email

    # Flask-Login erfordert die `is_active`-Eigenschaft
    @property
    def is_active(self):
        """Gibt den Status aus der Datenbank zurück."""
        return self._db_is_active

    # Optional: Eigenschaft für bessere Lesbarkeit im Code
    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_mitarbeiter(self):
        # Admins sind implizit auch Mitarbeiter in Bezug auf Rechte
        return self.role == 'admin' or self.role == 'mitarbeiter'

    def set_password(self, password):
        """Generiert einen Hash für das gegebene Passwort."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Prüft, ob das gegebene Passwort mit dem Hash übereinstimmt."""
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get_by_username(username):
        """Lädt einen Benutzer anhand seines Benutzernamens aus der DB."""
        sql = "SELECT * FROM users WHERE username = ?"
        row = Database.query(sql, [username], one=True)
        if row:
            # Erstellt ein User-Objekt aus der Datenbankzeile
            return User(id=row['id'], username=row['username'], password_hash=row['password_hash'], 
                        role=row['role'], is_active=row.get('is_active', True), email=row.get('email'))
        return None

    @staticmethod
    def get_by_id(user_id):
        """Lädt einen Benutzer anhand seiner ID (für Flask-Login user_loader)."""
        sql = "SELECT * FROM users WHERE id = ?"
        try:
            # Stelle sicher, dass user_id ein Integer ist
            row = Database.query(sql, [int(user_id)], one=True)
            if row:
                return User(id=row['id'], username=row['username'], password_hash=row['password_hash'], 
                            role=row['role'], is_active=row.get('is_active', True), email=row.get('email'))
        except ValueError:
            logger.error(f"Ungültige user_id empfangen: {user_id}")
            return None
        except Exception as e:
            logger.error(f"Fehler beim Laden von User mit ID {user_id}: {e}", exc_info=True)
            return None
        return None

    @staticmethod
    def create(username, password, role, email=None, is_active=True):
        """Erstellt einen neuen Benutzer in der Datenbank."""
        if role not in ['admin', 'mitarbeiter', 'anwender']:
            raise ValueError("Ungültige Rolle angegeben.")
        if User.get_by_username(username):
            raise ValueError(f"Benutzername '{username}' existiert bereits.")
        if email and User.get_by_email(email):
             raise ValueError(f"E-Mail '{email}' existiert bereits.")

        hashed_password = generate_password_hash(password)
        sql = """INSERT INTO users (username, email, password_hash, role, is_active)
                 VALUES (?, ?, ?, ?, ?)"""
        try:
            Database.query(sql, [username, email, hashed_password, role, is_active])
            return User.get_by_username(username)
        except Exception as e:
            logger.error(f"Fehler beim Erstellen von Benutzer {username}: {e}", exc_info=True)
            return None
            
    @staticmethod
    def get_by_email(email):
        """Lädt einen Benutzer anhand seiner E-Mail-Adresse."""
        if not email: 
            return None
        sql = "SELECT * FROM users WHERE email = ?"
        row = Database.query(sql, [email], one=True)
        if row:
            return User(id=row['id'], username=row['username'], password_hash=row['password_hash'], 
                        role=row['role'], is_active=row.get('is_active', True), email=row['email'])
        return None

    # Beispiel für eine Methode zum Aktualisieren (kann erweitert werden)
    def save(self):
        """Speichert Änderungen am Benutzerobjekt in der DB."""
        sql = """UPDATE users SET 
                 username = ?, email = ?, password_hash = ?, role = ?, is_active = ?
                 WHERE id = ?"""
        try:
            Database.query(sql, [self.username, self.email, self.password_hash, self.role, self.is_active, self.id])
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern von User {self.username}: {e}", exc_info=True)
            return False