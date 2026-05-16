"""Scheduler worker — runs all workers in sequence, tracks execution times, saves manifest."""
import json
import time
import traceback
from pathlib import Path
from datetime import datetime, timezone

SNAPSHOT_DIR = Path("memory/snapshots")
MANIFEST_FILE = SNAPSHOT_DIR / "scheduler_manifest.json"

WORKER_ORDER = [
    ("analytics_worker", "analytics_worker"),
    ("indexing_worker",  "indexing_worker"),
    ("seo_worker",       "seo_worker"),
    ("github_worker",    "github_worker"),
    ("revenue_worker",   "revenue_worker"),
    ("publishing_worker","publishing_worker"),
    ("games_worker",     "games_worker"),
    ("learning_worker",  "learning_worker"),   # depends on games/qa/indexing
    ("target_tracker",   "target_tracker"),    # depends on all above
    ("telemetry_worker", "telemetry_worker"),  # must run after others
    ("alerts_worker",    "alerts_worker"),     # must run last
]


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _import_worker(module_name: str):
    import importlib
    import sys
    import os
    workers_dir = Path(__file__).parent
    sys.path.insert(0, str(workers_dir.parent))
    module = importlib.import_module(f"workers.{module_name}")
    return module


def run() -> dict:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    start_time = time.time()
    results = []

    for label, module_name in WORKER_ORDER:
        t0 = time.time()
        try:
            worker = _import_worker(module_name)
            result = worker.run()
            elapsed = round(time.time() - t0, 2)
            health = result.get("health", "unknown")
            results.append({
                "worker": label,
                "status": "ok",
                "health": health,
                "elapsed_sec": elapsed,
                "timestamp": _now(),
            })
            print(f"[scheduler] {label} — {health} ({elapsed}s)")
        except Exception as exc:
            elapsed = round(time.time() - t0, 2)
            error = traceback.format_exc()[-500:]
            results.append({
                "worker": label,
                "status": "error",
                "health": "critical",
                "elapsed_sec": elapsed,
                "error": str(exc)[:200],
                "timestamp": _now(),
            })
            print(f"[scheduler] {label} FAILED: {exc}")

    total_elapsed = round(time.time() - start_time, 2)
    ok_count = sum(1 for r in results if r["status"] == "ok")
    err_count = sum(1 for r in results if r["status"] == "error")
    health = "critical" if err_count >= 3 else ("warning" if err_count >= 1 else "healthy")

    manifest = {
        "worker": "scheduler_worker",
        "timestamp": _now(),
        "total_workers": len(WORKER_ORDER),
        "ok_count": ok_count,
        "error_count": err_count,
        "total_elapsed_sec": total_elapsed,
        "health": health,
        "results": results,
    }

    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2))
    print(f"[scheduler] done — {ok_count}/{len(WORKER_ORDER)} ok — {total_elapsed}s — health={health}")
    return manifest


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, str(Path(__file__).parent.parent))
    result = run()
    print(json.dumps(result, indent=2))
