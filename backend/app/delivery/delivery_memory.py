"""
delivery_memory.py — File-based persistence for all delivery records.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

_BASE = Path(__file__).parent.parent / "memory" / "delivery"

_DIRS = ("plans", "runs", "checkpoints", "previews", "recovery", "audit", "phases", "rollouts")


def _ensure() -> None:
    for d in _DIRS:
        (_BASE / d).mkdir(parents=True, exist_ok=True)


def _write(path: Path, data: dict) -> None:
    _ensure()
    path.write_text(json.dumps(data, indent=2))


def _read(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _list_dir(subdir: str) -> list[dict]:
    _ensure()
    d = _BASE / subdir
    results = []
    for f in sorted(d.glob("*.json")):
        data = _read(f)
        if data:
            results.append(data)
    return results


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

def save_run(run: dict) -> None:
    _write(_BASE / "runs" / f"{run['run_id']}.json", run)


def get_run(run_id: str) -> Optional[dict]:
    return _read(_BASE / "runs" / f"{run_id}.json")


def get_run_for_plan(plan_id: str) -> Optional[dict]:
    """Return the most recent run for a plan_id."""
    return _read(_BASE / "runs" / f"run_{plan_id}.json")


def list_runs() -> list[dict]:
    return _list_dir("runs")


# ---------------------------------------------------------------------------
# Checkpoints
# ---------------------------------------------------------------------------

def save_checkpoint(cp: dict) -> None:
    _write(_BASE / "checkpoints" / f"{cp['checkpoint_id']}.json", cp)


def list_checkpoints(plan_id: str = "") -> list[dict]:
    all_cp = _list_dir("checkpoints")
    if plan_id:
        return [c for c in all_cp if c.get("plan_id") == plan_id]
    return all_cp


# ---------------------------------------------------------------------------
# Previews
# ---------------------------------------------------------------------------

def save_preview(preview: dict) -> None:
    _write(_BASE / "previews" / f"{preview['plan_id']}_preview.json", preview)


def get_preview(plan_id: str) -> Optional[dict]:
    return _read(_BASE / "previews" / f"{plan_id}_preview.json")


def list_previews() -> list[dict]:
    return _list_dir("previews")


# ---------------------------------------------------------------------------
# Recovery
# ---------------------------------------------------------------------------

def save_recovery(rec: dict) -> None:
    _write(_BASE / "recovery" / f"{rec['recovery_id']}.json", rec)


def list_recovery(plan_id: str = "") -> list[dict]:
    all_r = _list_dir("recovery")
    if plan_id:
        return [r for r in all_r if r.get("plan_id") == plan_id]
    return all_r


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

def save_audit(entry: dict) -> None:
    _write(_BASE / "audit" / f"{entry['audit_id']}.json", entry)


def list_audit(plan_id: str = "") -> list[dict]:
    all_a = _list_dir("audit")
    if plan_id:
        return [a for a in all_a if a.get("plan_id") == plan_id]
    return all_a


# ---------------------------------------------------------------------------
# Rollouts
# ---------------------------------------------------------------------------

def save_rollout(rollout: dict) -> None:
    _write(_BASE / "rollouts" / f"{rollout['rollout_id']}.json", rollout)


def list_rollouts() -> list[dict]:
    return _list_dir("rollouts")
