"""
Report Store — persists all intelligence reports to memory/reports/.
All reports are JSON with timestamps. Supports load, save, list, diff.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any

REPORTS_ROOT = Path(__file__).parents[2] / "memory" / "reports"

REPORT_DIRS = {
    "live": "live",
    "seo": "seo",
    "pr_review": "pr_reviews",
    "health": "health",
    "screenshot": "screenshots",
    "pipeline": "pipeline",
}


def _dir(report_type: str) -> Path:
    d = REPORTS_ROOT / REPORT_DIRS.get(report_type, report_type)
    d.mkdir(parents=True, exist_ok=True)
    return d


def save(report_type: str, project_id: str, data: dict) -> Path:
    """Save a report. Returns the path written."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{project_id}_{ts}.json"
    path = _dir(report_type) / filename

    payload = {
        "report_type": report_type,
        "project_id": project_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **data,
    }
    path.write_text(json.dumps(payload, indent=2, default=str))

    # Always update the "latest" symlink equivalent (a fixed-name file)
    latest = _dir(report_type) / f"{project_id}_latest.json"
    latest.write_text(json.dumps(payload, indent=2, default=str))

    return path


def load_latest(report_type: str, project_id: str) -> Optional[dict]:
    """Load the most recent report for a project."""
    latest = _dir(report_type) / f"{project_id}_latest.json"
    if latest.exists():
        return json.loads(latest.read_text())

    # Fallback: find newest timestamped file
    files = sorted(
        _dir(report_type).glob(f"{project_id}_2*.json"),
        key=lambda p: p.stem,
        reverse=True,
    )
    if files:
        return json.loads(files[0].read_text())
    return None


def list_reports(report_type: str, project_id: Optional[str] = None) -> list[dict]:
    """List all reports of a type, optionally filtered by project."""
    d = _dir(report_type)
    pattern = f"{project_id}_2*.json" if project_id else "*_2*.json"
    reports = []
    for f in sorted(d.glob(pattern), key=lambda p: p.stem, reverse=True):
        try:
            r = json.loads(f.read_text())
            reports.append({"file": f.name, "generated_at": r.get("generated_at"), "project_id": r.get("project_id")})
        except Exception:
            pass
    return reports


def diff_latest_two(report_type: str, project_id: str) -> Optional[dict]:
    """Compare the two most recent reports for a project, return delta summary."""
    d = _dir(report_type)
    files = sorted(d.glob(f"{project_id}_2*.json"), key=lambda p: p.stem, reverse=True)
    if len(files) < 2:
        return None

    curr = json.loads(files[0].read_text())
    prev = json.loads(files[1].read_text())

    def _flat(obj, prefix="") -> dict:
        out = {}
        for k, v in obj.items():
            key = f"{prefix}{k}"
            if isinstance(v, dict):
                out.update(_flat(v, f"{key}."))
            elif isinstance(v, (int, float, str, bool)) or v is None:
                out[key] = v
        return out

    curr_flat = _flat(curr)
    prev_flat = _flat(prev)
    changes = {}
    all_keys = set(curr_flat) | set(prev_flat)
    for k in all_keys:
        c, p = curr_flat.get(k), prev_flat.get(k)
        if c != p:
            changes[k] = {"before": p, "after": c}

    return {
        "project_id": project_id,
        "report_type": report_type,
        "current": files[0].name,
        "previous": files[1].name,
        "changed_fields": len(changes),
        "changes": changes,
    }


def save_summary(data: dict) -> Path:
    """Save a cross-project summary report."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = REPORTS_ROOT / f"summary_{ts}.json"
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))
    (REPORTS_ROOT / "summary_latest.json").write_text(json.dumps(data, indent=2, default=str))
    return path
