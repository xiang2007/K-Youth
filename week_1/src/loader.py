from pathlib import Path
import sqlite3
import json

def load_json_to_database(input_dir, output_dir):
    connection = sqlite3.connect(Path(output_dir) / "jobs.db")
    cursor = connection.cursor()
    infile = Path(input_dir).name

    try:
        with open(input_dir, 'r') as file:
            data = json.load(file)
    except PermissionError:
        print(f"Unable to openfile: {infile}")
        return False
    cursor.execute(
        "SELECT EXISTS(SELECT 1 FROM jobs WHERE source_id=?)", (data["source_id"],)
        )
    if cursor.fetchone()[0]:
        print(f"⏭️ Skipped (duplicate): {infile}")
        connection.close()
        return False
    try:
        cursor.execute(
        """
            INSERT INTO jobs (source_id, job_title, company, description)
            VALUES (?, ?, ?, ?)
        """,
            (data["source_id"], data["job_title"], data["company"], data["description"]),
        )
        connection.commit()
    except Exception as e:
        connection.rollback()
        print(f"Error {e} occur at: {infile}")
        return False
    print(f"✅ Inserted: {infile}")
    connection.close()
    return True

def load_all_jsons(input_dir, output_dir):
    try:
        FullInfileList = [item for item in Path(input_dir).iterdir()]
    except FileNotFoundError:
        print(f"Directory: {input_dir} not found")
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
            source_id text NOT NULL,
            job_title text NOT NULL,
            company text NOT NULL,
            description text NOT NULL,
            tech_stack text
            );
        """
    )
    connection.commit()
    for file in FullInfileList:
        if load_json_to_database(file, output_dir):
            inserted += 1
        else:
            skipped += 1
    connection.close()
    print("\n📊 Gold Summary:")
    print(f"Total: {inserted + skipped} | Inserted: {inserted} | Skipped: {skipped}\n")