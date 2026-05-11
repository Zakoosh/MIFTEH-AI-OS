from datetime import datetime, timedelta, timezone
import re


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed


def add_minutes(value: str | None, minutes: int) -> str:
    start = parse_iso_datetime(value) or utc_now()
    return (start + timedelta(minutes=minutes)).isoformat()


def is_due(next_run_at: str | None) -> bool:
    scheduled_at = parse_iso_datetime(next_run_at)
    return scheduled_at is None or scheduled_at <= utc_now()


def seconds_between(started_at: str, completed_at: str) -> float:
    start = parse_iso_datetime(started_at)
    end = parse_iso_datetime(completed_at)

    if start is None or end is None:
        return 0

    return max((end - start).total_seconds(), 0)


def safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "-", value).strip("-") or "unknown"
