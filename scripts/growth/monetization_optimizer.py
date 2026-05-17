"""
Monetization Optimizer
Analyzes CLS, mobile ad density, placement quality, policy risks,
lazy loading, viewport timing, and generates concrete fixes.
"""
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from typing import Optional

from scripts.intelligence.registry import get_project, get_adsense_publisher
from scripts.intelligence.report_store import save, REPORTS_ROOT

REPORT_TYPE = "monetization"
USER_AGENT = "MIFTEH-AI-OS/1.0 MonetizationOptimizer"
TIMEOUT = 15

# AdSense policy thresholds
POLICY = {
    "max_ads_per_screen_mobile": 3,
    "min_content_to_ad_ratio": 0.4,
    "min_ad_distance_px": 150,
    "max_cls_score": 0.25,
}

AD_FORMAT_RPM = {
    "auto":       {"base": 1.0, "note": "Auto-sized — best for responsive"},
    "rectangle":  {"base": 0.9, "note": "Medium rectangle (300×250) — high fill rate"},
    "leaderboard":{"base": 0.85,"note": "728×90 — good for desktop headers"},
    "skyscraper": {"base": 0.7, "note": "160×600 — desktop sidebars"},
    "in-article": {"base": 1.2, "note": "Native — highest CTR, best for content sites"},
    "in-feed":    {"base": 1.1, "note": "Blends with content — 2nd highest CTR"},
    "anchor":     {"base": 0.8, "note": "Sticky — good mobile supplement"},
}


def _fetch(url: str) -> tuple[int, str, float]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read().decode("utf-8", errors="replace")
            return r.status, body, time.time() - start
    except Exception:
        return 0, "", time.time() - start


# ──────────────────────────────────────────────────────────────────────────────
# CLS estimation (proxy — no real browser)
# ──────────────────────────────────────────────────────────────────────────────

def estimate_cls_risk(body: str) -> dict:
    """
    Estimate CLS risk from HTML patterns.
    CLS is caused by: unsized images, dynamic content insertion, ads without reserved space.
    """
    risks = []
    score = 0.0

    # Images without explicit dimensions
    imgs = re.findall(r"<img[^>]+>", body, re.IGNORECASE)
    unsized = [i for i in imgs if not (re.search(r'width=', i) and re.search(r'height=', i))]
    if unsized:
        risk_score = min(0.10, len(unsized) * 0.01)
        score += risk_score
        risks.append({
            "type": "unsized_images",
            "count": len(unsized),
            "cls_contribution": round(risk_score, 3),
            "fix": "Add explicit width/height to all <img> tags or use CSS aspect-ratio",
        })

    # Ad containers without min-height (CLS from ad loading)
    ad_divs = re.findall(r'<ins[^>]+class=["\'][^"\']*adsbygoogle[^"\']*["\'][^>]*>', body, re.IGNORECASE)
    ad_without_size = [a for a in ad_divs if not re.search(r'(min-height|height):\s*\d+', a)]
    if ad_without_size:
        risk_score = min(0.15, len(ad_without_size) * 0.04)
        score += risk_score
        risks.append({
            "type": "ads_without_reserved_space",
            "count": len(ad_without_size),
            "cls_contribution": round(risk_score, 3),
            "fix": "Add min-height to all ad containers before ad loads (e.g., min-height:90px)",
        })

    # Fonts loaded without font-display
    if re.search(r"@font-face", body) and not re.search(r"font-display\s*:", body):
        score += 0.05
        risks.append({
            "type": "font_no_display",
            "cls_contribution": 0.05,
            "fix": "Add font-display: swap or optional to @font-face declarations",
        })

    # Dynamic injection signals (document.write, innerHTML for ads)
    if re.search(r"document\.write\s*\(", body):
        score += 0.08
        risks.append({
            "type": "document_write",
            "cls_contribution": 0.08,
            "fix": "Remove document.write() — causes layout shift and is blocked by async loading",
        })

    cls_level = "good" if score < 0.1 else "needs_improvement" if score < 0.25 else "poor"

    return {
        "estimated_cls": round(score, 3),
        "cls_level": cls_level,
        "passes_core_web_vitals": score < POLICY["max_cls_score"],
        "risk_factors": risks,
        "recommendation": (
            "CLS is acceptable" if cls_level == "good" else
            "Fix unsized images and reserve ad space to improve CLS" if cls_level == "needs_improvement" else
            "Critical CLS issues — page may fail Core Web Vitals"
        ),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Mobile ad density analysis
# ──────────────────────────────────────────────────────────────────────────────

def analyze_ad_density(body: str, url: str) -> dict:
    """Check if ad density complies with AdSense policies on mobile."""
    ad_units = re.findall(r'<ins[^>]+adsbygoogle[^>]*>', body, re.IGNORECASE)
    content_words = len(re.findall(r'\b\w{3,}\b', re.sub(r'<[^>]+>', ' ', body)))
    ad_count = len(ad_units)

    # Estimate viewable ad count (assume 2 ads per screen on mobile)
    screens_of_content = max(1, content_words // 150)
    ads_per_screen = ad_count / max(screens_of_content, 1)

    policy_violation = ads_per_screen > POLICY["max_ads_per_screen_mobile"]
    content_ratio = max(0, 1 - (ad_count * 0.1))

    issues = []
    if policy_violation:
        issues.append(
            f"High ad density: {ads_per_screen:.1f} ads/screen (policy: ≤{POLICY['max_ads_per_screen_mobile']})"
        )
    if ad_count == 0:
        issues.append("No ads detected — monetization opportunity missed")
    if content_ratio < POLICY["min_content_to_ad_ratio"]:
        issues.append("Low content-to-ad ratio — may trigger policy review")

    return {
        "url": url,
        "ad_unit_count": ad_count,
        "content_words": content_words,
        "ads_per_screen_estimate": round(ads_per_screen, 2),
        "screens_of_content": screens_of_content,
        "content_ad_ratio": round(content_ratio, 2),
        "policy_compliant": not policy_violation,
        "issues": issues,
        "recommendation": (
            "Reduce ad count — too many ads per screen" if policy_violation else
            "Add more ad units to increase coverage" if ad_count == 0 else
            "Ad density is within policy limits"
        ),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Ad placement quality analysis
# ──────────────────────────────────────────────────────────────────────────────

def analyze_placements(body: str) -> dict:
    """Evaluate ad placement quality and format optimization."""
    slots = re.findall(r'data-ad-slot=["\']([^"\']+)["\']', body)
    formats = re.findall(r'data-ad-format=["\']([^"\']+)["\']', body)
    has_auto_ads = "adsbygoogle.js" in body or "enable_page_level_ads" in body

    used_formats = set(formats)
    missing_high_value = []
    if "in-article" not in used_formats and "in_article" not in used_formats:
        missing_high_value.append("in-article")
    if "in-feed" not in used_formats and "in_feed" not in used_formats:
        missing_high_value.append("in-feed")

    format_analysis = []
    for fmt in used_formats:
        canonical = fmt.replace("_", "-").lower()
        info = AD_FORMAT_RPM.get(canonical, {"base": 0.8, "note": "Standard format"})
        format_analysis.append({
            "format": fmt,
            "relative_rpm": info["base"],
            "note": info["note"],
        })

    # Sort by RPM value
    format_analysis.sort(key=lambda x: x["relative_rpm"], reverse=True)

    lazy_loaded = bool(re.search(r'loading=["\']lazy["\']', body))

    return {
        "slot_count": len(slots),
        "unique_formats": list(used_formats),
        "has_auto_ads": has_auto_ads,
        "lazy_loaded": lazy_loaded,
        "missing_high_value_formats": missing_high_value,
        "format_analysis": format_analysis,
        "avg_relative_rpm": round(sum(f["relative_rpm"] for f in format_analysis) / max(len(format_analysis), 1), 2),
        "recommendations": [
            f"Add {fmt} format — higher RPM and CTR" for fmt in missing_high_value
        ] + (
            ["Enable lazy loading for below-fold ads to improve page speed"] if not lazy_loaded else []
        ) + (
            ["Enable Auto Ads for AI-optimized placement"] if not has_auto_ads else []
        ),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Policy risk scanner
# ──────────────────────────────────────────────────────────────────────────────

def scan_policy_risks(body: str, url: str) -> dict:
    """Detect content or implementation patterns that may violate AdSense policies."""
    risks = []

    # Misleading click traps (overlapping UI over ads)
    if re.search(r'position:\s*absolute.*?z-index:\s*[1-9]', body, re.DOTALL):
        risks.append({
            "severity": "medium",
            "type": "potential_click_trap",
            "description": "Absolute positioned elements with high z-index may overlap ads",
            "fix": "Ensure no UI elements are positioned over ad units",
        })

    # Auto-refresh (not allowed near ads)
    if re.search(r'(setInterval|setTimeout).*?(location\.reload|window\.location)', body):
        risks.append({
            "severity": "high",
            "type": "auto_refresh",
            "description": "Page may auto-refresh — not allowed with AdSense ads visible",
            "fix": "Remove auto-refresh near ad units or disable ads on refreshed views",
        })

    # Explicit/adult content signals
    adult_terms = re.findall(r'\b(porn|adult|xxx|sex|nude|naked)\b', body, re.IGNORECASE)
    if adult_terms:
        risks.append({
            "severity": "critical",
            "type": "prohibited_content",
            "description": f"Potential prohibited content keywords detected: {adult_terms[:3]}",
            "fix": "Remove adult content — AdSense does not allow explicit material",
        })

    # Deceptive navigation
    if re.search(r'onclick=["\'].*?(location|window\.open)', body) and re.search(r'<a[^>]*onclick', body, re.IGNORECASE):
        risks.append({
            "severity": "low",
            "type": "deceptive_navigation",
            "description": "JavaScript navigation via onclick on links — may confuse users",
            "fix": "Use real href links for navigation to avoid accidental ad clicks",
        })

    # Ad stacking (multiple ads in same container)
    containers = re.findall(r'<div[^>]*>(.*?)</div>', body, re.DOTALL)
    for c in containers:
        if c.count("adsbygoogle") > 1:
            risks.append({
                "severity": "high",
                "type": "ad_stacking",
                "description": "Multiple ad units inside single container — violates AdSense policy",
                "fix": "Place each ad unit in its own container with clear spacing",
            })
            break

    return {
        "url": url,
        "risk_count": len(risks),
        "critical_count": sum(1 for r in risks if r["severity"] == "critical"),
        "high_count": sum(1 for r in risks if r["severity"] == "high"),
        "policy_clear": len([r for r in risks if r["severity"] in ("critical", "high")]) == 0,
        "risks": risks,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Page speed / viewport timing
# ──────────────────────────────────────────────────────────────────────────────

def analyze_page_speed(domain: str, path: str = "/") -> dict:
    """Measure server response time and estimate LCP proxy."""
    url = f"https://{domain}{path}"
    code, body, elapsed = _fetch(url)
    ttfb_ms = round(elapsed * 1000)

    render_blocking = len(re.findall(r'<script(?![^>]*async|[^>]*defer)[^>]*src=', body, re.IGNORECASE))
    total_scripts = len(re.findall(r'<script', body, re.IGNORECASE))
    async_scripts = len(re.findall(r'<script[^>]*(async|defer)', body, re.IGNORECASE))
    inline_styles = len(re.findall(r'<style', body, re.IGNORECASE))
    external_css = len(re.findall(r'<link[^>]+rel=["\']stylesheet["\']', body, re.IGNORECASE))

    issues = []
    if ttfb_ms > 600:
        issues.append(f"Slow TTFB: {ttfb_ms}ms (target: <600ms)")
    if render_blocking > 0:
        issues.append(f"{render_blocking} render-blocking scripts (add async/defer)")
    if external_css > 3:
        issues.append(f"{external_css} external stylesheets (consolidate to reduce round trips)")

    return {
        "url": url,
        "status": code,
        "ttfb_ms": ttfb_ms,
        "speed_rating": "fast" if ttfb_ms < 200 else "moderate" if ttfb_ms < 600 else "slow",
        "render_blocking_scripts": render_blocking,
        "total_scripts": total_scripts,
        "async_scripts": async_scripts,
        "inline_styles": inline_styles,
        "external_stylesheets": external_css,
        "issues": issues,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Full optimization report
# ──────────────────────────────────────────────────────────────────────────────

def optimize_project(project_id: str) -> dict:
    p = get_project(project_id)
    domain = p["domain"]
    publisher_id = get_adsense_publisher(project_id) or ""

    pages_to_check = ["/", "/games"]
    page_reports = {}

    for path in pages_to_check:
        url = f"https://{domain}{path}"
        code, body, elapsed = _fetch(url)
        if not body:
            page_reports[path] = {"error": f"Could not fetch {url}"}
            continue

        page_reports[path] = {
            "cls": estimate_cls_risk(body),
            "density": analyze_ad_density(body, url),
            "placements": analyze_placements(body),
            "policy": scan_policy_risks(body, url),
            "speed": {
                "ttfb_ms": round(elapsed * 1000),
                "speed_rating": "fast" if elapsed < 0.2 else "moderate" if elapsed < 0.6 else "slow",
            },
        }

    # Aggregate optimization score
    all_issues = []
    all_recs = []
    for path, pr in page_reports.items():
        if "error" in pr:
            continue
        all_issues.extend(pr.get("density", {}).get("issues", []))
        all_issues.extend(pr.get("policy", {}).get("risks", []))
        all_issues.extend(pr.get("cls", {}).get("risk_factors", []))
        all_recs.extend(pr.get("placements", {}).get("recommendations", []))

    critical_policy = sum(1 for r in all_issues if isinstance(r, dict) and r.get("severity") == "critical")
    high_policy = sum(1 for r in all_issues if isinstance(r, dict) and r.get("severity") == "high")

    score = 100
    score -= critical_policy * 30
    score -= high_policy * 15
    score -= len([i for i in all_issues if isinstance(i, str)]) * 5
    score = max(0, min(100, score))

    report = {
        "project_id": project_id,
        "domain": domain,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "optimization_score": score,
        "status": "healthy" if score >= 80 else "needs_work" if score >= 50 else "critical",
        "pages_analyzed": len(page_reports),
        "critical_issues": critical_policy,
        "high_issues": high_policy,
        "page_reports": page_reports,
        "top_recommendations": list(dict.fromkeys(all_recs))[:8],
        "policy_format_reference": AD_FORMAT_RPM,
    }

    save(REPORT_TYPE, project_id, report)
    return report


if __name__ == "__main__":
    import sys
    pid = sys.argv[1] if len(sys.argv) > 1 else "yallaplays"
    r = optimize_project(pid)
    print(json.dumps({k: v for k, v in r.items() if k not in ("page_reports", "policy_format_reference")}, indent=2))
