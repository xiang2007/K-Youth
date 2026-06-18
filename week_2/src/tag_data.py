from pathlib import Path
from typing import Optional, List, Any, Dict
from src.prompt_model import prompt_model_extra, ModelResult
import sqlite3
import time

# Set rate limits explicitly here instead of reading rate_limits.txt.
# Format: {model: {"rpm": requests/min, "tpm": tokens/min, "rpd": requests/day}}
RATE_LIMITS: Dict[str, Dict[str, int]] = {
    "gemini-2.5-flash": {"rpm": 5, "tpm": 250_000, "rpd": 20},
    "gemini-2.5-flash-lite": {"rpm": 10, "tpm": 250_000, "rpd": 500},
    "gemini-3-flash-preview": {"rpm": 5, "tpm": 250_000, "rpd": 20},
    "gemini-3.1-flash-lite-preview": {"rpm": 15, "tpm": 250_000, "rpd": 500},
}


def calculate_batch_size(
    model: str,
    avg_tokens_per_job: float,
    overhead_tokens: int = 150,
    limits: Optional[Dict[str, Dict[str, int]]] = None,
    fallback: int = 5,
) -> int:
    """Compute the largest batch size that should fit under the model's TPM limit.

    avg_tokens_per_job should include both the input tokens for one job
    description and the output tokens for its corresponding 'ID|tech...' line.
    overhead_tokens is the roughly-fixed cost of the instruction template itself.
    """
    if limits is None:
        limits = RATE_LIMITS

    model_limits = limits.get(model)
    if not model_limits:
        print(f"No rate limit info for '{model}', defaulting to batch size {fallback}")
        return fallback

    available = model_limits["tpm"] - overhead_tokens
    if available <= 0 or avg_tokens_per_job <= 0:
        return 1

    batch = int(available // avg_tokens_per_job)
    return max(1, batch)


class RateLimiter:
    """Simple pacing guard so calls don't exceed a model's requests-per-minute limit."""

    def __init__(self, rpm: int):
        self.min_interval = 60.0 / rpm if rpm > 0 else 0.0
        self._last_call = 0.0

    def wait(self):
        if self.min_interval <= 0:
            return
        elapsed = time.perf_counter() - self._last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call = time.perf_counter()


def call_with_retry(fn, *args, max_retries: int = 3, base_delay: float = 2.0, **kwargs):
    """Call fn(*args, **kwargs) and retry with exponential backoff if it returns falsy.

    Assumes fn returns None/falsy on failure (as llm()/prompt_model_extra() do)
    rather than raising, so this checks the return value rather than catching
    exceptions.
    """
    for attempt in range(1, max_retries + 1):
        result = fn(*args, **kwargs)
        if result:
            return result
        if attempt < max_retries:
            delay = base_delay * (2 ** (attempt - 1))
            print(f"Attempt {attempt}/{max_retries} failed, retrying in {delay:.0f}s...")
            time.sleep(delay)
    print(f"All {max_retries} attempts failed.")
    return None

def db_size(cur : sqlite3.Cursor) -> int:
    cur.execute("SELECT source_id FROM jobs")
    res = cur.fetchall()
    return len(res)


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
    try:
        cursor.execute(
        "UPDATE jobs SET tech_stack = ? WHERE source_id = ?", (input[1], input[0])
        )
    except IndexError:
        print("Index Error")
        print(input)


def llm(model, job_description) -> ModelResult | None:
    if "gemini" in model:
        return gemini_llm(model, job_description)
    else:
        return local_llm(model, job_description)

def local_llm(model, job_description) -> ModelResult | None:
    prompt = f"""Extract the tech stack from each job description.

    Rules:
    - Return only technologies.
    - Do not infer technologies.
    - Do not include "Here is the extracted tech stack for each job description:"
    - Output format: ID|None if no technologies are found. ID will be the actual id
    - Output format: ID|tech1, tech2, tech3
    - Do not give any examples
    - Each technical stack is separated by a space and a comma

    INPUT:{job_description}

    Output:"""
    res = prompt_model_extra(model, prompt)
    if not res:
        return None
    return res

def gemini_llm(model, job_description) -> ModelResult | None:
    prompt = f"""Extract the tech stack from each job description.

    Rules:
    - Return only technologies.
    - Do not infer technologies.
    - Output format: ID|None if no technologies are found. ID will be the actual id
    - Output format: ID|tech1, tech2, tech3
    - Do not give any examples

    INPUT:{job_description}

    Output:"""
    res = prompt_model_extra(model, prompt)
    if not res:
        return None
    return res

def tag_data(
    db_url: str,
    model: str = "gemini-3.1-flash-lite-preview",
    max_retries: int = 3,
    retry_base_delay: float = 2.0,
):
    fulldburl = Path(db_url).resolve()

    if not fulldburl.exists():
        print(f"db_url: {db_url} not exist")
        return

    model_limits = RATE_LIMITS.get(model)
    if not model_limits:
        print(
            f"Warning: '{model}' not found in RATE_LIMITS; "
            f"batch sizing will fall back to a small default. "
            f"Double-check the model name matches a key in RATE_LIMITS exactly."
        )

    limiter = RateLimiter(model_limits["rpm"] if model_limits else 10)

    with sqlite3.connect(fulldburl) as conn:
        cs = conn.cursor()
        batch_size = 5  # small calibration batch used until we know real token cost/job
        elapsed_time = 0
        token = 0
        curr_offset = 0
        remaining = db_size(cs)

        while remaining > 0:
            batch_size = min(batch_size, remaining)
            batch = fetch_next_batch(cs, batch_size, curr_offset)
            if not batch:
                break

            limiter.wait()  # respect RPM before making the call
            res = call_with_retry(
                llm, model, batch,
                max_retries=max_retries, base_delay=retry_base_delay
            )
            if not res:
                print(f"Skipping batch at offset {curr_offset} after repeated failures")
                curr_offset += len(batch)
                remaining -= len(batch)
                continue

            elapsed_time += res.time_taken
            token += res.total_tokens
            avg_tokens_per_job = res.total_tokens / len(batch)

            for line in res.text.splitlines():
                parsed = line.split('|', 1)
                insert_to_db(cs, parsed)
                if len(parsed) == 2:
                    print(f"Analyzed {parsed[0]}: {parsed[1]}")

            curr_offset += len(batch)
            remaining -= len(batch)

            # Now that we know the real token cost per job, size the next
            # batch to use as much of the TPM budget as safely possible.
            batch_size = calculate_batch_size(model, avg_tokens_per_job)

        print(f"Total tokens used: {token}, took {elapsed_time * 1000} ms")