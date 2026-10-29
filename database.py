import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(os.getenv('SQLITE_PATH', 'data/ocr_history.db'))

@contextmanager
def connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def initialize():
    with connection() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS ocr_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            raw_text TEXT NOT NULL,
            total_price REAL NOT NULL,
            average_price REAL NOT NULL,
            row_count INTEGER NOT NULL
        )''')
        con.execute('''CREATE TABLE IF NOT EXISTS ocr_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            history_id INTEGER NOT NULL REFERENCES ocr_history(id) ON DELETE CASCADE,
            row_number INTEGER NOT NULL,
            oil_name TEXT NOT NULL,
            dated_brent REAL NOT NULL,
            alpha REAL NOT NULL,
            price REAL NOT NULL
        )''')
        con.execute('CREATE INDEX IF NOT EXISTS idx_details_history ON ocr_details(history_id)')

def save(filename, sha256, raw_text, df):
    with connection() as con:
        cur = con.execute('''INSERT INTO ocr_history(filename,sha256,raw_text,total_price,average_price,row_count)
            VALUES(?,?,?,?,?,?)''', (filename,sha256,raw_text,float(df['Harga (US$/bbl)'].sum()),
            float(df['Harga (US$/bbl)'].mean()),len(df)))
        hid = cur.lastrowid
        con.executemany('''INSERT INTO ocr_details(history_id,row_number,oil_name,dated_brent,alpha,price)
            VALUES(?,?,?,?,?,?)''', [(hid,int(r['No']),str(r['Jenis Minyak Mentah Utama']),
            float(r['Dated Brent (US$/bbl)']),float(r['Alpha (US$/bbl)']),float(r['Harga (US$/bbl)']))
            for _,r in df.iterrows()])
        return hid

def histories(search=''):
    with connection() as con:
        return [dict(r) for r in con.execute('''SELECT id,filename,created_at,row_count,total_price,average_price
            FROM ocr_history WHERE filename LIKE ? ORDER BY id DESC''', ('%'+search+'%',)).fetchall()]

def detail(hid):
    with connection() as con:
        header=con.execute('SELECT * FROM ocr_history WHERE id=?',(hid,)).fetchone()
        rows=con.execute('''SELECT row_number AS "No",oil_name AS "Jenis Minyak Mentah Utama",
            dated_brent AS "Dated Brent (US$/bbl)",alpha AS "Alpha (US$/bbl)",price AS "Harga (US$/bbl)"
            FROM ocr_details WHERE history_id=? ORDER BY row_number''',(hid,)).fetchall()
        return (dict(header) if header else None,[dict(r) for r in rows])

def delete(hid):
    with connection() as con:
        con.execute('DELETE FROM ocr_history WHERE id=?',(hid,))
