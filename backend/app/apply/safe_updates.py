"""
safe_updates.py — Defines the whitelist of safe, low-risk update operations
per project type. Acts as the policy layer for what the Apply Engine is
allowed to execute autonomously.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Operation whitelists — keyed by project_id
# ---------------------------------------------------------------------------

YALLAPLAYS_ALLOWED_OPERATIONS: dict[str, dict] = {
    "seo": {
        "description": "SEO metadata improvements",
        "allowed_fields": [
            "title", "description", "keywords", "canonical_url",
            "og_title", "og_description", "og_image", "twitter_card",
            "twitter_title", "twitter_description",
        ],
        "risk_level": "low",
        "requires_preview": True,
        "max_field_length": 500,
    },
    "landing_page": {
        "description": "Landing page copy and layout updates",
        "allowed_fields": [
            "hero_title", "hero_subtitle", "cta_text", "cta_url",
            "feature_list", "testimonials_enabled",
        ],
        "risk_level": "low",
        "requires_preview": True,
        "max_field_length": 1000,
    },
    "category": {
        "description": "Game category label and ordering optimizations",
        "allowed_fields": [
            "category_name", "category_slug", "display_order",
            "category_description", "is_featured",
        ],
        "risk_level": "low",
        "requires_preview": True,
        "max_field_length": 200,
    },
    "manifest": {
        "description": "Web app manifest improvements",
        "allowed_fields": [
            "name", "short_name", "description", "theme_color",
            "background_color", "display", "icons",
        ],
        "risk_level": "low",
        "requires_preview": True,
        "max_field_length": 300,
    },
    "metadata": {
        "description": "Page metadata and structured data",
        "allowed_fields": [
            "page_title", "meta_description", "schema_type",
            "author", "language", "viewport",
        ],
        "risk_level": "low",
        "requires_preview": True,
        "max_field_length": 500,
    },
}

FIONERA_ALLOWED_OPERATIONS: dict[str, dict] = {
    "dashboard": {
        "description": "Dashboard layout and component improvements",
        "allowed_fields": [
            "widget_title", "widget_type", "widget_position",
            "refresh_interval", "chart_type", "color_scheme",
        ],
        "risk_level": "low",
        "requires_preview": True,
        "max_field_length": 300,
    },
    "widget": {
        "description": "Analytics widget additions",
        "allowed_fields": [
            "widget_id", "widget_name", "data_source", "display_type",
            "metrics", "time_range", "enabled",
        ],
        "risk_level": "low",
        "requires_preview": True,
        "max_field_length": 400,
    },
    "watchlist": {
        "description": "Watchlist configuration updates",
        "allowed_fields": [
            "watchlist_name", "tickers", "alert_threshold",
            "refresh_interval", "display_currency", "sort_by",
        ],
        "risk_level": "low",
        "requires_preview": True,
        "max_field_length": 300,
    },
    "metadata": {
        "description": "Page metadata and structured data",
        "allowed_fields": [
            "page_title", "meta_description", "schema_type",
            "author", "language",
        ],
        "risk_level": "low",
        "requires_preview": True,
        "max_field_length": 500,
    },
    "seo": {
        "description": "SEO metadata for Fionera pages",
        "allowed_fields": [
            "title", "description", "keywords", "og_title",
            "og_description", "canonical_url",
        ],
        "risk_level": "low",
        "requires_preview": True,
        "max_field_length": 500,
    },
}

# Map project_id → allowed operations
PROJECT_OPERATIONS: dict[str, dict] = {
    "yallaplays": YALLAPLAYS_ALLOWED_OPERATIONS,
    "fionera": FIONERA_ALLOWED_OPERATIONS,
}

# Globally forbidden patterns (applied to any field value)
FORBIDDEN_PATTERNS: list[str] = [
    "eval(", "exec(", "__import__", "os.system",
    "subprocess", "DROP TABLE", "DELETE FROM",
    "<script", "javascript:", "data:text/html",
]

# File extensions that are safe to read/modify
SAFE_EXTENSIONS: set[str] = {
    ".json", ".md", ".txt", ".html", ".css",
    ".js", ".ts", ".tsx", ".jsx", ".yaml", ".yml",
    ".env.example", ".toml", ".ini",
}

# Absolute path segments that must never appear in a target file path
FORBIDDEN_PATH_SEGMENTS: list[str] = [
    "/etc/", "/var/", "/usr/", "/sys/", "/proc/",
    "C:\\Windows", "C:\\System32",
    ".ssh", ".env", "secrets", "credentials",
    "private_key", "id_rsa",
]


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_allowed_operations(project_id: str) -> dict[str, dict]:
    """Return the allowed operation map for a given project."""
    return PROJECT_OPERATIONS.get(project_id.lower(), {})


def is_operation_allowed(project_id: str, operation_type: str) -> bool:
    """Check if an operation type is permitted for this project."""
    ops = get_allowed_operations(project_id)
    return operation_type.lower() in ops


def get_operation_policy(project_id: str, operation_type: str) -> dict | None:
    """Return the full policy dict for an operation, or None if not allowed."""
    ops = get_allowed_operations(project_id)
    return ops.get(operation_type.lower())


def classify_risk(proposal_type: str, changes: dict[str, Any]) -> str:
    """Classify the risk level of a proposal based on its type and changes.

    Returns "low", "medium", or "high".
    Only "low" is eligible for autonomous apply.
    """
    # Any change touching more than 10 fields is at least medium
    if len(changes) > 10:
        return "medium"

    # String values over 2000 chars are medium risk
    for val in changes.values():
        if isinstance(val, str) and len(val) > 2000:
            return "medium"

    # Detect forbidden patterns → high risk
    for val in changes.values():
        for pattern in FORBIDDEN_PATTERNS:
            if isinstance(val, str) and pattern.lower() in val.lower():
                return "high"

    return "low"


def contains_forbidden_content(value: Any) -> tuple[bool, str]:
    """Return (True, pattern) if value contains a forbidden pattern."""
    if not isinstance(value, str):
        return False, ""
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.lower() in value.lower():
            return True, pattern
    return False, ""


def is_safe_target_path(target_file: str) -> tuple[bool, str]:
    """Return (True, "") when a target file path is safe to touch."""
    for segment in FORBIDDEN_PATH_SEGMENTS:
        if segment.lower() in target_file.lower():
            return False, f"Forbidden path segment: {segment}"

    from pathlib import PurePath
    suffix = PurePath(target_file).suffix.lower()
    if suffix and suffix not in SAFE_EXTENSIONS:
        return False, f"Unsafe file extension: {suffix}"

    return True, ""
