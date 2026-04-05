from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

from clinic_nl2sql.constants import DATABASE_PATH, MAX_QUESTION_LENGTH, MEMORY_SEED_PATH


@dataclass(frozen=True)
class Settings:
    database_path: Path = DATABASE_PATH
    memory_seed_path: Path = MEMORY_SEED_PATH
    provider: str = "gemini"
    gemini_model: str = "gemini-2.5-flash"
    google_api_key: str | None = None
    max_question_length: int = MAX_QUESTION_LENGTH

    @property
    def llm_configured(self) -> bool:
        return bool(self.google_api_key)


def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        google_api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
        max_question_length=int(os.getenv("MAX_QUESTION_LENGTH", str(MAX_QUESTION_LENGTH))),
    )
