from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "clinic.db"
MEMORY_SEED_PATH = BASE_DIR / "memory_seed.json"
LOG_LEVEL = "INFO"
MAX_QUESTION_LENGTH = 500
