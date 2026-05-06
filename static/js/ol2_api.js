/**
 * Our Legacy 2 — JavaScript API Client
 *
 * Usage (ES Module):
 *   import { OL2Client } from './ol2_api.js';
 *   const client = new OL2Client('ol2_your_key_here');
 *   const state = await client.gameState();
 *
 * Usage (Browser script tag — exposes window.OL2Client):
 *   <script src="/static/js/ol2_api.js"></script>
 */

class OL2Error extends Error {
  constructor(message, status = 0, data = {}) {
    super(message);
    this.name = 'OL2Error';
    this.status = status;
    this.data = data;
  }
}

class OL2Client {
  /**
   * @param {string} apiKey  - Your ol2_ API key
   * @param {object} opts
   * @param {string}  opts.baseUrl       - Override server URL (default: current origin)
   * @param {number}  opts.timeout       - Fetch timeout ms (default: 15000)
   * @param {boolean} opts.raiseOnError  - Throw OL2Error when ok=false (default: false)
   */
  constructor(apiKey, opts = {}) {
    this.apiKey = (apiKey || '').trim();
    this.baseUrl = (opts.baseUrl || '').replace(/\/$/, '');
    this.timeout = opts.timeout || 15000;
    this.raiseOnError = opts.raiseOnError || false;
  }

  // ── Internal ──────────────────────────────────────────────────────────────

  async _request(method, path, body = null, params = null) {
    let url = this.baseUrl + path;
    if (params) {
      const qs = Object.entries(params)
        .filter(([, v]) => v != null)
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
        .join('&');
      if (qs) url += '?' + qs;
    }
    const headers = { 'X-API-Key': this.apiKey, 'Content-Type': 'application/json', 'Accept': 'application/json' };
    const init = { method: method.toUpperCase(), headers, credentials: 'include' };
    if (body !== null) init.body = JSON.stringify(body);

    const ctrl = new AbortController();
    const tid = setTimeout(() => ctrl.abort(), this.timeout);
    init.signal = ctrl.signal;

    let resp, data;
    try {
      resp = await fetch(url, init);
      data = await resp.json();
    } catch (e) {
      clearTimeout(tid);
      if (this.raiseOnError) throw new OL2Error('Network error: ' + e.message);
      return { ok: false, message: 'Network error: ' + e.message };
    }
    clearTimeout(tid);

    if (this.raiseOnError && data && data.ok === false)
      throw new OL2Error(data.message || 'API error', resp.status, data);
    return data;
  }

  _get(path, params) { return this._request('GET', path, null, params); }
  _post(path, body)  { return this._request('POST', path, body || {}); }
  _del(path)         { return this._request('DELETE', path); }

  // ── Keys ──────────────────────────────────────────────────────────────────

  /** List all available API scopes (no auth needed). */
  listScopes() { return this._get('/api/keys/scopes'); }

  /** Create a new API key. Requires keys:manage scope. */
  createKey(name, scopes) { return this._post('/api/keys', { name, scopes }); }

  /** List all API keys for the authenticated account. */
  listKeys() { return this._get('/api/keys').then(r => r.keys || []); }

  /** Revoke a key by ID. */
  revokeKey(keyId) { return this._del(`/api/keys/${keyId}`); }

  // ── Game State ────────────────────────────────────────────────────────────

  /** Full game state: player, inventory, area, battle status. */
  gameState() { return this._get('/api/game/state'); }

  /** Current battle state (enemy HP, combat log). */
  battleState() { return this._get('/api/battle/state'); }

  // ── Actions ───────────────────────────────────────────────────────────────

  /** Explore the current area. May trigger a battle or find loot. */
  explore() { return this._post('/api/action/explore'); }

  /** Travel to a connected area by key (e.g. 'dark_forest'). */
  travel(dest) { return this._post('/api/action/travel', { dest }); }

  /** Rest at the current location. Restores HP/MP. */
  rest() { return this._post('/api/action/rest'); }

  /** Mine ore (requires pickaxe). */
  mine() { return this._post('/api/action/mine'); }

  /** Buy an item from the area shop. */
  buy(item) { return this._post('/api/action/buy', { item }); }

  /** Sell an item from inventory. */
  sell(item) { return this._post('/api/action/sell', { item }); }

  /** Equip an item from inventory. */
  equip(item) { return this._post('/api/action/equip', { item }); }

  /** Unequip from a slot (weapon, armor, accessory, etc.). */
  unequip(slot) { return this._post('/api/action/unequip', { slot }); }

  /** Use a consumable item (Health Potion, Mana Potion, etc.). */
  useItem(item) { return this._post('/api/action/use_item', { item }); }

  // ── Battle ────────────────────────────────────────────────────────────────

  /** Attack the current enemy. */
  battleAttack() { return this._post('/api/battle/attack'); }

  /** Defend (reduces damage this turn). */
  battleDefend() { return this._post('/api/battle/defend'); }

  /** Attempt to flee (55% chance). */
  battleFlee() { return this._post('/api/battle/flee'); }

  /** Cast a spell by name. */
  battleSpell(spell) { return this._post('/api/battle/spell', { spell }); }

  /** Use an item during battle. */
  battleUseItem(item) { return this._post('/api/battle/use_item', { item }); }

  // ── Player ────────────────────────────────────────────────────────────────

  /** Full player profile (stats, equipment, attributes, land, quests). */
  playerProfile() { return this._get('/api/player/profile'); }

  /** Player inventory list. */
  playerInventory() { return this._get('/api/player/inventory'); }

  /** Active and completed missions. */
  playerQuests() { return this._get('/api/player/quests'); }

  /** Hired companions with HP and stats. */
  playerCompanions() { return this._get('/api/player/companions'); }

  /** Land, housing buildings, and farm crop slots. */
  playerLand() { return this._get('/api/player/land'); }

  /** Current weekly challenge progress. */
  playerChallenges() { return this._get('/api/player/challenges'); }

  // ── Social ────────────────────────────────────────────────────────────────

  /** Recent global chat messages. */
  chatHistory(limit = 50) { return this._get('/api/social/chat', { limit }); }

  /** Send a global chat message. */
  chatSend(message) { return this._post('/api/social/chat', { message }); }

  /** Player and group leaderboards. */
  leaderboard() { return this._get('/api/social/leaderboard'); }

  // ── World ─────────────────────────────────────────────────────────────────

  /** All world areas with connections, difficulty, and features. */
  worldAreas() { return this._get('/api/world/areas'); }

  /** Detail for a specific area by key. */
  worldArea(key) { return this._get(`/api/world/area/${encodeURIComponent(key)}`); }

  /** Active and upcoming world events. */
  worldEvents() { return this._get('/api/world/events'); }

  /** Current weekly challenges (public). */
  worldChallenges() { return this._get('/api/world/challenges'); }

  /** Weather for an area (pass area name or leave blank). */
  worldWeather(areaName = '') { return this._get('/api/world/weather', areaName ? { area: areaName } : null); }

  // ── Catalog ───────────────────────────────────────────────────────────────

  /** Search/browse all game items. */
  catalogItems(search = '', typeFilter = '') {
    return this._get('/api/catalog/items', { search: search || null, type: typeFilter || null });
  }

  /** Get a specific item by exact name. */
  catalogItem(name) { return this._get(`/api/catalog/items/${encodeURIComponent(name)}`); }

  /** All available spells. */
  catalogSpells() { return this._get('/api/catalog/spells'); }

  /** All character classes. */
  catalogClasses() { return this._get('/api/catalog/classes'); }

  /** All playable races. */
  catalogRaces() { return this._get('/api/catalog/races'); }

  /** All crafting recipes. */
  catalogCrafting() { return this._get('/api/catalog/crafting'); }

  /** Shop inventories by area. */
  catalogShops() { return this._get('/api/catalog/shops'); }

  /** All companions available for hire. */
  catalogCompanions() { return this._get('/api/catalog/companions'); }

  /** All enemies. */
  catalogEnemies() { return this._get('/api/catalog/enemies'); }

  /** All bosses. */
  catalogBosses() { return this._get('/api/catalog/bosses'); }

  /** All housing/building types. */
  catalogHousing() { return this._get('/api/catalog/housing'); }

  /** All farmable crops. */
  catalogFarming() { return this._get('/api/catalog/farming'); }

  // ── Convenience ───────────────────────────────────────────────────────────

  /**
   * Fight until battle ends (victory/defeat/fled) or maxRounds.
   * @param {object} opts
   * @param {string} opts.preferSpell  - Spell name to try first each round
   * @param {number} opts.maxRounds    - Max rounds (default 30)
   * @returns {Promise<Array>}
   */
  async autoBattle({ preferSpell = null, maxRounds = 30 } = {}) {
    const results = [];
    for (let i = 0; i < maxRounds; i++) {
      let r;
      if (preferSpell) {
        r = await this.battleSpell(preferSpell);
        if (!r.ok && r.message && r.message.includes('scope')) break;
        if (!r.ok) r = await this.battleAttack();
      } else {
        r = await this.battleAttack();
      }
      results.push(r);
      const outcome = r.outcome || 'ongoing';
      if (outcome === 'victory' || outcome === 'defeat' || outcome === 'fled') break;
    }
    return results;
  }
}

// Browser global export
if (typeof window !== 'undefined') {
  window.OL2Client = OL2Client;
  window.OL2Error = OL2Error;
}

// ES module export
export { OL2Client, OL2Error };
