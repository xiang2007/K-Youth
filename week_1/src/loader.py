import sqlite3
import json
import logging
from pathlib import Path
from hashlib import sha256

def get_data_from_json(input_dir, infile):
    try:
        with open(input_dir, 'r') as file:
            data = json.load(file)
    except (PermissionError) as e:
        logging.error(f"Unable to open/read json: {infile} Reason: {e}")
        return None

    hash_input = f'{data.get("job_title", "")}|{data.get("company", "")}|{data.get("description", "")}'
    content_hash = sha256(hash_input.encode()).hexdigest()

    return {
        "source_id": str(data.get("source_id", "")),
        "job_title": str(data.get("job_title", "")),
        "company": str(data.get("company", "")),
        "description": str(data.get("description", "")),
        "content_hash": content_hash,
    }

def load_json_to_database(input_dir, connection, cursor):
    infile = Path(input_dir).name
    data = get_data_from_json(input_dir, infile)
    if data is None:
        return False

    cursor.execute(
        """
        SELECT 1 FROM jobs WHERE source_id = ?
        UNION
        SELECT 1 FROM jobs_quarantine WHERE source_id = ?
        LIMIT 1
        """, 
        (data["source_id"], data["source_id"])
    )
    if cursor.fetchone():
        logging.warning(f"⏭️ Skipped (duplicate): {infile}")
        return False
    try:
        cursor.execute(
        """
            INSERT INTO jobs (source_id, job_title, company, description, content_hash)
            VALUES (?, ?, ?, ?, ?)
        """,
            (data["source_id"], data["job_title"], data["company"], data["description"], data["content_hash"])
        )
    except Exception as e:
        logging.error(f"Error at: {str(infile)} Reason: {str(e)}")
        return False

    logging.info(f"✅ Inserted: {infile}")
    return True

def load_all_jsons(input_dir, output_dir):
    try:
        FullInfileList = [item for item in Path(input_dir).iterdir()]
    except FileNotFoundError:
        logging.error(f"Directory not found: {input_dir}")
        return

    inserted = 0
    skipped = 0
    Path(output_dir).mkdir(exist_ok=True)
    db_path = Path(output_dir) / "jobs.db"
    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
                CREATE TABLE IF NOT EXISTS jobs(
                source_id text PRIMARY KEY,
                job_title text,
                company text,
                description text,
                content_hash TEXT,
                quality TEXT
            );
            """
        )
        cursor.execute(
            """
                CREATE TABLE IF NOT EXISTS jobs_quarantine(
                source_id TEXT PRIMARY KEY,
                job_title TEXT,
                company TEXT,
                description TEXT,
                content_hash TEXT,
                quality TEXT
            );
            """
        )
        for file in FullInfileList:
            if load_json_to_database(file, connection, cursor):
                inserted += 1
            else:
                skipped += 1

    print("\n📊 Gold Summary:")
    print(f"Total: {inserted + skipped} | Inserted: {inserted} | Skipped: {skipped}\n")