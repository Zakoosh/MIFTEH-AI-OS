from pathlib import Path


MEMORY_AI_DIR = Path("/workspace/backend/app/memory/memory_ai")
SNAPSHOT_FILE = MEMORY_AI_DIR / "snapshot.json"
MAX_MEMORY_ITEMS = 100


def ensure_memory_dir() -> Path:
    MEMORY_AI_DIR.mkdir(parents=True, exist_ok=True)
    return MEMORY_AI_DIR


def trim_items(items: list, limit: int = MAX_MEMORY_ITEMS) -> list:
    return items[:limit]
