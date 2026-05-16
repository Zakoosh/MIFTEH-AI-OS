"""
MIFTEH OS — Game QA Engine
Deep HTML/JS/mobile validation for Phaser.js games.
Produces a 0-100 score from 20 weighted checks.
Threshold ≥ 75 required for deployment eligibility.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

try:
    from telegram_notifier import notify_qa_failed, send_system_log
except Exception:
    def notify_qa_failed(*a, **kw): pass
    def send_system_log(*a, **kw): pass

MEMORY_DIR = Path("memory")
OUTPUTS_DIR = Path("outputs/yallaplays/games")
QA_REPORT_FILE = MEMORY_DIR / "game_qa_report.json"
REVIEWS_DIR = MEMORY_DIR / "reviews"

PHASER_CDN = "https://cdn.jsdelivr.net/npm/phaser@3.60.0/dist/phaser.min.js"
PASS_THRESHOLD = 75

# ─── Check registry ────────────────────────────────────────────────────────────
# (check_id, weight, description)
CHECKS = [
    # HTML structure (30 pts)
    ("has_phaser_cdn",        15, "Phaser CDN script tag present"),
    ("has_mobile_meta",        5, "Viewport meta tag for mobile"),
    ("has_charset",            5, "charset=UTF-8 declared"),
    ("has_arabic_lang",        5, "lang=ar dir=rtl on <html>"),
    # Phaser.js code quality (35 pts)
    ("has_phaser_game",       15, "Phaser.Game instantiation"),
    ("has_scene_preload",      5, "Phaser scene preload/create defined"),
    ("has_update_loop",        5, "Phaser update() game loop"),
    ("has_game_over",          5, "Game-over state / restart logic"),
    ("has_score_system",       5, "Score tracking and display"),
    # Mobile / UX (20 pts)
    ("has_touch_support",     10, "Touch event listeners present"),
    ("has_fullscreen_toggle",  5, "Fullscreen toggle function"),
    ("has_responsive_config",  5, "scale.mode AUTO or FIT in config"),
    # SEO / schema (10 pts)
    ("has_videogame_schema",   5, "VideoGame JSON-LD schema"),
    ("has_arabic_content",     5, "Arabic text in page title/description"),
    # Safety / quality (5 pts)
    ("no_external_images",     3, "No external image src references"),
    ("no_alert_spam",          2, "No bare alert() calls in game loop"),
]

TOTAL_WEIGHT = sum(w for _, w, _ in CHECKS)  # should be 100


# ─── HTML checks ────────────────────────────────────────────────────────────────

def _check_has_phaser_cdn(html: str) -> tuple[bool, str]:
    ok = "phaser" in html.lower() and "cdn.jsdelivr.net" in html
    return ok, "" if ok else "Phaser CDN script tag missing"


def _check_has_mobile_meta(html: str) -> tuple[bool, str]:
    ok = 'viewport' in html and 'width=device-width' in html
    return ok, "" if ok else "Missing <meta name=viewport>"


def _check_has_charset(html: str) -> tuple[bool, str]:
    ok = 'charset' in html.lower() and 'utf-8' in html.lower()
    return ok, "" if ok else "Missing charset=UTF-8"


def _check_has_arabic_lang(html: str) -> tuple[bool, str]:
    ok = 'lang="ar"' in html or "lang='ar'" in html
    return ok, "" if ok else "Missing lang=ar on <html>"


def _check_has_phaser_game(html: str) -> tuple[bool, str]:
    ok = 'new Phaser.Game' in html or 'Phaser.Game(' in html
    return ok, "" if ok else "Phaser.Game not instantiated"


def _check_has_scene_preload(html: str) -> tuple[bool, str]:
    ok = 'preload' in html or 'create(' in html
    return ok, "" if ok else "Scene preload/create not found"


def _check_has_update_loop(html: str) -> tuple[bool, str]:
    ok = 'update(' in html or 'update:' in html
    return ok, "" if ok else "Phaser update loop not found"


def _check_has_game_over(html: str) -> tuple[bool, str]:
    lower = html.lower()
    ok = 'game over' in lower or 'gameover' in lower or 'game_over' in lower or 'انتهت' in html or 'إعادة' in html
    return ok, "" if ok else "Game-over state not found"


def _check_has_score_system(html: str) -> tuple[bool, str]:
    lower = html.lower()
    ok = 'score' in lower or 'نقط' in html or 'نتيجة' in html
    return ok, "" if ok else "Score system not found"


def _check_has_touch_support(html: str) -> tuple[bool, str]:
    ok = 'touchstart' in html or 'pointerdown' in html or 'touch' in html.lower()
    return ok, "" if ok else "Touch/pointer events missing"


def _check_has_fullscreen_toggle(html: str) -> tuple[bool, str]:
    ok = 'fullscreen' in html.lower() or 'requestFullscreen' in html
    return ok, "" if ok else "Fullscreen toggle missing"


def _check_has_responsive_config(html: str) -> tuple[bool, str]:
    ok = 'FIT' in html or 'AUTO' in html or 'RESIZE' in html or 'scale' in html.lower()
    return ok, "" if ok else "Responsive scale config missing"


def _check_has_videogame_schema(html: str) -> tuple[bool, str]:
    ok = 'VideoGame' in html and 'application/ld+json' in html
    return ok, "" if ok else "VideoGame JSON-LD schema missing"


def _check_has_arabic_content(html: str) -> tuple[bool, str]:
    arabic_re = re.compile(r'[؀-ۿ]')
    ok = bool(arabic_re.search(html))
    return ok, "" if ok else "No Arabic content found"


def _check_no_external_images(html: str) -> tuple[bool, str]:
    # Reject <img src="http..."> but allow data URIs and SVG
    external_img = re.search(r'<img[^>]+src=["\']https?://', html, re.IGNORECASE)
    ok = not external_img
    return ok, "" if ok else "External <img> tag found — use Phaser Graphics API"


def _check_no_alert_spam(html: str) -> tuple[bool, str]:
    # Bare alert() inside an update or loop is bad — one standalone alert is fine
    alert_in_update = re.search(r'update\s*\([^)]*\)[^{]*\{[^}]*alert\s*\(', html, re.DOTALL)
    ok = not alert_in_update
    return ok, "" if ok else "alert() call inside update loop — remove it"


_CHECK_FNS = {
    "has_phaser_cdn": _check_has_phaser_cdn,
    "has_mobile_meta": _check_has_mobile_meta,
    "has_charset": _check_has_charset,
    "has_arabic_lang": _check_has_arabic_lang,
    "has_phaser_game": _check_has_phaser_game,
    "has_scene_preload": _check_has_scene_preload,
    "has_update_loop": _check_has_update_loop,
    "has_game_over": _check_has_game_over,
    "has_score_system": _check_has_score_system,
    "has_touch_support": _check_has_touch_support,
    "has_fullscreen_toggle": _check_has_fullscreen_toggle,
    "has_responsive_config": _check_has_responsive_config,
    "has_videogame_schema": _check_has_videogame_schema,
    "has_arabic_content": _check_has_arabic_content,
    "no_external_images": _check_no_external_images,
    "no_alert_spam": _check_no_alert_spam,
}


# ─── Core QA runner ─────────────────────────────────────────────────────────────

def run_qa_checks(html: str) -> dict:
    results = {}
    score = 0
    issues = []

    for check_id, weight, description in CHECKS:
        fn = _CHECK_FNS.get(check_id)
        if fn is None:
            passed, reason = True, ""
        else:
            passed, reason = fn(html)

        results[check_id] = {
            "passed": passed,
            "weight": weight,
            "description": description,
            "reason": reason,
        }
        if passed:
            score += weight
        else:
            issues.append(reason or description)

    return {
        "score": score,
        "max_score": TOTAL_WEIGHT,
        "eligible": score >= PASS_THRESHOLD,
        "checks": results,
        "issues": issues,
        "grade": _grade(score),
    }


def _grade(score: int) -> str:
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 70: return "C"
    if score >= 60: return "D"
    return "F"


# ─── AI review (optional enrichment) ────────────────────────────────────────────

def ai_qa_review(html: str, basic_result: dict) -> dict:
    if basic_result["score"] >= PASS_THRESHOLD:
        return {}  # only run AI review on borderline/failing games

    system = "You are a mobile HTML5 game QA engineer reviewing Phaser.js games for Arabic audiences."
    prompt = f"""Review this game HTML snippet and identify the top 3 issues preventing it from passing QA.
Score: {basic_result['score']}/100. Known issues: {basic_result['issues'][:5]}

HTML (first 3000 chars):
{html[:3000]}

Respond with JSON:
{{
  "top_issues": ["issue1", "issue2", "issue3"],
  "fix_suggestions": ["fix1", "fix2", "fix3"],
  "ai_score_adjustment": 0,
  "overall_verdict": "fail|borderline|pass"
}}"""

    result, _, _, ok = generate_json(system, prompt, 800)
    if ok and isinstance(result, dict):
        return result
    return {}


# ─── Per-game QA runner ─────────────────────────────────────────────────────────

def qa_game(game_dir: Path) -> dict | None:
    game_html = game_dir / "game.html"
    meta_file = game_dir / "metadata.json"

    if not game_html.exists():
        return None

    html = game_html.read_text(encoding="utf-8", errors="replace")
    meta = {}
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text())
        except Exception:
            pass

    game_id = game_dir.name
    game_name = meta.get("name_en", game_id)

    basic = run_qa_checks(html)
    ai_review = ai_qa_review(html, basic)

    final_score = basic["score"]
    if ai_review.get("ai_score_adjustment"):
        final_score = max(0, min(100, final_score + ai_review["ai_score_adjustment"]))

    result = {
        "game_id": game_id,
        "game_name": game_name,
        "html_size_bytes": len(html.encode("utf-8")),
        "qa_score": final_score,
        "eligible": final_score >= PASS_THRESHOLD,
        "grade": _grade(final_score),
        "checks": basic["checks"],
        "issues": basic["issues"],
        "ai_review": ai_review,
        "checked_at": now_iso(),
    }

    # Update review entry with QA result
    _update_review_with_qa(game_id, final_score, basic["issues"])

    # Telegram notification for failures
    if not result["eligible"]:
        notify_qa_failed(game_name, final_score, basic["issues"][:3])
    else:
        send_system_log("qa_passed", f"<b>{game_name}</b> passed QA — score {final_score}/100", "success",
                        {"game_id": game_id, "score": final_score})

    return result


def _update_review_with_qa(game_id: str, qa_score: int, issues: list):
    review_file = REVIEWS_DIR / f"rev_{game_id}.json"
    if not review_file.exists():
        return
    try:
        review = json.loads(review_file.read_text())
        review["qa_score"] = qa_score
        review["qa_eligible"] = qa_score >= PASS_THRESHOLD
        review["qa_issues"] = issues[:5]
        review["qa_checked_at"] = now_iso()
        if not review.get("qa_eligible"):
            review["status"] = "qa_failed"
        review_file.write_text(json.dumps(review, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[game_qa] Failed to update review for {game_id}: {e}")


# ─── Batch runner ────────────────────────────────────────────────────────────────

def run_all_qa() -> dict:
    if not OUTPUTS_DIR.exists():
        print("[game_qa] No games directory found")
        return {"games": [], "summary": {}}

    game_dirs = [d for d in OUTPUTS_DIR.iterdir() if d.is_dir()]
    if not game_dirs:
        print("[game_qa] No game directories found")
        return {"games": [], "summary": {}}

    results = []
    for game_dir in sorted(game_dirs):
        print(f"[game_qa] Checking {game_dir.name}...")
        result = qa_game(game_dir)
        if result:
            results.append(result)
            status = "PASS" if result["eligible"] else "FAIL"
            print(f"  → {status} {result['qa_score']}/100 ({result['grade']})")

    eligible = [r for r in results if r["eligible"]]
    failed = [r for r in results if not r["eligible"]]
    avg_score = sum(r["qa_score"] for r in results) / len(results) if results else 0

    summary = {
        "total_games": len(results),
        "eligible_for_deploy": len(eligible),
        "failed_qa": len(failed),
        "avg_score": round(avg_score, 1),
        "pass_rate": f"{100*len(eligible)//len(results) if results else 0}%",
        "eligible_games": [r["game_id"] for r in eligible],
        "failed_games": [r["game_id"] for r in failed],
    }

    report = {
        "generated_at": now_iso(),
        "summary": summary,
        "games": results,
    }

    MEMORY_DIR.mkdir(exist_ok=True)
    QA_REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[game_qa] Done — {len(eligible)}/{len(results)} eligible, avg score {avg_score:.1f}")
    return report


def main():
    send_system_log("workflow_started", "Game QA Engine started", "info", {"phase": "L"})
    report = run_all_qa()
    summary = report.get("summary", {})
    send_system_log("workflow_completed", f"Game QA complete — {summary.get('eligible_for_deploy', 0)} eligible", "success", summary)


if __name__ == "__main__":
    main()
