from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse

from clinic_nl2sql.logging_utils import configure_logging
from clinic_nl2sql.runtime import (
    check_database_status,
    create_request_context,
    explain_llm_error,
    extract_chart_payload,
    extract_message_text,
    normalize_runtime_error_message,
    validate_question_length,
)
from clinic_nl2sql.schemas import ChatRequestModel, ChatResponseModel, HealthResponseModel
from vanna_setup import get_runtime


configure_logging()
runtime = get_runtime()

app = FastAPI(
    title="Clinic NL2SQL Chatbot",
    description="FastAPI backend for a Vanna 2.0 powered clinic analytics chatbot.",
    version="1.0.0",
)


UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clinic NL2SQL Chat</title>
    <style>
        :root {
            --bg: #f7f4ea;
            --panel: #ffffff;
            --ink: #12344d;
            --muted: #6b7280;
            --accent: #0f8b8d;
            --accent-dark: #0b6470;
            --border: #d7d7d7;
            --error: #b42318;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: "Segoe UI", Tahoma, sans-serif;
            background: linear-gradient(180deg, #f7f4ea 0%, #fdfdfd 100%);
            color: var(--ink);
        }
        .shell {
            max-width: 980px;
            margin: 32px auto;
            padding: 0 20px;
        }
        .card {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 18px;
            box-shadow: 0 18px 50px rgba(18, 52, 77, 0.08);
            overflow: hidden;
        }
        .hero {
            padding: 28px 28px 18px;
            border-bottom: 1px solid var(--border);
        }
        .hero h1 {
            margin: 0 0 6px;
            font-size: 30px;
        }
        .hero p {
            margin: 0;
            color: var(--muted);
        }
        .body {
            display: grid;
            grid-template-columns: 1.1fr 0.9fr;
            gap: 0;
        }
        .pane {
            padding: 24px;
        }
        .pane + .pane {
            border-left: 1px solid var(--border);
            background: #fcfbf7;
        }
        label {
            display: block;
            font-weight: 600;
            margin-bottom: 10px;
        }
        textarea {
            width: 100%;
            min-height: 140px;
            resize: vertical;
            padding: 14px 16px;
            border: 1px solid var(--border);
            border-radius: 14px;
            font: inherit;
        }
        button {
            margin-top: 14px;
            border: 0;
            background: var(--accent);
            color: white;
            padding: 12px 18px;
            border-radius: 12px;
            font: inherit;
            font-weight: 600;
            cursor: pointer;
        }
        button:hover { background: var(--accent-dark); }
        button:disabled {
            opacity: 0.7;
            cursor: wait;
        }
        .quick {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 12px;
        }
        .quick button {
            margin-top: 0;
            background: #eef8f8;
            color: var(--accent-dark);
            border: 1px solid #ccebea;
            padding: 8px 12px;
            font-size: 14px;
        }
        .status {
            min-height: 22px;
            margin-top: 12px;
            color: var(--muted);
            font-size: 14px;
        }
        .status.error { color: var(--error); }
        .section-title {
            font-size: 12px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--muted);
            margin: 0 0 8px;
        }
        .result-box {
            border: 1px solid var(--border);
            border-radius: 14px;
            background: white;
            padding: 14px;
            margin-bottom: 16px;
        }
        pre {
            margin: 0;
            white-space: pre-wrap;
            word-break: break-word;
            font-family: Consolas, monospace;
            font-size: 13px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        th, td {
            border-bottom: 1px solid var(--border);
            padding: 8px;
            text-align: left;
            vertical-align: top;
        }
        th { background: #f7fafb; }
        .hint {
            color: var(--muted);
            font-size: 13px;
            margin-top: 8px;
        }
        @media (max-width: 820px) {
            .body { grid-template-columns: 1fr; }
            .pane + .pane { border-left: 0; border-top: 1px solid var(--border); }
        }
    </style>
</head>
<body>
    <div class="shell">
        <div class="card">
            <div class="hero">
                <h1>Clinic NL2SQL Chat</h1>
                <p>Ask a question in plain English. The app will generate SQL, run it safely, and show the result.</p>
            </div>
            <div class="body">
                <div class="pane">
                    <label for="question">Question</label>
                    <textarea id="question" placeholder="Example: Show revenue by doctor"></textarea>
                    <button id="ask-btn" type="button">Ask Question</button>
                    <div class="quick">
                        <button type="button" data-question="How many patients do we have?">Patient Count</button>
                        <button type="button" data-question="List all doctors and their specializations">Doctors</button>
                        <button type="button" data-question="Show revenue by doctor">Revenue By Doctor</button>
                        <button type="button" data-question="Top 5 patients by spending">Top Patients</button>
                    </div>
                    <div id="status" class="status"></div>
                    <div class="hint">Main API docs are still available at <code>/docs</code>. Optional built-in Vanna UI is at <code>/vanna-ui/</code>.</div>
                </div>
                <div class="pane">
                    <div class="section-title">Summary</div>
                    <div class="result-box"><pre id="message">No response yet.</pre></div>
                    <div class="section-title">Generated SQL</div>
                    <div class="result-box"><pre id="sql">No SQL yet.</pre></div>
                    <div class="section-title">Rows</div>
                    <div class="result-box" id="table-wrap">No rows yet.</div>
                </div>
            </div>
        </div>
    </div>
    <script>
        const questionInput = document.getElementById("question");
        const askBtn = document.getElementById("ask-btn");
        const statusEl = document.getElementById("status");
        const messageEl = document.getElementById("message");
        const sqlEl = document.getElementById("sql");
        const tableWrap = document.getElementById("table-wrap");

        function setStatus(text, isError = false) {
            statusEl.textContent = text;
            statusEl.className = isError ? "status error" : "status";
        }

        function renderRows(columns, rows) {
            if (!rows || rows.length === 0) {
                tableWrap.textContent = "No rows returned.";
                return;
            }

            const table = document.createElement("table");
            const thead = document.createElement("thead");
            const headRow = document.createElement("tr");
            columns.forEach((column) => {
                const th = document.createElement("th");
                th.textContent = column;
                headRow.appendChild(th);
            });
            thead.appendChild(headRow);
            table.appendChild(thead);

            const tbody = document.createElement("tbody");
            rows.forEach((row) => {
                const tr = document.createElement("tr");
                row.forEach((value) => {
                    const td = document.createElement("td");
                    td.textContent = value === null ? "null" : String(value);
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);

            tableWrap.innerHTML = "";
            tableWrap.appendChild(table);
        }

        async function askQuestion() {
            const question = questionInput.value.trim();
            if (!question) {
                setStatus("Please enter a question first.", true);
                return;
            }

            askBtn.disabled = true;
            setStatus("Running your question...");
            messageEl.textContent = "Waiting for response...";
            sqlEl.textContent = "Generating SQL...";
            tableWrap.textContent = "Loading rows...";

            try {
                const response = await fetch("/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ question }),
                });

                const payload = await response.json();
                if (!response.ok) {
                    throw new Error(payload.detail || "Request failed.");
                }

                messageEl.textContent = payload.message || "No summary returned.";
                sqlEl.textContent = payload.sql_query || "No SQL returned.";
                renderRows(payload.columns || [], payload.rows || []);
                setStatus("Completed successfully.");
            } catch (error) {
                messageEl.textContent = "Request failed.";
                sqlEl.textContent = "No SQL returned.";
                tableWrap.textContent = "No rows returned.";
                setStatus(error.message || "Request failed.", true);
            } finally {
                askBtn.disabled = false;
            }
        }

        askBtn.addEventListener("click", askQuestion);
        questionInput.addEventListener("keydown", (event) => {
            if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                askQuestion();
            }
        });
        document.querySelectorAll("[data-question]").forEach((button) => {
            button.addEventListener("click", () => {
                questionInput.value = button.dataset.question;
                askQuestion();
            });
        });
    </script>
</body>
</html>
"""


@app.get("/", tags=["meta"])
async def root() -> JSONResponse:
    return JSONResponse(
        {
            "message": "Clinic NL2SQL chatbot is running.",
            "docs": "/docs",
            "health": "/health",
            "ui": "/ui" if runtime.ui_app is not None else None,
        }
    )


@app.get("/ui", response_class=HTMLResponse, tags=["meta"])
@app.get("/ui/", response_class=HTMLResponse, tags=["meta"])
@app.get("/vanna-ui", response_class=HTMLResponse, tags=["meta"])
@app.get("/vanna-ui/", response_class=HTMLResponse, tags=["meta"])
async def ui_page() -> HTMLResponse:
    return HTMLResponse(
        UI_HTML,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/health", response_model=HealthResponseModel, tags=["meta"])
async def health() -> HealthResponseModel:
    database_status = check_database_status(str(runtime.settings.database_path))
    llm_status = "configured" if runtime.agent is not None else "not_configured"
    details = runtime.startup_error
    overall_status = "ok" if database_status == "connected" and runtime.agent is not None else "degraded"

    return HealthResponseModel(
        status=overall_status,
        database=database_status,
        agent_memory_items=runtime.tool_memory_count,
        provider=runtime.settings.provider,
        llm_status=llm_status,
        details=details,
    )


@app.post("/chat", response_model=ChatResponseModel, tags=["chat"])
async def chat(payload: ChatRequestModel) -> ChatResponseModel:
    try:
        validate_question_length(payload.question, runtime.settings.max_question_length)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if runtime.agent is None:
        raise HTTPException(
            status_code=503,
            detail=runtime.startup_error or "The LLM runtime is not configured.",
        )

    conversation_id = str(uuid.uuid4())
    request_context = create_request_context(conversation_id)

    try:
        components = [
            component
            async for component in runtime.agent.send_message(
                request_context=request_context,
                message=payload.question,
                conversation_id=conversation_id,
            )
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=normalize_runtime_error_message(exc)) from exc

    trace = runtime.trace_store.pop(conversation_id)
    llm_error_message = runtime.llm_error_store.pop()
    chart, chart_type = extract_chart_payload(components)
    message = extract_message_text(components, trace)

    if trace is None:
        friendly_llm_error = explain_llm_error(llm_error_message)
        return ChatResponseModel(
            message=friendly_llm_error or message,
            sql_query=None,
            columns=[],
            rows=[],
            row_count=0,
            chart=chart,
            chart_type=chart_type,
        )

    if trace["row_count"] == 0 and "no data" not in message.lower():
        message = "No data found for that question."

    return ChatResponseModel(
        message=message,
        sql_query=trace["sql_query"],
        columns=trace["columns"],
        rows=trace["rows"],
        row_count=trace["row_count"],
        chart=chart,
        chart_type=chart_type,
    )


# The built-in Vanna UI is intentionally not mounted now.
# Both /ui and /vanna-ui serve the simpler first-party chat page above,
# which directly calls the working /chat endpoint.
