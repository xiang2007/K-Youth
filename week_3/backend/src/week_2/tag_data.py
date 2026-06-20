from pathlib import Path
from typing import Optional, List, Any, Dict
from prompt_model import prompt_model_extra, ModelResult
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
    cur.execute("SELECT COUNT(*) FROM jobs")
    return cur.fetchone()[0]


def fetch_next_batch(cursor: sqlite3.Cursor, batch_size: int, offset: int) -> Optional[List[Any]]:
    try:
        cursor.execute(
            "SELECT source_id, description FROM jobs ORDER BY source_id LIMIT ? OFFSET ?",
            (batch_size, offset)
        )
    except Exception as e:
        print(f"sql3 error: {e}")
    batch = cursor.fetchall()

    if not batch:
        return None

    return batch

def insert_to_db(cursor: sqlite3.Cursor, source_id: str, tech_stack: str) -> None:
    cursor.execute(
        "UPDATE jobs SET tech_stack = ? WHERE source_id = ?", (tech_stack, source_id)
    )


PROMPT_TEMPLATE = """Extract the tech stack from each job description.

Rules:
- Return only technologies.
- Do not infer technologies.
- Do not give any examples
- Output format: ID|None if no technologies are found. ID will be the actual id
- Output format: ID|tech1, tech2, tech3
{extra_rules}
INPUT:{job_description}

Output:"""

# Local models tend to add a preamble or use inconsistent separators, so they
# need a couple of extra rules that Gemini doesn't.
LOCAL_MODEL_EXTRA_RULES = (
    '- Do not include "Here is the extracted tech stack for each job description:"\n'
    "- Each technical stack is separated by a space and a comma\n"
)


def llm(model: str, job_description) -> ModelResult | None:
    extra_rules = LOCAL_MODEL_EXTRA_RULES if "gemini" not in model else ""
    prompt = PROMPT_TEMPLATE.format(extra_rules=extra_rules, job_description=job_description)
    return prompt_model_extra(model, prompt)

def process_response(cursor: sqlite3.Cursor, text: str) -> None:
    """Parse one batch of 'ID|tech1, tech2, ...' lines and write each to the db."""
    for line in text.splitlines():
        parsed = line.split('|', 1)
        if len(parsed) != 2:
            print(f"Skipping malformed line: {line!r}")
            continue
        source_id, tech_stack = parsed
        insert_to_db(cursor, source_id, tech_stack)
        print(f"Analyzed {source_id}: {tech_stack}")


def tag_data(
    db_url: Path,
    model: str = "gemini-3.1-flash-lite-preview",
    max_retries: int = 3,
    retry_base_delay: float = 2.0,
):
    fulldburl = Path(db_url).resolve()

    if not fulldburl.exists():
        print(f"db_url: {db_url} not exist")
        return
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

            process_response(cs, res.text)

            curr_offset += len(batch)
            remaining -= len(batch)

            # Now that we know the real token cost per job, size the next
            # batch to use as much of the TPM budget as safely possible.
            batch_size = calculate_batch_size(model, avg_tokens_per_job)

        print(f"Total tokens used: {token}, took {elapsed_time * 1000} ms")

if __name__ == "__main__":
    tag_data(Path("data/jobs_d1.db"))