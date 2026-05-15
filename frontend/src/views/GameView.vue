<template>
  <div class="game-page">
    <!-- Left sidebar: player stats -->
    <aside class="sidebar">
      <PlayerStats v-if="game.player" :p="game.player" />

      <!-- Battle warning -->
      <div v-if="game.inBattle" class="battle-warning" @click="router.push('/battle')">
        ⚔ IN BATTLE — Click to fight!
      </div>

      <!-- Area info -->
      <div class="area-block" v-if="game.area">
        <div class="area-name text-gold">📍 {{ game.area.name }}</div>
        <div class="area-desc text-dim">{{ game.area.description }}</div>
        <div class="area-meta">
          <span v-if="game.area.has_shop" class="tag tag-gold">🏪 Shop</span>
          <span v-if="game.area.has_mine" class="tag tag-gold">⛏ Mine</span>
          <span v-if="game.area.can_rest" class="tag tag-gold">🛏 Inn</span>
          <span class="tag" style="background:var(--bg-panel-dark);border:1px solid var(--border)">Diff. {{ game.area.difficulty }}</span>
        </div>
      </div>

      <!-- Equipment -->
      <div class="panel equip-panel" v-if="game.player?.equipment">
        <div class="panel-title">Equipment</div>
        <div v-for="(item, slot) in game.player.equipment" :key="slot" class="equip-row">
          <span class="equip-slot text-dim">{{ slot }}</span>
          <span class="equip-item text-gold" v-if="item">{{ item }}</span>
          <span class="equip-item text-dim" v-else>—</span>
          <button v-if="item" class="btn btn-sm" @click="unequip(slot)" :disabled="loading">✕</button>
        </div>
      </div>

      <!-- Attribute points -->
      <div class="panel" v-if="game.player?.attr_points > 0">
        <div class="panel-title text-gold">⬆ {{ game.player.attr_points }} Attribute Points</div>
        <div class="attr-btns">
          <button v-for="a in attrList" :key="a.key" class="btn btn-sm btn-gold" @click="spendAttr(a.key)" :disabled="loading">
            +{{ a.label }}
          </button>
        </div>
      </div>

      <!-- Weather -->
      <div class="panel" v-if="weather">
        <div class="text-dim" style="font-size:0.8rem">🌤 {{ weather.current?.name || weather.name }} — {{ weather.current?.effect || weather.effect }}</div>
      </div>
    </aside>

    <!-- Main content -->
    <main class="game-main">
      <!-- Tab bar -->
      <div class="tab-bar scroll-x">
        <button v-for="t in tabs" :key="t.id" class="tab-btn" :class="{ active: activeTab === t.id }" @click="activeTab = t.id">
          {{ t.icon }} {{ t.label }}
        </button>
      </div>

      <!-- === EXPLORE TAB === -->
      <div v-if="activeTab === 'explore'" class="tab-content">
        <div class="action-group panel">
          <div class="panel-title">Actions</div>
          <div class="action-grid-main">
            <button class="btn btn-gold action-btn" @click="explore" :disabled="loading || game.inBattle">
              🗺 Explore
            </button>
            <button class="btn action-btn" @click="rest" :disabled="loading || game.inBattle || !game.area?.can_rest">
              🛏 Rest <span class="text-dim" v-if="game.area?.rest_cost">({{ game.area.rest_cost }}g)</span>
            </button>
            <button class="btn action-btn" @click="mine" :disabled="loading || game.inBattle || !game.area?.has_mine">
              ⛏ Mine
            </button>
            <button class="btn action-btn" @click="quickHeal" :disabled="loading || game.inBattle">
              💊 Quick Heal
            </button>
          </div>
          <div v-if="game.inBattle" class="battle-cta" @click="router.push('/battle')">
            ⚔ You are in combat! Click here to fight →
          </div>
        </div>

        <!-- World events -->
        <div class="panel" v-if="worldEvents.length">
          <div class="panel-title">World Events</div>
          <div class="events-list">
            <div v-for="(e, i) in worldEvents.slice(0, 8)" :key="i" class="event-line text-dim">
              <span class="event-time">{{ formatTime(e.t) }}</span> {{ e.msg }}
            </div>
          </div>
        </div>

        <!-- Message log -->
        <div class="panel msg-log-panel">
          <div class="panel-title">Activity Log</div>
          <div class="msg-log scroll-y" ref="logEl">
            <div v-for="(m, i) in game.messages" :key="i" class="msg-line">{{ m }}</div>
            <div v-if="!game.messages.length" class="text-dim">No recent activity.</div>
          </div>
        </div>
      </div>

      <!-- === TRAVEL TAB === -->
      <div v-if="activeTab === 'travel'" class="tab-content">
        <div class="panel">
          <div class="panel-title">Travel — {{ game.area?.name }}</div>
          <div v-if="!game.area?.connections?.length" class="text-dim">No destinations from here.</div>
          <div class="travel-grid">
            <div v-for="dest in travelDests" :key="dest.key" class="dest-card panel">
              <div class="dest-name text-gold">{{ dest.name }}</div>
              <div class="dest-desc text-dim">{{ dest.description }}</div>
              <div class="dest-meta">
                <span v-if="dest.has_shop" class="tag tag-gold">🏪</span>
                <span v-if="dest.has_mine" class="tag tag-gold">⛏</span>
                <span v-if="dest.can_rest" class="tag tag-gold">🛏</span>
                <span class="tag tag-gold">Diff.{{ dest.difficulty }}</span>
              </div>
              <button class="btn btn-gold btn-sm" @click="travel(dest.key)" :disabled="loading || game.inBattle">
                Travel →
              </button>
            </div>
          </div>
        </div>
        <div class="panel mt-1" v-if="visitedAreas.length">
          <div class="panel-title">Visited Areas ({{ visitedAreas.length }})</div>
          <div class="visited-list">
            <span v-for="a in visitedAreas" :key="a" class="visited-tag">{{ a }}</span>
          </div>
        </div>
      </div>

      <!-- === INVENTORY TAB === -->
      <div v-if="activeTab === 'inventory'" class="tab-content">
        <div class="panel">
          <div class="panel-title">
            Inventory ({{ game.inventory?.length || 0 }} items)
            <div class="inv-actions-header">
              <button class="btn btn-sm" @click="sortInventory" :disabled="loading">Sort</button>
              <button class="btn btn-sm btn-gold" @click="autoEquip" :disabled="loading">Auto-Equip</button>
            </div>
          </div>
          <div v-if="!game.inventory?.length" class="text-dim">Inventory is empty.</div>
          <div class="inv-grid">
            <div v-for="(item, i) in game.inventory" :key="i" class="inv-item">
              <span class="item-name">{{ item }}</span>
              <div class="item-actions">
                <button class="btn btn-sm" @click="equipItem(item)" :disabled="loading" title="Equip">E</button>
                <button class="btn btn-sm" @click="useItem(item)" :disabled="loading" title="Use">U</button>
                <button class="btn btn-sm btn-red" @click="sellItem(item)" :disabled="loading" title="Sell">$</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- === SHOP TAB === -->
      <div v-if="activeTab === 'shop'" class="tab-content">
        <div v-if="!game.area?.has_shop" class="panel text-dim">No shop in this area.</div>
        <template v-else>
          <div class="panel">
            <div class="panel-title">🏪 Shop — {{ game.player?.gold }}g available</div>
            <div v-if="!shopItems.length" class="text-dim">Loading shop…</div>
            <div class="shop-grid">
              <div v-for="item in shopItems" :key="item.name" class="shop-item panel">
                <div class="shop-item-name text-gold">{{ item.name }}</div>
                <div class="shop-item-desc text-dim">{{ item.description }}</div>
                <div class="shop-item-stats text-dim" v-if="item.attack || item.defense">
                  <span v-if="item.attack">ATK+{{ item.attack }}</span>
                  <span v-if="item.defense">DEF+{{ item.defense }}</span>
                  <span v-if="item.hp_bonus">HP+{{ item.hp_bonus }}</span>
                </div>
                <div class="shop-item-footer">
                  <span class="text-gold">{{ item.price }}g</span>
                  <button class="btn btn-sm btn-gold" @click="buyItem(item.name)" :disabled="loading || (game.player?.gold || 0) < item.price">
                    Buy
                  </button>
                </div>
              </div>
            </div>
          </div>
          <!-- Sell panel -->
          <div class="panel mt-1">
            <div class="panel-title">Sell Items</div>
            <div class="inv-grid">
              <div v-for="item in game.inventory" :key="item" class="inv-item">
                <span class="item-name">{{ item }}</span>
                <button class="btn btn-sm btn-gold" @click="sellItem(item)" :disabled="loading">Sell</button>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- === QUESTS TAB === -->
      <div v-if="activeTab === 'quests'" class="tab-content">
        <div class="panel">
          <div class="panel-title">Active Quests</div>
          <div v-if="!quests.active?.length" class="text-dim">No active quests.</div>
          <div v-for="q in quests.active" :key="q.id" class="quest-card">
            <div class="quest-name text-gold">{{ q.name }}</div>
            <div class="quest-progress text-dim">Progress: {{ JSON.stringify(q.progress) }}</div>
            <button class="btn btn-sm btn-gold" @click="completeMission(q.id)" :disabled="loading">Complete</button>
          </div>
        </div>

        <!-- All available missions -->
        <div class="panel mt-1">
          <div class="panel-title">Available Missions</div>
          <div v-if="!allMissions.length" class="text-dim">Loading missions…</div>
          <div class="mission-list">
            <div v-for="(m, id) in allMissionsObj" :key="id" class="mission-card">
              <div class="mission-name text-gold">{{ m.name }}</div>
              <div class="mission-desc text-dim">{{ m.description }}</div>
              <div class="mission-rewards">
                <span class="text-gold" v-if="m.experience_reward || m.reward?.experience">+{{ m.experience_reward || m.reward?.experience }}xp</span>
                <span class="text-gold" v-if="m.gold_reward || m.reward?.gold"> +{{ m.gold_reward || m.reward?.gold }}g</span>
              </div>
              <span v-if="isCompleted(id)" class="text-dim">✓ Completed</span>
              <button v-else class="btn btn-sm btn-gold" @click="completeMission(id)" :disabled="loading">Complete</button>
            </div>
          </div>
        </div>

        <div class="panel mt-1">
          <div class="panel-title">Completed ({{ quests.completed?.length || 0 }})</div>
          <div class="completed-list">
            <span v-for="q in quests.completed" :key="q.id" class="completed-tag text-dim">✓ {{ q.name }}</span>
          </div>
        </div>
      </div>

      <!-- === CHALLENGES TAB === -->
      <div v-if="activeTab === 'challenges'" class="tab-content">
        <div class="panel">
          <div class="panel-title">Weekly Challenges</div>
          <div v-if="!challenges.length" class="text-dim">Loading challenges…</div>
          <div v-for="ch in challenges" :key="ch.id" class="challenge-card">
            <div class="ch-name text-gold">{{ ch.name }}</div>
            <div class="ch-desc text-dim">{{ ch.description }}</div>
            <div class="ch-progress">
              <div class="bar-wrap"><div class="bar-fill bar-xp" :style="{ width: Math.min(100, (ch.progress / ch.target) * 100) + '%' }"></div></div>
              <span class="text-dim">{{ ch.progress }}/{{ ch.target }}</span>
            </div>
            <div class="ch-rewards text-gold">+{{ ch.reward_exp }}xp +{{ ch.reward_gold }}g</div>
            <button v-if="ch.progress >= ch.target && !ch.claimed" class="btn btn-sm btn-gold" @click="claimChallenge(ch.id)" :disabled="loading">Claim!</button>
            <span v-else-if="ch.claimed" class="text-dim">✓ Claimed</span>
          </div>
        </div>
      </div>

      <!-- === CRAFTING TAB === -->
      <div v-if="activeTab === 'crafting'" class="tab-content">
        <div class="panel">
          <div class="panel-title">🔨 Crafting</div>
          <div v-if="!recipes.length" class="text-dim">Loading recipes…</div>
          <div class="recipe-grid">
            <div v-for="r in recipes" :key="r.id" class="recipe-card panel">
              <div class="recipe-name text-gold">{{ r.result }}</div>
              <div class="recipe-ingredients text-dim">
                <span v-for="(qty, mat) in r.ingredients" :key="mat">{{ mat }} ×{{ qty }} </span>
              </div>
              <button class="btn btn-sm btn-gold" @click="craft(r.id)" :disabled="loading">Craft</button>
            </div>
          </div>
        </div>
      </div>

      <!-- === COMPANIONS TAB === -->
      <div v-if="activeTab === 'companions'" class="tab-content">
        <div class="panel">
          <div class="panel-title">Party Members</div>
          <div v-if="!companions.length" class="text-dim">No companions hired.</div>
          <div v-for="c in companions" :key="c.key" class="companion-card">
            <div class="comp-name text-gold">{{ c.name }}</div>
            <div class="comp-class text-dim">{{ c.class }}</div>
            <div class="bar-row">
              <span class="text-red">HP</span>
              <div class="bar-wrap"><div class="bar-fill bar-hp" :style="{ width: pct(c.hp, c.max_hp) }"></div></div>
              <span class="text-red">{{ c.hp }}/{{ c.max_hp }}</span>
            </div>
            <button class="btn btn-sm btn-red" @click="dismissCompanion(c.key)" :disabled="loading">Dismiss</button>
          </div>
        </div>

        <div class="panel mt-1" v-if="game.area?.key === 'tavern'">
          <div class="panel-title">Hire Companions (at Tavern)</div>
          <div class="hire-grid">
            <div v-for="(c, key) in availableCompanions" :key="key" class="hire-card panel">
              <div class="hire-name text-gold">{{ c.name }}</div>
              <div class="hire-class text-dim">{{ c.class }}</div>
              <div class="hire-stats text-dim">HP {{ c.hp }} | ATK {{ c.attack }}</div>
              <div class="hire-price text-gold">{{ c.price || c.cost }}g</div>
              <button class="btn btn-sm btn-gold" @click="hireCompanion(key)" :disabled="loading">Hire</button>
            </div>
          </div>
        </div>
        <div v-else-if="!companions.length" class="text-dim panel">Travel to the Tavern to hire companions.</div>
      </div>

      <!-- === DUNGEONS TAB === -->
      <div v-if="activeTab === 'dungeons'" class="tab-content">
        <div class="panel">
          <div class="panel-title">🗝 Dungeons</div>
          <p class="text-dim">Enter a dungeon for multi-room challenges with unique rewards.</p>
          <router-link to="/dungeon" class="btn btn-gold mt-2">Open Dungeon Map →</router-link>
        </div>
      </div>

      <!-- === SPELLS TAB === -->
      <div v-if="activeTab === 'spells'" class="tab-content">
        <div class="panel">
          <div class="panel-title">✨ Spellbook</div>
          <div class="text-dim" style="font-size:0.82rem;margin-bottom:0.5rem">Spells are used during battle. MP: {{ game.player?.mp }}/{{ game.player?.max_mp }}</div>
          <div v-if="!spells.length" class="text-dim">Loading spells…</div>
          <div class="spell-grid">
            <div v-for="sp in spells" :key="sp.name" class="spell-card panel">
              <div class="spell-name text-gold">{{ sp.name }}</div>
              <div class="spell-cost text-mana">{{ sp.cost }} MP</div>
              <div class="spell-desc text-dim">{{ sp.description }}</div>
              <div class="spell-stats text-dim">
                <span v-if="sp.damage">DMG {{ sp.damage }}</span>
                <span v-if="sp.heal">HEAL {{ sp.heal }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- === LAND TAB === -->
      <div v-if="activeTab === 'land'" class="tab-content">
        <div class="panel">
          <div class="panel-title">🏡 Your Land</div>
          <div class="text-dim" v-if="!landData">Loading land…</div>
          <template v-else>
            <div class="land-stats">
              <span class="text-gold">Plots: {{ game.player?.land_plots || 0 }}</span>
            </div>
            <div v-if="landData.buildings?.length" class="buildings-list mt-1">
              <div class="section-label text-dim">Buildings</div>
              <div v-for="b in landData.buildings" :key="b.slot" class="building-row">
                <span class="text-gold">{{ b.name }}</span> <span class="text-dim">Slot {{ b.slot }}</span>
              </div>
            </div>
            <div v-if="landData.crops?.length" class="crops-list mt-1">
              <div class="section-label text-dim">Farm Plots</div>
              <div v-for="crop in landData.crops" :key="crop.slot" class="crop-row">
                <span>{{ crop.slot }}: </span>
                <span class="text-gold" v-if="crop.crop">{{ crop.crop }}</span>
                <span class="text-dim" v-else>Empty</span>
                <span v-if="crop.ready" class="text-green"> (Ready!)</span>
              </div>
            </div>
            <div v-if="!landData.buildings?.length && !landData.crops?.length" class="text-dim">No buildings or crops yet.</div>
          </template>
        </div>
      </div>

      <!-- === CHAT TAB === -->
      <div v-if="activeTab === 'chat'" class="tab-content chat-tab">
        <div class="panel chat-panel">
          <div class="panel-title">💬 World Chat <span class="online-count text-dim">({{ onlineUsers.length }} online)</span></div>
          <div class="chat-messages scroll-y" ref="chatEl">
            <div v-for="(m, i) in chatMessages" :key="i" class="chat-msg" :class="{ 'sys-msg': m.is_system, 'my-msg': m.username === myName }">
              <span class="chat-user" :class="m.is_mod ? 'text-gold' : 'text-dim'">[{{ m.username }}]</span>
              <span class="chat-text">{{ m.message }}</span>
            </div>
          </div>
          <div class="chat-input-row">
            <input v-model="chatMsg" placeholder="Say something… (/me /help /mods)" maxlength="200" @keydown.enter="sendChat" :disabled="!socketConnected" />
            <button class="btn btn-sm btn-gold" @click="sendChat" :disabled="!socketConnected || !chatMsg.trim()">Send</button>
          </div>
          <div v-if="chatError" class="chat-error text-red">{{ chatError }}</div>
          <div class="online-list" v-if="onlineUsers.length">
            <span class="text-dim" style="font-size:0.75rem">Online: </span>
            <span v-for="u in onlineUsers" :key="u" class="online-name">{{ u }}</span>
          </div>
        </div>
      </div>

    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'
import { useGameStore } from '@/stores/game.js'
import { api } from '@/api/index.js'
import PlayerStats from '@/components/PlayerStats.vue'
import { io } from 'socket.io-client'

const auth = useAuthStore()
const game = useGameStore()
const router = useRouter()

const loading = ref(false)
const logEl = ref(null)
const chatEl = ref(null)
const myName = auth.user?.username

const tabs = [
  { id: 'explore', icon: '🗺', label: 'Explore' },
  { id: 'travel', icon: '✈', label: 'Travel' },
  { id: 'inventory', icon: '🎒', label: 'Inventory' },
  { id: 'shop', icon: '🏪', label: 'Shop' },
  { id: 'quests', icon: '📜', label: 'Quests' },
  { id: 'challenges', icon: '🏆', label: 'Challenges' },
  { id: 'crafting', icon: '🔨', label: 'Crafting' },
  { id: 'companions', icon: '👥', label: 'Party' },
  { id: 'dungeons', icon: '🗝', label: 'Dungeons' },
  { id: 'spells', icon: '✨', label: 'Spells' },
  { id: 'land', icon: '🏡', label: 'Land' },
  { id: 'chat', icon: '💬', label: 'Chat' },
]
const activeTab = ref('explore')

const attrList = [
  { key: 'strength', label: 'STR' },
  { key: 'intelligence', label: 'INT' },
  { key: 'agility', label: 'AGI' },
  { key: 'vitality', label: 'VIT' },
  { key: 'wisdom', label: 'WIS' },
  { key: 'luck', label: 'LCK' },
]

// Travel
const travelDests = ref([])
const visitedAreas = ref([])

// Quests
const quests = ref({ active: [], completed: [] })
const allMissionsObj = ref({})
const completedIds = ref([])
const allMissions = computed(() => Object.keys(allMissionsObj.value))
const isCompleted = (id) => completedIds.value.includes(id)

// Challenges
const challenges = ref([])

// Shop
const shopItems = ref([])

// Crafting
const recipes = ref([])

// Companions
const companions = ref([])
const availableCompanions = ref({})

// Spells
const spells = ref([])

// Land
const landData = ref(null)

// Weather
const weather = ref(null)

// World events
const worldEvents = ref([])

// Chat
const chatMessages = ref([])
const chatMsg = ref('')
const chatError = ref('')
const onlineUsers = ref([])
const socketConnected = ref(false)
let socket = null

function pct(v, m) { return m > 0 ? Math.min(100, Math.round(v / m * 100)) + '%' : '0%' }

function formatTime(ts) {
  const now = Math.floor(Date.now() / 1000)
  const diff = now - ts
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

// ── Actions ──
async function act(fn) {
  if (loading.value) return
  loading.value = true
  try {
    const r = await fn()
    if (r.ok !== false) {
      if (r.player) game.state && (game.state.player = r.player)
      if (r.inventory) game.state && (game.state.inventory = r.inventory)
      if (r.outcome === 'battle_started' || r.in_battle || r.battle) {
        game.state && (game.state.in_battle = true)
        if (r.battle) game.state && (game.state.battle = r.battle)
        game.showToast('Battle started!', 'var(--red)')
        router.push('/battle')
        return
      }
      game.showToast(r.message || r.msg || '', 'var(--green-bright)')
    } else {
      game.showToast(r.message || 'Action failed.', 'var(--red)')
    }
    return r
  } catch {
    game.showToast('Network error.', 'var(--red)')
  } finally {
    loading.value = false
  }
}

async function explore() { await act(api.explore) }
async function rest() { await act(api.rest) }
async function mine() { await act(api.mine) }
async function quickHeal() { await act(api.quickHeal) }
async function travel(dest) {
  const r = await act(() => api.travel(dest))
  if (r?.ok) {
    game.state && (game.state.area = { key: r.area_key, name: r.area_name, ...game.area })
    loadTravelDests()
  }
}
async function buyItem(name) { await act(() => api.buy(name, game.area?.key)) }
async function sellItem(name) { await act(() => api.sell(name)); await game.refresh() }
async function equipItem(name) { await act(() => api.equip(name)); await game.refresh() }
async function unequip(slot) { await act(() => api.unequip(slot)); await game.refresh() }
async function useItem(name) { await act(() => api.useItem(name)); await game.refresh() }
async function quickHeal2() { await act(api.quickHeal) }
async function sortInventory() { await act(api.sortInventory); await game.refresh() }
async function autoEquip() { await act(api.autoEquip); await game.refresh() }
async function craft(id) { await act(() => api.craft(id)); await game.refresh() }
async function hireCompanion(id) { await act(() => api.hireCmp(id)); loadCompanions() }
async function dismissCompanion(id) { await act(() => api.dismissCmp(id)); loadCompanions() }
async function completeMission(id) { await act(() => api.completeMission(id)); loadQuests() }
async function claimChallenge(id) { await act(() => api.claimChallenge(id)); loadChallenges() }
async function spendAttr(attr) { await act(() => api.spendAttrPoint(attr)); await game.refresh() }

// ── Load sub-data per tab ──
async function loadTravelDests() {
  const r = await api.worldAreas().catch(() => null)
  if (!r?.areas) return
  const connections = game.area?.connections || []
  travelDests.value = connections.map(k => ({ key: k, ...r.areas[k], name: r.areas[k]?.name || k.replace(/_/g, ' ') }))
  visitedAreas.value = (game.state?.player?.visited_areas || []).map(k => r.areas[k]?.name || k)
}

async function loadShop() {
  const r = await api.catalogShops().catch(() => null)
  if (!r?.shops) return
  const areaKey = game.area?.key
  const shop = r.shops[areaKey] || Object.values(r.shops)[0] || {}
  shopItems.value = (shop.items || []).map(name => {
    const catalogItem = itemsCatalog.value[name] || {}
    return { name, price: catalogItem.price || catalogItem.value || 50, description: catalogItem.description, ...catalogItem }
  })
}

const itemsCatalog = ref({})
async function loadItemsCatalog() {
  const r = await api.catalogItems().catch(() => null)
  if (r?.items) itemsCatalog.value = r.items
}

async function loadQuests() {
  const r = await api.playerQuests().catch(() => null)
  if (r?.ok) {
    quests.value = { active: r.active_quests || [], completed: r.completed_quests || [] }
    completedIds.value = (r.completed_quests || []).map(q => q.id)
  }
  const mr = await fetch('/api/catalog/missions', { credentials: 'include' }).then(r => r.json()).catch(() => null)
  allMissionsObj.value = mr?.missions || {}
}

async function loadChallenges() {
  const r = await api.playerChallenges().catch(() => null)
  challenges.value = r?.challenges || []
}

async function loadRecipes() {
  const r = await api.catalogCrafting().catch(() => null)
  if (r?.crafting) {
    recipes.value = Object.entries(r.crafting).map(([id, c]) => ({ id, result: c.result || id, ingredients: c.ingredients || {} }))
  }
}

async function loadCompanions() {
  const r = await api.playerCompanions().catch(() => null)
  companions.value = r?.companions || []
  const cr = await api.catalogCompanions().catch(() => null)
  availableCompanions.value = cr?.companions || {}
}

async function loadSpells() {
  const r = await api.catalogSpells().catch(() => null)
  if (r?.spells) spells.value = Object.entries(r.spells).map(([name, d]) => ({ name, ...d }))
}

async function loadLand() {
  const r = await api.playerLand().catch(() => null)
  landData.value = r || {}
}

async function loadWeather() {
  const r = await api.worldWeather().catch(() => null)
  weather.value = r?.weather || r
}

async function loadWorldEvents() {
  const r = await api.worldEvents().catch(() => null)
  worldEvents.value = r?.events || []
}

// ── Chat via Socket.IO ──
function connectSocket() {
  if (socket) return
  socket = io({ transports: ['websocket', 'polling'], withCredentials: true })
  socket.on('connect', () => { socketConnected.value = true })
  socket.on('disconnect', () => { socketConnected.value = false })
  socket.on('chat_message', (m) => {
    chatMessages.value.push(m)
    if (chatMessages.value.length > 100) chatMessages.value.shift()
    nextTick(() => { if (chatEl.value) chatEl.value.scrollTop = chatEl.value.scrollHeight })
  })
  socket.on('chat_history', (msgs) => {
    chatMessages.value = msgs || []
    nextTick(() => { if (chatEl.value) chatEl.value.scrollTop = chatEl.value.scrollHeight })
  })
  socket.on('online_users', (users) => { onlineUsers.value = users || [] })
  socket.on('chat_error', (d) => { chatError.value = d.message; setTimeout(() => { chatError.value = '' }, 4000) })
}

function sendChat() {
  if (!chatMsg.value.trim() || !socket) return
  socket.emit('chat_send', { message: chatMsg.value.trim() })
  chatMsg.value = ''
}

// ── Tab-specific loading ──
watch(activeTab, (tab) => {
  if (tab === 'travel') loadTravelDests()
  else if (tab === 'shop') { loadItemsCatalog(); loadShop() }
  else if (tab === 'quests') loadQuests()
  else if (tab === 'challenges') loadChallenges()
  else if (tab === 'crafting') loadRecipes()
  else if (tab === 'companions') loadCompanions()
  else if (tab === 'spells') loadSpells()
  else if (tab === 'land') loadLand()
  else if (tab === 'chat') connectSocket()
})

let refreshTimer = null

onMounted(async () => {
  await game.refresh()
  if (game.inBattle) router.push('/battle')
  loadWorldEvents()
  loadWeather()
  // Auto-refresh every 30s
  refreshTimer = setInterval(() => { game.refresh(); loadWorldEvents() }, 30000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
  if (socket) { socket.disconnect(); socket = null }
})
</script>

<style scoped>
.game-page {
  flex: 1;
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 0;
  min-height: 0;
  overflow: hidden;
}
.sidebar {
  padding: 0.75rem;
  background: var(--bg-panel-dark);
  border-right: 1px solid var(--border);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}
.battle-warning {
  background: var(--red-dark);
  border: 1px solid var(--red);
  border-radius: 3px;
  padding: 0.5rem 0.75rem;
  color: #ffc0c0;
  font-size: 0.85rem;
  cursor: pointer;
  text-align: center;
  animation: pulse 1.5s infinite;
}
@keyframes pulse { 0%,100% { opacity: 0.7; } 50% { opacity: 1; } }
.area-block { display: flex; flex-direction: column; gap: 0.3rem; }
.area-name { font-family: 'Cinzel', serif; font-size: 0.9rem; }
.area-desc { font-size: 0.78rem; font-style: italic; }
.area-meta { display: flex; flex-wrap: wrap; gap: 0.25rem; margin-top: 0.2rem; }
.equip-panel { padding: 0.6rem; }
.equip-row { display: flex; align-items: center; gap: 0.4rem; padding: 0.2rem 0; font-size: 0.8rem; border-bottom: 1px solid rgba(78,62,46,0.3); }
.equip-slot { width: 5rem; flex-shrink: 0; font-size: 0.72rem; }
.equip-item { flex: 1; font-size: 0.82rem; }
.attr-btns { display: flex; flex-wrap: wrap; gap: 0.3rem; }
.game-main {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.tab-bar {
  display: flex;
  overflow-x: auto;
  background: var(--bg-panel-dark);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  padding: 0 0.25rem;
}
.tab-bar::-webkit-scrollbar { height: 3px; }
.scroll-x { overflow-x: auto; }
.tab-btn {
  padding: 0.5rem 0.75rem;
  font-size: 0.8rem;
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--text-dim);
  cursor: pointer;
  white-space: nowrap;
  transition: color 0.15s, border-color 0.15s;
}
.tab-btn:hover { color: var(--text-light); }
.tab-btn.active { color: var(--gold); border-bottom-color: var(--gold); }
.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}
.action-group { }
.action-grid-main { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; }
.action-btn { padding: 0.6rem 0.5rem; font-size: 0.85rem; }
.battle-cta {
  margin-top: 0.5rem;
  background: var(--red-dark);
  border: 1px solid var(--red);
  border-radius: 3px;
  padding: 0.5rem 0.75rem;
  color: #ffc0c0;
  font-size: 0.85rem;
  cursor: pointer;
  text-align: center;
}
.events-list { display: flex; flex-direction: column; gap: 0.2rem; }
.event-line { font-size: 0.82rem; }
.event-time { color: var(--text-dim); font-size: 0.72rem; margin-right: 0.4rem; }
.msg-log-panel { }
.msg-log { max-height: 180px; overflow-y: auto; display: flex; flex-direction: column; gap: 0.15rem; }
.msg-line { font-size: 0.83rem; padding: 0.1rem 0; border-bottom: 1px solid rgba(78,62,46,0.2); }
.travel-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.5rem; margin-top: 0.5rem; }
.dest-card { display: flex; flex-direction: column; gap: 0.3rem; }
.dest-name { font-family: 'Cinzel', serif; font-size: 0.9rem; }
.dest-desc { font-size: 0.78rem; font-style: italic; }
.dest-meta { display: flex; flex-wrap: wrap; gap: 0.2rem; }
.visited-list { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 0.25rem; }
.visited-tag { font-size: 0.78rem; padding: 0.15rem 0.4rem; background: var(--bg-panel-dark); border: 1px solid var(--border); border-radius: 3px; color: var(--text-dim); }
.inv-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.4rem; margin-top: 0.25rem; }
.inv-item { display: flex; align-items: center; justify-content: space-between; padding: 0.3rem 0.5rem; background: var(--bg-panel-dark); border: 1px solid var(--border); border-radius: 3px; }
.item-name { font-size: 0.85rem; flex: 1; }
.item-actions { display: flex; gap: 0.25rem; }
.inv-actions-header { display: inline-flex; gap: 0.35rem; margin-left: 0.75rem; }
.shop-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.5rem; margin-top: 0.5rem; }
.shop-item { display: flex; flex-direction: column; gap: 0.3rem; padding: 0.6rem; }
.shop-item-name { font-size: 0.88rem; font-family: 'Cinzel', serif; }
.shop-item-desc { font-size: 0.75rem; font-style: italic; }
.shop-item-stats { font-size: 0.75rem; }
.shop-item-footer { display: flex; align-items: center; justify-content: space-between; margin-top: 0.2rem; }
.quest-card { padding: 0.5rem 0; border-bottom: 1px solid rgba(78,62,46,0.3); display: flex; flex-direction: column; gap: 0.3rem; }
.quest-name { font-size: 0.9rem; font-family: 'Cinzel', serif; }
.quest-progress { font-size: 0.78rem; }
.mission-list { display: flex; flex-direction: column; gap: 0.35rem; margin-top: 0.25rem; max-height: 320px; overflow-y: auto; }
.mission-card { padding: 0.5rem; background: var(--bg-panel-dark); border: 1px solid var(--border); border-radius: 3px; display: flex; flex-direction: column; gap: 0.25rem; }
.mission-name { font-size: 0.88rem; font-family: 'Cinzel', serif; }
.mission-desc { font-size: 0.78rem; font-style: italic; }
.mission-rewards { font-size: 0.78rem; display: flex; gap: 0.5rem; }
.completed-list { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.25rem; }
.completed-tag { font-size: 0.78rem; padding: 0.15rem 0.4rem; background: var(--bg-panel-dark); border: 1px solid var(--border); border-radius: 3px; }
.challenge-card { padding: 0.5rem 0; border-bottom: 1px solid rgba(78,62,46,0.3); display: flex; flex-direction: column; gap: 0.35rem; }
.ch-name { font-size: 0.9rem; font-family: 'Cinzel', serif; }
.ch-desc { font-size: 0.78rem; }
.ch-progress { display: flex; align-items: center; gap: 0.5rem; font-size: 0.78rem; }
.ch-progress .bar-wrap { flex: 1; }
.ch-rewards { font-size: 0.78rem; }
.recipe-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.5rem; margin-top: 0.25rem; }
.recipe-card { display: flex; flex-direction: column; gap: 0.3rem; padding: 0.6rem; }
.recipe-name { font-size: 0.88rem; font-family: 'Cinzel', serif; }
.recipe-ingredients { font-size: 0.75rem; }
.companion-card { padding: 0.5rem; background: var(--bg-panel-dark); border: 1px solid var(--border); border-radius: 3px; display: flex; flex-direction: column; gap: 0.3rem; margin-bottom: 0.4rem; }
.comp-name { font-size: 0.9rem; font-family: 'Cinzel', serif; }
.comp-class { font-size: 0.78rem; }
.bar-row { display: flex; align-items: center; gap: 0.4rem; font-size: 0.75rem; }
.bar-row > span:first-child { width: 1.5rem; }
.hire-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.5rem; margin-top: 0.25rem; }
.hire-card { display: flex; flex-direction: column; gap: 0.3rem; padding: 0.6rem; }
.hire-name { font-size: 0.88rem; font-family: 'Cinzel', serif; }
.hire-class, .hire-stats { font-size: 0.75rem; }
.spell-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.5rem; margin-top: 0.25rem; }
.spell-card { display: flex; flex-direction: column; gap: 0.3rem; padding: 0.6rem; }
.spell-name { font-size: 0.88rem; font-family: 'Cinzel', serif; }
.spell-cost, .spell-desc, .spell-stats { font-size: 0.78rem; }
.land-stats { display: flex; gap: 1rem; font-size: 0.9rem; }
.buildings-list, .crops-list { display: flex; flex-direction: column; gap: 0.25rem; }
.building-row, .crop-row { font-size: 0.85rem; padding: 0.2rem 0; border-bottom: 1px solid rgba(78,62,46,0.2); }
.section-label { font-size: 0.78rem; border-bottom: 1px solid var(--border); padding-bottom: 0.2rem; margin-bottom: 0.3rem; }
.chat-tab { }
.chat-panel { display: flex; flex-direction: column; gap: 0.5rem; height: 100%; }
.chat-messages { flex: 1; min-height: 200px; max-height: 360px; overflow-y: auto; display: flex; flex-direction: column; gap: 0.2rem; padding: 0.25rem; background: var(--bg-panel-dark); border-radius: 3px; border: 1px solid var(--border); }
.chat-msg { font-size: 0.85rem; display: flex; gap: 0.4rem; flex-wrap: wrap; }
.sys-msg .chat-text { color: var(--gold-dim); font-style: italic; }
.my-msg .chat-user { color: var(--green-bright) !important; }
.chat-user { font-size: 0.78rem; flex-shrink: 0; }
.chat-input-row { display: flex; gap: 0.5rem; }
.chat-input-row input { flex: 1; }
.chat-error { font-size: 0.82rem; }
.online-list { display: flex; flex-wrap: wrap; gap: 0.35rem; font-size: 0.75rem; }
.online-count { font-size: 0.78rem; }
.online-name { padding: 0.1rem 0.4rem; background: var(--bg-panel-dark); border: 1px solid var(--border); border-radius: 10px; color: var(--text-dim); }
@media (max-width: 768px) {
  .game-page { grid-template-columns: 1fr; }
  .sidebar { display: none; }
  .action-grid-main { grid-template-columns: repeat(2, 1fr); }
}
</style>
