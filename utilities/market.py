from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
import json

# Market API URL and cooldown
MARKET_API_URLS = [
    "https://our-legacy.vercel.app/api/market",
    "https://our-legacy-api.replit.app/api/market",  # Fallback 1
    "http://localhost:5000/api/market"  # Fallback 2 (Local)
]
MARKET_COOLDOWN_MINUTES = 10

class MarketAPI:
    """API for accessing the Elite Market with 10-minute cooldown"""

    def __init__(self, lang=None, colors=None):
        self.cache = None
        self.last_fetch = None
        self.cooldown_minutes = MARKET_COOLDOWN_MINUTES

        if colors:
            self.Colors = colors
        else:
            class MockColors:
                CYAN = ''
                GREEN = ''
                RED = ''
                END = ''
            self.Colors = MockColors

        if lang is None:
            class MockLang:
                def get(self, key, default=None, **kwargs):
                    return default if default is not None else key
            self.lang = MockLang()
        else:
            self.lang = lang

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid (within cooldown period)"""
        if not self.last_fetch or not self.cache:
            return False
        elapsed = datetime.now() - self.last_fetch
        return elapsed < timedelta(minutes=self.cooldown_minutes)

    def fetch_market_data(self,
                          force_refresh: bool = False
                          ) -> Optional[Dict[str, Any]]:
        """Fetch market data from the API with caching, cooldown, and fallback endpoints"""
        # Check cache validity
        if not force_refresh and self._is_cache_valid():
            print(
                f"{self.Colors.CYAN}{self.lang.get('visiting_market')}{self.Colors.END}")
            return self.cache

        # Check cooldown
        if self.last_fetch and not self._is_cache_valid():
            remaining = timedelta(minutes=self.cooldown_minutes) - (
                datetime.now() - self.last_fetch)
            mins = int(remaining.total_seconds() // 60)
            secs = int(remaining.total_seconds() % 60)
            print(
                self.lang.get(
                    "market_closed_msg",
                    "Merchants have left and the market is closed! Please come back in {mins}m {secs}s"
                ).format(mins=mins, secs=secs))
            return None

        print(
            f"{self.Colors.CYAN}{self.lang.get('checking_merchants_msg', 'Checking if merchants are in the market...')}{self.Colors.END}"
        )

        # Try each endpoint in order
        for url in MARKET_API_URLS:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    self.cache = data
                    self.last_fetch = datetime.now()
                    print(
                        f"{self.Colors.GREEN}{self.lang.get('market_open_msg', 'Market is open!')}{self.Colors.END}"
                    )
                    return data
            except Exception:
                continue

        print(
            f"{self.Colors.RED}{self.lang.get('market_reach_error', 'Failed to reach any market merchants at this time.')}{self.Colors.END}"
        )
        return None

    def get_cooldown_remaining(self) -> Optional[timedelta]:
        """Get remaining cooldown time"""
        if not self.last_fetch:
            return None
        elapsed = datetime.now() - self.last_fetch
        remaining = timedelta(minutes=self.cooldown_minutes) - elapsed
        if remaining.total_seconds() > 0:
            return remaining
        return None

    def get_all_items(self) -> List[Dict[str, Any]]:
        """Get all market items"""
        data = self.fetch_market_data()
        if data and data.get('ok'):
            return data.get('items', [])
        return []

    def filter_items(self,
                     item_type: Optional[str] = None,
                     rarity: Optional[str] = None,
                     class_req: Optional[str] = None,
                     max_price: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get filtered market items"""
        data = self.fetch_market_data()
        if not data or not data.get('ok'):
            return []

        items = data.get('items', [])

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
        """Get items grouped by type"""
        data = self.fetch_market_data()
        if data and data.get('ok'):
            return data.get('itemsByType', {})
        return {}
