import sqlite3
DB_PATH = r"c:\Users\atona\Documents\GitHub\model\data\asystent.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM pytania")
print(f"Liczba wpisów w tabeli 'pytania': {cursor.fetchone()[0]}")
conn.close()
