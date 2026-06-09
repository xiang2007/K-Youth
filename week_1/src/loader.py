from pathlib import Path
import sqlite3
import json
import logging
from hashlib import sha256

def quality_check(data):
    missing_field = 0
    special_char_count = 0

    missing_field = not ((data["description"] != "NULL") and (data["job_title"] != "NULL") and (data["company"] != "NULL"))
    
    desc = str(data["description"])
    special_char_count = 0
    for i in range(len(desc)):
        if desc[i] in "!#":
            special_char_count += 1

    low_quality = (
        len(desc) < 100
        or missing_field
        or special_char_count > 10
    )
    if low_quality:
        return "LOW"
    return "HIGH"



def load_json_to_database(input_dir, output_dir):
    connection = sqlite3.connect(Path(output_dir) / "jobs.db")
    cursor = connection.cursor()
    infile = Path(input_dir).name

    try:
        with open(input_dir, 'r') as file:
            data = json.load(file)
    except PermissionError:
        logging.error(f"Unable to openfile: {infile}")
        return False

    hash_input = f'{data["job_title"]}|{data["company"]}|{data["description"]}' # basic hashing
    content_hash = sha256(hash_input.encode()).hexdigest()

    quality = quality_check(data)

    cursor.execute(
        "SELECT 1 FROM jobs WHERE content_hash=? AND source_id=? LIMIT 1", (content_hash, data["source_id"])
        )
    if cursor.fetchone():
        logging.warning(f"⏭️ Skipped (duplicate): {infile}")
        connection.close()
        return False
    try:
        cursor.execute(
        """
            INSERT INTO jobs (source_id, job_title, company, description, content_hash, quality)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (data["source_id"], data["job_title"], data["company"], data["description"], str(content_hash), quality)
        )
        connection.commit()
    except Exception as e:
        connection.rollback()
        logging.error(f"Error at: {str(infile)} Reason: {str(e)}")
        return False

    logging.info(f"✅ Inserted: {infile}")
    connection.close()
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
    connection = sqlite3.connect(db_path)
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
            source_id text PRIMARY KEY,
            job_title text,
            company text,
            description text,
            content_hash TEXT,
            quality TEXT
        );
        """
    )
    connection.commit()
    for file in FullInfileList:
        if load_json_to_database(file, output_dir):
            inserted += 1
        else:
            skipped += 1

    cursor.execute("INSERT INTO jobs_quarantine SELECT * FROM jobs WHERE quality = 'LOW';")
    cursor.execute("DELETE FROM jobs WHERE quality = 'LOW';")
    connection.commit()
    connection.close()
    print("\n📊 Gold Summary:")
    print(f"Total: {inserted + skipped} | Inserted: {inserted} | Skipped: {skipped}\n")