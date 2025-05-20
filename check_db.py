from app.models.ticket_db import TicketDatabase
db = TicketDatabase()
print("Verwendeter Pfad:", db.db_path)
import sqlite3
conn = sqlite3.connect(db.db_path)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tabellen in der Datenbank:")
for row in cursor.fetchall():
    print(row[0])
conn.close()