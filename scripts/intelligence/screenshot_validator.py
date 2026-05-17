"""
Screenshot Validator — captures production site screenshots via Playwright
and runs visual regression comparisons between captures.

Falls back gracefully when Playwright is not installed (returns metadata only).
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .registry import get_project, get_all_active_projects
from .report_store import save, REPORTS_ROOT

SCREENSHOTS_DIR = REPORTS_ROOT / "screenshots"
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900},
    "tablet": {"width": 768, "height": 1024},
    "mobile": {"width": 390, "height": 844},
}

_PLAYWRIGHT_AVAILABLE: Optional[bool] = None


def _check_playwright() -> bool:
    global _PLAYWRIGHT_AVAILABLE
    if _PLAYWRIGHT_AVAILABLE is not None:
        return _PLAYWRIGHT_AVAILABLE
    try:
        import importlib
        importlib.import_module("playwright.sync_api")
        _PLAYWRIGHT_AVAILABLE = True
    except ImportError:
        _PLAYWRIGHT_AVAILABLE = False
    return _PLAYWRIGHT_AVAILABLE


# ──────────────────────────────────────────────────────────────────────────────
# Playwright screenshot capture
# ──────────────────────────────────────────────────────────────────────────────

def _capture_with_playwright(url: str, out_path: Path, viewport: dict, wait_ms: int = 2000) -> dict:
    """Capture screenshot using Playwright. Returns metadata dict."""
    try:
        from playwright.sync_api import sync_playwright, Error as PlaywrightError
    except ImportError:
        return {"ok": False, "error": "playwright not installed", "path": None}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = browser.new_context(
                viewport=viewport,
                user_agent="MIFTEH-AI-OS/1.0 ScreenshotValidator",
                ignore_https_errors=True,
            )
            page = ctx.new_page()
            response = page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(wait_ms)

            # Capture full page
            page.screenshot(path=str(out_path), full_page=True)
            elapsed = int((time.time() - start) * 1000)

            # Collect basic page info while we have the page
            title = page.title()
            has_h1 = page.locator("h1").count() > 0
            has_adsense = page.locator('[data-ad-client]').count() > 0 or \
                          "adsbygoogle" in page.content()

            browser.close()

        file_size = out_path.stat().st_size if out_path.exists() else 0
        img_hash = _file_hash(out_path) if out_path.exists() else None

        return {
            "ok": True,
            "path": str(out_path),
            "url": url,
            "status": response.status if response else 0,
            "elapsed_ms": elapsed,
            "file_size": file_size,
            "hash": img_hash,
            "viewport": viewport,
            "page_title": title,
            "has_h1": has_h1,
            "has_adsense": has_adsense,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "path": None, "url": url}


def _capture_fallback(url: str, viewport_name: str) -> dict:
    """Fallback when Playwright unavailable — records metadata only, no image."""
    return {
        "ok": False,
        "error": "playwright_not_available",
        "path": None,
        "url": url,
        "viewport_name": viewport_name,
        "note": "Install playwright: pip install playwright && playwright install chromium",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Hash + visual regression
# ──────────────────────────────────────────────────────────────────────────────

def _file_hash(path: Path) -> str:
    """SHA-256 of file contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _pixel_diff_score(path_a: Path, path_b: Path) -> Optional[float]:
    """
    Approximate pixel similarity score (0.0=identical, 1.0=completely different).
    Uses pure Python — no external image library required.
    Returns None if comparison not possible.
    """
    try:
        import struct
        import zlib

        def _read_png_pixels(p: Path):
            data = p.read_bytes()
            # Minimal PNG reader — extract IDAT and decode
            if data[:8] != b'\x89PNG\r\n\x1a\n':
                return None, 0, 0
            pos = 8
            width = height = 0
            idat_chunks = []
            while pos < len(data):
                length = struct.unpack('>I', data[pos:pos+4])[0]
                chunk_type = data[pos+4:pos+8]
                chunk_data = data[pos+8:pos+8+length]
                if chunk_type == b'IHDR':
                    width = struct.unpack('>I', chunk_data[0:4])[0]
                    height = struct.unpack('>I', chunk_data[4:8])[0]
                elif chunk_type == b'IDAT':
                    idat_chunks.append(chunk_data)
                elif chunk_type == b'IEND':
                    break
                pos += 12 + length
            if not idat_chunks:
                return None, width, height
            try:
                raw = zlib.decompress(b''.join(idat_chunks))
            except Exception:
                return None, width, height
            return raw, width, height

        raw_a, wa, ha = _read_png_pixels(path_a)
        raw_b, wb, hb = _read_png_pixels(path_b)

        if raw_a is None or raw_b is None or wa != wb or ha != hb:
            return None

        # Sample pixels (every 50th byte) for speed
        diffs = sum(abs(a - b) for a, b in zip(raw_a[::50], raw_b[::50]))
        max_diff = 255 * max(len(raw_a[::50]), 1)
        return round(diffs / max_diff, 4)

    except Exception:
        return None


def compare_screenshots(path_before: str, path_after: str) -> dict:
    """Compare two screenshots. Returns similarity score and diff metadata."""
    a, b = Path(path_before), Path(path_after)
    if not a.exists():
        return {"ok": False, "error": f"before screenshot not found: path_before"}
    if not b.exists():
        return {"ok": False, "error": f"after screenshot not found: path_after"}

    hash_a = _file_hash(a)
    hash_b = _file_hash(b)
    identical = hash_a == hash_b

    diff_score = None
    if not identical:
        diff_score = _pixel_diff_score(a, b)

    return {
        "ok": True,
        "identical": identical,
        "hash_before": hash_a,
        "hash_after": hash_b,
        "diff_score": diff_score,
        "changed": not identical,
        "change_level": (
            "none" if identical else
            "minor" if diff_score is not None and diff_score < 0.01 else
            "moderate" if diff_score is not None and diff_score < 0.05 else
            "major"
        ),
        "path_before": str(a),
        "path_after": str(b),
    }


# ──────────────────────────────────────────────────────────────────────────────
# High-level capture + regression
# ──────────────────────────────────────────────────────────────────────────────

def capture_page(
    url: str,
    project_id: str,
    label: str = "manual",
    viewports: Optional[list[str]] = None,
) -> dict:
    """
    Capture screenshots of a URL across viewports.
    Returns dict with per-viewport results.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    vp_names = viewports or list(VIEWPORTS.keys())
    results = {}

    for vp_name in vp_names:
        vp = VIEWPORTS.get(vp_name, VIEWPORTS["desktop"])
        slug = url.replace("https://", "").replace("http://", "").replace("/", "_").strip("_")[:60]
        fname = f"{project_id}_{slug}_{vp_name}_{label}_{ts}.png"
        out_path = SCREENSHOTS_DIR / fname

        if _check_playwright():
            result = _capture_with_playwright(url, out_path, vp)
        else:
            result = _capture_fallback(url, vp_name)

        result["viewport_name"] = vp_name
        result["label"] = label
        result["captured_at"] = datetime.now(timezone.utc).isoformat()
        results[vp_name] = result

    report = {
        "project_id": project_id,
        "url": url,
        "label": label,
        "captured_at": ts,
        "playwright_available": _check_playwright(),
        "viewports": results,
        "ok": all(r.get("ok") for r in results.values()),
    }
    save("screenshot", project_id, report)
    return report


def capture_project(project_id: str, label: str = "auto") -> dict:
    """Capture key pages of a project."""
    p = get_project(project_id)
    domain = p["domain"]
    priority_paths = ["/", "/games", "/about", "/contact", "/privacy"]
    all_captures = {}

    for path in priority_paths:
        url = f"https://{domain}{path}"
        all_captures[path] = capture_page(url, project_id, label=label, viewports=["desktop", "mobile"])

    overall_ok = all(c.get("ok") for c in all_captures.values())
    return {
        "project_id": project_id,
        "domain": domain,
        "label": label,
        "pages_captured": len(all_captures),
        "overall_ok": overall_ok,
        "captures": all_captures,
    }


def regression_check(project_id: str, before_label: str, after_label: str) -> dict:
    """
    Compare before/after screenshot sets for a project.
    Finds matching files by viewport+path pattern and diffs them.
    """
    results = []
    changed_pages = []

    before_files = list(SCREENSHOTS_DIR.glob(f"{project_id}_*_{before_label}_*.png"))
    after_files = list(SCREENSHOTS_DIR.glob(f"{project_id}_*_{after_label}_*.png"))

    # Match by viewport name prefix pattern
    for af in after_files:
        # Extract viewport from filename
        parts = af.stem.split("_")
        vp = None
        for vp_name in VIEWPORTS:
            if vp_name in parts:
                vp = vp_name
                break

        # Find matching before file (same viewport, same URL slug)
        url_slug_idx = parts.index(vp) - 1 if vp and vp in parts else -1
        url_slug = "_".join(parts[1:url_slug_idx + 1]) if url_slug_idx > 0 else ""

        matching_before = [
            bf for bf in before_files
            if vp and vp in bf.stem and url_slug and url_slug in bf.stem
        ]
        if not matching_before:
            continue

        bf = matching_before[0]
        diff = compare_screenshots(str(bf), str(af))
        diff["page_slug"] = url_slug
        diff["viewport"] = vp
        results.append(diff)
        if diff.get("changed"):
            changed_pages.append(url_slug)

    return {
        "project_id": project_id,
        "before_label": before_label,
        "after_label": after_label,
        "comparisons": len(results),
        "changed_count": len(changed_pages),
        "changed_pages": changed_pages,
        "results": results,
        "regression_detected": len(changed_pages) > 0,
    }


if __name__ == "__main__":
    pid = sys.argv[1] if len(sys.argv) > 1 else "yallaplays"
    url = sys.argv[2] if len(sys.argv) > 2 else None
    if url:
        r = capture_page(url, pid, label="cli")
    else:
        r = capture_project(pid, label="cli")
    print(json.dumps({k: v for k, v in r.items() if k != "captures"}, indent=2))
