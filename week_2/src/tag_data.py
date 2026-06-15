from pathlib import Path
from typing import Optional, List, Any
from src.prompt_model import prompt_model
import sqlite3

def fetch_next_batch(cursor: sqlite3.Cursor, batch_size: int, offset: int) -> Optional[List[Any]]:
    cursor.execute(
        "SELECT source_id, description FROM jobs ORDER BY source_id LIMIT ? OFFSET ?",
        (batch_size, offset)
    )
    batch = cursor.fetchall()

    if not batch:
        return None

    return batch


def tag_data(db_url : str):
    fulldburl = Path(db_url).resolve()

    if not fulldburl.exists:
        print(f"db_url: {db_url} not exist")
        return

    with sqlite3.connect(fulldburl) as conn:
        cs = conn.cursor()

    curr_offset = 0
    batch_size = 5
    db_list = []
    while True:
        batch = fetch_next_batch(cs, batch_size, curr_offset)
        if not batch:
            break
        curr_offset += batch_size
        for item in batch:
            db_list.append(item)
    job_description = db_list[5][1]
    prompt = f"""You are an advanced technical data extraction tool. Your job is to extract the tech stack from the job description provided below.

    <job_description>
    {job_description}
    </job_description>

    <extraction_checklist>
    Scan the text thoroughly for:
    - Programming languages
    - Databases
    - Cloud Platforms & Infrastructure
    </extraction_checklist>

    <constraints>
    - Extract EVERY explicit technical item mentioned. Do not omit anything.
    - Do NOT extract soft skills, administrative processes, or generic categories.
    - Do NOT explain or make up technical skills.
    - CRITICAL: If absolutely NO technical stack items from the checklist are found in the text, output exactly the word "None".
    </constraints>

    <formatting_rules>
    - Only output one line.
    - Output ONLY the final list as a raw, comma-separated string without space (or the single word "None").
    - Do not wrap the final output in conversational framing, code blocks, or pleasantries.
    - Only return a empty line if nothing is found
    - Do NOT give any examples
    - If the actual job description text was not given, just return None
    - Do not give any notes
    - Do not include brackets '()'
    - Do not use the word "or", "+'
    - Dont use Version control (Git) use Git instead
    - Dont include terms "no", "bad"
    </formatting_rules>

    Output:"""
    # res = prompt_model("gemini-2.5-flash-lite", prompt)
    res = prompt_model("llama3.1:latest", prompt)
    print(res)
