# K-Youth Week 3 — Full-Stack AI Chat Application

A containerized full-stack chat application that lets users upload PDF resumes for **skill-gap analysis** against job postings, or simply **chat with an AI model**. Built with FastAPI (frontend + backend), Ollama (local LLM), and Docker.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Setup Instructions](#setup-instructions)
4. [Usage](#usage)
5. [How the Code Works](#how-the-code-works)
6. [API / Function Reference](#api--function-reference)
7. [Data / Assumptions](#data--assumptions)
8. [Testing](#testing)
9. [Limitations](#limitations)
10. [Architecture Reflection](#architecture-reflection)

---

## Project Overview

### Goal

Build and containerize a full-stack chat application with a frontend, backend, and AI model integration. The application serves two purposes:

1. **AI Chat** — Users type a message and receive a response from a local AI model (Ollama) or cloud model (Gemini).
2. **Resume Skill-Gap Analysis** — Users upload a resume PDF, and the system extracts the candidate's technical skills, compares them against job postings stored in a SQLite database, and reports which skills are missing and which match.

### High-Level Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Browser    │────▶│  Frontend    │────▶│   Backend    │
│ (Chrome, etc)│     │  FastAPI     │     │  FastAPI     │
│  Port 8080   │◀────│  Port 8080   │◀────│  Port 8000   │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                           ┌──────▼───────┐
                                           │    Ollama    │
                                           │    Port      │
                                           │  11434/11435 │
                                           └──────────────┘
```

Three Docker containers communicate over a shared **bridge network**:

| Container | Role | Port (host) | Port (container) |
|---|---|---|---|
| `frontend` | Serves the chat UI + proxies API calls to backend | 8080 | 8080 |
| `backend` | Handles chat requests, skill-gap analysis, AI model routing | 8000 | 8000 |
| `ollama` | Runs the local AI model (llama3.2) on NVIDIA GPU | 11435 | 11434 |

---

## Setup Instructions

### Prerequisites

- **Docker** (24+) and **Docker Compose** (v2.20+)
- **NVIDIA GPU** with CUDA Toolkit and NVIDIA Container Toolkit (required for the Ollama service)
- Git

### Step 1 — Clone the repository

```bash
git clone <your-repo-url>
cd K-Youth/week_3
```

### Step 2 — Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` to set:

| Variable | Default | Description |
|---|---|---|
| `BACKEND_URL` | `http://backend:8000` | URL of the backend service (used by the frontend container) |
| `OLLAMA_HOST` | `http://ollama:11434` | URL of the Ollama service (used by the backend container) |
| `OLLAMA_MODEL` | `llama3.2:latest` | Default Ollama model for chat |
| `JOBS_DB_PATH` | `/app/src/week_2/data/jobs_d3_eval.db` | Path to the SQLite jobs database inside the backend container |
| `GOOGLE_API_KEY` | *(blank)* | Optional — Google Gemini API key for cloud model fallback |

> **Security note:** Never commit `.env`. The `.gitignore` file excludes it. The `.env.example` shows the structure without real secrets.

### Step 3 — Build and start

```bash
docker compose up --build
```

This builds the frontend and backend images from their respective Dockerfiles, pulls the `ollama/ollama` image, and starts all three containers.

### Optional — Manual dependency installation (outside Docker)

Each service uses [`uv`](https://github.com/astral-sh/uv) for dependency management.

```bash
# Backend
cd backend
uv sync --locked
uv run uvicorn src.app:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
uv sync --locked
uv run uvicorn src.app:app --host 0.0.0.0 --port 8080
```

---

## Usage

### Starting the application

```bash
docker compose up --build
```

Wait for all three services to start (you'll see `INFO:     Application startup complete.` logs).

### Accessing the application

Open **http://localhost:8080** in your browser.

### Two modes of use

#### 1. Chat (no PDF)

Type any message and press Enter or click **Send**. The message is forwarded to the backend, which routes it to Ollama (or Gemini if configured) and returns the AI's response.

#### 2. Resume Skill-Gap Analysis

1. Click **"📎 Attach PDF"** and select a resume file.
2. PDF.js extracts the text **client-side** (in your browser). No file is uploaded to the server.
3. Type a message (or leave it blank) and click **Send**.
4. The backend writes the extracted text to a temporary file, runs the LLM to extract technical skills, compares them against the jobs database, and returns a formatted report:

```
Missing skills: docker, kubernetes, restful api design
Matching skills: python, sql, php, node.js, mysql, mongodb
```

### Stopping the application

```bash
docker compose down          # stop containers, keep data
docker compose down -v       # stop containers and remove Ollama data volume
```

---

## How the Code Works

This section walks through every file and explains what it does, line by line (or block by block).

---

### 1. `docker-compose.yml` — Orchestrating Three Containers

```yaml
services:
  ollama:
    image: ollama/ollama                          # Pull official Ollama image from Docker Hub
    ports:
      - "11435:11434"                             # Map host port 11435 → container port 11434
    volumes:
      - ollama_data:/root/.ollama                 # Persist downloaded models across restarts
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia                      # Use NVIDIA GPU driver
              count: all                          # Allocate all available GPUs
              capabilities: [gpu]                 # Enable GPU compute

  backend:
    build:
      context: ./backend                          # Build from backend/ directory
      dockerfile: Dockerfile                      # Use backend/Dockerfile
    ports:
      - "8000:8000"                               # Expose backend on host port 8000
    environment:
      - OLLAMA_HOST=http://ollama:11434           # Tell backend how to reach Ollama
    depends_on:
      - ollama                                    # Start Ollama first

  frontend:
    build:
      context: ./frontend                         # Build from frontend/ directory
      dockerfile: Dockerfile                      # Use frontend/Dockerfile
    ports:
      - "8080:8080"                               # Expose frontend on host port 8080
    environment:
      - BACKEND_URL=http://backend:8000           # Tell frontend how to reach backend
    depends_on:
      - backend                                   # Start backend first

volumes:
  ollama_data:                                    # Named volume for Ollama model persistence

networks:
  default:
    driver: bridge                                # All services share a bridge network
```

**Key concepts:**

- **`image:` vs `build:`** — Ollama uses a pre-built image from Docker Hub. Frontend and backend are built from local Dockerfiles because they contain our custom code.
- **`ports:`** — Maps a host port to a container port. The format is `HOST:CONTAINER`. We use different host ports (11435 vs 11434) for Ollama to avoid conflicts with any local Ollama installation.
- **`depends_on:`** — Ensures startup order: Ollama → Backend → Frontend.
- **Bridge network** — Docker creates an internal network. Services resolve each other by **service name** (`http://backend:8000`, `http://ollama:11434`). This is why we don't need IP addresses.

---

### 2. `backend/Dockerfile` — Building the Backend Container

```dockerfile
FROM python:3.14.4-bookworm                     # Base image: Python 3.14 on Debian Bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/   # Multistage: copy `uv` binary from Astral's image
COPY . /app                                      # Copy all backend source code into /app in the container
ENV UV_NO_DEV=1                                  # Don't install dev dependencies (tests, linters)
WORKDIR /app                                     # Set working directory to /app
RUN uv sync --locked                             # Install production dependencies from uv.lock
ENTRYPOINT ["uv", "run", "uvicorn"]              # Default command: run uvicorn via uv
CMD ["--app-dir", "src", "--host", "0.0.0.0", "app:app"]  # Arguments: serve src/app.py on all interfaces
```

**Why this Dockerfile works:**

1. Starts with a clean Python 3.14 image.
2. Injects the `uv` package manager (faster than pip) via a multistage copy — no need to install it.
3. Copies the entire project into `/app`.
4. Runs `uv sync --locked` which installs exactly the versions in `uv.lock` (reproducible builds).
5. Sets `uvicorn` (ASGI server) as the entrypoint, configured to serve the FastAPI app.

---

### 3. `frontend/Dockerfile` — Building the Frontend Container

```dockerfile
FROM python:3.14.4-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY . /app
ENV UV_NO_DEV=1
WORKDIR /app
RUN uv sync --locked
ENTRYPOINT ["uv", "run", "uvicorn"]
CMD ["--app-dir", "src", "--host", "0.0.0.0", "--port", "8080", "app:app"]
```

Same structure as the backend Dockerfile, but:

- Exposes port **8080** instead of 8000
- Has fewer dependencies (no `google-genai`, `ollama` libraries — those are backend-only)

---

### 4. `backend/src/app.py` — The Backend API Server

```python
import os
import tempfile
import time
import uvicorn
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from week_2.find_skill_gaps import find_skill_gaps
from week_2.prompt_model import prompt_model
```

**Imports explained:**

| Import | Purpose |
|---|---|
| `tempfile` | Create a temporary file to hold the PDF text for skill extraction |
| `uvicorn` | ASGI server to run the FastAPI app |
| `FastAPI`, `HTTPException` | Web framework and error handling |
| `BaseModel` | Pydantic data validation for request/response schemas |
| `find_skill_gaps` | Core logic: compare resume skills vs. job database skills |
| `prompt_model` | AI model routing: Ollama or Gemini |

```python
WEEK2_DIR = Path(__file__).parent / "week_2"
DEFAULT_JOBS_DB = WEEK2_DIR / "data" / "jobs_d3_eval.db"
JOBS_DB_PATH = Path(os.environ.get("JOBS_DB_PATH", str(DEFAULT_JOBS_DB)))
```

**Database path resolution:**

1. `WEEK2_DIR` points to `backend/src/week_2/` (where the week_2 skill-analysis code lives).
2. `DEFAULT_JOBS_DB` is the default SQLite database: `jobs_d3_eval.db` containing 8 Malaysian job postings.
3. `JOBS_DB_PATH` can be overridden by the `JOBS_DB_PATH` environment variable (useful in Docker where paths differ).

```python
app = FastAPI()
```

Creates the FastAPI application instance. This is the entry point that Uvicorn will call.

```python
class ChatRequest(BaseModel):
    message: str
    pdf_text: str | None = None
    model: str = "llama3.2:latest"

class ChatResponse(BaseModel):
    reply: str
```

**Pydantic models for request/response validation:**

- `ChatRequest`: The frontend sends JSON with a `message` (required), optional `pdf_text` (extracted from PDF), and optional `model` name.
- `ChatResponse`: The backend always returns JSON with a `reply` string.

Pydantic automatically validates incoming JSON and generates OpenAPI documentation.

```python
def format_skill_gap_result(result) -> str:
    gaps = ", ".join(result.gaps) if result.gaps else "none"
    skills = ", ".join(result.skill) if result.skill else "none"
    return f"Missing skills: {gaps}\nMatching skills: {skills}"
```

Formats the skill-gap analysis result into a human-readable string. If a list is empty, shows "none" instead of an empty string.

```python
@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    if body.pdf_text:
        if not JOBS_DB_PATH.is_file():
            raise HTTPException(status_code=500, detail="Jobs database not found")

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=True, encoding="utf-8"
        ) as tmp:
            tmp.write(body.pdf_text)
            tmp.flush()
            result = find_skill_gaps(tmp.name, str(JOBS_DB_PATH))
            return ChatResponse(reply=format_skill_gap_result(result))

    reply = prompt_model(body.model, body.message)
    if reply is None:
        raise HTTPException(status_code=503, detail="Model unavailable")
    return ChatResponse(reply=reply)
```

**The `/chat` endpoint — the core of the backend:**

1. **If `pdf_text` is present** (resume analysis mode):
   - Checks that the jobs database file exists. Raises HTTP 500 if missing.
   - Creates a temporary file (auto-deleted on close) and writes the PDF text to it.
   - Calls `find_skill_gaps()` which extracts skills from the resume via Ollama, loads skills from the database, and computes the difference.
   - Formats and returns the result.

2. **If `pdf_text` is absent** (chat mode):
   - Calls `prompt_model()` with the user's message and model name.
   - If the model returns `None` (failure), raises HTTP 503.
   - Otherwise returns the AI's response.

```python
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, log_level="info")
```

Allows running the backend directly: `python backend/src/app.py`. Serves on all interfaces (`0.0.0.0`) on port 8000.

---

### 5. `backend/src/week_2/find_skill_gaps.py` — Resume Skill Extraction & Comparison

This is the heart of the skill-gap analysis feature. It uses an LLM to extract technical skills from a resume text file, then compares them against skills extracted from job postings in a SQLite database.

```python
from functools import lru_cache
import json
import re
import sqlite3
from pathlib import Path
from typing import List, Set

from ollama import Client
from pydantic import BaseModel

from week_2.prompt_model import ollama_client
```

**Imports:**

| Import | Purpose |
|---|---|
| `lru_cache` | Cache the database loading so we don't re-parse it on every request |
| `json` | Parse the LLM's JSON-array response |
| `re` | Regex for splitting comma/slash-separated tech stacks |
| `sqlite3` | Read the jobs database directly (no ORM needed) |
| `Client` from `ollama` | Actually, this is imported but unused — the shared `ollama_client` from `prompt_model.py` is used instead |
| `BaseModel` | Pydantic model for the result structure |

```python
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
```

Gets the model name from environment. Defaults to `llama3.2:latest`.

```python
class SkillGapResult(BaseModel):
    gaps:  List[str]
    skill: List[str]
```

The result structure: `gaps` = skills the job requires but the resume doesn't have. `skill` = skills both the resume and jobs share.

```python
ALIAS_CANON: dict[str, str] = {
    "c++":         "c++",
    "cpp":         "c++",
    "ci/cd":       "ci/cd",
    "a/b testing": "a/b testing",
}

PROTECTED_TOKENS: set[str] = {"ci/cd", "a/b testing"}
```

**Alias resolution table:** Normalizes different ways of writing the same skill. `"cpp"` → `"c++"`, `"cicd"` → `"ci/cd"`, etc. `PROTECTED_TOKENS` are tokens that contain slashes and must not be split.

```python
def normalize_skill(raw: str) -> Set[str]:
    """Lower-case + alias-resolve one raw token → 1+ canonical skills."""
    token = raw.strip().lower()
    if not token:
        return set()
    if token in PROTECTED_TOKENS:
        return {ALIAS_CANON[token]}
    if "/" in token:
        result: Set[str] = set()
        for part in token.split("/"):
            result |= normalize_skill(part)
        return result
    return {ALIAS_CANON.get(token, token)}
```

**`normalize_skill()` — the skill normalizer:**

1. Strips whitespace and lowercases the token.
2. If it's a protected token like `"ci/cd"`, returns the canonical form.
3. If it contains a `/` (e.g., `"python/java"`), splits and recursively normalizes each part.
4. Otherwise, looks it up in `ALIAS_CANON`. If not found, returns the token as-is.

Example: `"CICD"` → `"ci/cd"` → `{"ci/cd"}`. `"Python/Java"` → `{"python", "java"}`.

```python
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
```

**`extract_skills_with_ollama()` — LLM-powered skill extraction:**

1. Builds a prompt instructing the LLM to extract technical skills and return them as a JSON array.
2. Sends the prompt to Ollama using the shared client.
3. Strips accidental markdown code fences (```` ```json ````) that the LLM sometimes adds.
4. Parses the JSON response. If it's a list, returns the normalized skills.
5. If JSON parsing fails or any error occurs, returns an empty list (graceful degradation).

```python
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
```

**`parse_infile()` — reads a file and extracts skills:**

1. Opens the file (created from the PDF text by the backend).
2. Calls `extract_skills_with_ollama()` to get raw skill strings.
3. Normalizes each skill through `normalize_skill()` and collects them into a set.
4. Returns the set of canonical skills, or `None` on any failure.

```python
def _parse_db_tech_stack(tech_stack: str) -> Set[str]:
    """Split a comma/slash-separated tech_stack string into canonical skills."""
    pattern = r',|(?<!\bCI)(?<!\bA)/(?!CD)(?!B\s+testing\b)'
    parts = re.split(pattern, tech_stack, flags=re.IGNORECASE)
    result: Set[str] = set()
    for raw in parts:
        result |= normalize_skill(raw.strip())
    return result
```

**`_parse_db_tech_stack()` — splits database tech-stack strings:**

The regex `r',|(?<!\bCI)(?<!\bA)/(?!CD)(?!B\s+testing\b)'` splits on commas **or** slashes, but **not** when the slash is part of `"ci/cd"` or `"a/b testing"`. The negative lookbehinds/lookaheads protect compound tokens.

Example: `"python, java, ci/cd, a/b testing"` → `["python", " java", " ci/cd", " a/b testing"]`.

```python
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
```

**`_load_db_skills()` — loads and caches database skills:**

1. Connects to the SQLite database (no ORM, raw SQL).
2. Selects all `tech_stack` columns from the `jobs` table.
3. Splits each tech-stack string into individual skills using `_parse_db_tech_stack()`.
4. Collects all skills into a single set.
5. Decorated with `@lru_cache(maxsize=1)` — the result is cached after the first call, so repeated skill-gap analyses don't re-read the database.

```python
def getDbSkill(db_path: Path) -> Set[str] | None:
    """Return every canonical skill present in the jobs database (cached)."""
    return _load_db_skills(str(db_path))
```

Thin wrapper around the cached function.

```python
def find_skill_gaps(input_file_path: str, db_path: str) -> SkillGapResult:
    file_skills = parse_infile(input_file_path) or set()
    db_skills   = getDbSkill(Path(db_path))    or set()

    return SkillGapResult(
        gaps  = sorted(db_skills - file_skills),
        skill = sorted(file_skills & db_skills),
    )
```

**`find_skill_gaps()` — the public API, the core function:**

1. `file_skills` = skills extracted from the resume via LLM. Falls back to empty set if extraction fails.
2. `db_skills` = skills from the jobs database. Falls back to empty set if loading fails.
3. `gaps` = `db_skills - file_skills` → skills in job postings but NOT in the resume.
4. `skill` = `file_skills & db_skills` → skills present in BOTH the resume and job postings.
5. Both lists are sorted alphabetically for consistent output.

---

### 6. `backend/src/week_2/prompt_model.py` — AI Model Routing

```python
import os
import time
import sys
from dataclasses import dataclass
from dotenv import load_dotenv
from google import genai
from google.genai import types
from ollama import Client
```

**Imports:**

| Import | Purpose |
|---|---|
| `dotenv.load_dotenv()` | Load `.env` file for API keys |
| `google.genai` | Google Gemini SDK for cloud LLM calls |
| `ollama.Client` | Ollama SDK for local LLM calls |

```python
load_dotenv()
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
ollama_client = Client(host=OLLAMA_HOST)
try:
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    api_available = True
except ValueError:
    print("No API key was provided")
    api_available = False
```

**Initialization at module level:**

1. Loads `.env` for environment variables.
2. Creates the Ollama client pointing to the host from `OLLAMA_HOST` env var.
3. Attempts to create a Gemini client. If no `GOOGLE_API_KEY` is set, `api_available` is `False`.

```python
@dataclass
class ModelResult:
    text: str
    total_tokens: int
    time_taken: float
```

A simple dataclass to hold the response from an LLM call, including token count and timing for observability.

```python
def prompt_model(model: str, prompt: str) -> str | None:
    if "gemini" in model and api_available:
        response = prompt_google(model, prompt)
        if not response:
            print("Fallback to local llm")
            response = prompt_local_llm("llama3.1:latest", prompt)
            if not response:
                return None
    else:
        response = prompt_local_llm(model, prompt)
        if not response:
            return None
    return response.text
```

**`prompt_model()` — the router:**

1. If the model name contains `"gemini"` **and** an API key is available → try Gemini first, fall back to local Ollama.
2. Otherwise → use Ollama directly.
3. Returns the text response, or `None` if both paths fail.

```python
def prompt_google(model: str, prompt: str) -> ModelResult | None:
    start = time.perf_counter()
    config = types.GenerateContentConfig(temperature=0.0)
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config
        )
    except Exception as e:
        print(f"Gemini error: {((e.args[0]).split(',', 5))[1]}")
        return None
    total_token = response.usage_metadata.total_token_count
    text = str(response.text)
    end = time.perf_counter()
    total_time = end - start
    return ModelResult(text=text, total_tokens=total_token, time_taken=total_time)
```

**`prompt_google()` — calls Google Gemini:**

1. Sets `temperature=0.0` for deterministic, factual responses.
2. Sends the prompt to Gemini via the SDK.
3. Captures token usage and timing.
4. Returns `None` on any error.

```python
def prompt_local_llm(model: str, prompt: str) -> ModelResult | None:
    start = time.perf_counter()
    try:
        response = ollama_client.generate(
            model=model,
            prompt=prompt
        )
        text = response["response"]
        total_token = response["prompt_eval_count"] + response["eval_count"]
        end = time.perf_counter()
        total_time = end - start
    except Exception as e:
        print(f"Ollama error: {e}")
        return None
    return ModelResult(text=text, total_tokens=total_token, time_taken=total_time)
```

**`prompt_local_llm()` — calls Ollama:**

1. Sends the prompt to the local Ollama instance.
2. `prompt_eval_count` = tokens used to read the prompt. `eval_count` = tokens generated. Together they give total token usage.
3. Returns `None` on connection failure or timeout.

---

### 7. `backend/src/week_2/tag_data.py` — LLM-Based Job Description Tagging

This module is a **separate tool** (not used by the chat endpoint) that uses an LLM to extract tech stacks from job descriptions and write them into the SQLite database. It was used to populate the `tech_stack` column in `jobs_d3_eval.db`.

**Key components:**

| Component | Purpose |
|---|---|
| `RATE_LIMITS` | Dictionary of per-model rate limits (RPM, TPM, RPD) for Gemini models |
| `calculate_batch_size()` | Dynamically sizes API request batches to stay within token-per-minute limits |
| `RateLimiter` | Sleeps between API calls to respect requests-per-minute limits |
| `call_with_retry()` | Retries failed LLM calls with exponential backoff (2s, 4s, 8s) |
| `PROMPT_TEMPLATE` | Instructs the LLM to extract tech stacks in `ID|tech1, tech2` format |
| `llm()` | Wraps `prompt_model_extra()` with model-specific rules |
| `process_response()` | Parses LLM output and writes to the database |
| `tag_data()` | Main function — iterates through the database in batches, calls the LLM, and tags each job |

**How `tag_data()` works:**

```
1. Open the SQLite database
2. Get total row count
3. While rows remain:
   a. Fetch a batch (initially 5 rows, then dynamically sized)
   b. Wait if needed (respect RPM limit)
   c. Call LLM with the batch of job descriptions
   d. Retry up to 3 times on failure (exponential backoff)
   e. Parse the LLM response and UPDATE each row's tech_stack
   f. Recalculate batch size based on actual token usage
4. Print total tokens and time used
```

This is a **one-time data preparation tool**, not part of the runtime chat flow.

---

### 8. `frontend/src/app.py` — The Frontend Server

```python
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import uvicorn
import httpx
import os
```

**Imports:**

| Import | Purpose |
|---|---|
| `Jinja2Templates` | Serve the HTML template |
| `HTMLResponse` | Return raw HTML for the homepage |
| `JSONResponse` | Return JSON for the chat proxy |
| `httpx.AsyncClient` | Async HTTP client to proxy requests to the backend |

```python
app = FastAPI()
t_path = Path("src/templates").resolve()
templates = Jinja2Templates(directory=str(t_path))
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
```

1. Creates the FastAPI app.
2. Points Jinja2 to `src/templates/` for HTML templates.
3. Gets the backend URL from environment (set by docker-compose to `http://backend:8000`).

```python
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")
```

**`GET /` — serves the chat UI:**

Returns `index.html` rendered by Jinja2. This is the single page the user interacts with.

```python
@app.post("/chat")
async def chat(request: Request):
    data = await request.json()

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{BACKEND_URL}/chat",
            json=data,
        )

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return JSONResponse({"error": detail}, status_code=resp.status_code)

    try:
        return JSONResponse(resp.json())
    except httpx.InvalidJSONError:
        return JSONResponse(
            {"error": "Unexpected server response — please try again"},
            status_code=502,
        )
```

**`POST /chat` — the proxy:**

1. Reads the JSON body from the browser request.
2. Forwards it to the backend at `BACKEND_URL/chat` using an async HTTP client with a 120-second timeout (AI models can be slow).
3. **If the backend returns an error (HTTP ≥ 400):** extracts the error detail and returns it as `{"error": detail}` with the same status code.
4. **If the backend succeeds:** returns its JSON response as-is.
5. **If the backend returns invalid JSON:** returns a generic 502 error.

This proxy pattern means the browser never needs to know the backend's address — it only talks to the frontend on port 8080.

```python
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8080, log_level="info")
```

Run directly: `python frontend/src/app.py` serves on port 8080.

---

### 9. `frontend/src/templates/index.html` — The Chat Interface

This is a single-page application with **zero JavaScript frameworks** — just Bootstrap CSS, PDF.js, and vanilla JS.

**HTML Structure:**

```html
<div id="chat-history"></div>          <!-- Scrollable message area -->
<input type="file" id="pdf-input">     <!-- PDF upload button -->
<textarea id="user-input"></textarea>  <!-- Message text area -->
<button id="send-btn">Send</button>    <!-- Send button -->
```

**JavaScript — Key Functions:**

```javascript
// State
let pdfText = '';   // Holds extracted PDF text until cleared
```

```javascript
// PDF extraction (runs when user selects a file)
pdfInput.addEventListener('change', async () => {
    const file = pdfInput.files[0];
    if (!file) return;

    pdfStatus.textContent = `Reading "${file.name}"…`;
    try {
        const buffer = await file.arrayBuffer();
        const pdf = await pdfjsLib.getDocument({ data: buffer }).promise;

        let text = '';
        for (let i = 1; i <= pdf.numPages; i++) {
            const page = await pdf.getPage(i);
            const content = await page.getTextContent();
            text += content.items.map(item => item.str).join(' ') + '\n';
        }

        pdfText = text.trim();
        pdfStatus.textContent = `✔ "${file.name}" — ${pdfText.length} characters`;
    } catch (err) {
        pdfStatus.textContent = '⚠ Could not read PDF';
    }
});
```

**PDF.js extraction:**

1. Reads the selected file as an `ArrayBuffer`.
2. Creates a PDF.js document from the buffer.
3. Iterates through each page, extracting text content from each text item.
4. Joins all page text and stores it in `pdfText`.
5. Shows character count to the user.

**Important:** This runs entirely in the browser. No file is uploaded to any server during extraction.

```javascript
function addMessage(role, text) {
    const div = document.createElement('div');
    div.className = `msg ${role}`;
    div.innerHTML = `<span class="bubble">${escHtml(text)}</span>`;
    historyEl.appendChild(div);
    historyEl.scrollTop = historyEl.scrollHeight;
}

function escHtml(str) {
    return str
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>');
}
```

**`addMessage()` — appends a chat bubble:**

1. Creates a `<div>` with class `msg user` or `msg assistant`.
2. Wraps the text in a `<span class="bubble">`.
3. Escapes HTML to prevent XSS injection.
4. Appends to the chat history and scrolls to the bottom.

```javascript
async function send() {
    const message = inputEl.value.trim();
    if (!message) return;

    addMessage('user', message);
    inputEl.value = '';
    sendBtn.disabled = true;
    sendBtn.textContent = '…';

    const body = { message };
    if (pdfText) body.pdf_text = pdfText;

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await res.json();
        if (!res.ok) {
            addMessage('assistant', `⚠ Error: ${data.error ?? data.detail ?? res.statusText}`);
        } else {
            addMessage('assistant', data.reply ?? '(no reply)');
        }
    } catch (err) {
        addMessage('assistant', `⚠ Could not reach the backend: ${err.message}`);
    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = 'Send';
        pdfText = '';
        pdfInput.value = '';
        pdfStatus.textContent = 'No file chosen';
    }
}
```

**`send()` — the main send function:**

1. Validates the message is not empty.
2. Displays the user's message as a bubble.
3. Disables the send button to prevent double-submission.
4. Builds the request body: `{ message }` + `{ pdf_text }` if a PDF was attached.
5. Sends `POST /chat` to the frontend server (relative URL — no hardcoded address).
6. On success: displays the assistant's reply.
7. On error: displays the error message from the backend.
8. In `finally`: re-enables the button and **clears the PDF state** (so the next message doesn't accidentally include old PDF text).

```javascript
sendBtn.addEventListener('click', send);
inputEl.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
});
```

**Event listeners:**

- Click "Send" button → call `send()`.
- Press Enter (without Shift) → call `send()`. Shift+Enter creates a new line.

---

### 10. `docker-compose.yml` — How Containerization Works

```yaml
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend
```

**What `build:` does:**

1. Docker reads `./frontend/Dockerfile`.
2. Executes each instruction: copies source code, installs dependencies, sets the entrypoint.
3. Produces a local image tagged `k-youth_frontend` (or whatever the project name is).
4. Creates a container from that image and starts it.

**What `environment:` does:**

Sets environment variables **inside the container**. The frontend container receives `BACKEND_URL=http://backend:8000`, which `app.py` reads via `os.environ.get()`.

**What `depends_on:` does:**

Ensures Docker starts the backend container before the frontend. Note: it doesn't wait for the backend to be *ready* — only for it to be *started*. For production, you'd use health checks.

```yaml
networks:
  default:
    driver: bridge
```

**Bridge networking explained:**

Docker creates an internal virtual network. Each container gets an IP on this network. Containers resolve each other by **service name**:

- Frontend container → `http://backend:8000` → Docker DNS resolves `backend` to the backend container's IP.
- Backend container → `http://ollama:11434` → Docker DNS resolves `ollama` to the Ollama container's IP.

This is why you never need to hardcode IP addresses. Service names are the network's DNS entries.

---

## API / Function Reference

### Backend Endpoints

#### `POST /chat`

**URL:** `http://localhost:8000/chat` (direct) or `http://localhost:8080/chat` (via frontend proxy)

**Request:**
```json
{
  "message": "Explain Docker networking",
  "pdf_text": null,
  "model": "llama3.2:latest"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | `string` | Yes | User's chat message |
| `pdf_text` | `string \| null` | No | Extracted PDF text for skill-gap analysis |
| `model` | `string` | No | AI model name. Default: `llama3.2:latest` |

**Response (success):**
```json
{
  "reply": "Docker networking allows containers to communicate through bridges..."
}
```

**Response (skill-gap analysis):**
```json
{
  "reply": "Missing skills: kubernetes, tensorflow\nMatching skills: python, docker, sql"
}
```

**Response (error):**
```json
{
  "detail": "Jobs database not found"
}
```
(HTTP 500)

```json
{
  "detail": "Model unavailable"
}
```
(HTTP 503)

### Frontend Endpoints

#### `GET /`

Serves the chat UI (`index.html`). No parameters.

#### `POST /chat`

Proxies to `BACKEND_URL/chat`. Same request/response format as the backend endpoint, but errors are wrapped:

```json
{
  "error": "Jobs database not found"
}
```

### Key Backend Functions

| Function | File | Purpose |
|---|---|---|
| `chat(body)` | `backend/src/app.py:32` | Main endpoint handler — routes to skill-gap analysis or chat |
| `find_skill_gaps(input_file_path, db_path)` | `find_skill_gaps.py:146` | Core: extracts resume skills via LLM, compares against DB |
| `extract_skills_with_ollama(text)` | `find_skill_gaps.py:54` | Sends resume text to Ollama, returns JSON skill list |
| `normalize_skill(raw)` | `find_skill_gaps.py:38` | Lowercases, resolves aliases, splits compound tokens |
| `prompt_model(model, prompt)` | `prompt_model.py:41` | Routes to Gemini or Ollama based on model name |
| `prompt_google(model, prompt)` | `prompt_model.py:55` | Calls Google Gemini API |
| `prompt_local_llm(model, prompt)` | `prompt_model.py:79` | Calls local Ollama instance |
| `format_skill_gap_result(result)` | `backend/src/app.py:26` | Formats the SkillGapResult into readable text |

### Key Frontend Functions

| Function | File | Purpose |
|---|---|---|
| `send()` | `index.html:117` | Sends message (+ PDF text) to backend via `fetch('/chat')` |
| `addMessage(role, text)` | `index.html:103` | Appends a styled chat bubble to the history |
| `escHtml(str)` | `index.html:111` | Escapes HTML entities to prevent XSS |
| PDF `change` listener | `index.html:79` | Extracts text from uploaded PDF using PDF.js |

---

## Data / Assumptions

### Data Flow (End-to-End)

```
Browser                          Frontend Container              Backend Container              Ollama Container
   │                                 │                                │                               │
   │  1. User types message           │                                │                               │
   ├─────────────────────────────▶   │                                │                               │
   │  POST /chat {message}            │                                │                               │
   │                                 │  2. Proxy request              │                               │
   │                                 ├─────────────────────────────▶  │                               │
   │                                 │  POST /chat {message}           │                               │
   │                                 │                                │  3. Route to Ollama              │
   │                                 │                                ├──────────────────────────────▶  │
   │                                 │                                │  Ollama generate()             │
   │                                 │                                │  (llama3.2 model)              │
   │                                 │                                │                               │
   │                                 │                                │  4. Return AI response           │
   │                                 │                                │◀──────────────────────────────  │
   │                                 │                                │  {"reply": "..."}              │
   │                                 │  5. Forward response           │                               │
   │                                 │◀─────────────────────────────  │                               │
   │  6. Display response            │                                │                               │
   │◀─────────────────────────────   │                                │                               │
```

**For skill-gap analysis, steps 2-4 change:**

1. Frontend sends `{ message, pdf_text }` (PDF text extracted client-side).
2. Backend writes `pdf_text` to a temporary file.
3. Backend calls `find_skill_gaps(temp_file, jobs_db)`:
   a. Sends temp file content to Ollama: *"Extract every technical skill..."*
   b. Ollama returns JSON: `["python", "docker", "sql"]`
   c. Normalizes skills: `"cpp"` → `"c++"`, splits `"ci/cd"` protected tokens.
   d. Reads `jobs_d3_eval.db` (cached), parses each job's `tech_stack` column.
   e. Computes set difference: `db_skills - file_skills` = missing skills.
   f. Computes set intersection: `db_skills & file_skills` = matching skills.
4. Returns formatted string: `"Missing skills: docker, kubernetes\nMatching skills: python, sql"`.

### Database Schema

**`jobs` table** (`jobs_d3_eval.db`):

```sql
CREATE TABLE jobs (
    source_id   TEXT PRIMARY KEY,   -- Unique job identifier
    job_title   TEXT NOT NULL,      -- Job title
    company     TEXT NOT NULL,      -- Company name
    description TEXT NOT NULL,      -- Full job description
    tech_stack  TEXT                -- Comma/slash-separated skills (e.g., "python, sql, docker")
);
```

Contains **8 job postings** from Malaysian companies (GSR Technology, Lenovo, TalentSpark, CLOUDX Digital, OrbusNeich, Software International, Envision Digital).

### Data Formats

**Between browser ↔ frontend:**
```json
{ "message": "string", "pdf_text": "string | null" }
```

**Between frontend ↔ backend:**
```json
{ "message": "string", "pdf_text": "string | null", "model": "string" }
```

**Backend response:**
```json
{ "reply": "string" }
```

**Error response:**
```json
{ "error": "string" }    // from frontend proxy
{ "detail": "string" }   // from backend (FastAPI default)
```

### Assumptions

| Area | Assumption |
|---|---|
| **PDF content** | Only text-layer PDFs work. Scanned/image PDFs without OCR produce empty text. |
| **PDF size** | No explicit limit. Large PDFs may cause browser memory issues or timeout the 120s backend request. |
| **Message length** | No maximum enforced. Very long messages may exceed the LLM's context window. |
| **AI model** | Default is `llama3.2:latest` via Ollama. Gemini is a fallback if `GOOGLE_API_KEY` is set. |
| **Database** | `jobs_d3_eval.db` is bundled with the backend. The `tech_stack` column may be empty for untagged jobs (tagging requires running `tag_data.py` with an LLM). |
| **No persistence** | Chat messages are not saved. Each page load starts fresh. No user accounts. |
| **Single user** | The system is designed for local/single-user use. No concurrency handling beyond FastAPI's async model. |

---

## Testing

### Test the Backend Directly (bypassing the frontend)

```bash
# Chat without PDF
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain Docker networking"}'

# Skill-gap analysis with PDF text
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyze", "pdf_text": "Python, Docker, SQL, Machine Learning"}'

# Skill-gap analysis with a real resume file
RESUME_TEXT=$(cat backend/src/week_2/data/resume_d3.txt)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Analyze\", \"pdf_text\": \"$RESUME_TEXT\"}"
```

### Test the Frontend Proxy

```bash
# Same requests as above, but through port 8080 instead of 8000
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello via frontend proxy"}'
```

### Expected Responses

| Test | Success Response | Error Response |
|---|---|---|
| Chat (no PDF) | `{ "reply": "Docker networking allows..." }` | `{ "detail": "Model unavailable" }` (503) |
| Skill-gap (valid PDF text) | `{ "reply": "Missing skills: ...\nMatching skills: ..." }` | — |
| Skill-gap (missing DB) | — | `{ "detail": "Jobs database not found" }` (500) |
| Frontend proxy → backend down | — | `{ "error": "..." }` (502) |

### Test the Ollama Service Directly

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Test a direct generation call
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:latest",
  "prompt": "What is Docker?",
  "stream": false
}'
```

### Reproducing Tests

1. Start the application: `docker compose up --build`
2. Wait for all three `INFO: Application startup complete.` messages.
3. Run any of the `curl` commands above.
4. For the frontend UI test, open http://localhost:8080 and send a message.

---

## Limitations

- **No user authentication** — Anyone with access to the frontend can send messages. No login, no sessions.
- **No chat history persistence** — Messages are not saved between page reloads or sessions.
- **No conversation context** — Each message is independent. The AI model does not receive prior messages, so it has no memory of the conversation.
- **Client-side PDF processing only** — PDFs are parsed in the browser by PDF.js. Scanned/image PDFs without a text layer yield empty results. No server-side PDF parsing is implemented.
- **Small AI model** — `llama3.2:latest` is a 1-2B parameter model. Responses may be short, inaccurate, or hallucinated for complex queries.
- **No Gemini configuration in docker-compose** — The Gemini fallback requires a `GOOGLE_API_KEY` set outside the compose file (for security). Without it, only Ollama is available.
- **Single-user deployment** — Designed for local use. No load balancing, horizontal scaling, or connection pooling.
- **Tagging is manual** — The `tech_stack` column in the database may be empty for untagged jobs. Populating it requires running `tag_data.py` with an LLM (either Gemini or Ollama), which takes time and API quota.
- **Temp file cleanup** — PDF text is written to a temporary file on the backend. If an exception occurs during processing, the file may linger until the container is stopped.
- **No input validation** — Message length, PDF size, and file type are not validated on the backend.

---

## Architecture Reflection

### Design Choices

**Why microservices (frontend/backend separation)?**

The application is split into two independent services because they have different responsibilities and different dependency profiles:

- The **frontend** only needs `fastapi`, `jinja2`, `httpx`, and `uvicorn` — a small, fast-to-build image.
- The **backend** additionally needs `google-genai`, `ollama`, and the entire `week_2` skill-analysis module — a larger image with more dependencies.

Separating them means:
- Each service can be updated independently (e.g., swap the chat UI without touching the AI logic).
- Each container has only the dependencies it needs, reducing attack surface and image size.
- The frontend acts as a **reverse proxy**, hiding the backend's internal address from the browser. The browser only knows about `localhost:8080`.

**Why Docker containerization?**

Docker solves the classic "it works on my machine" problem:

- **Reproducibility** — Anyone with Docker can run the exact same setup. No manual Python installation, no virtual environment conflicts, no "which version of Ollama?"
- **Isolation** — Each service runs in its own filesystem with its own dependencies. The frontend's `fastapi` version doesn't conflict with the backend's.
- **Portability** — The same `docker-compose.yml` works on Linux, macOS, and Windows.
- **GPU passthrough** — The Ollama service needs an NVIDIA GPU. Docker's device reservation (`capabilities: [gpu]`) makes this declarative and portable.

**Why Ollama (local) over an API?**

- **Privacy** — Resume data never leaves the machine. PDF text is extracted in the browser and processed locally.
- **Cost** — No per-token billing. Free and unlimited.
- **Offline** — Works without an internet connection (once the model is downloaded).

### Trade-offs

**What we prioritized:**

1. **Simplicity of deployment** — Docker Compose replaces Kubernetes, Helm charts, and CI/CD pipelines. One command (`docker compose up`) starts everything. This is perfect for a local development project but would not scale to production.
2. **Minimal frontend** — Bootstrap + vanilla JS instead of React/Vue/Angular. No build step, no Node.js, no webpack. The Dockerfile is simpler (Python-only, no `npm install`). The trade-off is no component reusability, no state management, and no hot-reload.
3. **Client-side PDF extraction** — PDF.js runs in the browser, so no resume data is ever uploaded to the server. The trade-off is that large PDFs consume browser memory and scanned PDFs are unsupported.

**What we sacrificed:**

- **Performance** — No connection pooling, no caching of LLM responses, no CDN for static assets.
- **Scalability** — Single instance of each service. No load balancing.
- **UX** — No loading spinners, no markdown rendering in responses, no keyboard shortcuts beyond Enter-to-send.
- **Reliability** — No health checks in docker-compose, no circuit breakers, no retry logic at the proxy level.

### Improvements

If given more time, the following changes would be made (in priority order):

1. **Health checks** — Add `HEALTHCHECK` directives to Dockerfiles and `condition: service_healthy` to `depends_on` in docker-compose, so services don't start until their dependencies are truly ready.

2. **Server-side PDF parsing** — Replace client-side PDF.js with a backend endpoint that accepts file uploads and parses them with `pypdf` or `pdfplumber`, supporting scanned documents via OCR (Tesseract).

3. **Conversation history** — Store messages in a database (SQLite or PostgreSQL) and pass the conversation thread to the AI model for multi-turn context.

4. **Authentication** — Add user login (JWT tokens or session cookies) to protect the API and persist user-specific data like saved resumes and chat history.

5. **Response streaming** — Use FastAPI's `StreamingResponse` to stream AI responses token-by-token instead of waiting for the full response. This makes the UI feel responsive even for slow models.

6. **Cloud deployment** — Deploy to a cloud provider (AWS ECS, Railway, or Fly.io) with proper CI/CD, environment-specific configurations, and monitoring (logs, metrics, alerts).

7. **Markdown rendering** — Render AI responses as formatted markdown (code blocks, lists, bold) instead of plain text with `<br>` tags.

8. **Rate limiting** — Add request rate limiting at the frontend proxy to prevent abuse and protect the backend from being overwhelmed.
