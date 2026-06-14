from pathlib import Path
import sqlite3

def fetch_next_5_row(cursor : sqlite3.Cursor) -> list:
    rows = cursor.execute("""
        SELECT description
        FROM jobs
        WHERE processed = 0
        ORDER BY id
        LIMIT 5
    """).fetchall()
    return rows


def tag_data(db_url : str):
    fulldburl = Path(db_url).resolve()

    if not fulldburl.exists:
        print(f"db_url: {db_url} not exist")
        return

    with sqlite3.connect(fulldburl) as conn:
        cs = conn.cursor()

        res = fetch_next_5_row(cs)
        print(res)
        res = fetch_next_5_row(cs)
        print(res)



