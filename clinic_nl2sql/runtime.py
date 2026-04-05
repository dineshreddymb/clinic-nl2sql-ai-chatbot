from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import logging
import sqlite3
import threading
from threading import Lock
from typing import Any
import uuid

import pandas as pd
from vanna import Agent, AgentConfig
from vanna.capabilities.sql_runner import RunSqlToolArgs, SqlRunner
from vanna.core.registry import ToolRegistry
from vanna.core.tool import ToolContext
from vanna.core.user import RequestContext, User, UserResolver
from vanna.integrations.google import GeminiLlmService
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.servers.fastapi import VannaFastAPIServer
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.agent_memory import SaveQuestionToolArgsTool, SearchSavedCorrectToolUsesTool

from clinic_nl2sql.config import Settings
from clinic_nl2sql.seed_examples import SCHEMA_TEXT_MEMORIES, SEED_EXAMPLES
from clinic_nl2sql.sql_safety import SqlValidationError, validate_select_sql


LOGGER = logging.getLogger(__name__)


class DefaultClinicUserResolver(UserResolver):
    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(
            id="default-user",
            email="default@example.com",
            username="default-user",
            group_memberships=["admin", "user"],
        )


class ExecutionTraceStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._traces: dict[str, dict[str, Any]] = {}

    def set(self, conversation_id: str, value: dict[str, Any]) -> None:
        with self._lock:
            self._traces[conversation_id] = value

    def pop(self, conversation_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._traces.pop(conversation_id, None)


class LlmErrorStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._message: str | None = None

    def set(self, message: str) -> None:
        with self._lock:
            self._message = message

    def pop(self) -> str | None:
        with self._lock:
            message = self._message
            self._message = None
            return message

    def clear(self) -> None:
        with self._lock:
            self._message = None


class TrackingGeminiLlmService(GeminiLlmService):
    def __init__(self, error_store: LlmErrorStore, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.error_store = error_store

    async def send_request(self, request: Any) -> Any:
        self.error_store.clear()
        try:
            return await super().send_request(request)
        except Exception as exc:
            self.error_store.set(str(exc))
            raise

    async def stream_request(self, request: Any) -> Any:
        self.error_store.clear()
        try:
            async for chunk in super().stream_request(request):
                yield chunk
        except Exception as exc:
            self.error_store.set(str(exc))
            raise


class SafeSqliteRunner(SqlRunner):
    def __init__(self, database_path: str, trace_store: ExecutionTraceStore) -> None:
        self.database_path = database_path
        self.trace_store = trace_store

    async def run_sql(self, args: RunSqlToolArgs, context: ToolContext) -> pd.DataFrame:
        validated_sql = validate_select_sql(args.sql)
        LOGGER.info("Executing validated SQL for request_id=%s", context.request_id)

        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        try:
            dataframe = pd.read_sql_query(validated_sql, conn)
        except Exception:
            self.trace_store.set(
                context.conversation_id,
                {
                    "sql_query": validated_sql,
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "error": True,
                },
            )
            raise
        finally:
            conn.close()

        rows = [list(row) for row in dataframe.itertuples(index=False, name=None)]
        self.trace_store.set(
            context.conversation_id,
            {
                "sql_query": validated_sql,
                "columns": dataframe.columns.tolist(),
                "rows": rows,
                "row_count": len(rows),
                "error": False,
            },
        )
        return dataframe


@dataclass
class RuntimeBundle:
    settings: Settings
    trace_store: ExecutionTraceStore
    llm_error_store: LlmErrorStore
    agent_memory: DemoAgentMemory
    agent: Agent | None
    ui_app: Any | None
    tool_memory_count: int
    text_memory_count: int
    startup_error: str | None = None


def _load_seed_payload(settings: Settings) -> dict[str, Any]:
    if settings.memory_seed_path.exists():
        return json.loads(settings.memory_seed_path.read_text(encoding="utf-8"))

    return {
        "tool_memories": SEED_EXAMPLES,
        "text_memories": SCHEMA_TEXT_MEMORIES,
    }


async def _seed_agent_memory(agent_memory: DemoAgentMemory, settings: Settings) -> tuple[int, int]:
    seed_payload = _load_seed_payload(settings)
    tool_memories = seed_payload.get("tool_memories", SEED_EXAMPLES)
    text_memories = seed_payload.get("text_memories", SCHEMA_TEXT_MEMORIES)

    bootstrap_user = User(
        id="seed-user",
        email="seed@example.com",
        username="seed-user",
        group_memberships=["admin", "user"],
    )
    context = ToolContext(
        user=bootstrap_user,
        conversation_id="seed-conversation",
        request_id=str(uuid.uuid4()),
        agent_memory=agent_memory,
    )

    for memory_text in text_memories:
        await agent_memory.save_text_memory(memory_text, context)

    for example in tool_memories:
        await agent_memory.save_tool_usage(
            question=example["question"],
            tool_name="run_sql",
            args={"sql": example["sql"]},
            context=context,
            success=True,
            metadata={"seeded": True, "category": example["category"]},
        )

    return len(tool_memories), len(text_memories)


def _run_coroutine_safely(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:  # pragma: no cover
            error["value"] = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()

    if "value" in error:
        raise error["value"]

    return result["value"]


def extract_chart_payload(components: list[Any]) -> tuple[dict[str, Any] | None, str | None]:
    for component in components:
        rich_component = getattr(component, "rich_component", None)
        if rich_component is None:
            continue

        rich_type = getattr(rich_component, "type", None)
        if str(rich_type).lower().endswith("chart"):
            chart_payload = {
                "data": getattr(rich_component, "data", None),
                "title": getattr(rich_component, "title", None),
                "config": getattr(rich_component, "config", {}),
            }
            chart_type = None
            if isinstance(chart_payload["data"], dict):
                data_series = chart_payload["data"].get("data", [])
                if data_series:
                    chart_type = data_series[0].get("type")
            return chart_payload, chart_type or getattr(rich_component, "chart_type", None)

    return None, None


def extract_message_text(components: list[Any], trace: dict[str, Any] | None) -> str:
    messages: list[str] = []
    for component in components:
        simple_component = getattr(component, "simple_component", None)
        text = getattr(simple_component, "text", None)
        if text:
            cleaned = text.strip()
            if cleaned and cleaned not in messages:
                messages.append(cleaned)

    if messages:
        return messages[-1]

    if trace is None:
        return "The request completed without a model summary."

    if trace["row_count"] == 0:
        return "The SQL query ran successfully, but no data matched the question."

    return (
        f"The SQL query ran successfully and returned {trace['row_count']} row(s) "
        f"across {len(trace['columns'])} column(s)."
    )


def create_request_context(request_id: str) -> RequestContext:
    return RequestContext(
        cookies={},
        headers={},
        remote_addr="127.0.0.1",
        query_params={},
        metadata={"request_id": request_id},
    )


def build_runtime(settings: Settings) -> RuntimeBundle:
    trace_store = ExecutionTraceStore()
    llm_error_store = LlmErrorStore()
    agent_memory = DemoAgentMemory(max_items=5000)
    tool_memory_count, text_memory_count = _run_coroutine_safely(
        _seed_agent_memory(agent_memory, settings)
    )

    if not settings.llm_configured:
        return RuntimeBundle(
            settings=settings,
            trace_store=trace_store,
            llm_error_store=llm_error_store,
            agent_memory=agent_memory,
            agent=None,
            ui_app=None,
            tool_memory_count=tool_memory_count,
            text_memory_count=text_memory_count,
            startup_error="GOOGLE_API_KEY is not configured. Add it to your environment or .env file.",
        )

    try:
        llm_service = TrackingGeminiLlmService(
            llm_error_store,
            model=settings.gemini_model,
            api_key=settings.google_api_key,
            temperature=0.1,
        )

        tool_registry = ToolRegistry()
        tool_registry.register_local_tool(
            RunSqlTool(sql_runner=SafeSqliteRunner(str(settings.database_path), trace_store)),
            access_groups=["admin", "user"],
        )
        tool_registry.register_local_tool(VisualizeDataTool(), access_groups=["admin", "user"])
        tool_registry.register_local_tool(
            SaveQuestionToolArgsTool(),
            access_groups=["admin", "user"],
        )
        tool_registry.register_local_tool(
            SearchSavedCorrectToolUsesTool(),
            access_groups=["admin", "user"],
        )

        agent = Agent(
            llm_service=llm_service,
            tool_registry=tool_registry,
            user_resolver=DefaultClinicUserResolver(),
            agent_memory=agent_memory,
            config=AgentConfig(temperature=0.1),
        )
        ui_app = VannaFastAPIServer(
            agent,
            config={
                "api_base_url": "/vanna-ui",
            },
        ).create_app()

        return RuntimeBundle(
            settings=settings,
            trace_store=trace_store,
            llm_error_store=llm_error_store,
            agent_memory=agent_memory,
            agent=agent,
            ui_app=ui_app,
            tool_memory_count=tool_memory_count,
            text_memory_count=text_memory_count,
        )
    except Exception as exc:
        LOGGER.exception("Failed to initialize the Vanna runtime.")
        return RuntimeBundle(
            settings=settings,
            trace_store=trace_store,
            llm_error_store=llm_error_store,
            agent_memory=agent_memory,
            agent=None,
            ui_app=None,
            tool_memory_count=tool_memory_count,
            text_memory_count=text_memory_count,
            startup_error=str(exc),
        )


def check_database_status(database_path: str) -> str:
    try:
        conn = sqlite3.connect(database_path)
        conn.execute("SELECT 1")
        conn.close()
        return "connected"
    except Exception:
        return "disconnected"


def validate_question_length(question: str, max_question_length: int) -> None:
    if len(question.strip()) > max_question_length:
        raise ValueError(f"Question must be {max_question_length} characters or fewer.")


def normalize_runtime_error_message(exc: Exception) -> str:
    if isinstance(exc, SqlValidationError):
        return str(exc)
    return "The system could not complete the request. Please review the question and try again."


def explain_llm_error(message: str | None) -> str | None:
    if not message:
        return None

    lowered = message.lower()
    if "resource_exhausted" in lowered or "quota exceeded" in lowered or "429" in lowered:
        return (
            "Gemini quota exceeded for the current API key. Wait a bit and retry, "
            "or use a different Gemini key/project, or switch to another approved provider."
        )

    return message
