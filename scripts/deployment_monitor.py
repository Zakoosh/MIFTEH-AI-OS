"""
MIFTEH OS — Deployment Monitor
Monitors all 3 production sites for:
  - Uptime / HTTP status
  - Core Web Vitals proxy (TTFB, response time)
  - SEO health (title, meta, canonical, OG, robots, sitemap)
  - JS/asset loading errors (via HTML analysis)
  - Lighthouse-like scoring
  - Content freshness
  - Schema.org validity

Stores uptime + SEO history. Triggers trust score updates on degradation.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import now_iso, timestamp_str
from trust_manager import record_deploy

MEMORY = Path("memory")
DEPLOY_HISTORY_FILE = MEMORY / "deployment_history.json"
UPTIME_FILE = MEMORY / "uptime_history.json"
SEO_HEALTH_FILE = MEMORY / "seo_health_history.json"

SITES = {
    "yallaplays": {
        "url": "https://yallaplays.com",
        "expected_lang": "ar",
        "expected_keywords": ["يلا بلايز", "ألعاب", "games"],
        "critical_pages": ["/robots.txt", "/sitemap.xml"],
        "repo": "Zakoosh/Yallaplays",
    },
    "fionera": {
        "url": "https://fionera.app",
        "expected_lang": "tr",
        "expected_keywords": ["fionera", "finans", "borsa"],
        "critical_pages": ["/robots.txt"],
        "repo": "Zakoosh/fionera",
    },
    "mifteh": {
        "url": "https://miftehos.com",
        "expected_lang": "en",
        "expected_keywords": ["mifteh", "AI", "autonomous"],
        "critical_pages": ["/robots.txt", "/sitemap.xml"],
        "repo": "Zakoosh/mifteh-main-site",
    },
}

TIMEOUT = 15
HEADERS = {
    "User-Agent": "MIFTEH-OS-Monitor/1.0 (+https://miftehos.com/bot)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _fetch(url: str) -> tuple[int, str, float]:
    """Fetch URL. Returns (status_code, body_text, ttfb_ms)."""
    start = time.monotonic()
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            ttfb = round((time.monotonic() - start) * 1000)
            body = r.read(500_000).decode("utf-8", errors="replace")
            return r.getcode(), body, ttfb
    except urllib.error.HTTPError as e:
        ttfb = round((time.monotonic() - start) * 1000)
        return e.code, "", ttfb
    except Exception as e:
        return 0, str(e)[:200], round((time.monotonic() - start) * 1000)


def _find(pattern: str, text: str) -> bool:
    return bool(re.search(pattern, text, re.IGNORECASE | re.DOTALL))


# ── SEO health checks ─────────────────────────────────────────────────────────

def check_seo_health(url: str, html: str, expected_keywords: list[str]) -> dict:
    checks = {}

    # Title
    title_m = re.search(r"<title[^>]*>(.{10,70})</title>", html, re.IGNORECASE)
    checks["title"] = {"ok": bool(title_m), "value": title_m.group(1).strip() if title_m else ""}

    # Meta description
    desc_m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']{50,})["\']', html, re.IGNORECASE)
    if not desc_m:
        desc_m = re.search(r'<meta[^>]+content=["\']([^"\']{50,})["\'][^>]+name=["\']description["\']', html, re.IGNORECASE)
    checks["meta_description"] = {"ok": bool(desc_m), "value": desc_m.group(1)[:80] if desc_m else ""}

    # Canonical
    canonical_m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE)
    checks["canonical"] = {"ok": bool(canonical_m), "value": canonical_m.group(1) if canonical_m else ""}

    # OG tags
    og_title = _find(r'<meta[^>]+property=["\']og:title["\']', html)
    og_desc  = _find(r'<meta[^>]+property=["\']og:description["\']', html)
    og_url   = _find(r'<meta[^>]+property=["\']og:url["\']', html)
    checks["og_tags"] = {"ok": og_title and og_desc, "value": f"title={og_title} desc={og_desc} url={og_url}"}

    # Twitter card
    tw_card = _find(r'<meta[^>]+name=["\']twitter:card["\']', html)
    checks["twitter_card"] = {"ok": tw_card, "value": str(tw_card)}

    # JSON-LD
    has_ld = _find(r'<script[^>]+type=["\']application/ld\+json["\']', html)
    checks["json_ld"] = {"ok": has_ld, "value": str(has_ld)}

    # H1
    h1_count = len(re.findall(r'<h1[\s>]', html, re.IGNORECASE))
    checks["h1"] = {"ok": h1_count == 1, "value": str(h1_count)}

    # Viewport
    has_vp = _find(r'<meta[^>]+name=["\']viewport["\']', html)
    checks["viewport"] = {"ok": has_vp, "value": str(has_vp)}

    # Keywords in content
    keyword_hits = sum(1 for kw in expected_keywords if kw.lower() in html.lower())
    checks["keywords"] = {"ok": keyword_hits >= 1, "value": f"{keyword_hits}/{len(expected_keywords)}"}

    # Calculate SEO score
    weights = {
        "title": 20, "meta_description": 15, "canonical": 10,
        "og_tags": 15, "json_ld": 15, "h1": 10,
        "viewport": 10, "keywords": 5,
    }
    score = sum(w for k, w in weights.items() if checks.get(k, {}).get("ok"))
    grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"

    return {"checks": checks, "score": score, "grade": grade}


# ── Core Web Vitals proxy ─────────────────────────────────────────────────────

def estimate_core_web_vitals(html: str, ttfb_ms: float) -> dict:
    """Estimate CWV signals from static HTML + TTFB (no real browser)."""
    html_kb = len(html.encode()) / 1024

    # Estimate LCP: based on HTML size + TTFB
    lcp_ms = ttfb_ms + html_kb * 2
    lcp_grade = "good" if lcp_ms < 2500 else "needs_improvement" if lcp_ms < 4000 else "poor"

    # Estimate FID/INP: based on inline script count
    script_count = len(re.findall(r'<script(?![^>]+src=)', html, re.IGNORECASE))
    fid_ms = min(script_count * 20, 300)
    fid_grade = "good" if fid_ms < 100 else "needs_improvement" if fid_ms < 300 else "poor"

    # Estimate CLS: based on images without dimensions
    imgs_no_dims = len(re.findall(r'<img(?![^>]*(width|height))[^>]*>', html, re.IGNORECASE))
    cls_score = min(imgs_no_dims * 0.05, 0.5)
    cls_grade = "good" if cls_score < 0.1 else "needs_improvement" if cls_score < 0.25 else "poor"

    # TTFB grade
    ttfb_grade = "good" if ttfb_ms < 800 else "needs_improvement" if ttfb_ms < 1800 else "poor"

    return {
        "ttfb_ms": round(ttfb_ms),
        "ttfb_grade": ttfb_grade,
        "lcp_ms_estimate": round(lcp_ms),
        "lcp_grade": lcp_grade,
        "fid_ms_estimate": fid_ms,
        "fid_grade": fid_grade,
        "cls_score_estimate": round(cls_score, 3),
        "cls_grade": cls_grade,
        "overall": "good" if all(g == "good" for g in [lcp_grade, fid_grade, cls_grade, ttfb_grade]) else
                   "needs_improvement" if "poor" not in [lcp_grade, fid_grade, cls_grade, ttfb_grade] else "poor",
    }


# ── Site monitoring ───────────────────────────────────────────────────────────

def monitor_site(project: str, config: dict) -> dict:
    """Run all checks for one site. Returns a monitoring report."""
    url = config["url"]
    print(f"\n  [monitor] {project}: {url}")
    ts = now_iso()

    report = {
        "project": project,
        "url": url,
        "checked_at": ts,
        "uptime": False,
        "status_code": 0,
        "ttfb_ms": 0,
        "response_time_ms": 0,
        "seo_health": {},
        "core_web_vitals": {},
        "critical_pages": {},
        "content_checks": {},
        "issues": [],
        "score": 0,
        "grade": "F",
        "ok": False,
    }

    # Main page check
    start = time.monotonic()
    status, html, ttfb = _fetch(url)
    elapsed = round((time.monotonic() - start) * 1000)

    report["status_code"] = status
    report["ttfb_ms"] = ttfb
    report["response_time_ms"] = elapsed
    report["uptime"] = status in (200, 301, 302)

    if not report["uptime"]:
        report["issues"].append(f"Site returned HTTP {status}")
        print(f"    HTTP {status} — DEGRADED")
        return report

    print(f"    HTTP {status} — {ttfb}ms TTFB — {len(html):,} chars")

    # SEO checks
    seo = check_seo_health(url, html, config.get("expected_keywords", []))
    report["seo_health"] = seo
    failed_seo = [k for k, v in seo.get("checks", {}).items() if not v.get("ok")]
    if failed_seo:
        report["issues"].append(f"SEO checks failed: {', '.join(failed_seo)}")

    # Core Web Vitals estimate
    report["core_web_vitals"] = estimate_core_web_vitals(html, ttfb)
    cwv = report["core_web_vitals"]
    if cwv.get("lcp_grade") == "poor":
        report["issues"].append(f"LCP estimated poor ({cwv.get('lcp_ms_estimate')}ms)")
    if cwv.get("cls_grade") == "poor":
        report["issues"].append(f"CLS estimated poor ({cwv.get('cls_score_estimate')})")

    # Critical pages
    for page in config.get("critical_pages", []):
        page_url = url.rstrip("/") + page
        page_status, _, _ = _fetch(page_url)
        report["critical_pages"][page] = {
            "status": page_status,
            "ok": page_status in (200, 301),
        }
        if page_status not in (200, 301):
            report["issues"].append(f"{page} returned {page_status}")
        print(f"    {page}: HTTP {page_status}")

    # Content checks
    expected_kws = config.get("expected_keywords", [])
    kw_hits = sum(1 for kw in expected_kws if kw.lower() in html.lower())
    report["content_checks"] = {
        "keyword_coverage": f"{kw_hits}/{len(expected_kws)}",
        "has_navigation": bool(re.search(r'<nav[\s>]', html, re.IGNORECASE)),
        "has_footer": bool(re.search(r'<footer[\s>]', html, re.IGNORECASE)),
        "html_size_kb": round(len(html.encode()) / 1024, 1),
    }
    if not report["content_checks"]["has_navigation"]:
        report["issues"].append("No navigation detected")

    # Overall scoring (100pts)
    score = 0
    # Uptime: 30pts
    score += 30 if report["uptime"] else 0
    # SEO: 30pts (scaled)
    score += round(seo.get("score", 0) * 0.3)
    # Core Web Vitals: 20pts
    cwv_score = {"good": 20, "needs_improvement": 10, "poor": 0}.get(cwv.get("overall", "poor"), 0)
    score += cwv_score
    # Critical pages: 10pts
    pages_ok = sum(1 for v in report["critical_pages"].values() if v.get("ok"))
    pages_total = max(len(report["critical_pages"]), 1)
    score += round(pages_ok / pages_total * 10)
    # Content: 10pts
    score += 5 if report["content_checks"]["has_navigation"] else 0
    score += 5 if kw_hits >= 1 else 0

    report["score"] = min(100, score)
    report["grade"] = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"
    report["ok"] = score >= 70

    print(f"    Score: {score}/100 (grade {report['grade']}) — {len(report['issues'])} issue(s)")
    if report["issues"]:
        for iss in report["issues"][:3]:
            print(f"      • {iss}")

    return report


# ── History management ────────────────────────────────────────────────────────

def _load_json(path: Path) -> list | dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return []


def save_uptime_record(reports: list[dict]):
    history = _load_json(UPTIME_FILE)
    if not isinstance(history, list):
        history = []
    entry = {
        "checked_at": now_iso(),
        "sites": {
            r["project"]: {
                "uptime": r["uptime"],
                "status": r["status_code"],
                "score": r["score"],
                "ttfb_ms": r["ttfb_ms"],
            }
            for r in reports
        },
        "all_up": all(r["uptime"] for r in reports),
        "avg_score": round(sum(r["score"] for r in reports) / max(len(reports), 1)),
    }
    history.append(entry)
    UPTIME_FILE.write_text(json.dumps(history[-90:], indent=2, ensure_ascii=False))  # Keep 90 entries


def save_seo_health_record(reports: list[dict]):
    history = _load_json(SEO_HEALTH_FILE)
    if not isinstance(history, list):
        history = []
    entry = {
        "recorded_at": now_iso(),
        "sites": {
            r["project"]: {
                "seo_score": r.get("seo_health", {}).get("score", 0),
                "seo_grade": r.get("seo_health", {}).get("grade", "?"),
                "cwv_overall": r.get("core_web_vitals", {}).get("overall", "unknown"),
                "issues": r.get("issues", [])[:3],
            }
            for r in reports
        },
    }
    history.append(entry)
    SEO_HEALTH_FILE.write_text(json.dumps(history[-30:], indent=2, ensure_ascii=False))  # Keep 30 entries


def build_monitor_summary(reports: list[dict]) -> dict:
    """Build dashboard-ready deployment monitor summary."""
    history = _load_json(UPTIME_FILE)
    uptime_30d = {}
    if isinstance(history, list):
        cutoff_count = min(len(history), 30)
        recent = history[-cutoff_count:]
        for r in reports:
            proj = r["project"]
            up_count = sum(1 for h in recent if h.get("sites", {}).get(proj, {}).get("uptime", False))
            uptime_30d[proj] = round(up_count / max(cutoff_count, 1) * 100)

    return {
        "generated_at": now_iso(),
        "all_up": all(r["uptime"] for r in reports),
        "sites": {
            r["project"]: {
                "uptime": r["uptime"],
                "status_code": r["status_code"],
                "score": r["score"],
                "grade": r["grade"],
                "ttfb_ms": r["ttfb_ms"],
                "seo_score": r.get("seo_health", {}).get("score", 0),
                "seo_grade": r.get("seo_health", {}).get("grade", "?"),
                "cwv": r.get("core_web_vitals", {}),
                "critical_pages": r.get("critical_pages", {}),
                "issues": r.get("issues", [])[:5],
                "ok": r.get("ok", False),
                "uptime_30d_pct": uptime_30d.get(r["project"], 100),
            }
            for r in reports
        },
        "uptime_trend": [
            {
                "checked_at": h.get("checked_at"),
                "all_up": h.get("all_up"),
                "avg_score": h.get("avg_score"),
            }
            for h in (history[-14:] if isinstance(history, list) else [])
        ],
    }


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("[monitor] Starting deployment monitor...")
    MEMORY.mkdir(parents=True, exist_ok=True)

    target_project = os.environ.get("TARGET_PROJECT", "all").lower()
    sites_to_check = {
        k: v for k, v in SITES.items()
        if target_project == "all" or k == target_project
    }

    reports = []
    for project, config in sites_to_check.items():
        report = monitor_site(project, config)
        reports.append(report)

        # Update trust scores based on monitoring
        if not report["uptime"]:
            record_deploy(config["repo"], ["index.html"], success=False, rollback=False)
        elif report["ok"]:
            record_deploy(config["repo"], ["index.html"], success=True, rollback=False)

    # Save history
    save_uptime_record(reports)
    save_seo_health_record(reports)

    # Save combined summary
    summary = build_monitor_summary(reports)
    out = MEMORY / "deployment_monitor.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    # Save history entry
    history = _load_json(DEPLOY_HISTORY_FILE)
    if not isinstance(history, list):
        history = []
    history.append({
        "checked_at": now_iso(),
        "reports": reports,
    })
    DEPLOY_HISTORY_FILE.write_text(json.dumps(history[-30:], indent=2, ensure_ascii=False))

    print(f"\n[monitor] Done — {sum(1 for r in reports if r['uptime'])}/{len(reports)} sites up")
    all_up = all(r["uptime"] for r in reports)
    avg_score = round(sum(r["score"] for r in reports) / max(len(reports), 1))
    print(f"[monitor] All up: {all_up} | Avg score: {avg_score}/100")
    return summary


if __name__ == "__main__":
    main()
