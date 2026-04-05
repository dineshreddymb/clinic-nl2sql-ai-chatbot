import re


COMMENT_PATTERN = re.compile(r"(--[^\n]*|/\*.*?\*/)", re.DOTALL)
DISALLOWED_PATTERNS = [
    re.compile(r"\bINSERT\b", re.IGNORECASE),
    re.compile(r"\bUPDATE\b", re.IGNORECASE),
    re.compile(r"\bDELETE\b", re.IGNORECASE),
    re.compile(r"\bDROP\b", re.IGNORECASE),
    re.compile(r"\bALTER\b", re.IGNORECASE),
    re.compile(r"\bEXEC(?:UTE)?\b", re.IGNORECASE),
    re.compile(r"\bGRANT\b", re.IGNORECASE),
    re.compile(r"\bREVOKE\b", re.IGNORECASE),
    re.compile(r"\bSHUTDOWN\b", re.IGNORECASE),
    re.compile(r"\bxp_\w+\b", re.IGNORECASE),
    re.compile(r"\bsp_\w+\b", re.IGNORECASE),
    re.compile(r"\bPRAGMA\b", re.IGNORECASE),
    re.compile(r"\bATTACH\b", re.IGNORECASE),
    re.compile(r"\bDETACH\b", re.IGNORECASE),
]
SYSTEM_TABLE_PATTERNS = [
    re.compile(r"\bsqlite_master\b", re.IGNORECASE),
    re.compile(r"\bsqlite_schema\b", re.IGNORECASE),
    re.compile(r"\bsqlite_temp_master\b", re.IGNORECASE),
    re.compile(r"\bsqlite_sequence\b", re.IGNORECASE),
]


class SqlValidationError(ValueError):
    """Raised when SQL fails the safety checks."""


def _strip_comments(sql: str) -> str:
    return COMMENT_PATTERN.sub(" ", sql)


def _collapse_whitespace(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip()


def normalize_sql(sql: str) -> str:
    return _collapse_whitespace(_strip_comments(sql))


def validate_select_sql(sql: str) -> str:
    normalized = normalize_sql(sql)
    if not normalized:
        raise SqlValidationError("The generated SQL was empty.")

    statement = normalized[:-1].strip() if normalized.endswith(";") else normalized
    if ";" in statement:
        raise SqlValidationError("Multiple SQL statements are not allowed.")

    first_token = statement.split(" ", 1)[0].upper()
    if first_token not in {"SELECT", "WITH"}:
        raise SqlValidationError("Only read-only SELECT queries are allowed.")

    for pattern in DISALLOWED_PATTERNS:
        if pattern.search(statement):
            raise SqlValidationError("The generated SQL contains a disallowed keyword.")

    for pattern in SYSTEM_TABLE_PATTERNS:
        if pattern.search(statement):
            raise SqlValidationError("System tables cannot be queried.")

    return statement
