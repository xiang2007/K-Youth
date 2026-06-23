# K-Youth Week 2

## Project Overview

week_2 analyzes job descriptions and compares them with a resume. It has two parts:

- `tag_data.py` extracts a tech stack from each job description and stores it in SQLite.
- `find_skill_gaps.py` compares the database skills against the skills listed in a resume text file.

The project can use Gemini through the Google API or fall back to a local Ollama model.

## Setup Instructions

### Prerequisites

- Python 3.14
- `uv` 0.8.x
- Ollama, if you want local LLM fallback
- A Google Gemini API key in `GOOGLE_API_KEY`, if you want Gemini-backed extraction

### Install dependencies

From the `week_2` directory:

```bash
cd week_2
uv sync
```

If you plan to use Gemini, set the environment variable before running the scripts:

```bash
export GOOGLE_API_KEY="your_api_key_here"
```

If you plan to use Ollama, make sure the service is running and the fallback model exists:

```bash
ollama serve
ollama pull llama3.1:latest
```

## Usage

Run commands from `week_2`:

```bash
uv run tag_data.py
uv run find_skill_gaps.py
```

`tag_data.py` expects a SQLite database at `data/jobs_d1.db` and updates the `jobs.tech_stack` column with extracted technologies.

`find_skill_gaps.py` reads the resume text from `data/resume_d3.txt` and the evaluation database from `data/jobs_d3_eval.db`, then prints the missing skills and overlapping skills.

Expected outputs:

- `tag_data.py` prints per-batch tagging progress and token usage.
- `find_skill_gaps.py` prints a `gaps` list and a `skill` list.

## API / Function Reference

### `prompt_model.py`

- `ModelResult`: dataclass that stores model text, total token count, and elapsed time.
- `prompt_model_extra(model, prompt)`: routes a prompt to Gemini or Ollama and returns a `ModelResult`.
- `prompt_model(model, prompt)`: returns only the generated text.
- `prompt_google(model, prompt)`: calls Gemini and measures runtime and token usage.
- `prompt_local_llm(model, prompt)`: calls Ollama and measures runtime and token usage.

### `tag_data.py`

- `calculate_batch_size(...)`: estimates the next batch size from the model token budget.
- `RateLimiter`: enforces requests-per-minute spacing between LLM calls.
- `call_with_retry(...)`: retries a failed model call with exponential backoff.
- `fetch_next_batch(cursor, batch_size, offset)`: reads the next batch of jobs from SQLite.
- `process_response(cursor, text)`: parses `ID|tech1, tech2` lines and writes them to the database.
- `tag_data(db_url, model=..., max_retries=..., retry_base_delay=...)`: tags every job row in the database.

### `find_skill_gaps.py`

- `normalize_skill(raw)`: canonicalizes one raw skill token.
- `read_input_file(input_file_path)`: finds the resume line containing `Technical Skill`.
- `get_file_techStack(fileContent)`: splits the resume skill line into tokens.
- `parse_infile(input_file_path)`: turns the resume file into a normalized skill set.
- `extractDBSkill(tech_stack, techSet)`: merges one database stack string into the skill set.
- `getDbSkill(db_path)`: collects all skills from the SQLite database.
- `find_skill_gaps(input_file_path, db_path)`: returns a `SkillGapResult` with `gaps` and `skill`.

## Data / Assumptions

The tagging workflow assumes a SQLite database with a `jobs` table that contains `source_id`, `description`, and a writable `tech_stack` column. The prompt is based only on the job description text, and the model output is expected to be one or more `ID|tech1, tech2` lines.

The gap-analysis workflow assumes the resume file contains a line starting with `Technical Skill`, and that database tech stacks are comma-separated lists. It also assumes the token normalization rules in `find_skill_gaps.py` are sufficient for variants like `C/C++`, `CI/CD`, and `A/B testing`.

Current simplifications:

- Input file paths are hardcoded in the script entry points.
- Output parsing depends on the model following the exact `ID|...` format.
- The comparison logic is set-based, so it does not track skill frequency or context.

## Testing

Validation was done by running the scripts directly with `uv` and checking their output.

Scenarios used:

- `cd week_2 && uv run tag_data.py`
- `cd week_2 && uv run find_skill_gaps.py`

The tagging script was run successfully in this workspace and exited with code `0`.

## Limitations

- `tag_data.py` depends on the database schema already containing a `jobs` table and a writable `tech_stack` column.
- The model output must stay close to the requested `ID|tech1, tech2` format or rows may be skipped.
- Gemini and Ollama can produce different wording or formatting, so tagging results are not perfectly deterministic.
- The scripts are not parameterized through CLI flags, which makes them less flexible for reuse on other datasets.

## Architecture Reflection

The code is split into small modules because the project has three distinct responsibilities: prompt construction, database tagging, and skill comparison. That separation keeps the LLM-specific logic isolated from the parsing and normalization logic, which makes the workflow easier to reason about and modify.

The main trade-off is that the implementation stays simple and local instead of introducing a larger orchestration layer. That makes it easier to run and debug, but it also means the scripts rely on hardcoded paths and format assumptions.

If I had more time, I would make the scripts accept CLI arguments for input and output paths, add tests for the token normalization rules, and validate the model response format before writing to SQLite.