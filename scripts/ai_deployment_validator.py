"""
MIFTEH OS — Deployment Validation Script
After a merge, validates the live site: HTTP 200, meta tags, robots.txt, sitemap.xml.
Records pass/fail to memory and updates trust scores.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from trust_manager import record_deploy

MEMORY_DIR = Path("memory")
VALIDATION_LOG = MEMORY_DIR / "validation_log.json"
AUTOMERGE_LOG = MEMORY_DIR / "automerge_log.json"

REPOS = {
    "Zakoosh/Yallaplays":       "https://yallaplays.com",
    "Zakoosh/fionera":          "https://fionera.app",
    "Zakoosh/mifteh-main-site": "https://miftehos.com",
}


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(url, timeout=15):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MIFTEH-Validator/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, str(e)


def check_meta_tags(html):
    """Check for presence of basic SEO meta tags."""
    checks = {
        "description":  '<meta name="description"' in html.lower(),
        "og:title":     'og:title' in html.lower(),
        "og:url":       'og:url' in html.lower(),
        "twitter:card": 'twitter:card' in html.lower(),
        "canonical":    '<link rel="canonical"' in html.lower(),
        "json_ld":      'application/ld+json' in html.lower(),
    }
    return checks


def validate_site(base_url):
    results = {
        "base_url": base_url,
        "checks": {},
        "passed": 0,
        "total": 0,
        "ok": False,
    }

    checks = {}

    # 1. Homepage HTTP 200
    code, html = fetch(base_url)
    checks["homepage_200"] = (code == 200)
    if code == 200:
        meta = check_meta_tags(html)
        checks.update(meta)

    # 2. robots.txt
    robots_code, _ = fetch(f"{base_url}/robots.txt")
    checks["robots_txt_200"] = (robots_code == 200)

    # 3. sitemap.xml
    sitemap_code, sitemap_body = fetch(f"{base_url}/sitemap.xml")
    sitemap_ok = sitemap_code == 200 and "<?xml" in sitemap_body
    if not sitemap_ok:
        sitemap_index_code, sitemap_index_body = fetch(f"{base_url}/sitemap_index.xml")
        sitemap_ok = sitemap_index_code == 200 and "<?xml" in sitemap_index_body
    checks["sitemap_xml_200"] = sitemap_ok

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)

    results["checks"] = checks
    results["passed"] = passed
    results["total"] = total
    results["ok"] = passed >= (total * 0.75)  # 75% pass threshold

    return results


def load_log(path):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return []
    return []


def save_log(path, entries):
    MEMORY_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(entries, indent=2, ensure_ascii=False))


def main():
    # Find recently merged PRs to validate
    automerge_log = load_log(AUTOMERGE_LOG)
    recently_merged = [e for e in automerge_log if e.get("action") == "merged"]

    if not recently_merged:
        print("[validator] No recently merged PRs found — validating all known repos")
        repos_to_check = list(REPOS.items())
    else:
        seen = set()
        repos_to_check = []
        for entry in recently_merged:
            repo = entry.get("repo")
            if repo and repo in REPOS and repo not in seen:
                repos_to_check.append((repo, REPOS[repo]))
                seen.add(repo)

    print(f"[validator] Checking {len(repos_to_check)} site(s) at {_now()}")

    validation_log = load_log(VALIDATION_LOG)
    session_results = []

    for repo_full, base_url in repos_to_check:
        print(f"\n  Validating {repo_full} → {base_url}")
        result = validate_site(base_url)
        result["repo"] = repo_full
        result["validated_at"] = _now()

        for check, ok in result["checks"].items():
            status = "PASS" if ok else "FAIL"
            print(f"    [{status}] {check}")

        pct = int(result["passed"] / result["total"] * 100) if result["total"] else 0
        print(f"    Score: {result['passed']}/{result['total']} ({pct}%) — {'OK' if result['ok'] else 'DEGRADED'}")

        # Update trust scores based on validation result
        filenames = ["robots.txt", "sitemap.xml", "index.html"]  # canonical set
        if result["ok"]:
            record_deploy(repo_full, filenames, success=True, rollback=False)
            print(f"    [trust] +2 trust recorded for {repo_full}")
        else:
            # Validation failed — count as deployment failure but don't rollback yet
            record_deploy(repo_full, filenames, success=False, rollback=False)
            print(f"    [trust] -10 failure recorded for {repo_full} — manual review recommended")

        session_results.append(result)
        validation_log.append(result)

    save_log(VALIDATION_LOG, validation_log)

    print(f"\n[validator] Done — {len(session_results)} site(s) validated")
    ok_count = sum(1 for r in session_results if r["ok"])
    print(f"  OK: {ok_count}/{len(session_results)}")


if __name__ == "__main__":
    main()
