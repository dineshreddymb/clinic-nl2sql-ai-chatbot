from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from clinic_nl2sql.seed_examples import SEED_EXAMPLES
from clinic_nl2sql.sql_safety import normalize_sql
from main import app
from vanna_setup import get_runtime


def render_results_markdown(results: list[dict[str, object]], passed_count: int) -> str:
    lines = [
        "# RESULTS",
        "",
        f"Generated on: {datetime.now().isoformat(timespec='seconds')}",
        "",
        f"Passed {passed_count} out of {len(results)} benchmark questions.",
        "",
    ]

    for index, result in enumerate(results, start=1):
        lines.extend(
            [
                f"## {index}. {result['question']}",
                "",
                f"- Status: {'PASS' if result['passed'] else 'FAIL'}",
                f"- HTTP status: {result['http_status']}",
                f"- Expected SQL: `{result['expected_sql']}`",
                f"- Actual SQL: `{result['actual_sql']}`",
                f"- Summary: {result['summary']}",
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    runtime = get_runtime()
    if runtime.agent is None:
        print("Cannot run benchmark because the Gemini runtime is not configured. Set GOOGLE_API_KEY first.")
        raise SystemExit(1)

    client = TestClient(app)
    results: list[dict[str, object]] = []
    passed_count = 0

    for example in SEED_EXAMPLES:
        response = client.post("/chat", json={"question": example["question"]})
        payload = response.json()

        actual_sql = payload.get("sql_query") if isinstance(payload, dict) else None
        normalized_actual = normalize_sql(actual_sql or "") if actual_sql else ""
        normalized_expected = normalize_sql(example["sql"])
        passed = response.status_code == 200 and normalized_actual == normalized_expected
        if passed:
            passed_count += 1

        results.append(
            {
                "question": example["question"],
                "http_status": response.status_code,
                "expected_sql": normalized_expected,
                "actual_sql": normalized_actual or "N/A",
                "passed": passed,
                "summary": payload.get("message", "No summary returned.") if isinstance(payload, dict) else str(payload),
            }
        )

    output = render_results_markdown(results, passed_count)
    with open("RESULTS.md", "w", encoding="utf-8") as handle:
        handle.write(output)

    print(f"Wrote RESULTS.md with {passed_count}/{len(results)} passing benchmark questions.")


if __name__ == "__main__":
    main()
