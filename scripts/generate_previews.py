"""
MIFTEH OS — HTML Preview Generator + Visual QA Runner
Downloads generated HTML files from product PR branches via GitHub API,
runs visual_validator on each, and saves:
  - QA reports  →  memory/visual_qa/{project}_{feature_id}.json
  - HTML preview →  frontend/dashboard/previews/{project}/{feature_id}.html
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from visual_validator import validate_html

GH_TOKEN = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN", "")
MEMORY_DIR   = Path("memory")
PREVIEWS_DIR = Path("frontend/dashboard/previews")
QA_DIR       = MEMORY_DIR / "visual_qa"

_GH_API = "https://api.github.com"


# ── GitHub helpers ────────────────────────────────────────────────────────────

def _gh_get(path: str) -> dict | list | None:
    url = f"{_GH_API}{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  [gh] {e.code} on GET {url}")
        return None


def fetch_file_from_branch(owner: str, repo: str, path: str, branch: str) -> str | None:
    """Fetch raw file content from a GitHub branch, returns decoded string or None."""
    data = _gh_get(f"/repos/{owner}/{repo}/contents/{path}?ref={branch}")
    if not data or not isinstance(data, dict):
        return None
    encoded = data.get("content", "")
    try:
        return base64.b64decode(encoded.replace("\n", "")).decode("utf-8", errors="replace")
    except Exception:
        return None


def get_pr_files(owner: str, repo: str, pr_number: int) -> list[dict]:
    """List files changed in a PR."""
    data = _gh_get(f"/repos/{owner}/{repo}/pulls/{pr_number}/files")
    if not isinstance(data, list):
        return []
    return [{"filename": f["filename"], "status": f.get("status", "")} for f in data]


# ── product record helpers ────────────────────────────────────────────────────

def load_product_outputs() -> list[dict]:
    """Load all product output records from outputs/{project}/product/."""
    records = []
    for proj_dir in Path("outputs").iterdir():
        if not proj_dir.is_dir() or proj_dir.name.startswith("."):
            continue
        product_dir = proj_dir / "product"
        if not product_dir.exists():
            continue
        for f in product_dir.glob("*.json"):
            try:
                records.append(json.loads(f.read_text()))
            except Exception:
                pass
    records.sort(key=lambda x: x.get("generated_at", ""), reverse=True)
    return records


def load_all_prs() -> list[dict]:
    f = MEMORY_DIR / "all_prs.json"
    return json.loads(f.read_text()) if f.exists() else []


# ── QA persistence ───────────────────────────────────────────────────────────

def save_qa_report(report: dict, project: str, feature_id: str):
    QA_DIR.mkdir(parents=True, exist_ok=True)
    out = QA_DIR / f"{project}_{feature_id}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"    [qa] saved {out}")


def save_html_preview(html: str, project: str, feature_id: str) -> Path:
    dest_dir = PREVIEWS_DIR / project
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{feature_id}.html"
    dest.write_text(html, encoding="utf-8")
    print(f"    [preview] saved {dest}")
    return dest


def load_existing_qa(project: str, feature_id: str) -> dict | None:
    p = QA_DIR / f"{project}_{feature_id}.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return None


# ── per-PR processing ─────────────────────────────────────────────────────────

def process_pr_record(pr: dict, force: bool = False) -> list[dict]:
    """
    Download HTML files from a product PR, run QA, save reports + previews.
    Returns list of QA report dicts.
    """
    repo_full = pr.get("repo", "")
    branch    = pr.get("branch", "")
    pr_number = pr.get("pr_number")
    project   = pr.get("project", "")

    if not all([repo_full, branch, project, pr_number]):
        return []

    parts = repo_full.split("/")
    if len(parts) != 2:
        return []
    owner, repo = parts

    print(f"\n  [pr] {repo_full}#{pr_number}  branch={branch}")

    pr_files = get_pr_files(owner, repo, pr_number)
    html_files = [f for f in pr_files if f["filename"].endswith(".html")]

    if not html_files:
        print(f"    [pr] no HTML files in this PR")
        return []

    reports = []
    for file_info in html_files:
        path = file_info["filename"]
        feature_id = Path(path).stem

        if not force and load_existing_qa(project, feature_id):
            print(f"    [qa] {feature_id} already validated — skipping (use force=True to re-run)")
            reports.append(load_existing_qa(project, feature_id))
            continue

        print(f"    [fetch] {path}")
        html = fetch_file_from_branch(owner, repo, path, branch)
        if not html:
            print(f"    [fetch] FAILED — skipping")
            continue

        label = path.replace("/", "_").replace(".html", "")
        report = validate_html(html, label=label, project=project)
        report["pr_url"] = pr.get("pr_url", "")
        report["branch"] = branch
        report["file_path"] = path

        save_qa_report(report, project, feature_id)
        save_html_preview(html, project, feature_id)
        reports.append(report)

        status = "PASS" if report["passes_auto_merge_threshold"] else "FAIL"
        print(f"    [qa] {label} → {report['score']}/100 grade={report['grade']} [{status}]")

    return reports


# ── summary builder ───────────────────────────────────────────────────────────

def build_qa_summary() -> dict:
    """Aggregate all saved QA reports into a summary dict."""
    all_reports = []
    for f in QA_DIR.glob("*.json"):
        try:
            all_reports.append(json.loads(f.read_text()))
        except Exception:
            pass

    if not all_reports:
        return {"total": 0, "passing": 0, "avg_score": 0, "reports": []}

    passing = [r for r in all_reports if r.get("passes_auto_merge_threshold")]
    avg = round(sum(r.get("score", 0) for r in all_reports) / len(all_reports))

    return {
        "total": len(all_reports),
        "passing": len(passing),
        "blocking": len(all_reports) - len(passing),
        "avg_score": avg,
        "pass_rate_pct": round(len(passing) / len(all_reports) * 100),
        "reports": [
            {
                "label": r.get("label", ""),
                "project": r.get("project", ""),
                "score": r.get("score", 0),
                "grade": r.get("grade", "?"),
                "passes": r.get("passes_auto_merge_threshold", False),
                "pr_url": r.get("pr_url", ""),
                "branch": r.get("branch", ""),
                "file_path": r.get("file_path", ""),
                "validated_at": r.get("validated_at", ""),
                "summary": r.get("summary", ""),
                "categories": {
                    cat: {
                        "score": v.get("score", 0),
                        "max": v.get("max", 0),
                    }
                    for cat, v in r.get("categories", {}).items()
                },
                "top_issues": r.get("all_issues", [])[:3],
            }
            for r in sorted(all_reports, key=lambda x: x.get("score", 0), reverse=True)
        ],
    }


def save_qa_summary(summary: dict):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    out = MEMORY_DIR / "visual_qa_summary.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\n[previews] QA summary saved → {out}")
    print(f"[previews] {summary['passing']}/{summary['total']} features pass QA  avg={summary['avg_score']}/100")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("[previews] Starting HTML preview generation + visual QA...")

    force = os.environ.get("FORCE_REVALIDATE", "").lower() in ("1", "true", "yes")
    target_project = os.environ.get("TARGET_PROJECT", "all").lower()

    all_prs = load_all_prs()
    product_prs = [
        p for p in all_prs
        if p.get("pr_number") and (
            target_project == "all" or p.get("project") == target_project
        )
    ]

    print(f"[previews] {len(product_prs)} product PRs to check")

    all_reports = []
    for pr in product_prs:
        reports = process_pr_record(pr, force=force)
        all_reports.extend(reports)

    # Also validate any local previews that already exist (from previous runs)
    for proj_dir in PREVIEWS_DIR.iterdir() if PREVIEWS_DIR.exists() else []:
        if not proj_dir.is_dir():
            continue
        project = proj_dir.name
        for html_file in proj_dir.glob("*.html"):
            feature_id = html_file.stem
            if not load_existing_qa(project, feature_id):
                print(f"\n  [local] validating {project}/{html_file.name}")
                html = html_file.read_text(encoding="utf-8", errors="replace")
                report = validate_html(html, label=feature_id, project=project)
                report["file_path"] = str(html_file.relative_to(Path(".")))
                save_qa_report(report, project, feature_id)
                all_reports.append(report)

    summary = build_qa_summary()
    save_qa_summary(summary)

    return summary


if __name__ == "__main__":
    main()
