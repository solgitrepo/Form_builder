import sqlite3
import json
from datetime import datetime

def view_database():
    conn = sqlite3.connect('formbuilder.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("\n=== Database Tables ===")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for table in tables:
        print(f"\n--- {table[0]} Table ---")
        cursor.execute(f"SELECT * FROM {table[0]}")
        rows = cursor.fetchall()
        for row in rows:
            print(dict(row))
    
    conn.close()

if __name__ == '__main__':
    view_database() 