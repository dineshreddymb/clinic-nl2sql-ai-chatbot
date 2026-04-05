# Clinic NL2SQL Chatbot

A Natural Language to SQL analytics assistant for a clinic management database, built with `Vanna 2.0`, `FastAPI`, `SQLite`, and `Google Gemini`.

This project lets a user ask clinic analytics questions in plain English, converts that question into SQL, validates the SQL for safety, executes it against a local clinic database, and returns a readable answer with the generated query and result rows.

## Problem Statement

Many healthcare and clinic teams store useful operational data inside relational databases, but the people who need answers are often not comfortable writing SQL. Clinic managers, operations staff, and non-technical stakeholders still need quick answers to questions such as:

- How many patients visited this month?
- Which doctor generated the most revenue?
- What are the most common appointment statuses?
- Which patients spent the most on treatments?

In practice, these questions usually depend on engineers, analysts, or manually written reports. That creates delays, bottlenecks, and poor visibility into day-to-day clinic performance.

This project addresses that gap by providing a safe natural-language interface over structured clinic data.

## What This Project Solves

The system is designed to solve four practical problems:

1. It removes the need for end users to write SQL manually.
2. It shortens the time between a business question and an answer.
3. It adds guardrails so LLM-generated SQL is restricted to safe read-only queries.
4. It provides a demo-ready API and browser UI that clearly show the full NL-to-SQL flow.

## Why This Matters

Natural language interfaces for databases are useful only when they are:

- accurate enough to answer common business questions
- safe enough not to mutate or damage the database
- observable enough to show what SQL was generated
- simple enough for non-technical users to adopt

This project focuses on those fundamentals instead of trying to be a generic chatbot. It is intentionally built around a clinic analytics use case so the behavior is easier to evaluate, benchmark, and explain.

## Solution Overview

The application accepts a plain-English analytics request, routes it through a Vanna-powered runtime backed by Gemini, validates the generated SQL using explicit safety rules, runs the query on SQLite, and returns a structured JSON response.

The project includes:

- a FastAPI backend
- a browser-based chat UI at `/ui`
- a health-check endpoint at `/health`
- seeded memory examples to improve SQL generation quality
- a benchmark script to test the chatbot on a fixed set of questions

## Example Questions

The chatbot is intended for questions like:

- "How many patients do we have?"
- "Show revenue by doctor"
- "Top 5 patients by total spending"
- "List all doctors and their specializations"
- "Which appointment status appears most often?"

## End-to-End Workflow

1. A user sends a natural-language question to `POST /chat`.
2. The runtime sends the question to the Vanna agent backed by Gemini.
3. The agent generates SQL using the seeded examples and schema context.
4. The application validates the SQL before execution.
5. If the SQL is safe, it runs against the local `clinic.db` SQLite database.
6. The API returns:
   - a natural-language summary
   - the generated SQL
   - result columns
   - result rows
   - optional chart metadata if available

This makes the system easy to inspect during demos or interviews because the generated SQL is visible instead of hidden.

## Key Features

- Natural language to SQL conversion for clinic reporting questions
- Read-only SQL enforcement through custom validation
- FastAPI endpoints for chat, health checks, and browser access
- Lightweight SQLite setup for easy local execution
- Seeded memory examples to improve consistency on known question types
- Benchmark runner for repeatable evaluation
- Simple first-party UI for non-technical interaction

## Project Architecture

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

### File Responsibilities

- `main.py`: FastAPI app, API routes, and browser UI
- `vanna_setup.py`: runtime construction and Vanna agent setup
- `setup_database.py`: creates the clinic schema and sample data
- `seed_memory.py`: writes validated question-SQL examples to `memory_seed.json`
- `run_benchmark.py`: runs benchmark questions through the app and rewrites `RESULTS.md`
- `clinic_nl2sql/runtime.py`: runtime orchestration, execution helpers, and error handling
- `clinic_nl2sql/sql_safety.py`: SQL validation and blocking rules
- `clinic_nl2sql/seed_examples.py`: curated NL-to-SQL examples used for memory seeding

## Chosen LLM Provider

- Provider: Google Gemini
- Vanna integration: `GeminiLlmService`
- Model: `gemini-2.5-flash`

This choice keeps the stack modern, fast, and accessible for local experimentation while still supporting strong language understanding for query generation.

## API Endpoints

### `POST /chat`

Accepts a user question and returns the generated SQL plus execution results.

Example request:

```json
{
  "question": "Show me the top 5 patients by total spending"
}
```

Example response shape:

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

Returns application health and runtime configuration status.

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

Serves the main browser-based chat interface for asking questions and inspecting:

- the generated summary
- the SQL query
- the returned table rows

### `GET /docs`

FastAPI's automatic Swagger UI for testing endpoints interactively.

### `GET /vanna-ui`

Currently routed to the same stable first-party page used by `/ui`.

## SQL Safety Design

One of the most important parts of any NL-to-SQL system is controlling what the model is allowed to execute.

This project blocks unsafe behavior by allowing only read-only query patterns.

### Enforced Safety Rules

- Only `SELECT` and `WITH ... SELECT` queries are allowed
- Destructive keywords such as `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `EXEC`, `GRANT`, and `REVOKE` are blocked
- SQLite system tables like `sqlite_master` are blocked
- Multiple SQL statements separated by semicolons are blocked

These checks reduce the risk of accidental data mutation and make the app safer for demonstrations and controlled analytics use cases.

## Benchmarking and Evaluation

The project includes a repeatable benchmark flow based on the seeded assignment questions.

Run:

```bash
python run_benchmark.py
```

This script:

- spins up the FastAPI app through the test client
- sends the benchmark questions to `POST /chat`
- compares the returned SQL with the expected SQL
- rewrites `RESULTS.md` with the latest benchmark output

This makes the project easier to evaluate in an interview or take-home setting because there is a fixed test set instead of purely anecdotal examples.

## Setup

### Prerequisites

- Python 3.10 or newer
- A valid Gemini API key

### Installation

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file from `.env.example`:

```env
GOOGLE_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.5-flash
```

4. Create the database:

```bash
python setup_database.py
```

5. Seed the memory examples:

```bash
python seed_memory.py
```

6. Start the API:

```bash
uvicorn main:app --port 8000
```

Matching assignment bootstrap flow:

```bash
pip install -r requirements.txt && python setup_database.py && python seed_memory.py && uvicorn main:app --port 8000
```

## Tech Stack

- Python
- FastAPI
- SQLite
- Vanna 2.0
- Google Gemini
- Pandas
- Plotly

## Design Choices

### Why SQLite?

SQLite keeps the project easy to run locally, easy to inspect, and easy to reset during development or evaluation.

### Why seeded memory?

LLM-based SQL generation is more reliable when the model sees validated examples from the same problem domain. The seeded memory helps the agent stay aligned with expected clinic reporting patterns.

### Why return SQL to the user?

Showing the SQL improves transparency, debugging, and trust. A reviewer can inspect whether the natural-language interpretation actually matches the query being executed.

## Current Limitations

- The project is scoped to a clinic reporting schema rather than a fully generic database assistant
- Accuracy still depends on LLM behavior and the strength of the seeded examples
- SQLite is great for demos, but not a production multi-user analytics backend
- Benchmark quality is tied to the included question set and does not cover every phrasing variation
- If the Gemini quota is exhausted, requests can fail until quota is available again

## Future Improvements

- Add richer schema-aware prompting for better generalization
- Support follow-up conversational context across multiple questions
- Add authentication and role-based query access
- Improve result visualization in the browser UI
- Add broader evaluation datasets and failure-category reporting
- Support other SQL databases such as PostgreSQL or MySQL

## Notes

- `DemoAgentMemory` is in-memory only, so the app rehydrates it from `memory_seed.json` on startup
- If the Gemini key is missing, the server still starts so `/health` can explain the configuration problem
- During live testing, Gemini free-tier quota exhaustion can return `429 RESOURCE_EXHAUSTED`
- Local-only artifacts such as `.env`, `docs/`, `clinic.db`, and generated query-result CSV files are intentionally excluded from the public repository

## Repository Hygiene

The following files are intentionally not pushed to the public repository:

- `.env`
- `docs/`
- generated query result CSV files
- local database artifacts such as `clinic.db`

This keeps secrets and machine-specific generated files out of version control while preserving the code and reproducible setup steps.
