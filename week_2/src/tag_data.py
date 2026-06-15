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

def split_output(input : str):
    res = []
    for line in input.strip().splitlines():
        if not line:
            continue
        source_id, tech_stack = line.split('|', 1)
        res.append((source_id.strip(), tech_stack.strip()))
    return res

def local_llm(model, job_description):
    # prompt = f"""You are an advanced technical data extraction tool. Your job is to extract the tech stack from the job description provided below.

    # <job_description>
    # {job_description}
    # </job_description>

    # <extraction_checklist>
    # Scan the text thoroughly for:
    # - Programming languages
    # </extraction_checklist>

    # <constraints>
    # - Extract EVERY explicit technical item mentioned. Do not omit anything.
    # - Do NOT extract soft skills, administrative processes, or generic categories.
    # - Do NOT explain or make up technical skills.
    # - Do Not include terms "no", "bad"
    # - CRITICAL: If absolutely NO technical stack items from the checklist are found in the text, output exactly the word "None".
    # </constraints>

    # <formatting_rules>
    # - Only output one line.
    # - Output ONLY the final list as a raw, comma-separated string without space (or the single word "None").
    # - Do not wrap the final output in conversational framing, code blocks, or pleasantries.
    # - Only return a empty line if nothing is found
    # - Do NOT give any examples
    # - If the actual job description text was not given, just return None
    # - Do not give any notes
    # - Do not include brackets '()'
    # - Do not use the word "or", "+'
    # - Dont use Version control (Git) use Git instead
    # - Dont include terms "no", "bad"
    # </formatting_rules>

    # Output:"""
    prompt = f"""Extract the tech stack from each job description.

    Rules:
    - Return only technologies.
    - Do not infer technologies.
    - Do not include "Here is the extracted tech stack for each job description:"
    - Return NONE if no technologies are found.
    - Output format: ID|tech1, tech2, tech3

    INPUT:{job_description}

    Output:"""
    # res = prompt_model("gemini-2.5-flash-lite", prompt)
    res = prompt_model(model, prompt)
    return res

def gemini_llm(job_description):
    prompt = f"""Extract the tech stack from each job description.

    Rules:
    - Return only technologies.
    - Do not infer technologies.
    - Return NONE if no technologies are found.
    - Output format: ID|tech1,tech2,tech3

    INPUT:{job_description}

    Output:"""
    res = prompt_model("gemini-2.5-flash-lite", prompt)
    # res = prompt_model("llama3.1:latest", prompt)
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
            for item in batch:
                db_list.append(item)
            # gemini_llm(db_list)
            res = local_llm("llama3.1:latest", db_list)
            out.extend(split_output(res.text))
            db_list.clear()
        if out:
            i = 0
            for item in out:
                print(f"Analyzed Job{i} : {item[1]}")
            print(f"Total tokens used: {res.total_tokens}, took {res.time_taken}")
        return out

