from typing import Any

from pydantic import BaseModel, Field, field_validator


class ChatRequestModel(BaseModel):
    question: str = Field(..., description="Natural language question to convert into SQL")

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        question = value.strip()
        if not question:
            raise ValueError("Question must not be empty.")
        return question


class ChatResponseModel(BaseModel):
    message: str
    sql_query: str | None
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    chart: dict[str, Any] | None = None
    chart_type: str | None = None


class HealthResponseModel(BaseModel):
    status: str
    database: str
    agent_memory_items: int
    provider: str
    llm_status: str
    details: str | None = None
