from pathlib import Path
from pydantic import BaseModel
from typing import List, Set
import re
import sqlite3

class SkillGapResult(BaseModel):
    gaps: List[str]
    skill : List[str]

# Tokens that need a fixed casing because lower()-ing them isn't enough
# (e.g. "c" -> "C", not "c").
ALIAS_CANON = {
    "c": "C",
    "c++": "C++",
    "cpp": "C++",
    "ci/cd": "CI/CD",
    "a/b testing": "A/B Testing",
}

# Tokens that contain "/" but should NOT be split apart (mirrors the
# protection already in get_file_techStack's regex).
PROTECTED_TOKENS = {"ci/cd", "a/b testing"}

def normalize_skill(raw: str) -> Set[str]:
    """Turn one raw token into 1+ canonical skills.

    Handles two cases:
    - composite tokens like "C/C++" -> {"C", "C++"}
    - case variants like "c++" / "C++" -> {"C++"}
    Leaves protected compounds (CI/CD, A/B testing) intact, just normalized.
    """
    token = raw.strip()
    if not token:
        return set()
    if token.lower() in PROTECTED_TOKENS:
        return {ALIAS_CANON[token.lower()]}
    if "/" in token:
        result: Set[str] = set()
        for part in token.split("/"):
            result |= normalize_skill(part)
        return result
    return {ALIAS_CANON.get(token.lower(), token)}

def read_input_file(input_file_path : Path) -> str | None:
    try:
        with open(input_file_path, 'r') as f:
            t = (f.read()).splitlines()
            for i in t:
                if "Technical Skill" in i:
                    return i
    except FileNotFoundError:
        print("Oops! That file doesn't exist.")
    except PermissionError:
        print("You don't have permission to read this file.")
    return None

def get_file_techStack(fileContent : str)-> List[str] | None:
    raws_skill = re.sub(r"(?i)^Technical\s+Skills:\s*", "", fileContent)
    pattern = r',|(?<!\bCI)(?<!\bA)/(?!CD)(?!B\s+testing\b)'
    raw_split = re.split(pattern, raws_skill, flags=re.IGNORECASE)
    res = [skill.strip() for skill in raw_split if skill.split()]
    return res

def parse_infile(input_file_path : str) -> Set[str] | None:
    path = Path(input_file_path)
    file_content = read_input_file(path)
    if not file_content:
        return None
    raw_skills = get_file_techStack(file_content)
    if not raw_skills:
        return None
    techSet: Set[str] = set()
    for raw in raw_skills:
        techSet |= normalize_skill(raw)
    return techSet

def extractDBSkill(tech_stack: str, techSet: Set[str]) -> Set[str] | None:
    ts = get_file_techStack(tech_stack)
    if not ts:
        return None
    for raw in ts:
        techSet |= normalize_skill(raw)
    return techSet

def getDbSkill(db_path: Path) -> Set[str] | None:
    techStack: Set[str] = set()
    try:
        with sqlite3.connect(db_path) as conn:
            cs = conn.cursor()
            cs.execute("SELECT tech_stack FROM jobs")
            rows = cs.fetchall()
    except Exception as e:
        print(f"sqlite errorA: {e}")
        return None

    for (tech_stack_str,) in rows:
        if tech_stack_str:
            extractDBSkill(tech_stack_str, techStack)

    return techStack if techStack else None

def find_skill_gaps(input_file_path: str, db_path: str) -> SkillGapResult:
    file_skills = parse_infile(input_file_path) or set()
    db_skills = getDbSkill(Path(db_path)) or set()

    missing = db_skills - file_skills
    gaps = sorted(missing)
    skill = sorted(file_skills & db_skills)

    return SkillGapResult(
        gaps = gaps,
        skill = skill
    )

if __name__ == "__main__":
    print(find_skill_gaps("data/resume_d3.txt", "data/jobs_d3_eval.db").gaps)