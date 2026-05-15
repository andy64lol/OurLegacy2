const BASE = ''

async function req(method, path, body) {
  const opts = {
    method,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
  }
  if (body !== undefined) opts.body = JSON.stringify(body)
  const res = await fetch(BASE + path, opts)
  if (res.status === 204) return { ok: true }
  const data = await res.json().catch(() => ({ ok: false, message: 'Parse error' }))
  return data
}

const get = (path) => req('GET', path)
const post = (path, body) => req('POST', path, body)

export const api = {
  // Auth
  sessionCheck: () => get('/api/session/check'),
  login: (b) => post('/api/online/login', b),
  register: (b) => post('/api/online/register', b),
  logout: () => post('/api/online/logout', {}),
  localLogin: (b) => post('/api/login', b),

  // Game state
  gameState: () => get('/api/game/state'),
  battleState: () => get('/api/battle/state'),
  playerProfile: () => get('/api/player/profile'),
  playerQuests: () => get('/api/player/quests'),
  playerCompanions: () => get('/api/player/companions'),
  playerLand: () => get('/api/player/land'),
  playerChallenges: () => get('/api/player/challenges'),
  playerStats: () => get('/api/player_stats'),

  // World
  worldAreas: () => get('/api/world/areas'),
  worldArea: (k) => get(`/api/world/area/${k}`),
  worldEvents: () => get('/api/world/events'),
  worldChallenges: () => get('/api/world/challenges'),
  worldWeather: () => get('/api/world/weather'),

  // Actions
  explore: () => post('/api/action/explore', {}),
  travel: (dest) => post('/api/action/travel', { dest }),
  rest: () => post('/api/action/rest', {}),
  mine: () => post('/api/action/mine', {}),
  buy: (item_name, shop_key) => post('/api/action/buy', { item_name, shop_key }),
  sell: (item_name) => post('/api/action/sell', { item_name }),
  equip: (item_name) => post('/api/action/equip', { item_name }),
  unequip: (slot) => post('/api/action/unequip', { slot }),
  useItem: (item_name) => post('/api/action/use_item', { item_name }),

  // New API endpoints
  craft: (recipe_id) => post('/api/action/craft', { recipe_id }),
  hireCmp: (companion_id) => post('/api/action/hire_companion', { companion_id }),
  dismissCmp: (companion_id) => post('/api/action/dismiss_companion', { companion_id }),
  completeMission: (mission_id) => post('/api/action/complete_mission', { mission_id }),
  claimChallenge: (challenge_id) => post('/api/action/claim_challenge', { challenge_id }),
  quickHeal: () => post('/api/action/quick_heal', {}),
  sortInventory: () => post('/api/action/sort_inventory', {}),
  autoEquip: () => post('/api/action/auto_equip', {}),
  challengeBoss: (boss_key) => post('/api/action/challenge_boss', { boss_key }),
  spendAttrPoint: (attr) => post('/api/spend_attr_point', { attribute: attr }),
  dismissCutscene: () => post('/api/dismiss_cutscene', {}),

  // Dungeon
  dungeonEnter: (dungeon_id) => post('/api/dungeon/enter', { dungeon_id }),
  dungeonRoom: () => get('/api/dungeon/room'),
  dungeonProceed: () => post('/api/dungeon/proceed', {}),
  dungeonAnswer: (answer) => post('/api/dungeon/answer', { answer }),
  dungeonChoose: (choice) => post('/api/dungeon/choose', { choice }),
  dungeonComplete: () => post('/api/dungeon/complete', {}),
  dungeonAbandon: () => post('/api/dungeon/abandon', {}),

  // Battle
  battleAttack: () => post('/api/battle/attack', {}),
  battleDefend: () => post('/api/battle/defend', {}),
  battleFlee: () => post('/api/battle/flee', {}),
  battleSpell: (spell_name) => post('/api/battle/spell', { spell_name }),
  battleUseItem: (item_name) => post('/api/battle/use_item', { item_name }),

  // Market
  marketData: () => get('/api/market_data'),
  marketBuy: (item_name) => post('/api/action/market/buy', { item_name }),
  marketReset: () => post('/api/action/market/reset', {}),

  // Save/Load
  serverSave: () => post('/api/server_save', {}),
  serverSaves: () => get('/api/server_saves'),
  serverLoad: (slot) => post('/api/server_load', { slot }),
  cloudSave: () => post('/api/online/cloud_save', {}),
  cloudLoad: () => post('/api/online/cloud_load', {}),
  cloudMeta: () => get('/api/online/cloud_meta'),
  autosave: () => post('/api/online/autosave', {}),

  // Friends & Social
  friends: () => get('/api/friends'),
  friendRequest: (target) => post('/api/friends/request', { target }),
  friendRespond: (requester, action) => post('/api/friends/respond', { requester, action }),
  friendRemove: (target) => post('/api/friends/remove', { target }),
  dmGet: (other) => get(`/api/dm/${other}`),
  dmSend: (to, message) => post('/api/dm/send', { to, message }),
  dmUnread: () => get('/api/dm/unread'),
  block: (target, action) => post('/api/block', { target, action }),
  blockList: () => get('/api/block/list'),

  // Groups
  groupMy: () => get('/api/groups/my'),
  groupCreate: (name) => post('/api/groups/create', { name }),
  groupJoin: (name) => post('/api/groups/join', { name }),
  groupLeave: () => post('/api/groups/leave', {}),
  groupKick: (username) => post('/api/groups/kick', { username }),
  groupCollect: () => post('/api/groups/collect_gold', {}),

  // Leaderboard & Chat
  leaderboard: () => get('/api/social/leaderboard'),
  chatHistory: () => get('/api/social/chat'),
  announcements: () => get('/api/announcements'),
  areaActivity: () => get('/api/area_activity'),

  // Catalog
  catalogItems: () => get('/api/catalog/items'),
  catalogSpells: () => get('/api/catalog/spells'),
  catalogClasses: () => get('/api/catalog/classes'),
  catalogRaces: () => get('/api/catalog/races'),
  catalogCrafting: () => get('/api/catalog/crafting'),
  catalogShops: () => get('/api/catalog/shops'),
  catalogCompanions: () => get('/api/catalog/companions'),
  catalogEnemies: () => get('/api/catalog/enemies'),
  catalogBosses: () => get('/api/catalog/bosses'),
  catalogHousing: () => get('/api/catalog/housing'),
  catalogFarming: () => get('/api/catalog/farming'),

  // Admin
  adminStatus: () => get('/api/admin/status'),
  adminData: () => get('/api/admin/data'),
  adminBan: (b) => post('/api/admin/ban', b),
  adminUnban: (b) => post('/api/admin/unban', b),
  adminMute: (b) => post('/api/admin/mute', b),
  adminUnmute: (b) => post('/api/admin/unmute', b),
  adminKick: (b) => post('/api/admin/kick', b),
  adminWarn: (b) => post('/api/admin/warn', b),
  adminGameStats: (u) => get(`/api/admin/game/stats?username=${u}`),
  adminGameGive: (b) => post('/api/admin/game/give', b),
  adminGameSet: (b) => post('/api/admin/game/set', b),
  adminGameHeal: (b) => post('/api/admin/game/heal', b),

  // Profile / online
  setEmail: (email) => post('/api/online/set_email', { email }),
  forgotPassword: (email) => post('/api/online/forgot-password', { email }),
  resetPassword: (b) => post('/api/online/reset-password', b),
  profile: (b) => post('/api/online/profile', b),
  newGame: (b) => post('/api/online/profile', b),
}
