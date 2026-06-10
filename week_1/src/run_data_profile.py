import sqlite3
import logging
from pathlib import Path


def quality_check(data):
    missing_field = not ((data.get("description") != "NULL") and (data.get("job_title") != "NULL") and (data.get("company") != "NULL"))
    desc = str(data.get("description", ""))
    special_char_count = 0
    for ch in desc:
        if ch in "!#":
            special_char_count += 1

    low_quality = (
        len(desc) < 100
        or missing_field
        or special_char_count > 10
    )
    if low_quality:
        return "LOW"
    return "HIGH"


def run_data_profile(db_path):
    i = 0
    total = 0
    shortest_desc = 9999999
    shortest_id = ''
    shortest_id_title = ''
    longest_desc = 0
    longest_id = ''
    longest_id_title = ''
    no_title = 0
    no_company = 0
    no_desc = 0
    average = 0

    try:
        full_db_path = Path(db_path).resolve()
        # ensure file exists
        with open(full_db_path, 'r'):
            conn = sqlite3.connect(full_db_path)
    except FileNotFoundError:
        logging.error("❌ Database not found at: %s", str(db_path))
        return

    # use Row factory so we can access columns by name
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1) Label each record in `jobs` with a quality tag
    try:
        cursor.execute("SELECT source_id, job_title, company, description FROM jobs")
        rows = cursor.fetchall()
    except sqlite3.Error:
        rows = []

    for item in rows:
        data = {
            "source_id": item["source_id"],
            "job_title": item["job_title"],
            "company": item["company"],
            "description": item["description"],
        }
        q = quality_check(data)
        try:
            cursor.execute("UPDATE jobs SET quality = ? WHERE source_id = ?", (q, data["source_id"]))
        except sqlite3.Error as e:
            logging.error("Failed to update quality for %s: %s", data["source_id"], e)
    conn.commit()

    try:
        cursor.execute("INSERT OR IGNORE INTO jobs_quarantine SELECT * FROM jobs WHERE quality = 'LOW';")
        cursor.execute("DELETE FROM jobs WHERE quality = 'LOW';")
    except sqlite3.Error as e:
        logging.error("Error during quarantine move: %s", e)
    conn.commit()

    cursor.execute("SELECT * FROM jobs UNION ALL SELECT * FROM jobs_quarantine")
    for item in cursor.fetchall():
        length = len(item["description"])
        if length > longest_desc:
            longest_desc = length
            longest_id = item["source_id"]
            longest_id_title = item["job_title"]
        elif length < shortest_desc:
            shortest_desc = length
            shortest_id = item["source_id"]
            shortest_id_title = item["job_title"]
        total += length
        if item["job_title"] == "NULL":
            no_title += 1
        if item["company"] == "NULL":
            no_company += 1
        if item ["description"] == "NULL":
            no_desc += 1
        i += 1
    average = int(total / i) if i else 0
    print("--- 🔍 DATA QUALITY REPORT ---")
    print(f"📈 Total Records: {i}")
    print(f"❓ Missing Values -> job_title: {no_title}, company: {no_company}, description: {no_desc}")
    print(f"📝 Avg Description Length: {average} chars")
    print(f"⚠️  Shortest Description: {shortest_desc} chars\n↳ source_id: {shortest_id} | job_title: {shortest_id_title}")
    print(f"🚨 Longest Description: {longest_desc} chars\n↳ source_id: {longest_id} | job_title: {longest_id_title}")

    conn.close()