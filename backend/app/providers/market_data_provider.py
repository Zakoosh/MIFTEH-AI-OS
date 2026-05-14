from __future__ import annotations
import time
from datetime import datetime
from pathlib import Path
import json
from ..core.config import get_config


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "providers"

POPULAR_SYMBOLS = {
    "mena_stocks": ["2222.SR", "1120.SR", "1180.SR", "EMAAR.DU", "ADNOCDIST.AD", "COMI.CA"],
    "global": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"],
    "crypto": ["BTC/USD", "ETH/USD", "BNB/USD"],
    "forex": ["USD/SAR", "EUR/USD", "GBP/USD", "USD/AED"],
}


class TwelveDataProvider:
    def __init__(self):
        cfg = get_config()
        self._api_key = cfg.twelve_data_api_key
        self._base_url = cfg.twelve_data_base_url
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._cache_path = MEMORY_DIR / "market_data_cache.json"

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _load_cache(self) -> dict:
        if not self._cache_path.exists():
            return {}
        try:
            data = json.loads(self._cache_path.read_text())
            ts = data.get("_cached_at", "")
            if ts:
                age = (datetime.utcnow() - datetime.fromisoformat(ts)).total_seconds()
                if age < 60:
                    return data
        except Exception:
            pass
        return {}

    def _save_cache(self, data: dict) -> None:
        data["_cached_at"] = datetime.utcnow().isoformat()
        self._cache_path.write_text(json.dumps(data, indent=2, default=str))

    async def get_price(self, symbol: str) -> dict:
        if not self.is_configured():
            return self._mock_price(symbol)
        cache = self._load_cache()
        if symbol in cache:
            return cache[symbol]
        try:
            import httpx
            start = time.monotonic()
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._base_url}/price",
                    params={"symbol": symbol, "apikey": self._api_key},
                )
            latency = (time.monotonic() - start) * 1000
            if resp.status_code == 200:
                data = resp.json()
                price = float(data.get("price", 0))
                result = {"symbol": symbol, "price": price, "source": "twelve_data", "latency_ms": round(latency, 2), "fetched_at": datetime.utcnow().isoformat()}
                cache[symbol] = result
                self._save_cache(cache)
                return result
        except Exception as e:
            pass
        return self._mock_price(symbol)

    async def get_quote(self, symbol: str) -> dict:
        if not self.is_configured():
            return self._mock_quote(symbol)
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._base_url}/quote",
                    params={"symbol": symbol, "apikey": self._api_key},
                )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "symbol": symbol,
                    "name": data.get("name", symbol),
                    "price": float(data.get("close", data.get("price", 0))),
                    "open": float(data.get("open", 0)),
                    "high": float(data.get("high", 0)),
                    "low": float(data.get("low", 0)),
                    "volume": int(data.get("volume", 0)),
                    "change": float(data.get("change", 0)),
                    "change_pct": float(data.get("percent_change", 0)),
                    "fifty_two_week_high": float(data.get("fifty_two_week", {}).get("high", 0)),
                    "fifty_two_week_low": float(data.get("fifty_two_week", {}).get("low", 0)),
                    "source": "twelve_data",
                    "fetched_at": datetime.utcnow().isoformat(),
                }
        except Exception:
            pass
        return self._mock_quote(symbol)

    async def get_batch_prices(self, symbols: list[str]) -> list[dict]:
        results = []
        for sym in symbols:
            results.append(await self.get_price(sym))
        return results

    def _mock_price(self, symbol: str) -> dict:
        import random
        base = {"2222.SR": 28.5, "AAPL": 195.2, "BTC/USD": 67500, "USD/SAR": 3.75, "EMAAR.DU": 7.2}.get(symbol, 100.0)
        price = base * (1 + random.uniform(-0.02, 0.02))
        return {"symbol": symbol, "price": round(price, 4), "source": "mock", "fetched_at": datetime.utcnow().isoformat()}

    def _mock_quote(self, symbol: str) -> dict:
        import random
        p = self._mock_price(symbol)
        price = p["price"]
        change_pct = random.uniform(-3, 3)
        return {
            "symbol": symbol,
            "name": f"{symbol} Corp",
            "price": price,
            "open": round(price * 0.995, 4),
            "high": round(price * 1.01, 4),
            "low": round(price * 0.99, 4),
            "volume": random.randint(1000000, 50000000),
            "change": round(price * change_pct / 100, 4),
            "change_pct": round(change_pct, 2),
            "source": "mock",
            "fetched_at": datetime.utcnow().isoformat(),
        }
