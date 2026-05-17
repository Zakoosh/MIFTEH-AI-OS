"""
Auto PR Reviewer — analyzes git diffs for:
build risks, hydration risks, SEO risks, monetization risks, performance risks.
Works on raw diff text — no GitHub API required.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .registry import get_project, get_adsense_publisher
from .framework_detector import detect_framework
from .report_store import save


# ──────────────────────────────────────────────────────────────────────────────
# Risk levels
# ──────────────────────────────────────────────────────────────────────────────

class Risk:
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def _risk(level: str, category: str, description: str, file: Optional[str] = None, line: Optional[int] = None) -> dict:
    return {
        "level": level,
        "category": category,
        "description": description,
        "file": file,
        "line": line,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Diff parsing
# ──────────────────────────────────────────────────────────────────────────────

def _parse_diff(diff_text: str) -> list[dict]:
    """Parse unified diff into list of {file, added_lines, removed_lines}."""
    files = []
    current_file = None
    added = []
    removed = []

    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            if current_file:
                files.append({"file": current_file, "added": added, "removed": removed})
            m = re.search(r"b/(.+)$", line)
            current_file = m.group(1) if m else "unknown"
            added, removed = [], []
        elif line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])

    if current_file:
        files.append({"file": current_file, "added": added, "removed": removed})
    return files


# ──────────────────────────────────────────────────────────────────────────────
# Risk checkers
# ──────────────────────────────────────────────────────────────────────────────

def check_build_risks(files: list[dict], framework: str) -> list[dict]:
    risks = []
    for f in files:
        fname = f["file"]
        added = "\n".join(f["added"])
        removed = "\n".join(f["removed"])

        # TypeScript config changes
        if fname in ("tsconfig.json", "tsconfig.base.json"):
            risks.append(_risk(Risk.HIGH, "build", "tsconfig.json modified — may break TypeScript compilation", fname))

        # Package.json dependency changes
        if fname == "package.json":
            if re.search(r'"next":', removed) and re.search(r'"next":', added):
                old = re.search(r'"next":\s*"([^"]+)"', removed)
                new = re.search(r'"next":\s*"([^"]+)"', added)
                if old and new and old.group(1) != new.group(1):
                    risks.append(_risk(Risk.HIGH, "build",
                        f"Next.js version changed: {old.group(1)} → {new.group(1)}", fname))
            if re.search(r'^-\s+"', removed):
                risks.append(_risk(Risk.MEDIUM, "build", "Package removed from package.json", fname))

        # next.config changes
        if fname in ("next.config.ts", "next.config.js", "next.config.mjs"):
            risks.append(_risk(Risk.HIGH, "build", "next.config modified — review output/routing settings", fname))

        # Layout changes (affects all pages)
        if fname.endswith("layout.tsx") or fname.endswith("layout.ts"):
            risks.append(_risk(Risk.HIGH, "build", f"Root layout modified: {fname}", fname))

        # Import of missing modules
        for line in f["added"]:
            if re.search(r"^import .+ from ['\"](?!@/|\.\/|\.\.\/|next|react)", line):
                pkg = re.search(r"from ['\"]([^'\"/]+)", line)
                if pkg:
                    risks.append(_risk(Risk.LOW, "build",
                        f"New external import: '{pkg.group(1)}' — ensure it's in package.json", fname))

    return risks


def check_hydration_risks(files: list[dict], framework: str) -> list[dict]:
    risks = []
    if framework not in ("nextjs", "nuxt"):
        return risks

    for f in files:
        fname = f["file"]
        added = "\n".join(f["added"])
        removed = "\n".join(f["removed"])

        # Removing 'use client' from a file that had it
        if "'use client'" in removed and "'use client'" not in added:
            risks.append(_risk(Risk.HIGH, "hydration",
                f"'use client' removed — component now server-side. Check for window/document usage.", fname))

        # Adding browser APIs in server components
        for line in f["added"]:
            if re.search(r"\b(window|document|localStorage|sessionStorage|navigator)\.", line):
                if "'use client'" not in added and not fname.endswith(".test.tsx"):
                    risks.append(_risk(Risk.HIGH, "hydration",
                        f"Browser API ({line.strip()[:60]}) used without 'use client'", fname))
                    break

        # useEffect/useState without 'use client'
        if re.search(r"\b(useState|useEffect|useRef|useCallback)\b", added):
            if "'use client'" not in added and "import" not in fname:
                risks.append(_risk(Risk.MEDIUM, "hydration",
                    f"React hooks used — verify 'use client' directive is present", fname))

        # Dynamic import() added
        if "import(" in added:
            risks.append(_risk(Risk.LOW, "hydration",
                "Dynamic import() added — ensure fallback/loading is handled", fname))

    return risks


def check_seo_risks(files: list[dict]) -> list[dict]:
    risks = []
    for f in files:
        fname = f["file"]
        added = "\n".join(f["added"])
        removed = "\n".join(f["removed"])

        # Metadata removed from layout or page
        if re.search(r"export const metadata", removed) and not re.search(r"export const metadata", added):
            risks.append(_risk(Risk.HIGH, "seo",
                "Metadata export removed — page may lose title/description in search results", fname))

        # Title/description removed
        if re.search(r"'title'|\"title\"", removed) and not re.search(r"'title'|\"title\"", added):
            risks.append(_risk(Risk.HIGH, "seo",
                "Title field removed from metadata — impacts search result display", fname))

        if re.search(r"'description'|\"description\"", removed) and not re.search(r"'description'|\"description\"", added):
            risks.append(_risk(Risk.MEDIUM, "seo",
                "Meta description removed", fname))

        # Canonical URL removed
        if "canonical" in removed and "canonical" not in added:
            risks.append(_risk(Risk.HIGH, "seo", "Canonical URL removed — risk of duplicate content", fname))

        # noindex added
        if "noindex" in added and "noindex" not in removed:
            risks.append(_risk(Risk.HIGH, "seo", "noindex directive added — page will be de-indexed", fname))

        # robots.txt changes
        if fname.endswith("robots.txt"):
            risks.append(_risk(Risk.MEDIUM, "seo", "robots.txt modified — verify crawl directives", fname))

        # sitemap changes
        if "sitemap" in fname.lower():
            risks.append(_risk(Risk.LOW, "seo", "Sitemap file modified — re-submit to Google Search Console", fname))

        # Heading tags removed
        if re.search(r"<h1", removed) and not re.search(r"<h1", added):
            risks.append(_risk(Risk.HIGH, "seo", "H1 tag removed — impacts page relevance signal", fname))

    return risks


def check_monetization_risks(files: list[dict], publisher_id: Optional[str]) -> list[dict]:
    risks = []
    for f in files:
        fname = f["file"]
        added = "\n".join(f["added"])
        removed = "\n".join(f["removed"])

        # AdSense script removed
        if "pagead2.googlesyndication.com" in removed and "pagead2.googlesyndication.com" not in added:
            risks.append(_risk(Risk.HIGH, "monetization",
                "AdSense script removed — all ad revenue will stop", fname))

        # Publisher ID changed
        if publisher_id and publisher_id in removed and publisher_id not in added:
            risks.append(_risk(Risk.HIGH, "monetization",
                f"AdSense publisher ID {publisher_id} removed", fname))

        # Ad slot removed
        if re.search(r"data-ad-slot=['\"][0-9]+['\"]", removed) and not re.search(r"data-ad-slot=['\"][0-9]+['\"]", added):
            risks.append(_risk(Risk.MEDIUM, "monetization",
                "AdSense ad slot removed", fname))

        # MonetizationSlot component removed
        if "MonetizationSlot" in removed and "MonetizationSlot" not in added:
            risks.append(_risk(Risk.MEDIUM, "monetization",
                "MonetizationSlot component removed from page", fname))

        # AdSense component changes
        if "adsense" in fname.lower() or "AdSense" in fname:
            risks.append(_risk(Risk.MEDIUM, "monetization",
                f"AdSense component modified: {fname}", fname))

    return risks


def check_performance_risks(files: list[dict]) -> list[dict]:
    risks = []
    heavy_packages = {
        "babylonjs": "3D engine (~500KB)",
        "three": "3D library (~600KB)",
        "phaser": "Game engine (~1MB)",
        "pixi.js": "2D renderer (~600KB)",
        "lodash": "Use tree-shaking: lodash/xxx",
        "moment": "Use date-fns or dayjs instead",
        "rxjs": "Ensure tree-shaking is configured",
    }

    for f in files:
        fname = f["file"]
        added = "\n".join(f["added"])

        # New heavy package imports
        for pkg, note in heavy_packages.items():
            if re.search(rf"import .+ from ['\"]({re.escape(pkg)})['\"]", added):
                risks.append(_risk(Risk.MEDIUM, "performance",
                    f"Heavy package added: {pkg} — {note}", fname))

        # Large image imports
        if re.search(r"import .+\.(png|jpg|jpeg|gif|bmp)", added, re.IGNORECASE):
            risks.append(_risk(Risk.LOW, "performance",
                "Direct image import — prefer next/image for optimization", fname))

        # Missing dynamic import for game/3D code
        if re.search(r"import \{.+(BabylonJS|Scene|Engine|Phaser|PIXI|THREE)", added):
            if "dynamic(" not in added:
                risks.append(_risk(Risk.MEDIUM, "performance",
                    "Heavy 3D/game library imported statically — consider dynamic import for SSR safety", fname))

        # Inline styles added
        if added.count("style={{") > 5:
            risks.append(_risk(Risk.LOW, "performance",
                f"Many inline styles added ({added.count('style={{')} occurrences) — prefer CSS classes", fname))

        # Bundle splitting concern
        if fname.endswith("layout.tsx") and len(added) > 500:
            risks.append(_risk(Risk.MEDIUM, "performance",
                "Large changes to root layout — verify it doesn't bloat the shared bundle", fname))

    return risks


# ──────────────────────────────────────────────────────────────────────────────
# Full review
# ──────────────────────────────────────────────────────────────────────────────

def review_diff(diff_text: str, project_id: str, pr_number: Optional[int] = None) -> dict:
    """
    Full automated PR review.
    Returns structured report with all risk categories.
    """
    p = get_project(project_id)
    publisher_id = get_adsense_publisher(project_id)

    # Detect framework
    source_path = Path(__file__).parents[2] / p["local_path"]
    fw_info = detect_framework(source_path)
    framework = fw_info.get("framework", "unknown")

    files = _parse_diff(diff_text)

    build_risks = check_build_risks(files, framework)
    hydration_risks = check_hydration_risks(files, framework)
    seo_risks = check_seo_risks(files)
    monetization_risks = check_monetization_risks(files, publisher_id)
    performance_risks = check_performance_risks(files)

    all_risks = build_risks + hydration_risks + seo_risks + monetization_risks + performance_risks
    high_count = sum(1 for r in all_risks if r["level"] == Risk.HIGH)
    medium_count = sum(1 for r in all_risks if r["level"] == Risk.MEDIUM)
    low_count = sum(1 for r in all_risks if r["level"] == Risk.LOW)

    # Overall recommendation
    if high_count >= 2:
        recommendation = "REQUEST_CHANGES"
        recommendation_reason = f"{high_count} high-severity risks detected — review required"
    elif high_count == 1:
        recommendation = "REVIEW_CAREFULLY"
        recommendation_reason = "1 high-severity risk — verify before merging"
    elif medium_count >= 3:
        recommendation = "REVIEW_CAREFULLY"
        recommendation_reason = f"{medium_count} medium risks — consider addressing before merge"
    else:
        recommendation = "APPROVE"
        recommendation_reason = "No blocking risks detected"

    report = {
        "project_id": project_id,
        "pr_number": pr_number,
        "framework": framework,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "files_changed": len(files),
        "recommendation": recommendation,
        "recommendation_reason": recommendation_reason,
        "risk_summary": {"high": high_count, "medium": medium_count, "low": low_count, "total": len(all_risks)},
        "risks": {
            "build": build_risks,
            "hydration": hydration_risks,
            "seo": seo_risks,
            "monetization": monetization_risks,
            "performance": performance_risks,
        },
        "changed_files": [f["file"] for f in files],
    }

    save("pr_review", project_id, report)
    return report


def review_pr_from_github(project_id: str, pr_number: int, gh_pat: str) -> dict:
    """Fetch PR diff from GitHub and run review."""
    import urllib.request
    p = get_project(project_id)
    repo = p["repo"].replace("https://github.com/", "").replace(".git", "")
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {gh_pat}",
            "Accept": "application/vnd.github.diff",
            "User-Agent": "MIFTEH-AI-OS/1.0",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            diff = r.read().decode("utf-8", errors="replace")
        return review_diff(diff, project_id, pr_number)
    except Exception as e:
        return {"error": str(e), "project_id": project_id, "pr_number": pr_number}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        pid = sys.argv[1]
        diff_file = sys.argv[2]
        diff_text = Path(diff_file).read_text()
        r = review_diff(diff_text, pid)
        print(json.dumps(r, indent=2))
    else:
        print("Usage: python -m scripts.intelligence.pr_reviewer <project_id> <diff_file>")
