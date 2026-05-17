"""Validate that a live URL reflects expected production content."""
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import List


@dataclass
class LiveValidationResult:
    url: str
    reachable: bool
    status_code: int
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)
    ready: bool = False
    message: str = ""


_PRODUCTION_SIGNALS = [
    ("adsense_script", "pagead2.googlesyndication.com"),
    ("publisher_id", "ca-pub-1206965892808259"),
    ("ai_powered_banner", "AI POWERED"),
    ("adsense_ready_badge", "AdSense Ready"),
    ("mifteh_footer", "MIFTEH AI OS"),
    ("rtl_layout", 'dir="rtl"'),
]

_COMPLIANCE_PATHS = [
    "/privacy.html",
    "/terms.html",
    "/cookies.html",
    "/about.html",
    "/contact.html",
]


def validate_live_url(base_url: str, timeout: int = 15) -> LiveValidationResult:
    """HTTP GET base_url, check for production signals."""
    base_url = base_url.rstrip("/")
    result = LiveValidationResult(url=base_url, reachable=False, status_code=0)

    try:
        req = urllib.request.Request(base_url, headers={"User-Agent": "MIFTEH-AI-OS/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result.status_code = resp.status
            result.reachable = True
            html = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        result.status_code = e.code
        result.message = f"HTTP {e.code}"
        return result
    except Exception as e:
        result.message = str(e)[:200]
        return result

    for name, signal in _PRODUCTION_SIGNALS:
        if signal in html:
            result.checks_passed.append(name)
        else:
            result.checks_failed.append(name)

    result.ready = len(result.checks_failed) == 0
    if result.ready:
        result.message = "All production signals detected on live site"
    else:
        result.message = f"Missing: {', '.join(result.checks_failed)}"

    return result


def validate_compliance_pages(base_url: str, timeout: int = 10) -> dict:
    """Check each compliance page returns HTTP 200."""
    base_url = base_url.rstrip("/")
    results = {}
    for path in _COMPLIANCE_PATHS:
        url = base_url + path
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MIFTEH-AI-OS/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                results[path] = {"status": resp.status, "ok": resp.status == 200}
        except urllib.error.HTTPError as e:
            results[path] = {"status": e.code, "ok": False}
        except Exception as e:
            results[path] = {"status": 0, "ok": False, "error": str(e)[:100]}
    return results
