"""
MIFTEH OS — Google Indexing Engine
Real Google Indexing API integration via service account credentials.
Credentials loaded from GOOGLE_SERVICE_ACCOUNT_JSON env var (never committed).
Submits URL_UPDATED / URL_DELETED to indexing.googleapis.com.
Queue, status, logs persisted in memory/indexing/.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import tempfile
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import now_iso

try:
    from telegram_notifier import send_system_log, send_admin_alert
except Exception:
    def send_system_log(*a, **kw): pass
    def send_admin_alert(*a, **kw): pass

# ─── Auth library detection ───────────────────────────────────────────────────

GOOGLE_AUTH_MODE = None

try:
    import google.oauth2.service_account as _sa
    import google.auth.transport.requests as _gatr
    GOOGLE_AUTH_MODE = "google-auth"
except ImportError:
    pass

if not GOOGLE_AUTH_MODE:
    try:
        from oauth2client.service_account import ServiceAccountCredentials as _oac
        import httplib2 as _h2
        GOOGLE_AUTH_MODE = "oauth2client"
    except ImportError:
        pass

# ─── Constants ────────────────────────────────────────────────────────────────

SCOPES = ["https://www.googleapis.com/auth/indexing"]
ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"
QUOTA_ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications/metadata"

MEMORY_DIR = Path("memory")
INDEXING_DIR = MEMORY_DIR / "indexing"
QUEUE_FILE = INDEXING_DIR / "queue.json"
INDEXED_FILE = INDEXING_DIR / "indexed_urls.json"
FAILED_FILE = INDEXING_DIR / "failed.json"
LOGS_DIR = INDEXING_DIR / "logs"

REPORT_FILE = MEMORY_DIR / "indexing_report.json"

DAILY_QUOTA = 200       # Google's free-tier limit
RETRY_LIMIT = 3
RETRY_BACKOFF_SEC = 5
BATCH_SIZE = 20         # URLs per run


# ─── Credential loading ───────────────────────────────────────────────────────

def _load_creds_dict() -> dict | None:
    """Load service account JSON from env var or local file."""
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if raw:
        try:
            return json.loads(raw)
        except Exception as e:
            print(f"[indexing] Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
            return None

    # Fallback: local file (never committed, only for local dev)
    local_file = Path("service_account_file.json")
    if local_file.exists():
        try:
            return json.loads(local_file.read_text())
        except Exception:
            return None

    return None


def _get_access_token(creds_dict: dict) -> str | None:
    """Get OAuth2 access token from service account credentials."""
    if GOOGLE_AUTH_MODE == "google-auth":
        try:
            credentials = _sa.Credentials.from_service_account_info(
                creds_dict, scopes=SCOPES
            )
            request = _gatr.Request()
            credentials.refresh(request)
            return credentials.token
        except Exception as e:
            print(f"[indexing] google-auth token error: {e}")
            return None

    elif GOOGLE_AUTH_MODE == "oauth2client":
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(creds_dict, f)
                temp_path = f.name
            credentials = _oac.from_json_keyfile_name(temp_path, scopes=SCOPES)
            credentials.get_access_token()
            token = credentials.access_token
            Path(temp_path).unlink(missing_ok=True)
            return token
        except Exception as e:
            print(f"[indexing] oauth2client token error: {e}")
            return None

    # Manual JWT via Google token endpoint
    return _get_token_manual(creds_dict)


def _get_token_manual(creds_dict: dict) -> str | None:
    """Manual JWT token exchange when auth libraries unavailable."""
    try:
        import base64
        import hashlib
        import hmac
        import struct

        private_key_pem = creds_dict.get("private_key", "")
        client_email = creds_dict.get("client_email", "")
        token_uri = creds_dict.get("token_uri", "https://oauth2.googleapis.com/token")

        if not private_key_pem or not client_email:
            print("[indexing] Manual JWT: missing private_key or client_email")
            return None

        # Try RSA signing via cryptography library
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding

            now_ts = int(time.time())
            header = {"alg": "RS256", "typ": "JWT"}
            payload = {
                "iss": client_email,
                "scope": SCOPES[0],
                "aud": token_uri,
                "exp": now_ts + 3600,
                "iat": now_ts,
            }

            def b64(data):
                if isinstance(data, str):
                    data = data.encode()
                return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

            header_b64 = b64(json.dumps(header))
            payload_b64 = b64(json.dumps(payload))
            signing_input = f"{header_b64}.{payload_b64}".encode()

            private_key = serialization.load_pem_private_key(
                private_key_pem.encode(), password=None
            )
            signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
            jwt_token = f"{header_b64}.{payload_b64}.{b64(signature)}"

            # Exchange JWT for access token
            body = urllib.parse.urlencode({
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": jwt_token,
            }).encode()
            req = urllib.request.Request(token_uri, data=body,
                                          headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=15) as r:
                resp = json.loads(r.read())
                return resp.get("access_token")
        except ImportError:
            print("[indexing] Manual JWT: cryptography library not available")
            return None

    except Exception as e:
        print(f"[indexing] Manual JWT error: {e}")
        return None


# ─── URL submission ───────────────────────────────────────────────────────────

def submit_url(url: str, notification_type: str = "URL_UPDATED",
               access_token: str = None) -> dict:
    """Submit a single URL to Google Indexing API."""
    if not access_token:
        print(f"[indexing] No access token — cannot submit {url}")
        return {"url": url, "success": False, "error": "no_access_token", "submitted_at": now_iso()}

    payload = json.dumps({"url": url, "type": notification_type}).encode()
    req = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        method="POST",
    )

    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                resp = json.loads(r.read())
                return {
                    "url": url,
                    "success": True,
                    "notification_type": notification_type,
                    "submitted_at": now_iso(),
                    "response": resp,
                }
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode()[:300]
            except Exception:
                pass
            if e.code == 429:
                print(f"[indexing] Quota exceeded for {url}")
                return {"url": url, "success": False, "error": "quota_exceeded",
                        "http_code": 429, "submitted_at": now_iso()}
            if e.code in (400, 403):
                return {"url": url, "success": False, "error": f"http_{e.code}: {body}",
                        "http_code": e.code, "submitted_at": now_iso()}
            if attempt < RETRY_LIMIT:
                time.sleep(RETRY_BACKOFF_SEC * attempt)
                continue
            return {"url": url, "success": False, "error": f"http_{e.code}", "submitted_at": now_iso()}
        except Exception as e:
            if attempt < RETRY_LIMIT:
                time.sleep(RETRY_BACKOFF_SEC * attempt)
                continue
            return {"url": url, "success": False, "error": str(e)[:200], "submitted_at": now_iso()}

    return {"url": url, "success": False, "error": "max_retries", "submitted_at": now_iso()}


# ─── Queue management ────────────────────────────────────────────────────────

def _ensure_dirs():
    for d in [INDEXING_DIR, LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default=None):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return default if default is not None else {}


def _save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def load_queue() -> list:
    return _load_json(QUEUE_FILE, {}).get("urls", [])


def add_to_queue(urls: list[str], priority: str = "normal", source: str = ""):
    _ensure_dirs()
    q = _load_json(QUEUE_FILE, {"urls": []})
    existing = {item["url"] for item in q.get("urls", [])}
    new_items = []
    for url in urls:
        if url not in existing:
            new_items.append({
                "url": url,
                "priority": priority,
                "source": source,
                "added_at": now_iso(),
                "attempts": 0,
            })
            existing.add(url)
    q.setdefault("urls", []).extend(new_items)
    q["updated_at"] = now_iso()
    _save_json(QUEUE_FILE, q)
    print(f"[indexing] Added {len(new_items)} URLs to queue (skipped {len(urls)-len(new_items)} duplicates)")
    return len(new_items)


def remove_from_queue(urls: set):
    _ensure_dirs()
    q = _load_json(QUEUE_FILE, {"urls": []})
    q["urls"] = [item for item in q.get("urls", []) if item["url"] not in urls]
    q["updated_at"] = now_iso()
    _save_json(QUEUE_FILE, q)


def save_indexed(results: list[dict]):
    _ensure_dirs()
    data = _load_json(INDEXED_FILE, {"urls": [], "total": 0})
    succeeded = [r for r in results if r["success"]]
    data["urls"] = (succeeded + data.get("urls", []))[:500]
    data["total"] = data.get("total", 0) + len(succeeded)
    data["updated_at"] = now_iso()
    _save_json(INDEXED_FILE, data)


def save_failed(results: list[dict]):
    _ensure_dirs()
    data = _load_json(FAILED_FILE, {"urls": []})
    failed = [r for r in results if not r["success"]]
    for f in failed:
        f["retry_count"] = f.get("retry_count", 0) + 1
    data["urls"] = (failed + data.get("urls", []))[:200]
    data["updated_at"] = now_iso()
    _save_json(FAILED_FILE, data)


def _write_log(results: list[dict]):
    _ensure_dirs()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = LOGS_DIR / f"indexing_{date_str}.json"
    log = _load_json(log_file, {"entries": []})
    log["entries"].extend(results)
    log["entries"] = log["entries"][-500:]
    log["updated_at"] = now_iso()
    _save_json(log_file, log)


# ─── Validation ───────────────────────────────────────────────────────────────

def validate_url(url: str) -> tuple[bool, str]:
    """Check that URL is valid for indexing submission."""
    if not url.startswith("https://"):
        return False, "URL must start with https://"
    if len(url) > 2048:
        return False, "URL too long (>2048 chars)"
    # Don't submit admin/internal paths
    blocked = ["/admin", "localhost", "127.0.0.1", ".github", "/memory/"]
    for b in blocked:
        if b in url:
            return False, f"URL contains blocked pattern: {b}"
    return True, ""


# ─── Batch runner ─────────────────────────────────────────────────────────────

def run_batch(urls_override: list[str] = None, priority_filter: str = None) -> dict:
    _ensure_dirs()

    creds_dict = _load_creds_dict()
    if not creds_dict:
        msg = "GOOGLE_SERVICE_ACCOUNT_JSON not configured — indexing skipped"
        print(f"[indexing] {msg}")
        send_system_log("indexing_skipped", msg, "warning")
        return {"submitted": 0, "succeeded": 0, "failed": 0, "skipped": True,
                "reason": "no_credentials", "generated_at": now_iso()}

    if GOOGLE_AUTH_MODE is None:
        msg = "No auth library available — install google-auth or oauth2client"
        print(f"[indexing] {msg}")
        send_system_log("indexing_skipped", msg, "warning", {"auth_mode": "none"})
        return {"submitted": 0, "succeeded": 0, "failed": 0, "skipped": True,
                "reason": "no_auth_library", "generated_at": now_iso()}

    access_token = _get_access_token(creds_dict)
    if not access_token:
        send_admin_alert("indexing_auth_failed", "Failed to get Google access token", "error")
        return {"submitted": 0, "succeeded": 0, "failed": 0, "skipped": True,
                "reason": "auth_failed", "generated_at": now_iso()}

    # Get URLs to submit
    if urls_override:
        queue_items = [{"url": u, "priority": "manual", "attempts": 0} for u in urls_override]
    else:
        q = _load_json(QUEUE_FILE, {"urls": []})
        queue_items = q.get("urls", [])
        if priority_filter:
            queue_items = [item for item in queue_items if item.get("priority") == priority_filter]
        # Sort by priority: high > normal > low
        priority_order = {"high": 0, "normal": 1, "low": 2}
        queue_items.sort(key=lambda x: priority_order.get(x.get("priority", "normal"), 1))
        queue_items = queue_items[:BATCH_SIZE]

    if not queue_items:
        print("[indexing] Queue empty — nothing to submit")
        return {"submitted": 0, "succeeded": 0, "failed": 0, "queue_empty": True, "generated_at": now_iso()}

    results = []
    succeeded_urls = set()
    failed_urls = set()

    for item in queue_items:
        url = item["url"] if isinstance(item, dict) else item
        valid, reason = validate_url(url)
        if not valid:
            results.append({"url": url, "success": False, "error": reason, "submitted_at": now_iso()})
            failed_urls.add(url)
            continue

        result = submit_url(url, access_token=access_token)
        results.append(result)
        if result["success"]:
            succeeded_urls.add(url)
            print(f"[indexing] ✅ Indexed: {url}")
        else:
            failed_urls.add(url)
            print(f"[indexing] ❌ Failed: {url} — {result.get('error', '')}")

        time.sleep(0.3)  # Rate limiting

    # Persist results
    if not urls_override:
        remove_from_queue(succeeded_urls)

    save_indexed(results)
    save_failed([r for r in results if not r["success"]])
    _write_log(results)

    summary = {
        "submitted": len(results),
        "succeeded": len(succeeded_urls),
        "failed": len(failed_urls),
        "success_rate": f"{100*len(succeeded_urls)//max(len(results),1)}%",
        "auth_mode": GOOGLE_AUTH_MODE,
        "generated_at": now_iso(),
    }

    if failed_urls:
        send_admin_alert("indexing_failures", f"{len(failed_urls)} URLs failed to index", "warning",
                         {"count": len(failed_urls), "succeeded": len(succeeded_urls)})
    send_system_log("indexing_batch_complete",
                    f"Indexed {len(succeeded_urls)}/{len(results)} URLs", "success", summary)
    return summary


def retry_failed() -> dict:
    """Re-submit URLs from the failed queue."""
    data = _load_json(FAILED_FILE, {"urls": []})
    failed = [f for f in data.get("urls", []) if f.get("retry_count", 0) < RETRY_LIMIT]
    if not failed:
        print("[indexing] No retryable failed URLs")
        return {"retried": 0}
    urls = [f["url"] for f in failed[:BATCH_SIZE]]
    return run_batch(urls_override=urls)


# ─── Auto-queue helpers ────────────────────────────────────────────────────────

def queue_deployed_games():
    """Queue all deployed game pages for indexing."""
    from pathlib import Path
    reviews_dir = Path("memory/reviews")
    if not reviews_dir.exists():
        return 0
    urls = []
    for f in reviews_dir.glob("rev_*.json"):
        try:
            review = json.loads(f.read_text())
            if review.get("status") == "deployed":
                game_id = review.get("game_id", "")
                deploy_url = review.get("deploy_url", "")
                if deploy_url and deploy_url.startswith("https://"):
                    urls.append(deploy_url)
                elif game_id:
                    urls.append(f"https://yallaplays.com/games/{game_id}/")
        except Exception:
            pass
    return add_to_queue(urls, priority="high", source="deployed_games")


def queue_seo_pages(seo_dir: str = "outputs/yallaplays/programmatic"):
    """Queue programmatic SEO pages for indexing."""
    seo_path = Path(seo_dir)
    if not seo_path.exists():
        return 0
    urls = []
    for f in seo_path.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            url = data.get("canonical_url") or data.get("url")
            if url and url.startswith("https://"):
                urls.append(url)
        except Exception:
            pass
    return add_to_queue(urls, priority="normal", source="seo_pages")


# ─── Report builder ───────────────────────────────────────────────────────────

def build_report() -> dict:
    _ensure_dirs()
    q = _load_json(QUEUE_FILE, {"urls": []})
    indexed = _load_json(INDEXED_FILE, {"urls": [], "total": 0})
    failed = _load_json(FAILED_FILE, {"urls": []})

    queue_items = q.get("urls", [])
    indexed_today = [u for u in indexed.get("urls", [])
                     if u.get("submitted_at", "")[:10] == now_iso()[:10]]

    report = {
        "generated_at": now_iso(),
        "auth_mode": GOOGLE_AUTH_MODE or "none",
        "credentials_configured": bool(_load_creds_dict()),
        "queue_size": len(queue_items),
        "total_indexed_all_time": indexed.get("total", 0),
        "indexed_today": len(indexed_today),
        "failed_count": len(failed.get("urls", [])),
        "daily_quota": DAILY_QUOTA,
        "quota_used_today": len(indexed_today),
        "quota_remaining": max(0, DAILY_QUOTA - len(indexed_today)),
        "success_rate": _calc_success_rate(indexed, failed),
        "queue_by_priority": {
            "high": sum(1 for u in queue_items if u.get("priority") == "high"),
            "normal": sum(1 for u in queue_items if u.get("priority") == "normal"),
            "low": sum(1 for u in queue_items if u.get("priority") == "low"),
        },
        "recent_indexed": indexed.get("urls", [])[:20],
        "recent_failed": failed.get("urls", [])[:10],
        "queue_preview": queue_items[:10],
    }

    REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return report


def _calc_success_rate(indexed: dict, failed: dict) -> str:
    total_indexed = indexed.get("total", 0)
    total_failed = len(failed.get("urls", []))
    total = total_indexed + total_failed
    if total == 0:
        return "N/A"
    return f"{100*total_indexed//total}%"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("[indexing] Starting Google Indexing Engine...")
    send_system_log("workflow_started", "Google Indexing Engine started", "info", {"phase": "M"})

    # Auto-queue deployed games and SEO pages
    game_count = queue_deployed_games()
    seo_count = queue_seo_pages()
    print(f"[indexing] Queued: {game_count} game pages, {seo_count} SEO pages")

    # Run batch submission
    result = run_batch()

    # Build and save report
    report = build_report()

    send_system_log("workflow_completed",
                    f"Indexing complete — {result.get('succeeded',0)} submitted, "
                    f"{report['queue_size']} remaining in queue",
                    "success", {"succeeded": result.get("succeeded", 0),
                                "failed": result.get("failed", 0),
                                "queue": report["queue_size"]})
    print(f"[indexing] Done — {result}")


if __name__ == "__main__":
    main()
