import sqlite3
import os

DB_PATH = r"c:\Users\atona\Documents\GitHub\model\data\asystent.db"

if not os.path.exists(DB_PATH):
    print(f"Baza nie istnieje w: {DB_PATH}")
else:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(pytania)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Kolumny w tabeli 'pytania': {columns}")
    conn.close()
