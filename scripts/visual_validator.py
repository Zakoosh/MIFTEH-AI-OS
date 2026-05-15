"""
MIFTEH OS — Visual Validator
Scores HTML files without a browser: SEO, Mobile, Accessibility, Performance, UX.
Total: 100 points. passes_auto_merge_threshold = score >= 70.

Usage:
    from visual_validator import validate_html
    report = validate_html(html_str, label="my-feature", project="yallaplays")
    # or from CLI:
    python scripts/visual_validator.py path/to/file.html
"""

import re
import sys
import json
from pathlib import Path
from datetime import datetime, timezone


# ── helpers ──────────────────────────────────────────────────────────────────

def _find(pattern, html, flags=re.IGNORECASE | re.DOTALL):
    return bool(re.search(pattern, html, flags))

def _findall(pattern, html, flags=re.IGNORECASE | re.DOTALL):
    return re.findall(pattern, html, flags)

def _count(pattern, html, flags=re.IGNORECASE | re.DOTALL):
    return len(re.findall(pattern, html, flags))


# ── scoring categories ────────────────────────────────────────────────────────

def score_seo(html: str) -> tuple[int, int, list[str]]:
    """SEO checks — max 30 points."""
    max_pts = 30
    earned = 0
    issues = []

    # title tag (5 pts)
    title_m = re.search(r'<title[^>]*>(.+?)</title>', html, re.IGNORECASE | re.DOTALL)
    if title_m:
        title_text = title_m.group(1).strip()
        if 20 <= len(title_text) <= 70:
            earned += 5
        else:
            earned += 2
            issues.append(f"Title length {len(title_text)} (ideal 20-70 chars)")
    else:
        issues.append("Missing <title> tag")

    # meta description (5 pts)
    desc_m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if not desc_m:
        desc_m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']', html, re.IGNORECASE)
    if desc_m:
        desc_text = desc_m.group(1).strip()
        if 50 <= len(desc_text) <= 160:
            earned += 5
        else:
            earned += 2
            issues.append(f"Meta description length {len(desc_text)} (ideal 50-160 chars)")
    else:
        issues.append("Missing meta description")

    # canonical (3 pts)
    if _find(r'<link[^>]+rel=["\']canonical["\']', html):
        earned += 3
    else:
        issues.append("Missing canonical link")

    # OG tags (5 pts: 1 each for og:title, og:description, og:url, og:image, og:type)
    og_tags = ["og:title", "og:description", "og:url", "og:image", "og:type"]
    og_found = sum(1 for t in og_tags if _find(rf'<meta[^>]+property=["\']og:{t.split(":")[1]}["\']', html))
    og_pts = min(5, og_found)
    earned += og_pts
    if og_pts < 3:
        issues.append(f"Only {og_found}/5 Open Graph tags present")

    # JSON-LD structured data (5 pts)
    if _find(r'<script[^>]+type=["\']application/ld\+json["\']', html):
        earned += 5
    else:
        issues.append("No JSON-LD structured data")

    # H1 tag (4 pts)
    h1_count = _count(r'<h1[\s>]', html)
    if h1_count == 1:
        earned += 4
    elif h1_count > 1:
        earned += 2
        issues.append(f"Multiple H1 tags ({h1_count}) — should have exactly one")
    else:
        issues.append("Missing H1 tag")

    # lang attribute (3 pts)
    if _find(r'<html[^>]+lang=["\'][^"\']+["\']', html):
        earned += 3
    else:
        issues.append("Missing lang attribute on <html>")

    return min(earned, max_pts), max_pts, issues


def score_mobile(html: str) -> tuple[int, int, list[str]]:
    """Mobile-readiness checks — max 25 points."""
    max_pts = 25
    earned = 0
    issues = []

    # viewport meta (8 pts — critical)
    if _find(r'<meta[^>]+name=["\']viewport["\']', html):
        viewport_m = re.search(r'<meta[^>]+name=["\']viewport["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if not viewport_m:
            viewport_m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']viewport["\']', html, re.IGNORECASE)
        if viewport_m and "width=device-width" in viewport_m.group(1):
            earned += 8
        else:
            earned += 4
            issues.append("Viewport meta found but missing width=device-width")
    else:
        issues.append("Missing viewport meta tag — site will not render correctly on mobile")

    # media queries (7 pts)
    mq_count = _count(r'@media\s*\(', html)
    if mq_count >= 3:
        earned += 7
    elif mq_count >= 1:
        earned += 4
        issues.append(f"Only {mq_count} media query found — consider more responsive breakpoints")
    else:
        issues.append("No CSS media queries detected — layout may break on mobile")

    # no fixed pixel widths on containers (3 pts)
    fixed_widths = _count(r'width\s*:\s*\d{4,}px', html)
    if fixed_widths == 0:
        earned += 3
    else:
        issues.append(f"{fixed_widths} large fixed pixel widths detected — may cause overflow on small screens")

    # touch-friendly: no hover-only interactions (2 pts)
    hover_only = _count(r':hover\s*\{[^}]*(?:display|visibility)\s*:', html)
    if hover_only == 0:
        earned += 2
    else:
        issues.append(f"{hover_only} hover-only visibility pattern(s) — inaccessible on touch devices")

    # max-width usage (2 pts)
    if _find(r'max-width\s*:', html):
        earned += 2
    else:
        issues.append("No max-width detected — consider constraining layout width")

    # no horizontal scroll triggers (3 pts)
    overflow_x = _find(r'overflow-x\s*:\s*auto|overflow-x\s*:\s*scroll', html)
    if not overflow_x:
        earned += 3
    else:
        issues.append("overflow-x scroll/auto found — verify this is intentional")

    return min(earned, max_pts), max_pts, issues


def score_accessibility(html: str) -> tuple[int, int, list[str]]:
    """Accessibility checks — max 20 points."""
    max_pts = 20
    earned = 0
    issues = []

    # img alt attributes (6 pts)
    imgs_total = _count(r'<img\s', html)
    imgs_with_alt = _count(r'<img\s[^>]*alt=["\'][^"\']*["\']', html)
    if imgs_total == 0:
        earned += 6
    elif imgs_with_alt == imgs_total:
        earned += 6
    else:
        ratio = imgs_with_alt / imgs_total
        earned += int(6 * ratio)
        issues.append(f"{imgs_total - imgs_with_alt}/{imgs_total} images missing alt attributes")

    # heading hierarchy (4 pts)
    headings = re.findall(r'<(h[1-6])[\s>]', html, re.IGNORECASE)
    if headings:
        levels = [int(h[1]) for h in headings]
        bad_jumps = sum(1 for i in range(1, len(levels)) if levels[i] - levels[i-1] > 1)
        if bad_jumps == 0:
            earned += 4
        else:
            earned += 2
            issues.append(f"{bad_jumps} heading level jump(s) — headings should not skip levels")
    else:
        issues.append("No heading tags found")

    # aria-label / role attributes (4 pts)
    aria_count = _count(r'aria-[a-z]+=', html)
    role_count = _count(r'\brole=["\']', html)
    if aria_count + role_count >= 5:
        earned += 4
    elif aria_count + role_count >= 2:
        earned += 2
        issues.append("Limited ARIA attributes — consider adding more for screen reader support")
    else:
        issues.append("No ARIA attributes found — important for screen reader accessibility")

    # form labels (3 pts)
    inputs = _count(r'<input[^>]+type=["\'](?:text|email|password|tel|search)["\']', html)
    labels = _count(r'<label\s', html)
    if inputs == 0 or labels >= inputs:
        earned += 3
    else:
        issues.append(f"{inputs - labels} form input(s) may be missing labels")

    # skip link (1 pt)
    if _find(r'href=["\']#(?:main|content|skip)["\']', html):
        earned += 1
    # (no penalty — it's nice-to-have)

    # focus styles (2 pts)
    if _find(r':focus\s*\{', html):
        earned += 2
    else:
        issues.append("No :focus styles — keyboard navigation may be invisible")

    return min(earned, max_pts), max_pts, issues


def score_performance(html: str) -> tuple[int, int, list[str]]:
    """Performance checks — max 15 points."""
    max_pts = 15
    earned = 0
    issues = []

    # lazy loading on images (3 pts)
    imgs_total = _count(r'<img\s', html)
    lazy_imgs = _count(r'<img\s[^>]*loading=["\']lazy["\']', html)
    if imgs_total == 0 or lazy_imgs >= max(1, imgs_total - 1):
        earned += 3
    elif lazy_imgs > 0:
        earned += 1
        issues.append(f"Only {lazy_imgs}/{imgs_total} images use loading='lazy'")
    else:
        if imgs_total > 3:
            issues.append(f"{imgs_total} images without lazy loading — consider adding loading='lazy'")

    # no render-blocking inline scripts (3 pts)
    blocking_scripts = _count(r'<script(?!\s[^>]*(?:async|defer|type=["\']module))[^>]*src=["\']', html)
    if blocking_scripts == 0:
        earned += 3
    else:
        earned += 1
        issues.append(f"{blocking_scripts} potentially render-blocking external script(s)")

    # HTML size (3 pts)
    size_kb = len(html.encode("utf-8")) / 1024
    if size_kb <= 100:
        earned += 3
    elif size_kb <= 200:
        earned += 1
        issues.append(f"HTML size {size_kb:.1f} KB — consider reducing (ideal < 100 KB)")
    else:
        issues.append(f"HTML size {size_kb:.1f} KB — too large, will hurt TTI")

    # no external CDN font blocking (3 pts)
    cdn_fonts = _count(r'<link[^>]+href=["\'][^"\']*(?:fonts\.googleapis\.com|fonts\.gstatic\.com)[^"\']*["\'](?![^>]*(?:preload|preconnect))', html)
    if cdn_fonts == 0:
        earned += 3
    else:
        earned += 1
        issues.append(f"{cdn_fonts} Google Fonts link(s) without preconnect — consider adding rel='preconnect'")

    # preload / prefetch hints (3 pts)
    if _find(r'<link[^>]+rel=["\'](?:preload|prefetch|preconnect)["\']', html):
        earned += 3
    else:
        issues.append("No preload/prefetch/preconnect hints — consider adding for critical resources")

    return min(earned, max_pts), max_pts, issues


def score_ux(html: str) -> tuple[int, int, list[str]]:
    """UX quality checks — max 10 points."""
    max_pts = 10
    earned = 0
    issues = []

    # has navigation (2 pts)
    if _find(r'<nav[\s>]', html) or _find(r'role=["\']navigation["\']', html):
        earned += 2
    else:
        issues.append("No <nav> element — consider adding navigation for usability")

    # has footer (1 pt)
    if _find(r'<footer[\s>]', html):
        earned += 1

    # has call-to-action (2 pts)
    cta_patterns = [
        r'<a[^>]*class=["\'][^"\']*(?:btn|button|cta)[^"\']*["\']',
        r'<button[^>]*>',
        r'<a[^>]*href=[^>]+>[^<]*(?:get started|sign up|learn more|try|download|subscribe|contact|join)',
    ]
    if any(_find(p, html) for p in cta_patterns):
        earned += 2
    else:
        issues.append("No clear call-to-action button or link found")

    # no broken placeholder content (2 pts)
    placeholders = _count(r'(?:lorem ipsum|placeholder text|\[insert\]|\{\{[^}]+\}\}|FIXME|TODO:)', html, re.IGNORECASE)
    if placeholders == 0:
        earned += 2
    else:
        issues.append(f"{placeholders} placeholder text(s) found — remove before publishing")

    # page has meaningful content length (3 pts)
    # strip tags and measure text
    text_only = re.sub(r'<[^>]+>', ' ', html)
    text_only = re.sub(r'\s+', ' ', text_only).strip()
    word_count = len(text_only.split())
    if word_count >= 300:
        earned += 3
    elif word_count >= 100:
        earned += 1
        issues.append(f"Only ~{word_count} words of visible text — consider adding more content")
    else:
        issues.append(f"Very little visible text (~{word_count} words) — page may appear thin to users")

    return min(earned, max_pts), max_pts, issues


# ── main entry point ──────────────────────────────────────────────────────────

GRADE_MAP = [(90, "A"), (80, "B"), (70, "C"), (60, "D")]

def _grade(score: int) -> str:
    for threshold, letter in GRADE_MAP:
        if score >= threshold:
            return letter
    return "F"


def validate_html(html: str, label: str = "", project: str = "") -> dict:
    """
    Validate HTML and return a quality report dict.

    Keys:
        label, project, validated_at
        score (0-100), grade (A-F), passes_auto_merge_threshold (bool)
        categories: {seo, mobile, accessibility, performance, ux}
            each: {score, max, issues}
        all_issues: [str]
        summary: str
    """
    seo_score,   seo_max,   seo_issues   = score_seo(html)
    mob_score,   mob_max,   mob_issues   = score_mobile(html)
    a11y_score,  a11y_max,  a11y_issues  = score_accessibility(html)
    perf_score,  perf_max,  perf_issues  = score_performance(html)
    ux_score,    ux_max,    ux_issues    = score_ux(html)

    total = seo_score + mob_score + a11y_score + perf_score + ux_score
    all_issues = seo_issues + mob_issues + a11y_issues + perf_issues + ux_issues

    grade = _grade(total)
    passes = total >= 70

    summary_parts = []
    if seo_score < seo_max * 0.6:
        summary_parts.append("SEO weak")
    if mob_score < mob_max * 0.6:
        summary_parts.append("mobile layout concerns")
    if a11y_score < a11y_max * 0.6:
        summary_parts.append("accessibility gaps")
    if perf_score < perf_max * 0.6:
        summary_parts.append("performance issues")

    if passes and not summary_parts:
        summary = f"Grade {grade} — passes auto-merge threshold"
    elif passes:
        summary = f"Grade {grade} — passes threshold; improve: {', '.join(summary_parts)}"
    else:
        summary = f"Grade {grade} — blocked from auto-merge; fix: {', '.join(summary_parts) or 'review issues'}"

    return {
        "label": label,
        "project": project,
        "validated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "score": total,
        "grade": grade,
        "passes_auto_merge_threshold": passes,
        "categories": {
            "seo":           {"score": seo_score,  "max": seo_max,  "issues": seo_issues},
            "mobile":        {"score": mob_score,   "max": mob_max,  "issues": mob_issues},
            "accessibility": {"score": a11y_score,  "max": a11y_max, "issues": a11y_issues},
            "performance":   {"score": perf_score,  "max": perf_max, "issues": perf_issues},
            "ux":            {"score": ux_score,    "max": ux_max,   "issues": ux_issues},
        },
        "all_issues": all_issues,
        "summary": summary,
    }


def validate_file(path: str | Path, label: str = "", project: str = "") -> dict:
    """Convenience wrapper for validating a file on disk."""
    p = Path(path)
    if not label:
        label = p.name
    html = p.read_text(encoding="utf-8", errors="replace")
    return validate_html(html, label=label, project=project)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/visual_validator.py <file.html> [label] [project]")
        sys.exit(1)

    path = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else ""
    project = sys.argv[3] if len(sys.argv) > 3 else ""

    report = validate_file(path, label=label, project=project)

    print(f"\n{'='*60}")
    print(f"  Visual QA Report — {report['label'] or path}")
    print(f"{'='*60}")
    print(f"  Score  : {report['score']}/100  (Grade {report['grade']})")
    print(f"  Status : {'✓ PASSES' if report['passes_auto_merge_threshold'] else '✗ BLOCKED'}")
    print(f"  Summary: {report['summary']}")
    print()
    for cat, data in report["categories"].items():
        bar = "█" * data["score"] + "░" * (data["max"] - data["score"])
        print(f"  {cat.capitalize():<15} {data['score']:>2}/{data['max']}  {bar}")
    if report["all_issues"]:
        print("\n  Issues:")
        for issue in report["all_issues"]:
            print(f"    • {issue}")
    print(f"{'='*60}\n")

    print(json.dumps(report, indent=2))
