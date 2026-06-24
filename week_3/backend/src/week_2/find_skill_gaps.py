from functools import lru_cache
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import List, Set

from pydantic import BaseModel

from week_2.prompt_model import ollama_client

# ── Ollama client ────────────────────────────────────────────────────────────
# Shared with prompt_model.py — don't create a second instance.
# Model config is local since prompt_model.py doesn't expose it.
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")


# ── Result model ─────────────────────────────────────────────────────────────
class SkillGapResult(BaseModel):
    gaps:  List[str]
    skill: List[str]


# ── Alias / protected token tables ───────────────────────────────────────────
# All keys AND values must already be lowercase.
ALIAS_CANON: dict[str, str] = {
    "c++":         "c++",
    "cpp":         "c++",
    "ci/cd":       "ci/cd",
    "a/b testing": "a/b testing",
}

PROTECTED_TOKENS: set[str] = {"ci/cd", "a/b testing"}


# ── Normalisation ─────────────────────────────────────────────────────────────
def normalize_skill(raw: str) -> Set[str]:
    """Lower-case + alias-resolve one raw token → 1+ canonical skills."""
    token = raw.strip().lower()
    if not token:
        return set()
    if token in PROTECTED_TOKENS:
        return {ALIAS_CANON[token]}
    # Ollama may strip "/" from compound skills ("a/b testing" → "ab testing");
    # check the slash-stripped form against protected tokens too.
    stripped = token.replace("/", "")
    stripped_protected = {t.replace("/", "") for t in PROTECTED_TOKENS}
    if stripped in stripped_protected:
        # Map back to the canonical form
        canon = next(c for c, t in ALIAS_CANON.items() if t.replace("/", "") == stripped)
        return {canon}
    if "/" in token:
        result: Set[str] = set()
        for part in token.split("/"):
            result |= normalize_skill(part)
        return result
    return {ALIAS_CANON.get(token, token)}


# ── Ollama extraction (for unstructured resume / PDF text) ───────────────────
def extract_skills_with_ollama(text: str) -> List[str]:
    """Ask the local LLM to pull every technical skill out of free-form text.

    Returns a list of lowercase skill strings, or [] on failure.
    """
    prompt = (
        "Extract every technical skill mentioned in the text below.\n"
        "If the text is a list of skills (e.g. comma-separated), return ALL of them.\n"
        "Keep compound skills intact with slashes: return \"a/b testing\" and \"ci/cd\",\n"
        "NOT \"ab testing\" or \"cicd\".\n"
        "Return ONLY a JSON array of lowercase strings — no explanation, "
        "no markdown fences, no extra keys.\n\n"
        'Example input: "Python, Docker, SQL"\n'
        'Example output: ["python", "docker", "sql"]\n\n'
        f"Text:\n{text}"
    )
    try:
        response = ollama_client.generate(model=OLLAMA_MODEL, prompt=prompt)
        raw = response["response"].strip()
        # Strip accidental markdown code fences
        raw = re.sub(r"```(?:json)?|```", "", raw).strip()
        skills = json.loads(raw)
        if isinstance(skills, list):
            return [str(s).strip().lower() for s in skills if s]
    except json.JSONDecodeError:
        print("Ollama returned non-JSON — falling back to empty skill set")
    except Exception as e:
        print(f"Ollama extraction error: {e}")
    return []


# ── Input-file parsing (uses Ollama) ─────────────────────────────────────────
def parse_infile(input_file_path: str) -> Set[str] | None:
    """Read any text file (resume, PDF dump, etc.) and extract skills via LLM."""
    path = Path(input_file_path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print("Input file not found.")
        return None
    except (OSError, UnicodeDecodeError) as e:
        print(f"Could not read input file: {e}")
        return None

    if not text.strip():
        return None

    raw_skills = extract_skills_with_ollama(text)
    if not raw_skills:
        return None

    tech_set: Set[str] = set()
    for skill in raw_skills:
        tech_set |= normalize_skill(skill)
    return tech_set or None


# ── DB skill extraction (regex split — already structured from tag_data.py) ──
def _parse_db_tech_stack(tech_stack: str) -> Set[str]:
    """Split a comma/slash-separated tech_stack string into canonical skills."""
    pattern = r',|(?<!\bCI)(?<!\bA)/(?!CD)(?!B\s+testing\b)'
    parts = re.split(pattern, tech_stack, flags=re.IGNORECASE)
    result: Set[str] = set()
    for raw in parts:
        result |= normalize_skill(raw.strip())
    return result


@lru_cache(maxsize=1)
def _load_db_skills(db_path: str) -> Set[str] | None:
    """Load and cache all canonical skills from the jobs database."""
    tech_set: Set[str] = set()
    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute("SELECT tech_stack FROM jobs").fetchall()
    except Exception as e:
        print(f"SQLite error: {e}")
        return None

    for (tech_stack_str,) in rows:
        if tech_stack_str:
            tech_set |= _parse_db_tech_stack(tech_stack_str.lower())

    return tech_set or None


def getDbSkill(db_path: Path) -> Set[str] | None:
    """Return every canonical skill present in the jobs database (cached)."""
    return _load_db_skills(str(db_path))


# ── Public API ────────────────────────────────────────────────────────────────
def find_skill_gaps(input_file_path: str, db_path: str) -> SkillGapResult:
    file_skills = parse_infile(input_file_path) or set()
    db_skills   = getDbSkill(Path(db_path))    or set()

    return SkillGapResult(
        gaps  = sorted(db_skills - file_skills),
        skill = sorted(file_skills & db_skills),
    )


if __name__ == "__main__":
    result = find_skill_gaps("data/resume_d3.txt", "data/jobs_d3_eval.db")
    print("Missing:", result.gaps)
    print("Matching:", result.skill)