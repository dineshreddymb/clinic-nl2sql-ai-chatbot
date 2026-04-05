from clinic_nl2sql.config import get_settings
from clinic_nl2sql.logging_utils import configure_logging
from clinic_nl2sql.runtime import RuntimeBundle, build_runtime


configure_logging()
SETTINGS = get_settings()
RUNTIME: RuntimeBundle = build_runtime(SETTINGS)


def get_runtime() -> RuntimeBundle:
    return RUNTIME
