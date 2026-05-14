from __future__ import annotations
import os
from pathlib import Path
from functools import lru_cache


BACKEND_DIR = Path(__file__).parent.parent.parent
DASHBOARD_ROUTE = "miftehos.com"
DASHBOARD_URL = "https://miftehos.com"


def _load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    env: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and val:
                env[key] = val
    return env


def load_env() -> None:
    """Load env vars — .env.local → .env → .env.example, first file wins per key.

    All three files override shell env vars so application tokens (e.g. GITHUB_TOKEN)
    are not shadowed by Codespaces-injected or CI-injected tokens. The first file that
    defines a key wins; later files are skipped for that key.
    """
    sources = [
        BACKEND_DIR / ".env.local",
        BACKEND_DIR / ".env",
        BACKEND_DIR / ".env.example",
    ]
    loaded_from = None
    seen_keys: set[str] = set()
    for path in sources:
        env_vars = _load_env_file(path)
        if not env_vars:
            continue
        for key, val in env_vars.items():
            if key not in seen_keys:
                os.environ[key] = val
                seen_keys.add(key)
        if loaded_from is None:
            loaded_from = str(path.name)
    return loaded_from


@lru_cache(maxsize=1)
def get_config() -> "AppConfig":
    load_env()
    return AppConfig()


class AppConfig:
    def __init__(self):
        self.dashboard_route = DASHBOARD_ROUTE
        self.dashboard_url = DASHBOARD_URL

        self.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        self.openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o")

        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        self.gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

        self.github_token = os.environ.get("GITHUB_TOKEN", "")

        self.twelve_data_api_key = os.environ.get("VITE_TWELVE_DATA_API_KEY", os.environ.get("TWELVE_DATA_API_KEY", ""))
        self.twelve_data_base_url = os.environ.get("VITE_TWELVE_DATA_BASE_URL", "https://api.twelvedata.com")
        self.alpha_vantage_key = os.environ.get("VITE_ALPHA_VANTAGE_API_KEY", os.environ.get("ALPHA_VANTAGE_API_KEY", ""))

        self.daily_budget_usd = float(os.environ.get("DAILY_BUDGET_USD", "10.0"))
        self.max_ops_per_hour = int(os.environ.get("MAX_OPS_PER_HOUR", "50"))
        self.min_trust_score = float(os.environ.get("MIN_TRUST_SCORE", "0.3"))

        # Admin auth
        self.admin_secret = os.environ.get("ADMIN_SECRET", "")
        self.admin_password = os.environ.get("ADMIN_PASSWORD", "mifteh-admin")
        self.admin_email = os.environ.get("ADMIN_EMAIL", "")
        self.mifteh_os_url = os.environ.get("MIFTEH_OS_URL", "https://miftehos.com")
        self.mifteh_api_url = os.environ.get("MIFTEH_API_URL", "")
        self.github_repo_mifteh = os.environ.get("GITHUB_REPO_MIFTEH", "Zakoosh/mifteh")

        # GitHub repo targets
        self.github_repo_yallaplays = os.environ.get("GITHUB_REPO_YALLAPLAYS", "Zakoosh/Yallaplays")
        self.github_repo_fionera = os.environ.get("GITHUB_REPO_FIONERA", "Zakoosh/fionera")

    @property
    def openai_active(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def gemini_active(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def market_data_active(self) -> bool:
        return bool(self.twelve_data_api_key or self.alpha_vantage_key)

    @property
    def github_active(self) -> bool:
        return bool(self.github_token)

    def provider_summary(self) -> dict:
        return {
            "openai": "active" if self.openai_active else "not_configured",
            "gemini": "active" if self.gemini_active else "not_configured",
            "twelve_data": "active" if self.twelve_data_api_key else "not_configured",
            "alpha_vantage": "active" if self.alpha_vantage_key else "not_configured",
            "github": "active" if self.github_active else "not_configured",
        }
