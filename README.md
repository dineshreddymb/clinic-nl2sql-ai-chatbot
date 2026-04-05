# Clinic NL2SQL Chatbot

This project is a take-home submission for an AI/ML Developer Intern assignment. It builds a Natural Language to SQL chatbot for a clinic management database using `Vanna 2.0`, `FastAPI`, `SQLite`, and `Gemini`.

The app accepts a plain-English analytics question, lets a Vanna agent generate SQL, validates that SQL, runs it against `clinic.db`, and returns rows plus any chart the agent creates.

## Chosen LLM Provider

- Provider: Google Gemini
- Vanna integration: `GeminiLlmService`
- Model: `gemini-2.5-flash`

## Project Structure

```text
.
|-- clinic_nl2sql/
|   |-- config.py
|   |-- constants.py
|   |-- logging_utils.py
|   |-- runtime.py
|   |-- schemas.py
|   |-- seed_examples.py
|   `-- sql_safety.py
|-- .env.example
|-- README.md
|-- RESULTS.md
|-- main.py
|-- memory_seed.json
|-- requirements.txt
|-- run_benchmark.py
|-- seed_memory.py
|-- setup_database.py
`-- vanna_setup.py
```

## Setup

1. Create and activate a Python 3.10+ virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file from `.env.example` and add your Gemini key:

```env
GOOGLE_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.5-flash
```

4. Create the SQLite database:

```bash
python setup_database.py
```

5. Seed the memory file with validated question-SQL examples:

```bash
python seed_memory.py
```

6. Start the API:

```bash
uvicorn main:app --port 8000
```

This matches the assignment bootstrap flow:

```bash
pip install -r requirements.txt && python setup_database.py && python seed_memory.py && uvicorn main:app --port 8000
```

## Endpoints

### `POST /chat`

Request:

```json
{
  "question": "Show me the top 5 patients by total spending"
}
```

Response shape:

```json
{
  "message": "The SQL query ran successfully and returned 5 row(s) across 3 column(s).",
  "sql_query": "SELECT ...",
  "columns": ["first_name", "last_name", "total_spending"],
  "rows": [["John", "Smith", 4200.0]],
  "row_count": 5,
  "chart": null,
  "chart_type": null
}
```

### `GET /health`

Example:

```json
{
  "status": "ok",
  "database": "connected",
  "agent_memory_items": 20,
  "provider": "gemini",
  "llm_status": "configured",
  "details": null
}
```

### `GET /ui`

This is the main browser-based chat page for the project. It sends questions directly to the working `/chat` endpoint and shows:

- the natural-language summary
- the generated SQL
- the returned table rows

Both `/ui` and `/vanna-ui` currently serve this same reliable first-party page so the interview demo path is stable.

## Architecture Overview

- `setup_database.py` creates the schema and deterministic dummy data.
- `seed_memory.py` validates 20 known-good SQL examples and writes `memory_seed.json`.
- `vanna_setup.py` builds the runtime bundle and rehydrates `DemoAgentMemory`.
- `main.py` exposes the custom FastAPI API and serves the custom browser UI.
- `clinic_nl2sql/runtime.py` contains the safe SQLite runner, trace capture, memory loading, and runtime helpers.
- `clinic_nl2sql/sql_safety.py` blocks dangerous SQL before execution.

## SQL Safety Rules

- Only read-only `SELECT` and `WITH ... SELECT` queries are allowed.
- Dangerous keywords like `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `EXEC`, `GRANT`, and `REVOKE` are blocked.
- SQLite system tables such as `sqlite_master` are blocked.
- Multiple statements separated by semicolons are blocked.

## Benchmarking

After adding a valid Gemini key, run:

```bash
python run_benchmark.py
```

That script sends the 20 assignment questions through `/chat` using FastAPI's test client and rewrites `RESULTS.md` with the live benchmark output.

## Notes

- `DemoAgentMemory` is in-memory only, so the app rehydrates it from `memory_seed.json` on startup.
- If the Gemini key is missing, the server still starts so `/health` can explain the configuration problem.
- The seeded benchmark SQL intentionally covers the same clinic reporting patterns described in the assignment so the agent has a strong starting memory.
- During live testing, Gemini free-tier quota exhaustion can return `429 RESOURCE_EXHAUSTED`. The runtime now converts that into a clearer user-facing explanation, and this is a good interview talking point about handling third-party API limits.
- Local-only artifacts such as `.env`, `docs/`, `clinic.db`, and generated query-result CSV files are intentionally excluded from the public repository.
