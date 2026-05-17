"""
Revenue Intelligence Engine
Monitors AdSense presence, estimates RPM/CTR/revenue, scores monetization health,
generates optimization suggestions. All stdlib — no Google API required.
"""
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scripts.intelligence.registry import get_project, get_all_active_projects, get_adsense_publisher
from scripts.intelligence.report_store import save, load_latest, REPORTS_ROOT

REPORT_TYPE = "revenue"
USER_AGENT = "MIFTEH-AI-OS/1.0 RevenueIntelligence"

# Gaming niche RPM benchmarks (USD) by region/device
RPM_BENCHMARKS = {
    "gaming_global":   {"min": 0.40, "mid": 1.20, "max": 3.50},
    "gaming_mena":     {"min": 0.20, "mid": 0.65, "max": 1.80},
    "gaming_us":       {"min": 1.50, "mid": 3.20, "max": 8.00},
    "gaming_mobile":   {"min": 0.25, "mid": 0.80, "max": 2.20},
}

# Ad slot signals and their quality weights
AD_QUALITY_SIGNALS = {
    "above_fold":       3.0,
    "in_content":       2.5,
    "sticky":           2.0,
    "below_fold":       1.0,
    "auto_ads":         1.5,
    "responsive":       1.2,
    "fixed_size":       0.8,
}


def _fetch(url: str, timeout: int = 15) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, ""


# ──────────────────────────────────────────────────────────────────────────────
# AdSense presence analysis
# ──────────────────────────────────────────────────────────────────────────────

def analyze_adsense_presence(domain: str, publisher_id: str, sample_paths: Optional[list] = None) -> dict:
    """Check AdSense integration across multiple pages."""
    paths = sample_paths or ["/", "/games", "/about"]
    results = {}

    for path in paths:
        url = f"https://{domain}{path}"
        code, body = _fetch(url)
        if not body:
            results[path] = {"ok": False, "status": code}
            continue

        has_script = "pagead2.googlesyndication.com" in body
        has_pub = publisher_id in body if publisher_id else False
        has_auto = "enable_page_level_ads" in body or '"adsbygoogle"' in body
        slot_matches = re.findall(r'data-ad-slot=["\'](\d+)["\']', body)
        format_matches = re.findall(r'data-ad-format=["\']([^"\']+)["\']', body)
        unit_count = len(slot_matches)

        # Estimate ad quality score for this page
        quality = 0.0
        if has_auto:
            quality += AD_QUALITY_SIGNALS["auto_ads"]
        if unit_count > 0:
            quality += min(unit_count, 3) * AD_QUALITY_SIGNALS["in_content"]
        if "responsive" in " ".join(format_matches) or "auto" in " ".join(format_matches):
            quality += AD_QUALITY_SIGNALS["responsive"]

        results[path] = {
            "ok": has_script and has_pub,
            "status": code,
            "has_adsense_script": has_script,
            "has_publisher_id": has_pub,
            "has_auto_ads": has_auto,
            "ad_units": unit_count,
            "ad_slots": slot_matches,
            "ad_formats": format_matches,
            "quality_score": round(quality, 2),
        }

    pages_with_ads = sum(1 for r in results.values() if r.get("has_adsense_script"))
    total_pages = len(results)
    coverage = round(pages_with_ads / total_pages * 100) if total_pages else 0
    avg_quality = (
        sum(r.get("quality_score", 0) for r in results.values()) / total_pages
        if total_pages else 0
    )

    return {
        "publisher_id": publisher_id,
        "pages_checked": total_pages,
        "pages_with_ads": pages_with_ads,
        "coverage_pct": coverage,
        "avg_quality_score": round(avg_quality, 2),
        "pages": results,
    }


# ──────────────────────────────────────────────────────────────────────────────
# RPM / Revenue estimation
# ──────────────────────────────────────────────────────────────────────────────

def estimate_revenue(
    monthly_pageviews: int,
    ad_coverage_pct: float,
    avg_quality_score: float,
    benchmark: str = "gaming_global",
) -> dict:
    """
    Estimate monthly revenue range based on pageviews and ad metrics.
    Returns low/mid/high estimates in USD.
    """
    bench = RPM_BENCHMARKS.get(benchmark, RPM_BENCHMARKS["gaming_global"])

    # Quality multiplier: normalize quality score to 0.5-1.5 range
    quality_mult = max(0.5, min(1.5, avg_quality_score / 5.0 + 0.5))

    # Coverage factor
    coverage_factor = ad_coverage_pct / 100.0

    effective_views = monthly_pageviews * coverage_factor
    thousands = effective_views / 1000

    low  = round(thousands * bench["min"] * quality_mult, 2)
    mid  = round(thousands * bench["mid"] * quality_mult, 2)
    high = round(thousands * bench["max"] * quality_mult, 2)

    return {
        "monthly_pageviews": monthly_pageviews,
        "effective_monetized_views": int(effective_views),
        "coverage_pct": ad_coverage_pct,
        "quality_multiplier": round(quality_mult, 2),
        "benchmark": benchmark,
        "rpm_range": bench,
        "revenue_usd": {"low": low, "mid": mid, "high": high},
        "annual_usd": {
            "low": round(low * 12, 2),
            "mid": round(mid * 12, 2),
            "high": round(high * 12, 2),
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# CTR analysis (proxy via ad unit count and placement)
# ──────────────────────────────────────────────────────────────────────────────

def estimate_ctr(ad_units_per_page: float, has_auto_ads: bool, niche: str = "gaming") -> dict:
    """
    Estimate CTR range based on ad unit density and auto-ads status.
    Gaming niche CTR benchmarks: 0.5-2.5%
    """
    base_ctr_ranges = {
        "gaming": (0.005, 0.015, 0.025),
        "general": (0.008, 0.020, 0.040),
        "tech": (0.003, 0.010, 0.020),
    }
    low_ctr, mid_ctr, high_ctr = base_ctr_ranges.get(niche, base_ctr_ranges["gaming"])

    # Auto ads typically boost CTR 20-40%
    auto_boost = 1.30 if has_auto_ads else 1.0

    # More units = slightly lower individual CTR but higher total
    density_factor = max(0.7, 1.0 - (ad_units_per_page - 1) * 0.05)

    return {
        "niche": niche,
        "ad_units_per_page": ad_units_per_page,
        "has_auto_ads": has_auto_ads,
        "ctr_estimate": {
            "low":  round(low_ctr  * auto_boost * density_factor * 100, 2),
            "mid":  round(mid_ctr  * auto_boost * density_factor * 100, 2),
            "high": round(high_ctr * auto_boost * density_factor * 100, 2),
        },
        "ctr_notes": "CTR in percent. Actual CTR visible in AdSense dashboard.",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Monetization scoring
# ──────────────────────────────────────────────────────────────────────────────

def score_monetization(adsense: dict, seo_score: int, page_count: int) -> dict:
    """Composite monetization health score 0-100."""
    score = 0
    factors = []

    # AdSense presence (40 pts max)
    if adsense.get("coverage_pct", 0) >= 80:
        score += 40
        factors.append(("AdSense coverage ≥80%", +40))
    elif adsense.get("coverage_pct", 0) >= 50:
        score += 25
        factors.append(("AdSense coverage 50-80%", +25))
    elif adsense.get("coverage_pct", 0) > 0:
        score += 10
        factors.append(("AdSense coverage <50%", +10))
    else:
        factors.append(("No AdSense detected", 0))

    # Quality score (20 pts max)
    aq = adsense.get("avg_quality_score", 0)
    quality_pts = min(20, int(aq / 10.0 * 20))
    score += quality_pts
    factors.append((f"Ad quality score {aq:.1f}", quality_pts))

    # SEO drives traffic (25 pts max)
    seo_pts = min(25, int(seo_score / 100 * 25))
    score += seo_pts
    factors.append((f"SEO score {seo_score}/100", seo_pts))

    # Content volume (15 pts max)
    content_pts = min(15, int(page_count / 100 * 15))
    score += content_pts
    factors.append((f"Page count {page_count}", content_pts))

    status = (
        "excellent" if score >= 80 else
        "good" if score >= 65 else
        "fair" if score >= 45 else
        "poor"
    )

    return {
        "monetization_score": score,
        "status": status,
        "factors": [{"factor": f, "points": p} for f, p in factors],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Optimization suggestions
# ──────────────────────────────────────────────────────────────────────────────

def generate_suggestions(adsense: dict, ctr: dict, revenue: dict, seo_score: int) -> list[dict]:
    """Generate prioritized revenue optimization suggestions."""
    suggestions = []

    coverage = adsense.get("coverage_pct", 0)
    quality = adsense.get("avg_quality_score", 0)
    mid_rev = revenue.get("revenue_usd", {}).get("mid", 0)
    mid_ctr = ctr.get("ctr_estimate", {}).get("mid", 0)

    if coverage < 80:
        uplift = round((80 - coverage) / 100 * mid_rev * 0.5, 2)
        suggestions.append({
            "priority": "high",
            "category": "coverage",
            "action": "Add AdSense to all game pages and category pages",
            "estimated_uplift_usd": uplift,
            "effort": "low",
            "detail": f"Currently {coverage}% coverage. Each 10pp increase ≈ +${round(mid_rev*0.05, 2)}/mo",
        })

    if not adsense.get("pages", {}).get("/", {}).get("has_auto_ads"):
        suggestions.append({
            "priority": "high",
            "category": "auto_ads",
            "action": "Enable Google Auto Ads (Page-level ads) for automatic placement",
            "estimated_uplift_usd": round(mid_rev * 0.15, 2),
            "effort": "low",
            "detail": "Auto Ads use ML to find optimal placements. Typical uplift: +10-25%",
        })

    if quality < 5.0:
        suggestions.append({
            "priority": "medium",
            "category": "placement",
            "action": "Add above-fold ad unit to homepage and game pages",
            "estimated_uplift_usd": round(mid_rev * 0.20, 2),
            "effort": "medium",
            "detail": "Above-fold ads have 2-3x higher viewability and CPM vs below-fold",
        })

    if seo_score < 70:
        suggestions.append({
            "priority": "high",
            "category": "seo_traffic",
            "action": f"Improve SEO score from {seo_score} to 80+ to grow organic traffic",
            "estimated_uplift_usd": round(mid_rev * 0.30, 2),
            "effort": "high",
            "detail": "Every 10% traffic increase = ~10% revenue increase with same ad setup",
        })

    if mid_ctr < 1.0:
        suggestions.append({
            "priority": "medium",
            "category": "ctr",
            "action": "A/B test ad formats: try native/in-feed ads instead of display",
            "estimated_uplift_usd": round(mid_rev * 0.12, 2),
            "effort": "medium",
            "detail": f"Current estimated CTR: {mid_ctr}%. Native ads typically 2-4x CTR",
        })

    suggestions.append({
        "priority": "low",
        "category": "anchor_ads",
        "action": "Enable anchor ads (sticky bottom bar) for mobile traffic",
        "estimated_uplift_usd": round(mid_rev * 0.08, 2),
        "effort": "low",
        "detail": "Mobile anchor ads: high viewability, non-intrusive, typically +8-15% mobile RPM",
    })

    suggestions.append({
        "priority": "medium",
        "category": "content_expansion",
        "action": "Add 20+ SEO game landing pages to capture long-tail search traffic",
        "estimated_uplift_usd": round(mid_rev * 0.25, 2),
        "effort": "medium",
        "detail": "Long-tail game pages convert 3x better for ad revenue than homepage traffic",
    })

    return sorted(suggestions, key=lambda s: {"high": 0, "medium": 1, "low": 2}[s["priority"]])


# ──────────────────────────────────────────────────────────────────────────────
# Full project revenue analysis
# ──────────────────────────────────────────────────────────────────────────────

def analyze_project(
    project_id: str,
    monthly_pageviews: int = 10000,
    benchmark: str = "gaming_mena",
) -> dict:
    """Full revenue intelligence analysis for a project."""
    p = get_project(project_id)
    domain = p["domain"]
    publisher_id = get_adsense_publisher(project_id) or ""

    # Pull latest SEO score if available
    seo_report = load_latest("seo", project_id) or {}
    seo_score = seo_report.get("overall_seo_score", 50)

    # Pull page count from sitemap if available
    live_report = load_latest("live", project_id) or {}
    page_count = live_report.get("sitemap", {}).get("url_count", 20)

    # AdSense analysis
    adsense = analyze_adsense_presence(domain, publisher_id)

    # CTR estimate
    avg_units = (
        sum(p.get("ad_units", 0) for p in adsense["pages"].values()) / max(len(adsense["pages"]), 1)
    )
    has_auto = any(p.get("has_auto_ads") for p in adsense["pages"].values())
    ctr = estimate_ctr(avg_units, has_auto)

    # Revenue estimate
    revenue = estimate_revenue(monthly_pageviews, adsense["coverage_pct"], adsense["avg_quality_score"], benchmark)

    # Monetization score
    scoring = score_monetization(adsense, seo_score, page_count)

    # Suggestions
    suggestions = generate_suggestions(adsense, ctr, revenue, seo_score)

    report = {
        "project_id": project_id,
        "domain": domain,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "monthly_pageviews_assumption": monthly_pageviews,
        "benchmark": benchmark,
        "adsense": adsense,
        "ctr": ctr,
        "revenue": revenue,
        "scoring": scoring,
        "suggestions": suggestions,
        "suggestion_count": len(suggestions),
        "total_estimated_uplift_usd": round(
            sum(s.get("estimated_uplift_usd", 0) for s in suggestions if s["priority"] in ("high", "medium")), 2
        ),
    }

    save(REPORT_TYPE, project_id, report)
    return report


def analyze_all(monthly_pageviews: int = 10000) -> dict:
    results = {}
    for p in get_all_active_projects():
        try:
            results[p["id"]] = analyze_project(p["id"], monthly_pageviews)
        except Exception as e:
            results[p["id"]] = {"error": str(e), "project_id": p["id"]}
    return results


if __name__ == "__main__":
    import sys
    pid = sys.argv[1] if len(sys.argv) > 1 else "yallaplays"
    pv = int(sys.argv[2]) if len(sys.argv) > 2 else 10000
    r = analyze_project(pid, pv)
    print(json.dumps({k: v for k, v in r.items() if k != "adsense"}, indent=2))
