"""
Live Validator — validates production sites via HTTP.
Checks: HTTP status, routes, AdSense, SEO basics, robots.txt, sitemap, broken links.
All stdlib — no external dependencies required.
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

from .registry import get_all_active_projects, get_project, get_adsense_publisher
from .report_store import save

USER_AGENT = "MIFTEH-AI-OS/1.0 (+https://github.com/Zakoosh/MIFTEH-AI-OS)"
TIMEOUT = 15

# Expected routes per project type — merged with registry required_pages
_DEFAULT_ROUTES = ["/", "/about", "/contact", "/privacy", "/terms", "/cookies"]
_SEO_ROUTES = ["/sitemap.xml", "/robots.txt"]


# ──────────────────────────────────────────────────────────────────────────────
# HTTP helpers
# ──────────────────────────────────────────────────────────────────────────────

def _fetch(url: str, timeout: int = TIMEOUT) -> tuple[int, str, dict]:
    """Fetch URL, return (status_code, body, headers). On error: (0, '', {})."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            charset = "utf-8"
            ct = r.headers.get("Content-Type", "")
            m = re.search(r"charset=([^\s;]+)", ct)
            if m:
                charset = m.group(1)
            body = r.read().decode(charset, errors="replace")
            return r.status, body, dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, "", {}
    except Exception:
        return 0, "", {}


class _LinkExtractor(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base = base_url
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        href = None
        if tag == "a":
            href = d.get("href")
        elif tag in ("link", "script"):
            href = d.get("href") or d.get("src")
        elif tag == "img":
            href = d.get("src")
        if href and href.startswith(("http", "/")):
            self.links.append(urllib.parse.urljoin(self.base, href))


# ──────────────────────────────────────────────────────────────────────────────
# Validation functions
# ──────────────────────────────────────────────────────────────────────────────

def check_http(url: str) -> dict:
    start = time.time()
    code, body, headers = _fetch(url)
    ms = int((time.time() - start) * 1000)
    ok = 200 <= code < 400
    return {
        "url": url,
        "status": code,
        "ok": ok,
        "response_ms": ms,
        "content_length": len(body),
        "server": headers.get("Server", ""),
        "content_type": headers.get("Content-Type", ""),
    }


def check_routes(domain: str, routes: list[str]) -> dict:
    base = f"https://{domain}"
    results = {}
    for route in routes:
        url = base + route
        code, _, _ = _fetch(url)
        results[route] = {
            "url": url,
            "status": code,
            "ok": 200 <= code < 400,
        }
    live = sum(1 for r in results.values() if r["ok"])
    return {
        "total": len(routes),
        "live": live,
        "dead": len(routes) - live,
        "routes": results,
    }


def check_adsense(domain: str, publisher_id: str) -> dict:
    url = f"https://{domain}"
    _, body, _ = _fetch(url)
    if not body:
        return {"ok": False, "reason": "Could not fetch page", "publisher_id": publisher_id}

    has_script = "pagead2.googlesyndication.com" in body
    has_pub_id = publisher_id in body
    auto_ads = 'adsbygoogle.js' in body or 'adsbygoogle' in body

    return {
        "ok": has_script and has_pub_id,
        "has_adsense_script": has_script,
        "has_publisher_id": has_pub_id,
        "has_auto_ads": auto_ads,
        "publisher_id": publisher_id,
        "url": url,
    }


def check_seo_basics(domain: str, path: str = "/") -> dict:
    url = f"https://{domain}{path}"
    _, body, _ = _fetch(url)
    if not body:
        return {"ok": False, "reason": "Could not fetch page", "url": url}

    def _meta(name: str) -> Optional[str]:
        m = re.search(
            rf'<meta[^>]+(?:name|property)=["\'](?:og:)?{re.escape(name)}["\'][^>]+content=["\'](.*?)["\']',
            body, re.IGNORECASE,
        )
        if not m:
            m = re.search(
                rf'<meta[^>]+content=["\'](.*?)["\'][^>]+(?:name|property)=["\'](?:og:)?{re.escape(name)}["\']',
                body, re.IGNORECASE,
            )
        return m.group(1).strip() if m else None

    title_m = re.search(r"<title[^>]*>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
    title = title_m.group(1).strip() if title_m else None
    description = _meta("description")
    canonical_m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\'](.*?)["\']', body, re.IGNORECASE)
    canonical = canonical_m.group(1) if canonical_m else None
    og_title = _meta("title")
    og_desc = _meta("description")
    h1_m = re.findall(r"<h1[^>]*>(.*?)</h1>", body, re.IGNORECASE | re.DOTALL)
    h1_count = len(h1_m)
    lang_m = re.search(r'<html[^>]+lang=["\']([^"\']+)["\']', body, re.IGNORECASE)
    lang = lang_m.group(1) if lang_m else None
    rtl_m = re.search(r'dir=["\']rtl["\']', body, re.IGNORECASE)

    score = 0
    issues = []
    if title and 10 <= len(title) <= 70:
        score += 20
    elif title:
        score += 10
        issues.append(f"Title length {len(title)} (optimal: 10-70)")
    else:
        issues.append("Missing <title>")

    if description and 50 <= len(description) <= 160:
        score += 20
    elif description:
        score += 10
        issues.append(f"Meta description length {len(description)} (optimal: 50-160)")
    else:
        issues.append("Missing meta description")

    if canonical:
        score += 15
    else:
        issues.append("Missing canonical URL")

    if og_title:
        score += 10
    if og_desc:
        score += 10

    if h1_count == 1:
        score += 15
    elif h1_count == 0:
        issues.append("Missing H1")
    else:
        issues.append(f"Multiple H1 tags ({h1_count})")

    if lang:
        score += 10

    return {
        "ok": score >= 60,
        "score": score,
        "url": url,
        "title": title,
        "title_length": len(title) if title else 0,
        "meta_description": description,
        "meta_description_length": len(description) if description else 0,
        "canonical": canonical,
        "og_title": og_title,
        "og_description": og_desc,
        "h1_count": h1_count,
        "lang": lang,
        "rtl": bool(rtl_m),
        "issues": issues,
    }


def check_robots(domain: str) -> dict:
    url = f"https://{domain}/robots.txt"
    code, body, _ = _fetch(url)
    if code != 200 or not body:
        return {"ok": False, "status": code, "url": url, "reason": "Not found or empty"}

    lines = [l.strip() for l in body.splitlines() if l.strip()]
    has_user_agent = any(l.lower().startswith("user-agent") for l in lines)
    has_sitemap = any(l.lower().startswith("sitemap") for l in lines)
    disallowed = [l.split(":", 1)[1].strip() for l in lines if l.lower().startswith("disallow")]
    sitemap_url = next(
        (l.split(":", 1)[1].strip() for l in lines if l.lower().startswith("sitemap")), None
    )
    blocks_all = any(d.strip() == "/" and "User-agent: *" in "\n".join(lines) for d in disallowed)

    return {
        "ok": has_user_agent and has_sitemap and not blocks_all,
        "status": code,
        "url": url,
        "has_user_agent": has_user_agent,
        "has_sitemap_directive": has_sitemap,
        "sitemap_url": sitemap_url,
        "blocks_all": blocks_all,
        "disallow_count": len(disallowed),
        "raw_lines": len(lines),
    }


def check_sitemap(domain: str) -> dict:
    url = f"https://{domain}/sitemap.xml"
    code, body, headers = _fetch(url)
    if code != 200 or not body:
        return {"ok": False, "status": code, "url": url, "reason": "Not found or empty"}

    urls = re.findall(r"<loc>(.*?)</loc>", body, re.IGNORECASE)
    last_mods = re.findall(r"<lastmod>(.*?)</lastmod>", body, re.IGNORECASE)
    is_index = "<sitemapindex" in body.lower()

    return {
        "ok": len(urls) > 0,
        "status": code,
        "url": url,
        "url_count": len(urls),
        "has_lastmod": len(last_mods) > 0,
        "is_sitemap_index": is_index,
        "sample_urls": urls[:5],
        "content_type": headers.get("Content-Type", ""),
    }


def check_broken_links(domain: str, max_links: int = 50) -> dict:
    base_url = f"https://{domain}"
    code, body, _ = _fetch(base_url)
    if not body:
        return {"ok": False, "reason": "Could not fetch homepage", "checked": 0, "broken": []}

    parser = _LinkExtractor(base_url)
    parser.feed(body)

    # Only check internal links
    internal = [
        l for l in parser.links
        if domain in l and not l.endswith((".css", ".js", ".png", ".jpg", ".svg", ".ico", ".woff"))
    ][:max_links]

    broken = []
    checked = 0
    for link in internal:
        c, _, _ = _fetch(link, timeout=8)
        checked += 1
        if c == 0 or c >= 400:
            broken.append({"url": link, "status": c})

    return {
        "ok": len(broken) == 0,
        "checked": checked,
        "broken_count": len(broken),
        "broken": broken[:20],
        "total_links_found": len(parser.links),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Full project validation
# ──────────────────────────────────────────────────────────────────────────────

def validate_project(project_id: str, check_links: bool = False) -> dict:
    """Run full validation suite for a project. Returns structured report."""
    p = get_project(project_id)
    domain = p["domain"]
    publisher_id = get_adsense_publisher(project_id)

    # Required pages from registry + defaults
    required = list({
        *_DEFAULT_ROUTES,
        *[f"/{pg.replace('.html', '')}" for pg in p.get("adsense", {}).get("required_pages", [])],
    })

    report: dict = {
        "project_id": project_id,
        "domain": domain,
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }

    # 1. Homepage HTTP
    report["http"] = check_http(f"https://{domain}")

    # 2. All routes
    all_routes = required + _SEO_ROUTES
    report["routes"] = check_routes(domain, all_routes)

    # 3. AdSense
    if publisher_id:
        report["adsense"] = check_adsense(domain, publisher_id)
    else:
        report["adsense"] = {"ok": None, "reason": "No publisher ID configured"}

    # 4. SEO basics
    report["seo"] = check_seo_basics(domain)

    # 5. Robots.txt
    report["robots"] = check_robots(domain)

    # 6. Sitemap
    report["sitemap"] = check_sitemap(domain)

    # 7. Broken links (optional — slow)
    if check_links:
        report["broken_links"] = check_broken_links(domain)

    # Overall health score
    checks = [
        report["http"]["ok"],
        report["routes"]["live"] >= report["routes"]["total"] * 0.8,
        report["adsense"].get("ok") is not False,
        report["seo"]["ok"],
        report["robots"]["ok"],
        report["sitemap"]["ok"],
    ]
    passed = sum(1 for c in checks if c)
    report["health_score"] = int(passed / len(checks) * 100)
    report["overall_ok"] = report["health_score"] >= 80

    # Save report
    save("live", project_id, report)
    return report


def validate_all(check_links: bool = False) -> dict:
    """Validate all active projects."""
    results = {}
    for p in get_all_active_projects():
        try:
            results[p["id"]] = validate_project(p["id"], check_links=check_links)
        except Exception as e:
            results[p["id"]] = {"error": str(e), "project_id": p["id"]}
    return results


if __name__ == "__main__":
    import sys
    pid = sys.argv[1] if len(sys.argv) > 1 else "yallaplays"
    links = "--links" in sys.argv
    r = validate_project(pid, check_links=links)
    print(json.dumps(r, indent=2, default=str))
