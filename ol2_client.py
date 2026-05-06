"""
Our Legacy 2 — Python API Client
Usage:
    from ol2_client import OL2Client
    client = OL2Client("ol2_your_key_here")
    state = client.game_state()
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


class OL2Error(Exception):
    """Raised when the OL2 API returns an error response."""
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


class OL2Client:
    """
    Client for the Our Legacy 2 JSON API.

    Args:
        api_key: Your OL2 API key (starts with ol2_).
        base_url: Base URL of the OL2 server. Defaults to the official server.
        timeout: Request timeout in seconds. Default 15.
        raise_on_error: If True, raise OL2Error when ok=False. Default False.
    """

    DEFAULT_BASE = "https://ol2.replit.app"

    def __init__(
        self,
        api_key: str,
        base_url: str = "",
        timeout: int = 15,
        raise_on_error: bool = False,
    ):
        self.api_key = api_key.strip()
        self.base_url = (base_url or self.DEFAULT_BASE).rstrip("/")
        self.timeout = timeout
        self.raise_on_error = raise_on_error

    # ─── Internal ────────────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        url = self.base_url + path
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result: Dict[str, Any] = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            try:
                result = json.loads(e.read())
            except Exception:
                result = {"ok": False, "message": f"HTTP {e.code}: {e.reason}", "status": e.code}
            if self.raise_on_error:
                raise OL2Error(result.get("message", str(e)), e.code) from e
            return result
        except urllib.error.URLError as e:
            if self.raise_on_error:
                raise OL2Error(f"Network error: {e.reason}") from e
            return {"ok": False, "message": f"Network error: {e.reason}"}

        if self.raise_on_error and not result.get("ok", True):
            raise OL2Error(result.get("message", "Unknown error"))
        return result

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        return self._request("GET", path, params=params)

    def _post(self, path: str, body: Optional[Dict] = None) -> Dict:
        return self._request("POST", path, body=body or {})

    def _delete(self, path: str) -> Dict:
        return self._request("DELETE", path)

    # ─── Keys ────────────────────────────────────────────────────────────────

    def list_scopes(self) -> Dict:
        """List all available API scopes and their descriptions."""
        return self._get("/api/keys/scopes")

    def create_key(self, name: str, scopes: Optional[List[str]] = None) -> Dict:
        """Create a new API key. Requires keys:manage scope."""
        return self._post("/api/keys", {"name": name, "scopes": scopes})

    def list_keys(self) -> List[Dict]:
        """List all API keys for this account."""
        result = self._get("/api/keys")
        return result.get("keys", [])

    def revoke_key(self, key_id: str) -> Dict:
        """Revoke an API key by its ID."""
        return self._delete(f"/api/keys/{key_id}")

    # ─── Game State ──────────────────────────────────────────────────────────

    def game_state(self) -> Dict:
        """Full game state: player, inventory, area, battle status, messages."""
        return self._get("/api/game/state")

    def battle_state(self) -> Dict:
        """Current battle state (enemy HP, log, etc.)."""
        return self._get("/api/battle/state")

    # ─── Actions ─────────────────────────────────────────────────────────────

    def explore(self) -> Dict:
        """Explore the current area. May trigger a battle or find loot."""
        return self._post("/api/action/explore")

    def travel(self, dest: str) -> Dict:
        """Travel to a connected area. Pass the area key (e.g. 'dark_forest')."""
        return self._post("/api/action/travel", {"dest": dest})

    def rest(self) -> Dict:
        """Rest at the current area (if a rest spot exists). Restores HP/MP."""
        return self._post("/api/action/rest")

    def mine(self) -> Dict:
        """Mine ore at the current area (requires pickaxe in inventory)."""
        return self._post("/api/action/mine")

    def buy(self, item: str) -> Dict:
        """Buy an item from the current area's shop."""
        return self._post("/api/action/buy", {"item": item})

    def sell(self, item: str) -> Dict:
        """Sell an item from your inventory."""
        return self._post("/api/action/sell", {"item": item})

    def equip(self, item: str) -> Dict:
        """Equip an item from your inventory."""
        return self._post("/api/action/equip", {"item": item})

    def unequip(self, slot: str) -> Dict:
        """Unequip an item from a slot (weapon, armor, accessory, etc.)."""
        return self._post("/api/action/unequip", {"slot": slot})

    def use_item(self, item: str) -> Dict:
        """Use a consumable item (Health Potion, Mana Potion, etc.)."""
        return self._post("/api/action/use_item", {"item": item})

    # ─── Battle ──────────────────────────────────────────────────────────────

    def battle_attack(self) -> Dict:
        """Attack the current enemy."""
        return self._post("/api/battle/attack")

    def battle_defend(self) -> Dict:
        """Defend (reduces damage taken this turn)."""
        return self._post("/api/battle/defend")

    def battle_flee(self) -> Dict:
        """Attempt to flee the battle (55% chance)."""
        return self._post("/api/battle/flee")

    def battle_spell(self, spell: str) -> Dict:
        """Cast a spell. Pass the spell name."""
        return self._post("/api/battle/spell", {"spell": spell})

    def battle_use_item(self, item: str) -> Dict:
        """Use an item during battle."""
        return self._post("/api/battle/use_item", {"item": item})

    # ─── Player ──────────────────────────────────────────────────────────────

    def player_profile(self) -> Dict:
        """Full player profile: stats, equipment, attributes, land, quests."""
        return self._get("/api/player/profile")

    def player_inventory(self) -> Dict:
        """Player inventory list."""
        return self._get("/api/player/inventory")

    def player_quests(self) -> Dict:
        """Active and completed missions/quests."""
        return self._get("/api/player/quests")

    def player_companions(self) -> Dict:
        """Hired companions with HP and stats."""
        return self._get("/api/player/companions")

    def player_land(self) -> Dict:
        """Land, housing buildings, and farm crop slots."""
        return self._get("/api/player/land")

    def player_weekly_challenges(self) -> Dict:
        """Current weekly challenges and progress."""
        return self._get("/api/player/challenges")

    # ─── Social ──────────────────────────────────────────────────────────────

    def chat_history(self, limit: int = 50) -> List[Dict]:
        """Recent global chat messages."""
        result = self._get("/api/social/chat", {"limit": limit})
        return result.get("messages", [])

    def chat_send(self, message: str) -> Dict:
        """Send a global chat message."""
        return self._post("/api/social/chat", {"message": message})

    def leaderboard(self) -> Dict:
        """Player and group leaderboards."""
        return self._get("/api/social/leaderboard")

    # ─── World ───────────────────────────────────────────────────────────────

    def world_areas(self) -> Dict:
        """All world areas with connections, difficulty, and features."""
        return self._get("/api/world/areas")

    def world_area(self, key: str) -> Dict:
        """Detail for a specific area by key."""
        return self._get(f"/api/world/area/{key}")

    def world_events(self) -> Dict:
        """Active and upcoming world events."""
        return self._get("/api/world/events")

    def world_challenges(self) -> Dict:
        """Current weekly challenges (public view)."""
        return self._get("/api/world/challenges")

    def world_weather(self, area_name: str = "") -> Dict:
        """Current weather for an area (optional)."""
        return self._get("/api/world/weather", {"area": area_name} if area_name else None)

    # ─── Catalog ─────────────────────────────────────────────────────────────

    def catalog_items(self, search: str = "", type_filter: str = "") -> Dict:
        """Search/browse all items in the game."""
        return self._get("/api/catalog/items", {"search": search or None, "type": type_filter or None})

    def catalog_item(self, name: str) -> Dict:
        """Get a specific item by exact name."""
        return self._get(f"/api/catalog/items/{urllib.parse.quote(name)}")

    def catalog_spells(self) -> Dict:
        """All available spells."""
        return self._get("/api/catalog/spells")

    def catalog_classes(self) -> Dict:
        """All character classes and their stats."""
        return self._get("/api/catalog/classes")

    def catalog_races(self) -> Dict:
        """All playable races and their bonuses."""
        return self._get("/api/catalog/races")

    def catalog_crafting(self) -> Dict:
        """All crafting recipes."""
        return self._get("/api/catalog/crafting")

    def catalog_shops(self) -> Dict:
        """All shop inventories by area."""
        return self._get("/api/catalog/shops")

    def catalog_companions(self) -> Dict:
        """All available companions for hire."""
        return self._get("/api/catalog/companions")

    def catalog_enemies(self) -> Dict:
        """All enemies."""
        return self._get("/api/catalog/enemies")

    def catalog_bosses(self) -> Dict:
        """All boss encounters."""
        return self._get("/api/catalog/bosses")

    def catalog_housing(self) -> Dict:
        """All housing/building types."""
        return self._get("/api/catalog/housing")

    def catalog_farming(self) -> Dict:
        """All farmable crops."""
        return self._get("/api/catalog/farming")

    # ─── Convenience ─────────────────────────────────────────────────────────

    def auto_battle(self, prefer_spell: Optional[str] = None) -> List[Dict]:
        """
        Fight until battle ends (victory, defeat, or max 30 rounds).
        Returns list of battle result dicts.
        """
        results = []
        for _ in range(30):
            if prefer_spell:
                r = self.battle_spell(prefer_spell)
                if r.get("ok") is False and "scope" not in r.get("message", ""):
                    r = self.battle_attack()
            else:
                r = self.battle_attack()
            results.append(r)
            outcome = r.get("outcome", "ongoing")
            if outcome in ("victory", "defeat", "fled"):
                break
        return results

    def safe_explore(self) -> Dict:
        """
        Explore until a non-battle event occurs or a battle starts.
        Returns the explore result (may include battle info).
        """
        return self.explore()

    def __repr__(self) -> str:
        masked = self.api_key[:8] + "..." if len(self.api_key) > 8 else "?"
        return f"OL2Client(key={masked}, base={self.base_url})"
