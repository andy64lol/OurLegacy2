from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import os
import random

MARKET_COOLDOWN_MINUTES = 10
MARKET_ITEM_COUNT = 12
BIRTHDAY_MONTH = 3
BIRTHDAY_DAY = 24
BIRTHDAY_ITEM_NAME = "Talisman of Andy"

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_ITEMS_FILE = os.path.join(_DATA_DIR, "items.json")

ELITE_RARITIES = {"rare", "legendary"}
ELITE_TYPES = {"weapon", "armor", "accessory", "consumable"}
MARKET_PRICE_MULTIPLIER = 2.0


def _load_items() -> Dict[str, Any]:
    try:
        with open(_ITEMS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _build_elite_pool(items: Dict[str, Any]) -> List[Dict[str, Any]]:
    pool = []
    for name, data in items.items():
        if not isinstance(data, dict):
            continue
        if data.get("rarity") not in ELITE_RARITIES:
            continue
        if data.get("type") not in ELITE_TYPES:
            continue
        if name == BIRTHDAY_ITEM_NAME:
            continue
        entry = dict(data)
        entry["name"] = name
        base_price = data.get("price", 100)
        entry["marketPrice"] = int(base_price * MARKET_PRICE_MULTIPLIER)
        pool.append(entry)
    return pool


def _get_time_window_seed() -> int:
    now = datetime.now()
    total_minutes = int(now.timestamp()) // 60
    window = total_minutes // MARKET_COOLDOWN_MINUTES
    return window


def _is_birthday() -> bool:
    now = datetime.now()
    return now.month == BIRTHDAY_MONTH and now.day == BIRTHDAY_DAY


def _select_market_items(pool: List[Dict[str, Any]], extra_seed: int = 0) -> List[Dict[str, Any]]:
    seed = _get_time_window_seed() + extra_seed * 999983
    rng = random.Random(seed)
    count = min(MARKET_ITEM_COUNT, len(pool))
    return rng.sample(pool, count)


def _get_birthday_item(items: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    data = items.get(BIRTHDAY_ITEM_NAME)
    if not data or not isinstance(data, dict):
        return None
    entry = dict(data)
    entry["name"] = BIRTHDAY_ITEM_NAME
    entry["marketPrice"] = 0
    entry["birthday_special"] = True
    return entry


class MarketAPI:
    """Elite Market backed by local items data with a time-window rotation."""

    def __init__(self):
        self.cache: Optional[Dict[str, Any]] = None
        self.cache_window: Optional[int] = None
        self.cooldown_minutes = MARKET_COOLDOWN_MINUTES
        self._last_extra_seed: int = 0

    def _is_cache_valid(self) -> bool:
        if self.cache is None or self.cache_window is None:
            return False
        return self.cache_window == _get_time_window_seed()

    def get_cooldown_remaining(self) -> Optional[timedelta]:
        now = datetime.now()
        total_seconds = int(now.timestamp())
        window_seconds = self.cooldown_minutes * 60
        seconds_into_window = total_seconds % window_seconds
        remaining_seconds = window_seconds - seconds_into_window
        if remaining_seconds > 0 and self._is_cache_valid():
            return timedelta(seconds=remaining_seconds)
        return None

    def fetch_market_data(self, force_refresh: bool = False, extra_seed: int = 0) -> Dict[str, Any]:
        """Fetch market data from local items.json. Returns result dict with ok, data, message."""
        current_window = _get_time_window_seed()

        if not force_refresh and self._is_cache_valid() and extra_seed == self._last_extra_seed:
            return {"ok": True, "data": self.cache, "cached": True}

        items = _load_items()
        pool = _build_elite_pool(items)

        if not pool:
            return {"ok": False, "message": "The Elite Market has no wares today."}

        selected = _select_market_items(pool, extra_seed=extra_seed)

        if _is_birthday():
            bday_item = _get_birthday_item(items)
            if bday_item:
                if not any(i["name"] == BIRTHDAY_ITEM_NAME for i in selected):
                    selected.insert(0, bday_item)

        data = {"ok": True, "items": selected}
        self.cache = data
        self.cache_window = current_window
        self._last_extra_seed = extra_seed
        return {"ok": True, "data": data, "cached": False}

    def get_all_items(self) -> List[Dict[str, Any]]:
        result = self.fetch_market_data()
        if result.get("ok") and result.get("data", {}).get("ok"):
            return result["data"].get("items", [])
        return []

    def filter_items(
        self,
        item_type: Optional[str] = None,
        rarity: Optional[str] = None,
        class_req: Optional[str] = None,
        max_price: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        items = self.get_all_items()
        filtered = []
        for item in items:
            if item_type and item.get("type", "").lower() != item_type.lower():
                continue
            if rarity and item.get("rarity", "").lower() != rarity.lower():
                continue
            if class_req:
                req = item.get("requirements") or {}
                if req.get("class", "").lower() != class_req.lower():
                    continue
            if max_price and item.get("marketPrice", 0) > max_price:
                continue
            filtered.append(item)
        return filtered

    def get_items_by_type(self) -> Dict[str, List[Dict[str, Any]]]:
        items = self.get_all_items()
        by_type: Dict[str, List[Dict[str, Any]]] = {}
        for item in items:
            t = item.get("type", "other")
            by_type.setdefault(t, []).append(item)
        return by_type


_market_api = MarketAPI()


def get_market_api() -> MarketAPI:
    return _market_api
