from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests

MARKET_API_URLS = [
    "https://our-legacy.vercel.app/api/market",
    "https://our-legacy-api.replit.app/api/market",
]
MARKET_COOLDOWN_MINUTES = 10


class MarketAPI:
    """API for accessing the Elite Market with 10-minute cooldown."""

    def __init__(self):
        self.cache: Optional[Dict[str, Any]] = None
        self.last_fetch: Optional[datetime] = None
        self.cooldown_minutes = MARKET_COOLDOWN_MINUTES

    def _is_cache_valid(self) -> bool:
        if not self.last_fetch or not self.cache:
            return False
        elapsed = datetime.now() - self.last_fetch
        return elapsed < timedelta(minutes=self.cooldown_minutes)

    def get_cooldown_remaining(self) -> Optional[timedelta]:
        if not self.last_fetch:
            return None
        elapsed = datetime.now() - self.last_fetch
        remaining = timedelta(minutes=self.cooldown_minutes) - elapsed
        return remaining if remaining.total_seconds() > 0 else None

    def fetch_market_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch market data from the API. Returns result dict with ok, data, message."""
        if not force_refresh and self._is_cache_valid():
            return {"ok": True, "data": self.cache, "cached": True}

        if self.last_fetch and not self._is_cache_valid():
            remaining = self.get_cooldown_remaining()
            if remaining:
                mins = int(remaining.total_seconds() // 60)
                secs = int(remaining.total_seconds() % 60)
                return {
                    "ok": False,
                    "message": f"Market closed. Come back in {mins}m {secs}s.",
                    "cooldown": True
                }

        for url in MARKET_API_URLS:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    self.cache = data
                    self.last_fetch = datetime.now()
                    return {"ok": True, "data": data, "cached": False}
            except Exception:
                continue

        return {
            "ok": False,
            "message": "Failed to reach any market merchants at this time."
        }

    def get_all_items(self) -> List[Dict[str, Any]]:
        result = self.fetch_market_data()
        if result.get("ok") and result.get("data", {}).get('ok'):
            return result["data"].get('items', [])
        return []

    def filter_items(self,
                     item_type: Optional[str] = None,
                     rarity: Optional[str] = None,
                     class_req: Optional[str] = None,
                     max_price: Optional[int] = None) -> List[Dict[str, Any]]:
        items = self.get_all_items()
        filtered = []
        for item in items:
            if item_type and item.get('type', '').lower() != item_type.lower():
                continue
            if rarity and item.get('rarity', '').lower() != rarity.lower():
                continue
            if class_req:
                req = item.get('requirements') or {}
                if req.get('class', '').lower() != class_req.lower():
                    continue
            if max_price and item.get('marketPrice', 0) > max_price:
                continue
            filtered.append(item)
        return filtered

    def get_items_by_type(self) -> Dict[str, List[Dict[str, Any]]]:
        result = self.fetch_market_data()
        if result.get("ok") and result.get("data", {}).get('ok'):
            return result["data"].get('itemsByType', {})
        return {}


_market_api = MarketAPI()


def get_market_api() -> MarketAPI:
    return _market_api
