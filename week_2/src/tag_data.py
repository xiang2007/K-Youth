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

def insert_to_db(cursor : sqlite3.Cursor, input):
    cursor.execute("INSERT INTO jobs (source_id, tech_stack) VALUES (?, ?)", input)

def local_llm(model, job_description):
    prompt = f"""Extract the tech stack from each job description.

    Rules:
    - Return only technologies.
    - Do not infer technologies.
    - Do not include "Here is the extracted tech stack for each job description:"
    - Output format: ID|NONE if no technologies are found. ID will be the actual id
    - Output format: ID|tech1, tech2, tech3
    - Do not give any examples

    INPUT:{job_description}

    Output:"""
    res = prompt_model(model, prompt)
    return res

def gemini_llm(job_description):
    prompt = f"""Extract the tech stack from each job description.

    Rules:
    - Return only technologies.
    - Do not infer technologies.
    - Output format: ID|NONE if no technologies are found.
    - Output format: ID|tech1, tech2, tech3

    INPUT:{job_description}

    Output:"""
    res = prompt_model("gemini-2.5-flash-lite", prompt)
    print(res)

def tag_data(db_url : str):
    fulldburl = Path(db_url).resolve()

    if not fulldburl.exists():
        print(f"db_url: {db_url} not exist")
        return

    with sqlite3.connect(fulldburl) as conn:
        cs = conn.cursor()
        curr_offset = 0
        batch_size = 5
        db_list = []
        out = []
        while True:
            batch = fetch_next_batch(cs, batch_size, curr_offset)
            if not batch:
                break
            curr_offset += batch_size
            # gemini_llm(db_list)
            res = local_llm("llama3.1:latest", batch)
            out = res.text.splitlines()
            for i in out:
                res = i.split('|', 1)
                insert_to_db(cs, res)
                print("Analyzed {res[0]}: res[1]")
        return out

