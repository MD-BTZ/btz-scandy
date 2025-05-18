import sqlite3

# Pfad zur Ticket-Datenbank
DB_PATH = "app/database/tickets.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(users);")
columns = cursor.fetchall()
print("Spalten der Tabelle 'users':")
for col in columns:
    print(col)
conn.close() 