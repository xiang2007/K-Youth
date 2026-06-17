from pathlib import Path
from typing import Optional, List, Any
from src.prompt_model import prompt_model, ModelResult
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
    if not input:
        print("Invalid input")
        return
    cursor.execute(
    "UPDATE jobs SET tech_stack = ? WHERE source_id = ?", (input[1], input[0])
)

def local_llm(model, job_description) -> ModelResult | None:
    prompt = f"""Extract the tech stack from each job description.

    Rules:
    - Return only technologies.
    - Do not infer technologies.
    - Do not include "Here is the extracted tech stack for each job description:"
    - Output format: ID|NONE if no technologies are found. ID will be the actual id
    - Output format: ID|tech1, tech2, tech3
    - Do not give any examples
    - Each technical stack is separated by a space and a comma

    INPUT:{job_description}

    Output:"""
    res = prompt_model(model, prompt)
    if not res:
        return None
    return res

def gemini_llm(model, job_description) -> ModelResult | None:
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
    if not res:
        return None
    return res

def tag_data(db_url : str):
    fulldburl = Path(db_url).resolve()

    if not fulldburl.exists():
        print(f"db_url: {db_url} not exist")
        return

    with sqlite3.connect(fulldburl) as conn:
        cs = conn.cursor()
        curr_offset = 0
        batch_size = 5
        time = 0
        token = 0
        out = []
        while True:
            batch = fetch_next_batch(cs, batch_size, curr_offset)
            if not batch:
                break
            curr_offset += batch_size
            # res = local_llm("deepseek-r1:1.5b", batch)
            res = gemini_llm("gemini1243", batch)
            if not res:
                break
            time = res.time_taken
            token = res.total_tokens
            out = res.text.splitlines()
            for i in out:
                res = i.split('|', 1)
                insert_to_db(cs, res)
                print(f"Analyzed {res[0]}: {res[1]}")
        print(f"Total tokens used: {token}, took {time * 1000} ms")

