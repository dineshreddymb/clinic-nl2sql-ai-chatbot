from __future__ import annotations

import json
import sqlite3

from clinic_nl2sql.config import get_settings
from clinic_nl2sql.logging_utils import configure_logging
from clinic_nl2sql.seed_examples import SCHEMA_TEXT_MEMORIES, SEED_EXAMPLES
from clinic_nl2sql.sql_safety import validate_select_sql


def main() -> None:
    configure_logging()
    settings = get_settings()

    if not settings.database_path.exists():
        raise FileNotFoundError(
            f"Database not found at {settings.database_path}. Run setup_database.py first."
        )

    conn = sqlite3.connect(settings.database_path)
    validation_summaries: list[dict[str, object]] = []

    for example in SEED_EXAMPLES:
        validated_sql = validate_select_sql(example["sql"])
        cursor = conn.execute(validated_sql)
        rows = cursor.fetchmany(3)
        validation_summaries.append(
            {
                "question": example["question"],
                "sql": validated_sql,
                "category": example["category"],
                "preview_row_count": len(rows),
                "columns": [column[0] for column in cursor.description] if cursor.description else [],
            }
        )

    conn.close()

    payload = {
        "provider": settings.provider,
        "tool_memories": SEED_EXAMPLES,
        "text_memories": SCHEMA_TEXT_MEMORIES,
        "validation_preview": validation_summaries,
    }
    settings.memory_seed_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(
        f"Validated {len(SEED_EXAMPLES)} seed SQL pairs and wrote "
        f"{settings.memory_seed_path.name} with {len(SCHEMA_TEXT_MEMORIES)} text memories."
    )


if __name__ == "__main__":
    main()
