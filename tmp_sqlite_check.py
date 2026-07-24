import os
import sqlite3

path = 'world_cup.db'
print('exists', os.path.exists(path))
conn = sqlite3.connect(path)
cur = conn.cursor()
print('tables', cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall())
for table in ['world_cups', 'teams', 'matches', 'standings']:
    try:
        print(table, cur.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0])
    except Exception as exc:
        print(table, 'ERR', exc)
conn.close()
