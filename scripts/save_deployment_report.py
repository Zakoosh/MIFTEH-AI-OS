"""Save deployment report to memory/last_yallaplays_deployment.json."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

report = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "project": "yallaplays",
    "branch": os.environ.get("DEPLOY_BRANCH", "feat/adsense-production-activation"),
    "repo": os.environ.get("YALLAPLAYS_REPO", "Zakoosh/Yallaplays"),
    "pr_url": os.environ.get("PR_URL", ""),
    "pr_number": os.environ.get("PR_NUMBER", ""),
    "live_url": os.environ.get("LIVE_URL", "https://yallaplays.com"),
    "auto_merge": os.environ.get("INPUT_AUTO_MERGE", "false"),
    "run_id": os.environ.get("GITHUB_RUN_ID", ""),
    "run_url": (
        f"https://github.com/Zakoosh/MIFTEH-AI-OS/actions/runs/"
        f"{os.environ.get('GITHUB_RUN_ID', '')}"
    ),
}

out_dir = Path("memory")
out_dir.mkdir(exist_ok=True)
report_file = out_dir / "last_yallaplays_deployment.json"
report_file.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
