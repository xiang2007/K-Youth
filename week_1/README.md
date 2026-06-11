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
- **Answer**: Keeping the original raw HTML files is valuable because they serve as an immutable source of truth. If a parsing bug, schema  change, or data quality issue is discovered later, you can reprocess the raw files without needing to re-scrape the website. This prevents data loss and allows the pipeline to evolve while preserving access to the original content.Raw files also make debugging and recovery much easier. When incorrect records appear in the database, engineers can compare the processed output against the original HTML to determine whether the problem came from data collection, parsing, transformation, or loading. If a database is corrupted or processing logic changes, the raw files enable a full rebuild of downstream datasets, improving reliability and reproducibility.

### Day 2: Treatment Plant (ETL vs ELT & Scale)
- **Answer**: Cloud systems often prefer ELT (Extract, Load, Transform) because storage is relatively inexpensive and keeping raw data preserves flexibility. By loading data first, teams can apply different transformation rules later, reprocess historical data when requirements change, and avoid losing information due to mistakes in early cleaning steps. This approach also supports multiple use cases from the same raw dataset.

### Day 3: The Blueprint & The Vault (Storage & Contracts)
- **Answer**: If an important field such as job_title disappears, the pipeline should fail validation and stop processing rather than loading incomplete records. A missing required field often indicates a schema change, extraction bug, or upstream data issue. Failing early makes the problem immediately visible so it can be investigated and fixed before bad data spreads through reports, dashboards, or downstream systems. Silently inserting NULL values can hide data quality problems and lead to incorrect analytics or business decisions. Similarly, INSERT OR IGNORE helps maintain data integrity by preventing duplicate records from being inserted when the same data is loaded multiple times.

### Day 4: The QA Inspector & Orchestrator (Orchestration & DAGs)
**Answer**: If processor.py crashes halfway through execution, some files may be processed while others remain unfinished, leaving the pipeline in a partially completed state. Manual recovery usually requires checking which steps succeeded, rerunning scripts, and ensuring duplicate or inconsistent data is not introduced. Automated orchestration tools such as Apache Airflow are more reliable because they track task status, manage dependencies, and automatically retry failed tasks.