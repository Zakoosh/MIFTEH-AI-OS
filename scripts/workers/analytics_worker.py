"""Analytics worker — reads analytics memory, detects anomalies, saves snapshot."""
import json
import os
from pathlib import Path
from datetime import datetime, timezone

SNAPSHOT_DIR = Path("memory/snapshots")
ANALYTICS_FILE = Path("memory/analytics_intelligence.json")
OUTPUT_FILE = SNAPSHOT_DIR / "analytics_snapshot.json"

ANOMALY_THRESHOLDS = {
    "trust_score_drop": 10,       # points drop in 7 days
    "revenue_drop_pct": 20,       # percent revenue drop
    "error_rate_spike": 50,       # percent spike in errors
}


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_analytics() -> dict:
    if ANALYTICS_FILE.exists():
        try:
            return json.loads(ANALYTICS_FILE.read_text())
        except Exception:
            pass
    return {}


def _load_trust() -> dict:
    f = Path("memory/trust_scores.json")
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def detect_anomalies(analytics: dict, trust: dict) -> list:
    anomalies = []

    # Check trust score stability
    scores = trust.get("scores", {})
    if scores:
        values = [v for v in scores.values() if isinstance(v, (int, float))]
        if values:
            avg = sum(values) / len(values)
            if avg < 60:
                anomalies.append({
                    "type": "low_trust_scores",
                    "severity": "warning",
                    "detail": f"Average trust score {avg:.1f} is below threshold 60",
                })

    # Check for missing data freshness
    updated = analytics.get("updated_at") or analytics.get("generated_at")
    if updated:
        try:
            from datetime import datetime, timezone
            ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            if age_hours > 48:
                anomalies.append({
                    "type": "stale_analytics",
                    "severity": "warning",
                    "detail": f"Analytics data is {age_hours:.1f}h old (threshold 48h)",
                })
        except Exception:
            pass

    # Check revenue signals
    revenue = analytics.get("revenue", {})
    if isinstance(revenue, dict):
        mrr = revenue.get("mrr_usd", 0)
        if mrr == 0:
            anomalies.append({
                "type": "zero_revenue",
                "severity": "info",
                "detail": "MRR is 0 — no revenue recorded yet",
            })

    return anomalies


def run() -> dict:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    analytics = _load_analytics()
    trust = _load_trust()
    anomalies = detect_anomalies(analytics, trust)

    snapshot = {
        "worker": "analytics_worker",
        "timestamp": _now(),
        "status": "ok",
        "analytics_keys": list(analytics.keys()),
        "trust_domains": len(trust.get("scores", {})),
        "anomalies": anomalies,
        "anomaly_count": len(anomalies),
        "health": "warning" if anomalies else "healthy",
    }

    OUTPUT_FILE.write_text(json.dumps(snapshot, indent=2))
    print(f"[analytics_worker] done — {len(anomalies)} anomalies — health={snapshot['health']}")
    return snapshot


if __name__ == "__main__":
    run()
