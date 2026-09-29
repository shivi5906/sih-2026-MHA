import psycopg2, sqlite3
from datetime import datetime
pg = psycopg2.connect('postgresql://vaultx:vaultx-dev@localhost:5432/vaultx')
pg.autocommit = True
cur = pg.cursor()
cur.execute("INSERT INTO cases (id, number, title, status, created_at, updated_at) VALUES ('CYBER-2026-001', 'CYBER-2026-001', 'Bitfinex Hack 2016 (Replay)', 'open', %s, %s) ON CONFLICT DO NOTHING", (datetime.now(), datetime.now()))
cur.execute("INSERT INTO investigation_runs (id, case_id, status, manifest, created_at, updated_at) VALUES ('run-001', 'CYBER-2026-001', 'completed', '{\"banner\":\"SNAPSHOT / CASE REPLAY\",\"calibrated\":false}', %s, %s) ON CONFLICT DO NOTHING", (datetime.now(), datetime.now()))

sqlite = sqlite3.connect('vaultx.db')
sqlite.row_factory = sqlite3.Row
cur_sqlite = sqlite.cursor()

cur_sqlite.execute("SELECT * FROM transactions WHERE case_id='CYBER-2026-001'")
count = 0
for row in cur_sqlite.fetchall():
    try:
        cur.execute("INSERT INTO transactions (id, case_id, payload) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", (row['id'], row['case_id'], row['payload']))
        count += 1
    except Exception as e: print(e)
print(f'Inserted {count} transactions.')
print('Mock case restored!')
