# K-Youth Week_1

# Objective
1. build a robust, local data engineering pipeline that successfully extracts raw data from the 0_source
2. processes and cleans it into a structured format
3. stores it in a relational database (jobs.db)

# Project Setup

## Prerequisites
- Python `3.14.x`
- `uv` `0.8.x`
- Internet access to install dependencies

## 1) Verify Python 3.14
Use Python 3.14 for this project.

```bash
python3 --version
```

Expected output starts with `Python 3.14`.

If your default `python3` is not 3.14, install Python 3.14

## 2) Install uv 0.8.x
Install/upgrade `uv` and pin it to `0.8.*`.

```bash
curl -LsSf https://astral.sh/uv/0.8.24/install.sh | sh
uv --version
```

Expected output starts with `uv 0.8`.

## 3) Create environment and install dependencies
From the `week_1` directory:

```bash
cd week_1
uv sync
```

This will create/update the project environment and install dependencies from `pyproject.toml`.

## 4) Verify tool versions
The project requires:
- Python `3.14.*`
- `uv` `0.8.*`
- `ruff` `0.15.*`

Run:

```bash
python3 --version
uv --version
uv run ruff --version
```

## 5) Format all Python code with ruff 0.15

```bash
uv run ruff format .
uv run ruff check . --fix
```

## 6) Run the pipeline
Run the full flow (ingest -> process -> load -> profile):

```bash
uv run main.py all
```

Or run only profiling:

```bash
uv run main.py profile
```

## Optional: quick environment check
If you use `make`, you can run:

```bash
make list
```

# Usage

## Required inputs
- Place raw source files in `data/0_source`
- Keep the expected folder structure under `data/`

## Command syntax

```bash
uv run main.py <command>
```

Available commands:
- `ingest`
- `process`
- `load`
- `profile`
- `all`

## Examples

Run full pipeline end-to-end:

```bash
uv run main.py all
```

Run only a single stage:

```bash
uv run main.py ingest
uv run main.py process
uv run main.py load
uv run main.py profile
```

## Expected outputs

After `ingest`:
- HTML files are created in `data/1_bronze`

After `process`:
- JSON files are created in `data/2_silver`

After `load`:
- SQLite DB is created/updated at `data/3_gold/jobs.db`
- Terminal prints a gold summary like:

```text
📊 Gold Summary:
Total: 84 | Inserted: 83 | Skipped: 1
```

After `profile`:
- Terminal prints data quality statistics like:

```text
--- 🔍 DATA QUALITY REPORT ---
📈 Total Records: 83
❓ Missing Values -> job_title: 0, company: 0, description: 0
```

## If command fails
- `Invalid input`: command argument is missing or not one of `ingest/process/load/profile/all`
- `Database not found`: run `uv run main.py load` first, then `uv run main.py profile`

# Technical Reflection

### Day 1: The Extractor (Medallion & Lakehouses)
Why is it useful to keep the original raw HTML files instead of directly inserting processed data into the database? What problems become easier to debug or recover from?
- **Answer**: INSERT ANSWER HERE