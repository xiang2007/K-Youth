import sqlite3
from pathlib import Path

def data_profiler(row):
    i = 0
    total = 0
    shortest_desc = 0
    shortest_id = ''
    shortest_id_title = ''
    longest_desc = 0
    longest_id = ''
    longest_id_title = ''
    no_title = 0
    no_company = 0
    no_desc = 0
    average = 0

    for item in row:
        length = len(row["description"])
        if length > longest_desc:
            longest_desc = length
            longest_id = row["source_id"]
        elif length < shortest_desc:
            shortest_desc = length
            shortest_id = row["source_id"]
        total += length
        i += 1
        if row["job_title"] == "NULL":
            no_title += 1
        if row["company"] == "NULL":
            no_company += 1
        if row["description"] == "NULL":
            no_desc += 1
    average = total / i

    print("--- 🔍 DATA QUALITY REPORT ---")
    print(f"📈 Total Records: {total}")
    print(f"❓ Missing Values -> job_title: {no_title}, company: {no_company}, description: {no_desc}")
    print(f"📝 Avg Description Length: {average} chars")
    print(f"""⚠️  Shortest Description: {shortest_desc} chars
              ↳ source_id: {shortest_id} | job_title: {shortest_id_title}
        """)
    print(f"""🚨 Longest Description: {longest_desc} chars
               ↳ source_id: {longest_id} | job_title: {longest_id_title}
        """)
    return



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
        with open(full_db_path, 'r'):
            conn = sqlite3.connect(full_db_path)
    except FileNotFoundError:
        print(f"❌ Database not found at {db_path}")
        return
    cursor = conn.cursor()
    cursor.row_factory = sqlite3.Row
    cursor.execute("SELECT * FROM jobs")
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
    average = int(total / i)
    print("--- 🔍 DATA QUALITY REPORT ---")
    print(f"📈 Total Records: {i}")
    print(f"❓ Missing Values -> job_title: {no_title}, company: {no_company}, description: {no_desc}")
    print(f"📝 Avg Description Length: {average} chars")
    print(f"⚠️  Shortest Description: {shortest_desc} chars\n↳ source_id: {shortest_id} | job_title: {shortest_id_title}")
    print(f"🚨 Longest Description: {longest_desc} chars\n↳ source_id: {longest_id} | job_title: {longest_id_title}")

    conn.close()