"""
MIFTEH OS — Trust Score Manager
Tracks success/failure rates per file category and per repo.
Determines whether autonomous apply is allowed.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

TRUST_FILE = Path("memory/trust_scores.json")

ALLOWED_PATHS = frozenset([
    "robots.txt", "sitemap.xml", "sitemap_index.xml", "manifest.json",
    "index.html",        # SEO head changes only
    "public/robots.txt", "public/sitemap.xml", "public/manifest.json",
    "ads.txt", ".well-known/assetlinks.json",
])

FORBIDDEN_PATHS = frozenset([
    ".github/workflows", ".github/actions",
    "auth", "password", "secret", ".env",
    "deploy", "payment", "Dockerfile", "railway", "vercel",
    "supabase/migrations", "prisma", "database",
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "vite.config", "next.config", "webpack.config",
])

DEFAULTS = {
    "generated_at": "",
    "categories": {
        "robots_txt":   {"score": 85, "deploys": 0, "rollbacks": 0, "failures": 0},
        "sitemap_xml":  {"score": 85, "deploys": 0, "rollbacks": 0, "failures": 0},
        "meta_tags":    {"score": 78, "deploys": 0, "rollbacks": 0, "failures": 0},
        "json_ld":      {"score": 72, "deploys": 0, "rollbacks": 0, "failures": 0},
        "manifest_json":{"score": 83, "deploys": 0, "rollbacks": 0, "failures": 0},
        "open_graph":   {"score": 78, "deploys": 0, "rollbacks": 0, "failures": 0},
        "twitter_card": {"score": 78, "deploys": 0, "rollbacks": 0, "failures": 0},
        "canonical":    {"score": 80, "deploys": 0, "rollbacks": 0, "failures": 0},
    },
    "repos": {
        "Zakoosh/Yallaplays":        {"score": 85, "deploys": 0, "rollbacks": 0, "failures": 0},
        "Zakoosh/fionera":           {"score": 85, "deploys": 0, "rollbacks": 0, "failures": 0},
        "Zakoosh/mifteh-main-site":  {"score": 85, "deploys": 0, "rollbacks": 0, "failures": 0},
    },
    "suspended_categories": [],
    "suspended_repos": [],
}


def load():
    if TRUST_FILE.exists():
        try:
            return json.loads(TRUST_FILE.read_text())
        except Exception:
            pass
    d = dict(DEFAULTS)
    d["generated_at"] = _now()
    return d


def save(data):
    data["generated_at"] = _now()
    TRUST_FILE.parent.mkdir(exist_ok=True)
    TRUST_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_repo_score(repo_full):
    d = load()
    return d["repos"].get(repo_full, {}).get("score", 85)


def classify_files(filenames):
    """Return list of category keys for the given file paths."""
    cats = set()
    for f in filenames:
        if "robots" in f:   cats.add("robots_txt")
        if "sitemap" in f:  cats.add("sitemap_xml")
        if "manifest" in f: cats.add("manifest_json")
        if f.endswith(".html") or f.endswith(".htm"):
            cats.update(["meta_tags", "open_graph", "json_ld", "canonical"])
    return list(cats)


def is_path_allowed(filename):
    f = filename.lower()
    if any(forbidden in f for forbidden in FORBIDDEN_PATHS):
        return False
    # Allow known safe files directly
    basename = filename.split("/")[-1]
    if basename in ALLOWED_PATHS:
        return True
    # Allow HTML files (index.html, etc.) — changes should be head-only
    if f.endswith(".html") or f.endswith(".htm"):
        return True
    # Allow sitemap variants
    if "sitemap" in f and f.endswith(".xml"):
        return True
    return False


def calculate_safety_score(pr_files, repo_full):
    """
    Score 0-100. Score >= 90 qualifies for auto-merge.
    pr_files: list of dicts with 'filename' and 'additions'/'deletions' keys.
    """
    d = load()
    score = 0
    reasons = []

    filenames = [f["filename"] for f in pr_files]
    file_count = len(filenames)

    # 1. All files in allowed list (+40)
    all_allowed = all(is_path_allowed(fn) for fn in filenames)
    if all_allowed:
        score += 40
        reasons.append("+40: all files are allowed SEO/metadata types")
    else:
        blocked = [fn for fn in filenames if not is_path_allowed(fn)]
        reasons.append(f"+0: forbidden files present: {blocked}")
        return score, reasons, False   # Hard fail

    # 2. No forbidden paths (+20)
    no_forbidden = not any(
        any(fb in fn.lower() for fb in FORBIDDEN_PATHS) for fn in filenames
    )
    if no_forbidden:
        score += 20
        reasons.append("+20: no forbidden paths")

    # 3. File count bonus (+20 if <5, +10 if <10)
    if file_count < 5:
        score += 20
        reasons.append(f"+20: only {file_count} files changed")
    elif file_count < 10:
        score += 10
        reasons.append(f"+10: {file_count} files changed")
    else:
        reasons.append(f"+0: {file_count} files — too many")

    # 4. Repo trust score component (+10 if repo score >= 70)
    repo_score = d["repos"].get(repo_full, {}).get("score", 85)
    if repo_score >= 70:
        score += 10
        reasons.append(f"+10: repo trust score {repo_score}")

    # 5. Category trust scores (+10 if all categories >= 70)
    cats = classify_files(filenames)
    cat_scores = [d["categories"].get(c, {}).get("score", 75) for c in cats]
    if cat_scores and min(cat_scores) >= 70:
        score += 10
        reasons.append(f"+10: all category trust scores >= 70")

    qualifies = (all_allowed and no_forbidden and score >= 90)
    return score, reasons, qualifies


def record_deploy(repo_full, filenames, success=True, rollback=False):
    d = load()
    repo = d["repos"].setdefault(repo_full, {"score": 85, "deploys": 0, "rollbacks": 0, "failures": 0})
    cats = classify_files(filenames)

    if success and not rollback:
        repo["deploys"] = repo.get("deploys", 0) + 1
        repo["score"] = min(100, repo.get("score", 85) + 2)
        for c in cats:
            cat = d["categories"].setdefault(c, {"score": 75, "deploys": 0, "rollbacks": 0, "failures": 0})
            cat["deploys"] = cat.get("deploys", 0) + 1
            cat["score"] = min(100, cat.get("score", 75) + 2)
    elif rollback:
        repo["rollbacks"] = repo.get("rollbacks", 0) + 1
        repo["score"] = max(0, repo.get("score", 85) - 15)
        for c in cats:
            cat = d["categories"].setdefault(c, {"score": 75, "deploys": 0, "rollbacks": 0, "failures": 0})
            cat["rollbacks"] = cat.get("rollbacks", 0) + 1
            cat["score"] = max(0, cat.get("score", 75) - 15)
    else:
        repo["failures"] = repo.get("failures", 0) + 1
        repo["score"] = max(0, repo.get("score", 85) - 10)

    # Auto-suspend if rollback rate > 20%
    deploys = repo.get("deploys", 0)
    rollbacks = repo.get("rollbacks", 0)
    if deploys > 0 and rollbacks / deploys > 0.20:
        if repo_full not in d.get("suspended_repos", []):
            d.setdefault("suspended_repos", []).append(repo_full)
            print(f"[trust] SUSPENDED repo {repo_full} — rollback rate {rollbacks/deploys:.0%}")

    save(d)
    return d


def is_suspended(repo_full):
    d = load()
    return repo_full in d.get("suspended_repos", [])
