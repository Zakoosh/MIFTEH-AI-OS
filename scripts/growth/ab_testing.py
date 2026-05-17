"""
AI A/B Testing Engine
Manages variant definitions, statistical significance, winner selection,
and applies winning variants. No external dependencies.
"""
import hashlib
import json
import math
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any

from scripts.intelligence.registry import get_project
from scripts.intelligence.report_store import save, load_latest, REPORTS_ROOT

REPORT_TYPE = "ab_tests"
TESTS_FILE = REPORTS_ROOT / "ab_tests" / "active_tests.json"
MIN_SAMPLE_SIZE = 100
CONFIDENCE_LEVEL = 0.95


# ──────────────────────────────────────────────────────────────────────────────
# Statistical helpers
# ──────────────────────────────────────────────────────────────────────────────

def _z_score_for_confidence(confidence: float) -> float:
    """Approximate z-score for given confidence level."""
    z_map = {0.90: 1.645, 0.95: 1.960, 0.99: 2.576}
    return z_map.get(confidence, 1.960)


def compute_significance(
    control_n: int, control_conversions: int,
    variant_n: int, variant_conversions: int,
    confidence: float = CONFIDENCE_LEVEL,
) -> dict:
    """
    Two-proportion z-test for A/B significance.
    Returns: significant, p_value_approx, uplift_pct, winner.
    """
    if control_n < MIN_SAMPLE_SIZE or variant_n < MIN_SAMPLE_SIZE:
        return {
            "significant": False,
            "reason": f"Insufficient sample (need {MIN_SAMPLE_SIZE} per variant)",
            "control_n": control_n,
            "variant_n": variant_n,
        }

    p_c = control_conversions / control_n if control_n else 0
    p_v = variant_conversions / variant_n if variant_n else 0

    p_pool = (control_conversions + variant_conversions) / (control_n + variant_n)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / control_n + 1 / variant_n))

    if se == 0:
        return {"significant": False, "reason": "Zero standard error — check data"}

    z = abs(p_v - p_c) / se
    z_crit = _z_score_for_confidence(confidence)
    significant = z >= z_crit

    # Approximate p-value via normal CDF approximation
    p_approx = 2 * (1 - _norm_cdf(z))

    uplift = (p_v - p_c) / p_c * 100 if p_c else 0

    return {
        "significant": significant,
        "z_score": round(z, 3),
        "z_critical": z_crit,
        "p_value_approx": round(p_approx, 4),
        "confidence": confidence,
        "control_rate": round(p_c * 100, 2),
        "variant_rate": round(p_v * 100, 2),
        "uplift_pct": round(uplift, 2),
        "winner": "variant" if significant and uplift > 0 else "control" if significant else "inconclusive",
        "control_n": control_n,
        "variant_n": variant_n,
    }


def _norm_cdf(z: float) -> float:
    """Approximate normal CDF using Horner's method."""
    t = 1 / (1 + 0.2316419 * abs(z))
    d = 0.3989422819 * math.exp(-0.5 * z * z)
    p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.7814779 + t * (-1.8212560 + t * 1.3302744))))
    return 1 - p if z > 0 else p


def required_sample_size(baseline_rate: float, min_detectable_effect: float, confidence: float = CONFIDENCE_LEVEL) -> int:
    """Calculate required sample size per variant."""
    z = _z_score_for_confidence(confidence)
    p1 = baseline_rate
    p2 = baseline_rate * (1 + min_detectable_effect)
    p_bar = (p1 + p2) / 2
    n = (z ** 2 * 2 * p_bar * (1 - p_bar)) / ((p2 - p1) ** 2)
    return math.ceil(n)


# ──────────────────────────────────────────────────────────────────────────────
# Test definitions
# ──────────────────────────────────────────────────────────────────────────────

PREDEFINED_TESTS = {
    "hero_layout": {
        "name": "Homepage Hero Layout",
        "description": "Test different hero section layouts",
        "metric": "click_through_rate",
        "baseline_rate": 0.03,
        "min_effect": 0.20,
        "variants": {
            "control": {
                "name": "Current hero with stats row",
                "description": "Existing layout",
                "changes": [],
            },
            "variant_a": {
                "name": "Hero with video background",
                "description": "Add looping game preview video",
                "changes": ["hero_background: video", "cta_position: center"],
            },
            "variant_b": {
                "name": "Minimal hero with featured game",
                "description": "Large featured game card in hero",
                "changes": ["hero_style: minimal", "featured_game: visible"],
            },
        },
    },
    "cta_button": {
        "name": "CTA Button Color & Text",
        "description": "Test CTA button variants for game click-through",
        "metric": "game_start_rate",
        "baseline_rate": 0.08,
        "min_effect": 0.15,
        "variants": {
            "control": {
                "name": "Current purple button",
                "description": "العب الآن — violet/purple",
                "changes": [],
            },
            "variant_a": {
                "name": "Green button with arrow",
                "description": "ابدأ اللعب ← — green with arrow icon",
                "changes": ["cta_color: green", "cta_text: ابدأ اللعب ←"],
            },
            "variant_b": {
                "name": "Gradient pulsing button",
                "description": "Animated gradient button",
                "changes": ["cta_style: gradient-pulse", "cta_animation: pulse"],
            },
        },
    },
    "game_card": {
        "name": "Game Card Design",
        "description": "Test game card layout for click-through",
        "metric": "game_card_ctr",
        "baseline_rate": 0.12,
        "min_effect": 0.15,
        "variants": {
            "control": {
                "name": "Current card with thumbnail",
                "description": "Existing game card",
                "changes": [],
            },
            "variant_a": {
                "name": "Card with hover preview",
                "description": "Show animated preview on hover",
                "changes": ["card_hover: preview", "thumbnail_animation: on"],
            },
            "variant_b": {
                "name": "Larger card with description",
                "description": "Bigger card showing game description",
                "changes": ["card_size: large", "description: visible"],
            },
        },
    },
    "ad_placement": {
        "name": "Ad Placement Position",
        "description": "Test ad placement for highest revenue without UX impact",
        "metric": "ad_rpm",
        "baseline_rate": 0.015,
        "min_effect": 0.20,
        "variants": {
            "control": {
                "name": "Bottom banner only",
                "description": "Single bottom ad unit",
                "changes": [],
            },
            "variant_a": {
                "name": "Top + bottom banners",
                "description": "Ads above and below game list",
                "changes": ["ad_top: enabled", "ad_bottom: enabled"],
            },
            "variant_b": {
                "name": "In-feed between game rows",
                "description": "Native in-feed ad every 3 game rows",
                "changes": ["ad_style: in-feed", "ad_interval: 3_rows"],
            },
        },
    },
    "homepage_structure": {
        "name": "Homepage Content Structure",
        "description": "Test homepage content ordering for engagement",
        "metric": "session_duration",
        "baseline_rate": 0.45,
        "min_effect": 0.10,
        "variants": {
            "control": {
                "name": "Hero → Featured → Categories",
                "description": "Existing structure",
                "changes": [],
            },
            "variant_a": {
                "name": "Hero → Trending → Featured → Categories",
                "description": "Add trending section before featured",
                "changes": ["section_order: hero,trending,featured,categories"],
            },
            "variant_b": {
                "name": "Search → Hero → Games Grid",
                "description": "Prominent search bar first",
                "changes": ["section_order: search,hero,grid", "search_prominent: true"],
            },
        },
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# Test state management
# ──────────────────────────────────────────────────────────────────────────────

def _load_tests() -> dict:
    TESTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if TESTS_FILE.exists():
        try:
            return json.loads(TESTS_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_tests(tests: dict) -> None:
    TESTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TESTS_FILE.write_text(json.dumps(tests, indent=2))


# ──────────────────────────────────────────────────────────────────────────────
# Test operations
# ──────────────────────────────────────────────────────────────────────────────

def create_test(test_id: str, project_id: str, custom_config: Optional[dict] = None) -> dict:
    """Create and activate an A/B test."""
    config = custom_config or PREDEFINED_TESTS.get(test_id, {})
    if not config:
        raise ValueError(f"Unknown test_id: {test_id}. Available: {list(PREDEFINED_TESTS)}")

    tests = _load_tests()
    if test_id in tests and tests[test_id].get("status") == "running":
        return {"ok": False, "reason": f"Test '{test_id}' is already running"}

    n_required = required_sample_size(
        config.get("baseline_rate", 0.05),
        config.get("min_effect", 0.15),
    )

    test = {
        "test_id": test_id,
        "project_id": project_id,
        "name": config.get("name", test_id),
        "description": config.get("description", ""),
        "metric": config.get("metric", "click_through_rate"),
        "status": "running",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "required_sample_size": n_required,
        "variants": config.get("variants", {}),
        "results": {
            v: {"impressions": 0, "conversions": 0}
            for v in config.get("variants", {})
        },
        "winner": None,
        "significance": None,
    }
    tests[test_id] = test
    _save_tests(tests)
    return {"ok": True, "test": test, "required_sample_size": n_required}


def record_impression(test_id: str, variant: str) -> None:
    """Record an impression for a variant."""
    tests = _load_tests()
    if test_id not in tests:
        return
    tests[test_id]["results"].setdefault(variant, {"impressions": 0, "conversions": 0})
    tests[test_id]["results"][variant]["impressions"] += 1
    _save_tests(tests)


def record_conversion(test_id: str, variant: str) -> None:
    """Record a conversion for a variant."""
    tests = _load_tests()
    if test_id not in tests:
        return
    tests[test_id]["results"].setdefault(variant, {"impressions": 0, "conversions": 0})
    tests[test_id]["results"][variant]["conversions"] += 1
    _save_tests(tests)


def simulate_test_data(test_id: str, days: int = 14, base_traffic: int = 500) -> dict:
    """
    Simulate realistic test traffic data for a given number of days.
    Used for demonstration and testing the engine.
    """
    tests = _load_tests()
    if test_id not in tests:
        return {"error": f"Test {test_id} not found — create it first"}

    test = tests[test_id]
    config = PREDEFINED_TESTS.get(test_id, {})
    baseline = config.get("baseline_rate", 0.05)
    variants = list(test["results"].keys())

    for day in range(days):
        daily_traffic = base_traffic + random.randint(-100, 100)
        per_variant = daily_traffic // len(variants)
        for i, v in enumerate(variants):
            # Simulate variant uplift: variant_a gets +15%, variant_b gets +8%
            uplift = 1.0 if v == "control" else (1.15 if v == "variant_a" else 1.08)
            impressions = per_variant + random.randint(-20, 20)
            conversions = int(impressions * baseline * uplift * random.uniform(0.9, 1.1))
            tests[test_id]["results"][v]["impressions"] += impressions
            tests[test_id]["results"][v]["conversions"] += conversions

    _save_tests(tests)
    return analyze_test(test_id)


def analyze_test(test_id: str) -> dict:
    """Compute current statistical results for a test."""
    tests = _load_tests()
    if test_id not in tests:
        return {"error": f"Test not found: {test_id}"}

    test = tests[test_id]
    results = test.get("results", {})
    control_data = results.get("control", {"impressions": 0, "conversions": 0})

    variant_analyses = {}
    for v, data in results.items():
        if v == "control":
            rate = data["conversions"] / data["impressions"] * 100 if data["impressions"] else 0
            variant_analyses[v] = {
                "impressions": data["impressions"],
                "conversions": data["conversions"],
                "rate": round(rate, 2),
                "is_control": True,
            }
            continue

        sig = compute_significance(
            control_data["impressions"], control_data["conversions"],
            data["impressions"], data["conversions"],
        )
        rate = data["conversions"] / data["impressions"] * 100 if data["impressions"] else 0
        variant_analyses[v] = {
            "impressions": data["impressions"],
            "conversions": data["conversions"],
            "rate": round(rate, 2),
            "is_control": False,
            "vs_control": sig,
        }

    # Determine winner
    best_variant = None
    best_uplift = 0
    for v, va in variant_analyses.items():
        if v == "control":
            continue
        uplift = va.get("vs_control", {}).get("uplift_pct", 0)
        significant = va.get("vs_control", {}).get("significant", False)
        if significant and uplift > best_uplift:
            best_uplift = uplift
            best_variant = v

    winner = best_variant or (
        "control" if any(va.get("vs_control", {}).get("significant") for va in variant_analyses.values() if not va.get("is_control")) else "inconclusive"
    )

    analysis = {
        "test_id": test_id,
        "name": test.get("name", ""),
        "status": test.get("status", "running"),
        "metric": test.get("metric", ""),
        "required_sample_size": test.get("required_sample_size", MIN_SAMPLE_SIZE),
        "current_winner": winner,
        "best_uplift_pct": round(best_uplift, 2),
        "variants": variant_analyses,
        "recommendation": (
            f"Deploy variant '{best_variant}' — +{best_uplift:.1f}% {test.get('metric','')}" if best_variant else
            "Continue running test — not yet statistically significant"
        ),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }

    # Update stored test
    tests[test_id]["significance"] = analysis
    tests[test_id]["winner"] = winner
    _save_tests(tests)

    return analysis


def conclude_test(test_id: str) -> dict:
    """Conclude a test and mark the winner."""
    analysis = analyze_test(test_id)
    tests = _load_tests()
    if test_id in tests:
        tests[test_id]["status"] = "concluded"
        tests[test_id]["concluded_at"] = datetime.now(timezone.utc).isoformat()
        _save_tests(tests)
    return {**analysis, "status": "concluded"}


def get_all_tests(project_id: Optional[str] = None) -> dict:
    """List all tests, optionally filtered by project."""
    tests = _load_tests()
    if project_id:
        tests = {k: v for k, v in tests.items() if v.get("project_id") == project_id}
    return tests


def run_full_suite(project_id: str) -> dict:
    """Create all predefined tests, simulate data, and analyze results."""
    results = {}
    for test_id in PREDEFINED_TESTS:
        try:
            create_test(test_id, project_id)
            simulate_test_data(test_id, days=14)
            analysis = analyze_test(test_id)
            results[test_id] = analysis
        except Exception as e:
            results[test_id] = {"error": str(e)}

    report = {
        "project_id": project_id,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "tests_run": len(results),
        "winners": {
            tid: r.get("current_winner") for tid, r in results.items() if not r.get("error")
        },
        "top_opportunity": max(
            [(tid, r.get("best_uplift_pct", 0)) for tid, r in results.items() if not r.get("error")],
            key=lambda x: x[1],
            default=("none", 0),
        ),
        "results": results,
    }
    save(REPORT_TYPE, project_id, report)
    return report


if __name__ == "__main__":
    import sys
    pid = sys.argv[1] if len(sys.argv) > 1 else "yallaplays"
    r = run_full_suite(pid)
    print(f"Tests run: {r['tests_run']}")
    print(f"Top opportunity: {r['top_opportunity']}")
    for tid, winner in r.get("winners", {}).items():
        uplift = r["results"][tid].get("best_uplift_pct", 0)
        print(f"  {tid}: winner={winner} uplift={uplift:.1f}%")
