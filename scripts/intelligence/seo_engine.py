"""
SEO Intelligence Engine — deep metadata analysis, schema validation,
keyword coverage, internal link graph, orphan page detection, indexing readiness.
"""
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Optional

from .registry import get_project, get_all_active_projects
from .report_store import save

USER_AGENT = "MIFTEH-AI-OS/1.0 SEO-Engine"
TIMEOUT = 12


def _fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read().decode("utf-8", errors="replace")
            return r.status, body
    except Exception:
        return 0, ""


# ──────────────────────────────────────────────────────────────────────────────
# HTML Parsers
# ──────────────────────────────────────────────────────────────────────────────

class _HeadingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.headings: list[tuple[str, str]] = []  # (tag, text)
        self._current = None
        self._buf = []

    def handle_starttag(self, tag, attrs):
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._current = tag
            self._buf = []

    def handle_endtag(self, tag):
        if tag == self._current:
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            self.headings.append((tag, text))
            self._current = None

    def handle_data(self, data):
        if self._current:
            self._buf.append(data)


class _LinkParser(HTMLParser):
    def __init__(self, base: str):
        super().__init__()
        self.base = base
        self.internal: list[dict] = []
        self.external: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        d = dict(attrs)
        href = d.get("href", "")
        text = d.get("title", "")
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            return
        abs_url = urllib.parse.urljoin(self.base, href)
        parsed_base = urllib.parse.urlparse(self.base)
        parsed = urllib.parse.urlparse(abs_url)
        if parsed.netloc == parsed_base.netloc:
            self.internal.append({"url": abs_url, "anchor": text, "href": href})
        else:
            self.external.append(abs_url)


class _SchemaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.schemas: list[dict] = []
        self._in_script = False
        self._script_type = ""
        self._buf = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "script":
            self._script_type = d.get("type", "")
            if "application/ld+json" in self._script_type:
                self._in_script = True
                self._buf = []

    def handle_endtag(self, tag):
        if tag == "script" and self._in_script:
            raw = "".join(self._buf).strip()
            try:
                self.schemas.append(json.loads(raw))
            except json.JSONDecodeError:
                pass
            self._in_script = False

    def handle_data(self, data):
        if self._in_script:
            self._buf.append(data)


# ──────────────────────────────────────────────────────────────────────────────
# Page-level analysis
# ──────────────────────────────────────────────────────────────────────────────

def analyze_page(url: str) -> dict:
    """Deep SEO analysis of a single page."""
    code, body = _fetch(url)
    if not body:
        return {"url": url, "status": code, "ok": False, "error": "Could not fetch"}

    # Meta tags
    def _meta(attr_name: str, attr_val: str) -> Optional[str]:
        for pattern in [
            rf'<meta[^>]+{attr_name}=["\'](?:og:)?{re.escape(attr_val)}["\'][^>]+content=["\'](.*?)["\']',
            rf'<meta[^>]+content=["\'](.*?)["\'][^>]+{attr_name}=["\'](?:og:)?{re.escape(attr_val)}["\']',
        ]:
            m = re.search(pattern, body, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    title_m = re.search(r"<title[^>]*>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
    title = re.sub(r"\s+", " ", title_m.group(1)).strip() if title_m else None
    description = _meta("name", "description")
    keywords = _meta("name", "keywords")
    robots_meta = _meta("name", "robots")
    canonical_m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\'](.*?)["\']', body, re.IGNORECASE)
    canonical = canonical_m.group(1) if canonical_m else None
    og_title = _meta("property", "title")
    og_description = _meta("property", "description")
    og_image = _meta("property", "image")
    og_url = _meta("property", "url")
    og_type = _meta("property", "type")
    twitter_card = _meta("name", "twitter:card")
    lang_m = re.search(r'<html[^>]+lang=["\']([^"\']+)["\']', body, re.IGNORECASE)
    lang = lang_m.group(1) if lang_m else None
    dir_m = re.search(r'dir=["\']([^"\']+)["\']', body, re.IGNORECASE)
    text_dir = dir_m.group(1) if dir_m else None

    # Headings
    hp = _HeadingParser()
    hp.feed(body)
    headings = hp.headings
    h1s = [h for h in headings if h[0] == "h1"]
    h2s = [h for h in headings if h[0] == "h2"]

    # Schema
    sp = _SchemaParser()
    sp.feed(body)
    schemas = sp.schemas
    schema_types = [s.get("@type") for s in schemas if s.get("@type")]

    # Links
    lp = _LinkParser(url)
    lp.feed(body)

    # Image alt attributes
    img_total = len(re.findall(r"<img[^>]+>", body, re.IGNORECASE))
    img_with_alt = len(re.findall(r'<img[^>]+alt=["\'][^"\']+["\'][^>]*>', body, re.IGNORECASE))
    img_missing_alt = img_total - img_with_alt

    # Indexability
    noindex = bool(robots_meta and "noindex" in robots_meta.lower())
    nofollow = bool(robots_meta and "nofollow" in robots_meta.lower())

    # Scoring
    score = 0
    issues = []
    suggestions = []

    if title and 10 <= len(title) <= 70:
        score += 15
    elif title:
        score += 7
        issues.append(f"Title length {len(title)} chars — optimal 10-70")
    else:
        issues.append("Missing <title> tag")

    if description and 50 <= len(description) <= 160:
        score += 15
    elif description:
        score += 7
        issues.append(f"Meta description {len(description)} chars — optimal 50-160")
    else:
        issues.append("Missing meta description")

    if canonical:
        score += 10
    else:
        issues.append("Missing canonical URL")
        suggestions.append("Add <link rel='canonical' href='...'> to prevent duplicate content")

    if len(h1s) == 1:
        score += 10
    elif len(h1s) == 0:
        issues.append("Missing H1 tag")
    else:
        issues.append(f"Multiple H1 tags ({len(h1s)}) — use only one")

    if len(h2s) >= 1:
        score += 5

    if og_title and og_description and og_image:
        score += 10
    elif og_title:
        score += 5
        suggestions.append("Add og:description and og:image for social sharing")
    else:
        issues.append("Missing Open Graph tags")

    if twitter_card:
        score += 5

    if schemas:
        score += 10
        if "WebSite" not in schema_types and "Organization" not in schema_types:
            suggestions.append("Add WebSite or Organization schema for better rich results")
    else:
        issues.append("No structured data (JSON-LD) found")
        suggestions.append("Add JSON-LD schema for WebSite, BreadcrumbList, etc.")

    if lang:
        score += 5
    else:
        issues.append("Missing lang attribute on <html>")

    if img_total > 0 and img_missing_alt == 0:
        score += 5
    elif img_missing_alt > 0:
        issues.append(f"{img_missing_alt} images missing alt text")

    if noindex:
        score -= 30
        issues.append("Page has noindex — will not be indexed by search engines")

    return {
        "url": url,
        "status": code,
        "ok": score >= 60 and not noindex,
        "seo_score": min(100, max(0, score)),
        "indexable": not noindex,
        "title": title,
        "title_length": len(title) if title else 0,
        "meta_description": description,
        "meta_description_length": len(description) if description else 0,
        "keywords": keywords,
        "canonical": canonical,
        "lang": lang,
        "text_direction": text_dir,
        "robots_meta": robots_meta,
        "noindex": noindex,
        "nofollow": nofollow,
        "og": {
            "title": og_title,
            "description": og_description,
            "image": og_image,
            "url": og_url,
            "type": og_type,
        },
        "twitter_card": twitter_card,
        "headings": {
            "h1": h1s,
            "h2": [h[1] for h in h2s[:5]],
            "h1_count": len(h1s),
            "h2_count": len(h2s),
            "total": len(headings),
        },
        "schema": {
            "count": len(schemas),
            "types": schema_types,
        },
        "images": {
            "total": img_total,
            "with_alt": img_with_alt,
            "missing_alt": img_missing_alt,
        },
        "links": {
            "internal_count": len(lp.internal),
            "external_count": len(lp.external),
            "internal_sample": lp.internal[:10],
        },
        "issues": issues,
        "suggestions": suggestions,
    }


def detect_orphan_pages(domain: str, sitemap_urls: list[str], linked_urls: set[str]) -> list[str]:
    """Pages in sitemap not reachable from homepage link graph."""
    base = f"https://{domain}"
    orphans = []
    for url in sitemap_urls:
        norm = url.rstrip("/")
        if norm != base and norm not in linked_urls and f"{norm}/" not in linked_urls:
            orphans.append(url)
    return orphans


def _extract_sitemap_urls(domain: str) -> list[str]:
    _, body = _fetch(f"https://{domain}/sitemap.xml")
    if not body:
        return []
    return re.findall(r"<loc>(.*?)</loc>", body, re.IGNORECASE)


def _crawl_internal_urls(domain: str, depth: int = 1) -> set[str]:
    """BFS crawl to discover linked internal URLs."""
    base = f"https://{domain}"
    visited: set[str] = {base}
    queue = [base]
    for _ in range(depth):
        next_queue = []
        for url in queue:
            _, body = _fetch(url)
            if not body:
                continue
            lp = _LinkParser(base)
            lp.feed(body)
            for link in lp.internal:
                href = link["url"].split("?")[0].split("#")[0].rstrip("/")
                if href not in visited and domain in href:
                    visited.add(href)
                    next_queue.append(href)
        queue = next_queue[:30]  # cap per level
    return visited


# ──────────────────────────────────────────────────────────────────────────────
# Full project SEO analysis
# ──────────────────────────────────────────────────────────────────────────────

_PRIORITY_PAGES = ["/", "/about", "/contact", "/privacy", "/terms", "/cookies", "/games"]


def analyze_project(project_id: str) -> dict:
    """Run full SEO intelligence analysis for a project."""
    p = get_project(project_id)
    domain = p["domain"]
    base = f"https://{domain}"

    pages_analysis = {}
    for route in _PRIORITY_PAGES:
        url = f"https://{domain}{route}"
        pages_analysis[route] = analyze_page(url)

    # Sitemap and orphan detection
    sitemap_urls = _extract_sitemap_urls(domain)
    linked_urls = _crawl_internal_urls(domain, depth=1)
    orphans = detect_orphan_pages(domain, sitemap_urls, linked_urls)

    # Aggregate score
    scored_pages = [v for v in pages_analysis.values() if isinstance(v.get("seo_score"), int)]
    avg_score = int(sum(v["seo_score"] for v in scored_pages) / len(scored_pages)) if scored_pages else 0

    # Collect all issues across pages
    all_issues = []
    for route, analysis in pages_analysis.items():
        for issue in analysis.get("issues", []):
            all_issues.append({"page": route, "issue": issue})

    # Indexing readiness
    homepage = pages_analysis.get("/", {})
    indexing_ready = (
        homepage.get("indexable", False)
        and homepage.get("canonical") is not None
        and homepage.get("seo_score", 0) >= 60
    )

    report = {
        "project_id": project_id,
        "domain": domain,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "overall_seo_score": avg_score,
        "indexing_ready": indexing_ready,
        "sitemap_url_count": len(sitemap_urls),
        "crawled_urls": len(linked_urls),
        "orphan_pages": orphans[:20],
        "orphan_count": len(orphans),
        "total_issues": len(all_issues),
        "issues": all_issues[:50],
        "pages": pages_analysis,
    }

    save("seo", project_id, report)
    return report


if __name__ == "__main__":
    import sys
    pid = sys.argv[1] if len(sys.argv) > 1 else "yallaplays"
    r = analyze_project(pid)
    print(json.dumps({k: v for k, v in r.items() if k != "pages"}, indent=2))
    print(f"\nAnalyzed {len(r['pages'])} pages — score: {r['overall_seo_score']}/100")
