from flask_login import UserMixin
from .database import Database

class User(UserMixin):
    def __init__(self, id, username, is_admin=False):
        self.id = id
        self.username = username
        self.is_admin = is_admin

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    @staticmethod
    def get(user_id):
        if not user_id:
            return None
        try:
            with Database.get_db() as conn:
                user = conn.execute(
                    'SELECT id, username, is_admin FROM users WHERE id = ?', 
                    (user_id,)
                ).fetchone()
                
                if user:
                    return User(
                        id=user['id'],
                        username=user['username'],
                        is_admin=bool(user['is_admin'])
                    )
        except Exception as e:
            print(f"Fehler beim Laden des Users: {e}")
        return None

    # Alias für Flask-Login Kompatibilität
    get_by_id = get