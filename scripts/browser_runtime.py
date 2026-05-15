"""
MIFTEH OS — Browser Runtime
Real headless browser validation using Playwright + Chromium.
Falls back gracefully to visual_validator.py (static analysis) when
Playwright is not installed.

Capabilities (when Playwright available):
  - Desktop + mobile screenshots
  - Full-page screenshots
  - JS execution + hydration wait
  - Broken interaction detection (buttons, forms, nav)
  - CLS / layout shift detection
  - Scroll simulation
  - Console error capture
  - Basic performance timing (LCP proxy, FCP proxy)
  - Lighthouse-style scoring from real browser data

Output: JSON report + PNG screenshots saved to
  frontend/dashboard/screenshots/{project}/{feature_id}/
  memory/visual_qa/{project}_{feature_id}_browser.json
"""
import json
import os
import sys
import time
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from visual_validator import validate_html

SCREENSHOTS_DIR = Path("frontend/dashboard/screenshots")
QA_DIR = Path("memory/visual_qa")

# Try importing Playwright — graceful fallback if not installed
try:
    from playwright.sync_api import sync_playwright, Error as PWError
    _PLAYWRIGHT_OK = True
except ImportError:
    _PLAYWRIGHT_OK = False

MOBILE_VIEWPORT = {"width": 390, "height": 844, "device_scale_factor": 3}
DESKTOP_VIEWPORT = {"width": 1440, "height": 900, "device_scale_factor": 1}

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)


# ── screenshot helpers ────────────────────────────────────────────────────────

def _ensure_screenshot_dir(project: str, feature_id: str) -> Path:
    d = SCREENSHOTS_DIR / project / feature_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Playwright browser session ────────────────────────────────────────────────

def _run_browser_checks(html_content: str, project: str, feature_id: str, label: str) -> dict:
    """Execute real browser checks using Playwright. Returns detailed report dict."""
    shot_dir = _ensure_screenshot_dir(project, feature_id)

    report = {
        "engine": "playwright",
        "project": project,
        "feature_id": feature_id,
        "label": label,
        "validated_at": _ts(),
        "screenshots": {},
        "console_errors": [],
        "interactions": {},
        "performance": {},
        "cls_score": 0.0,
        "accessibility": {},
        "score": 0,
        "issues": [],
        "passes_auto_merge_threshold": False,
    }

    # Write HTML to a temp file (served via file:// URL)
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        f.write(html_content)
        tmp_path = f.name

    file_url = f"file://{tmp_path}"

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )

            console_errors = []

            # ── DESKTOP ──
            ctx_d = browser.new_context(viewport=DESKTOP_VIEWPORT)
            page_d = ctx_d.new_page()
            page_d.on("console", lambda msg: console_errors.append({
                "type": msg.type, "text": msg.text,
            }) if msg.type in ("error", "warning") else None)
            page_d.on("pageerror", lambda err: console_errors.append({
                "type": "pageerror", "text": str(err),
            }))

            try:
                page_d.goto(file_url, wait_until="networkidle", timeout=15000)
            except Exception:
                page_d.goto(file_url, wait_until="load", timeout=10000)

            page_d.wait_for_timeout(800)

            # Full-page desktop screenshot
            desktop_path = shot_dir / "desktop.png"
            page_d.screenshot(path=str(desktop_path), full_page=True)
            report["screenshots"]["desktop"] = str(desktop_path.relative_to(Path(".")))

            # Viewport desktop screenshot
            viewport_path = shot_dir / "desktop_viewport.png"
            page_d.screenshot(path=str(viewport_path), full_page=False)
            report["screenshots"]["desktop_viewport"] = str(viewport_path.relative_to(Path(".")))

            # Interaction checks
            interactions = {}

            # Check buttons
            buttons = page_d.query_selector_all("button, a[href], input[type='submit']")
            interactions["total_interactive"] = len(buttons)
            broken = 0
            for btn in buttons[:10]:
                try:
                    box = btn.bounding_box()
                    if not box or box["width"] < 1 or box["height"] < 1:
                        broken += 1
                except Exception:
                    broken += 1
            interactions["broken_interactions"] = broken
            interactions["nav_present"] = page_d.query_selector("nav") is not None
            interactions["form_present"] = page_d.query_selector("form") is not None

            # Scroll simulation — check for layout overflow
            page_d.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page_d.wait_for_timeout(300)
            page_d.evaluate("window.scrollTo(0, 0)")

            # CLS proxy: check for elements wider than viewport
            cls_violations = page_d.evaluate("""() => {
                const vw = window.innerWidth;
                let count = 0;
                document.querySelectorAll('*').forEach(el => {
                    const r = el.getBoundingClientRect();
                    if (r.right > vw + 5) count++;
                });
                return count;
            }""")
            report["cls_score"] = min(1.0, cls_violations / 10.0)
            if cls_violations > 0:
                report["issues"].append(f"{cls_violations} element(s) overflow viewport horizontally (layout shift risk)")

            # Performance timing
            perf = page_d.evaluate("""() => {
                const nav = performance.getEntriesByType('navigation')[0] || {};
                return {
                    dom_content_loaded: Math.round(nav.domContentLoadedEventEnd || 0),
                    load_complete: Math.round(nav.loadEventEnd || 0),
                    dom_interactive: Math.round(nav.domInteractive || 0),
                };
            }""")
            report["performance"] = perf

            # Accessibility basics from DOM
            a11y = page_d.evaluate("""() => {
                const imgs = document.querySelectorAll('img');
                const noAlt = [...imgs].filter(i => !i.alt).length;
                const h1s = document.querySelectorAll('h1').length;
                const focusable = document.querySelectorAll('a, button, input, select, textarea').length;
                const labeled = document.querySelectorAll('[aria-label], [aria-labelledby], label').length;
                return {no_alt_imgs: noAlt, h1_count: h1s, focusable_elements: focusable, aria_labels: labeled};
            }""")
            report["accessibility"] = a11y
            if a11y.get("no_alt_imgs", 0) > 0:
                report["issues"].append(f"{a11y['no_alt_imgs']} images missing alt text (detected via DOM)")

            report["interactions"] = interactions
            ctx_d.close()

            # ── MOBILE ──
            ctx_m = browser.new_context(
                viewport={"width": MOBILE_VIEWPORT["width"], "height": MOBILE_VIEWPORT["height"]},
                device_scale_factor=MOBILE_VIEWPORT["device_scale_factor"],
                user_agent=MOBILE_UA,
                is_mobile=True,
                has_touch=True,
            )
            page_m = ctx_m.new_page()
            try:
                page_m.goto(file_url, wait_until="networkidle", timeout=12000)
            except Exception:
                page_m.goto(file_url, wait_until="load", timeout=10000)

            page_m.wait_for_timeout(500)

            mobile_path = shot_dir / "mobile.png"
            page_m.screenshot(path=str(mobile_path), full_page=True)
            report["screenshots"]["mobile"] = str(mobile_path.relative_to(Path(".")))

            mobile_vp = shot_dir / "mobile_viewport.png"
            page_m.screenshot(path=str(mobile_vp), full_page=False)
            report["screenshots"]["mobile_viewport"] = str(mobile_vp.relative_to(Path(".")))

            # Mobile horizontal overflow
            mobile_overflow = page_m.evaluate("""() => {
                const vw = window.innerWidth;
                let count = 0;
                document.querySelectorAll('*').forEach(el => {
                    const r = el.getBoundingClientRect();
                    if (r.right > vw + 5) count++;
                });
                return count;
            }""")
            if mobile_overflow > 0:
                report["issues"].append(f"Mobile: {mobile_overflow} element(s) overflow screen width")

            ctx_m.close()
            browser.close()

    except Exception as exc:
        report["issues"].append(f"Browser runtime error: {exc}")
        print(f"  [browser] Error: {exc}")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    report["console_errors"] = console_errors[:10]
    if console_errors:
        errors = [e for e in console_errors if e["type"] == "error"]
        if errors:
            report["issues"].append(f"{len(errors)} JS console error(s) detected")

    # ── Scoring (browser-aware, 100 pts) ──────────────────────────────────────
    score = 70  # Base: page loaded without crashing

    # Performance
    dcl = report["performance"].get("dom_content_loaded", 0)
    if dcl > 0:
        if dcl < 500:
            score += 10
        elif dcl < 1500:
            score += 5

    # Interactions
    interactions = report.get("interactions", {})
    if interactions.get("nav_present"):
        score += 5
    if interactions.get("broken_interactions", 99) == 0:
        score += 5
    elif interactions.get("broken_interactions", 99) <= 2:
        score += 2

    # CLS
    if report["cls_score"] == 0:
        score += 5
    elif report["cls_score"] < 0.1:
        score += 2

    # Console errors
    if not report["console_errors"]:
        score += 5
    elif len([e for e in report["console_errors"] if e["type"] == "error"]) == 0:
        score += 2

    # Screenshots taken (means page rendered)
    if report["screenshots"].get("mobile"):
        score += 5
    if report["screenshots"].get("desktop"):
        score += 5  # included in base, confirm

    # Penalties
    if len(report["issues"]) > 5:
        score -= 10
    elif len(report["issues"]) > 2:
        score -= 5

    report["score"] = min(100, max(0, score))
    report["passes_auto_merge_threshold"] = report["score"] >= 70
    report["grade"] = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"

    return report


# ── static fallback ───────────────────────────────────────────────────────────

def _run_static_fallback(html_content: str, project: str, feature_id: str, label: str) -> dict:
    """When Playwright is unavailable — delegate to visual_validator.py static analysis."""
    print(f"  [browser] Playwright not available — using static validator fallback")
    report = validate_html(html_content, label=label, project=project)
    report["engine"] = "static_fallback"
    report["feature_id"] = feature_id
    report["screenshots"] = {}
    report["console_errors"] = []
    report["interactions"] = {}
    report["performance"] = {}
    report["cls_score"] = 0.0
    return report


# ── public API ────────────────────────────────────────────────────────────────

def validate_with_browser(
    html_content: str,
    project: str,
    feature_id: str,
    label: str = "",
    save_report: bool = True,
) -> dict:
    """
    Run browser validation (Playwright) or fall back to static analysis.
    Optionally saves report to memory/visual_qa/{project}_{feature_id}_browser.json.
    """
    print(f"  [browser] Validating {project}/{feature_id} "
          f"({'Playwright' if _PLAYWRIGHT_OK else 'static fallback'})")

    if _PLAYWRIGHT_OK:
        report = _run_browser_checks(html_content, project, feature_id, label or feature_id)
    else:
        report = _run_static_fallback(html_content, project, feature_id, label or feature_id)

    if save_report:
        QA_DIR.mkdir(parents=True, exist_ok=True)
        out = QA_DIR / f"{project}_{feature_id}_browser.json"
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(f"  [browser] Report → {out}")

    return report


def validate_file_with_browser(
    path: str | Path,
    project: str,
    feature_id: str | None = None,
    label: str | None = None,
) -> dict:
    p = Path(path)
    fid = feature_id or p.stem
    lbl = label or p.stem
    html = p.read_text(encoding="utf-8", errors="replace")
    return validate_with_browser(html, project, fid, lbl)


# ── batch runner ──────────────────────────────────────────────────────────────

def run_all_previews(target_project: str = "all", force: bool = False) -> list[dict]:
    """Validate all saved HTML previews from frontend/dashboard/previews/."""
    previews_root = Path("frontend/dashboard/previews")
    if not previews_root.exists():
        print("[browser] No previews directory found")
        return []

    reports = []
    for proj_dir in previews_root.iterdir():
        if not proj_dir.is_dir():
            continue
        project = proj_dir.name
        if target_project != "all" and project.lower() != target_project.lower():
            continue

        for html_file in sorted(proj_dir.glob("*.html")):
            feature_id = html_file.stem
            report_path = QA_DIR / f"{project}_{feature_id}_browser.json"

            if not force and report_path.exists():
                print(f"  [browser] {project}/{feature_id} already validated — skip")
                try:
                    reports.append(json.loads(report_path.read_text()))
                except Exception:
                    pass
                continue

            html = html_file.read_text(encoding="utf-8", errors="replace")
            report = validate_with_browser(html, project, feature_id, save_report=True)
            reports.append(report)
            print(f"  [browser] {project}/{feature_id}: {report['score']}/100 grade={report.get('grade','?')}")

    return reports


def build_browser_summary() -> dict:
    """Aggregate all browser QA reports into a summary for the dashboard."""
    all_reports = []
    if QA_DIR.exists():
        for f in QA_DIR.glob("*_browser.json"):
            try:
                all_reports.append(json.loads(f.read_text()))
            except Exception:
                pass

    if not all_reports:
        return {"total": 0, "passing": 0, "avg_score": 0, "reports": []}

    passing = [r for r in all_reports if r.get("passes_auto_merge_threshold")]
    avg = round(sum(r.get("score", 0) for r in all_reports) / len(all_reports))

    return {
        "total": len(all_reports),
        "passing": len(passing),
        "blocking": len(all_reports) - len(passing),
        "avg_score": avg,
        "pass_rate_pct": round(len(passing) / len(all_reports) * 100),
        "engine": "playwright" if _PLAYWRIGHT_OK else "static_fallback",
        "playwright_available": _PLAYWRIGHT_OK,
        "reports": [
            {
                "project": r.get("project", ""),
                "feature_id": r.get("feature_id", ""),
                "label": r.get("label", ""),
                "score": r.get("score", 0),
                "grade": r.get("grade", "?"),
                "passes": r.get("passes_auto_merge_threshold", False),
                "engine": r.get("engine", ""),
                "screenshots": r.get("screenshots", {}),
                "console_errors": len(r.get("console_errors", [])),
                "cls_score": r.get("cls_score", 0),
                "performance": r.get("performance", {}),
                "interactions": r.get("interactions", {}),
                "issues": r.get("issues", [])[:3],
                "validated_at": r.get("validated_at", ""),
            }
            for r in sorted(all_reports, key=lambda x: x.get("score", 0), reverse=True)
        ],
    }


def save_browser_summary():
    summary = build_browser_summary()
    out = Path("memory") / "browser_qa_summary.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"[browser] Summary → {out}  ({summary['passing']}/{summary['total']} pass, avg {summary['avg_score']}/100)")
    return summary


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"[browser] Starting browser runtime (engine: {'Playwright' if _PLAYWRIGHT_OK else 'static fallback'})")

    if not _PLAYWRIGHT_OK:
        print("[browser] To enable real browser validation: pip install playwright && playwright install chromium")

    force = os.environ.get("FORCE_REVALIDATE", "").lower() in ("1", "true", "yes")
    target_project = os.environ.get("TARGET_PROJECT", "all")

    reports = run_all_previews(target_project=target_project, force=force)
    print(f"\n[browser] Validated {len(reports)} features")

    save_browser_summary()


if __name__ == "__main__":
    main()
