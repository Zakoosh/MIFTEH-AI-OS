"""
Indexing Intelligence Engine
Tracks indexed pages, non-indexed pages, sitemap freshness, orphan pages,
crawlability, and generates Google Search Console submission reports.
"""
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scripts.intelligence.registry import get_project, get_all_active_projects
from scripts.intelligence.report_store import save, load_latest, REPORTS_ROOT

REPORT_TYPE = "indexing"
USER_AGENT = "MIFTEH-AI-OS/1.0 IndexingIntelligence"
TIMEOUT = 12


def _fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except Exception:
        return 0, ""


# ──────────────────────────────────────────────────────────────────────────────
# Sitemap analysis
# ──────────────────────────────────────────────────────────────────────────────

def analyze_sitemap(domain: str) -> dict:
    """Fetch and analyze sitemap.xml for freshness and coverage."""
    url = f"https://{domain}/sitemap.xml"
    code, body = _fetch(url)
    if code != 200 or not body:
        return {"ok": False, "status": code, "url": url, "error": "Sitemap not accessible"}

    urls = re.findall(r"<loc>(.*?)</loc>", body, re.IGNORECASE)
    lastmods = re.findall(r"<lastmod>(.*?)</lastmod>", body, re.IGNORECASE)
    priorities = re.findall(r"<priority>(.*?)</priority>", body, re.IGNORECASE)
    changefreqs = re.findall(r"<changefreq>(.*?)</changefreq>", body, re.IGNORECASE)
    is_index = "<sitemapindex" in body.lower()

    # Freshness: check most recent lastmod
    latest_mod = None
    stale_count = 0
    today = datetime.now(timezone.utc)
    for mod in lastmods:
        try:
            mod_date = datetime.fromisoformat(mod.replace("Z", "+00:00"))
            if latest_mod is None or mod_date > latest_mod:
                latest_mod = mod_date
            days_old = (today - mod_date).days
            if days_old > 30:
                stale_count += 1
        except Exception:
            pass

    freshness_days = (today - latest_mod).days if latest_mod else None

    # Priority distribution
    priority_counts = {}
    for p in priorities:
        try:
            bucket = str(round(float(p), 1))
            priority_counts[bucket] = priority_counts.get(bucket, 0) + 1
        except Exception:
            pass

    has_high_priority = any(float(p) >= 0.8 for p in priorities if p.replace(".", "").isdigit())
    missing_lastmod = len(urls) - len(lastmods)

    issues = []
    if not lastmods:
        issues.append("No <lastmod> dates — add for better crawl scheduling")
    elif stale_count > 0:
        issues.append(f"{stale_count} URLs have lastmod >30 days old")
    if missing_lastmod > 0:
        issues.append(f"{missing_lastmod} URLs missing <lastmod>")
    if not priorities:
        issues.append("No <priority> tags — add to guide crawler focus")
    if not has_high_priority:
        issues.append("No URLs with priority ≥0.8 — homepage should be 1.0")
    if len(urls) == 0:
        issues.append("Sitemap has no URLs")

    return {
        "ok": len(urls) > 0 and code == 200,
        "url": url,
        "status": code,
        "total_urls": len(urls),
        "is_sitemap_index": is_index,
        "has_lastmod": len(lastmods) > 0,
        "latest_lastmod": latest_mod.isoformat() if latest_mod else None,
        "freshness_days": freshness_days,
        "stale_count": stale_count,
        "missing_lastmod": missing_lastmod,
        "priority_distribution": priority_counts,
        "changefreq_values": list(set(changefreqs)),
        "sample_urls": urls[:10],
        "issues": issues,
        "all_urls": urls,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Robots.txt analysis
# ──────────────────────────────────────────────────────────────────────────────

def analyze_robots(domain: str) -> dict:
    """Verify robots.txt allows all important paths."""
    url = f"https://{domain}/robots.txt"
    code, body = _fetch(url)
    if code != 200:
        return {"ok": False, "status": code, "url": url, "error": "robots.txt not found"}

    lines = [l.strip() for l in body.splitlines() if l.strip() and not l.startswith("#")]
    agents = [l for l in lines if l.lower().startswith("user-agent")]
    disallows = [l.split(":", 1)[-1].strip() for l in lines if l.lower().startswith("disallow")]
    allows = [l.split(":", 1)[-1].strip() for l in lines if l.lower().startswith("allow")]
    sitemaps = [l.split(":", 1)[-1].strip() for l in lines if l.lower().startswith("sitemap")]

    blocks_all = "/" in disallows and not allows
    crawl_delay = next((l.split(":", 1)[-1].strip() for l in lines if l.lower().startswith("crawl-delay")), None)

    blocked_paths = [d for d in disallows if d not in ("", "/")]
    important_blocked = [p for p in ["/games", "/about", "/contact", "/privacy"] if any(p.startswith(d) for d in blocked_paths)]

    issues = []
    if blocks_all:
        issues.append("CRITICAL: robots.txt blocks all crawlers (Disallow: /)")
    if not sitemaps:
        issues.append("Missing Sitemap: directive in robots.txt")
    if important_blocked:
        issues.append(f"Important paths may be blocked: {important_blocked}")
    if crawl_delay and int(crawl_delay) > 5:
        issues.append(f"High crawl-delay: {crawl_delay}s — may slow indexing")

    return {
        "ok": not blocks_all and bool(sitemaps),
        "url": url,
        "status": code,
        "user_agents": len(agents),
        "disallow_count": len(disallows),
        "allow_count": len(allows),
        "sitemap_urls": sitemaps,
        "blocks_all": blocks_all,
        "crawl_delay": crawl_delay,
        "blocked_paths": blocked_paths,
        "important_blocked": important_blocked,
        "issues": issues,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Indexability checking (proxy via HTTP + meta robots)
# ──────────────────────────────────────────────────────────────────────────────

def check_indexability(domain: str, urls: list[str], max_check: int = 30) -> dict:
    """Check if pages are indexable (no noindex, accessible)."""
    results = {}
    check_urls = urls[:max_check]

    for url in check_urls:
        full_url = url if url.startswith("http") else f"https://{domain}{url}"
        code, body = _fetch(full_url)

        noindex = False
        canonical_matches = True
        if body:
            robots_meta = re.search(
                r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'](.*?)["\']', body, re.IGNORECASE
            )
            if robots_meta and "noindex" in robots_meta.group(1).lower():
                noindex = True

            canonical_m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\'](.*?)["\']', body, re.IGNORECASE)
            if canonical_m:
                canonical_url = canonical_m.group(1).rstrip("/")
                page_url = full_url.rstrip("/")
                canonical_matches = canonical_url == page_url or page_url.endswith(canonical_url.split("/")[-1])

        path = url if not url.startswith("http") else "/" + "/".join(url.split("/")[3:])
        results[path] = {
            "url": full_url,
            "status": code,
            "accessible": 200 <= code < 400,
            "noindex": noindex,
            "indexable": 200 <= code < 400 and not noindex,
            "canonical_ok": canonical_matches,
        }

    indexable = sum(1 for r in results.values() if r["indexable"])
    not_indexable = sum(1 for r in results.values() if not r["indexable"])
    noindex_count = sum(1 for r in results.values() if r["noindex"])
    broken = sum(1 for r in results.values() if not r["accessible"])

    return {
        "checked": len(results),
        "indexable": indexable,
        "not_indexable": not_indexable,
        "noindex_count": noindex_count,
        "broken_count": broken,
        "indexability_pct": round(indexable / max(len(results), 1) * 100),
        "pages": results,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Orphan page detection
# ──────────────────────────────────────────────────────────────────────────────

def detect_orphan_pages(domain: str, sitemap_urls: list[str]) -> dict:
    """Find sitemap URLs not linked from the homepage link graph."""
    from scripts.intelligence.seo_engine import _crawl_internal_urls
    linked = _crawl_internal_urls(domain, depth=1)

    orphans = []
    for url in sitemap_urls:
        norm = url.rstrip("/")
        if (norm != f"https://{domain}" and
            norm not in linked and
            f"{norm}/" not in linked):
            orphans.append(url)

    return {
        "sitemap_urls": len(sitemap_urls),
        "crawled_linked_urls": len(linked),
        "orphan_count": len(orphans),
        "orphans": orphans[:30],
        "orphan_pct": round(len(orphans) / max(len(sitemap_urls), 1) * 100),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Google Search Console submission helpers
# ──────────────────────────────────────────────────────────────────────────────

def build_gsc_submission_plan(domain: str, sitemap_url: str, priority_urls: list[str]) -> dict:
    """Generate a GSC submission checklist (manual steps + Indexing API prep)."""
    return {
        "domain": domain,
        "sitemap_submission": {
            "url": sitemap_url,
            "gsc_url": f"https://search.google.com/search-console/sitemaps?resource_id=sc-domain%3A{domain}",
            "action": "Submit sitemap in Google Search Console",
        },
        "url_inspection": {
            "tool": f"https://search.google.com/search-console/inspect?resource_id=sc-domain%3A{domain}",
            "priority_urls": priority_urls[:10],
            "action": "Request indexing for high-priority URLs via URL Inspection tool",
        },
        "indexing_api": {
            "endpoint": "https://indexing.googleapis.com/v3/urlNotifications:publish",
            "type": "URL_UPDATED",
            "note": "Requires Google Search Console API credentials (service account)",
            "sample_payload": {
                "url": f"https://{domain}/",
                "type": "URL_UPDATED",
            },
        },
        "checklist": [
            "Verify domain ownership in Google Search Console",
            "Submit sitemap.xml",
            "Request indexing for homepage and top 10 pages",
            "Check Coverage report for crawl errors",
            "Monitor Index Coverage > Pages report weekly",
        ],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Full indexing analysis
# ──────────────────────────────────────────────────────────────────────────────

def analyze_project(project_id: str) -> dict:
    p = get_project(project_id)
    domain = p["domain"]

    sitemap = analyze_sitemap(domain)
    robots = analyze_robots(domain)
    sitemap_urls = sitemap.get("all_urls", [])

    # Check indexability for priority pages + sample from sitemap
    priority = ["/", "/games", "/about", "/contact", "/privacy", "/terms", "/cookies"]
    sample_from_sitemap = sitemap_urls[:20]
    check_urls = list(dict.fromkeys(priority + sample_from_sitemap))
    indexability = check_indexability(domain, check_urls)

    orphans = detect_orphan_pages(domain, sitemap_urls)

    gsc_plan = build_gsc_submission_plan(
        domain,
        f"https://{domain}/sitemap.xml",
        [u for u in sitemap_urls[:10] if u],
    )

    # Overall indexing health score
    score = 0
    if sitemap["ok"]:
        score += 25
    if robots["ok"]:
        score += 20
    if indexability["indexability_pct"] >= 90:
        score += 30
    elif indexability["indexability_pct"] >= 70:
        score += 15
    if orphans["orphan_pct"] <= 10:
        score += 15
    elif orphans["orphan_pct"] <= 30:
        score += 7
    if sitemap["freshness_days"] is not None and sitemap["freshness_days"] <= 7:
        score += 10

    all_issues = sitemap.get("issues", []) + robots.get("issues", [])
    if orphans["orphan_count"] > 0:
        all_issues.append(f"{orphans['orphan_count']} orphan pages not linked from homepage")

    report = {
        "project_id": project_id,
        "domain": domain,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "indexing_score": score,
        "indexing_status": (
            "healthy" if score >= 75 else
            "degraded" if score >= 50 else
            "critical"
        ),
        "sitemap": {k: v for k, v in sitemap.items() if k != "all_urls"},
        "robots": robots,
        "indexability": indexability,
        "orphans": orphans,
        "gsc_plan": gsc_plan,
        "total_issues": len(all_issues),
        "issues": all_issues,
        "recommendations": [
            i for i in [
                "Update sitemap lastmod dates to today" if sitemap.get("freshness_days", 999) > 7 else None,
                "Add Sitemap: directive to robots.txt" if not robots.get("sitemap_urls") else None,
                f"Fix {orphans['orphan_count']} orphan pages by adding internal links" if orphans["orphan_count"] > 0 else None,
                f"Request indexing for {indexability.get('not_indexable', 0)} non-indexable pages" if indexability.get("not_indexable", 0) > 0 else None,
                "Submit updated sitemap to Google Search Console" if score < 75 else None,
            ]
            if i
        ],
    }

    save(REPORT_TYPE, project_id, report)
    return report


def analyze_all() -> dict:
    results = {}
    for p in get_all_active_projects():
        try:
            results[p["id"]] = analyze_project(p["id"])
        except Exception as e:
            results[p["id"]] = {"error": str(e), "project_id": p["id"]}
    return results


if __name__ == "__main__":
    import sys
    pid = sys.argv[1] if len(sys.argv) > 1 else "yallaplays"
    r = analyze_project(pid)
    print(json.dumps({k: v for k, v in r.items() if k not in ("sitemap", "indexability", "orphans")}, indent=2))
