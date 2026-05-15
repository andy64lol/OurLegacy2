<template>
  <div class="admin-page">
    <div class="admin-container">
      <h2 class="page-title">🛡 Admin Console</h2>

      <div v-if="!isAdmin" class="panel text-red">Access denied.</div>

      <template v-else>
        <!-- Status panel -->
        <div class="panel">
          <div class="panel-title">Server Status</div>
          <div class="status-grid text-dim">
            <span>Online: <strong class="text-gold">{{ status.online_count }}</strong></span>
            <span>Battles: <strong class="text-gold">{{ status.activity?.battles }}</strong></span>
            <span>Quests: <strong class="text-gold">{{ status.activity?.quests }}</strong></span>
            <span>Dungeons: <strong class="text-gold">{{ status.activity?.dungeons }}</strong></span>
          </div>
        </div>

        <!-- Tab bar -->
        <div class="tab-bar">
          <button v-for="t in tabs" :key="t" class="tab-btn" :class="{ active: tab === t }" @click="tab = t">{{ t }}</button>
        </div>

        <!-- Moderation tab -->
        <template v-if="tab === 'Moderation'">
          <div class="panel">
            <div class="panel-title">Player Actions</div>
            <div class="admin-row">
              <input v-model="target" placeholder="Username…" class="input-sm" />
              <input v-model="reason" placeholder="Reason…" class="input-sm" />
            </div>
            <div class="admin-actions flex flex-wrap gap-1 mt-1">
              <button class="btn btn-sm btn-red" @click="doAction('ban')">Ban</button>
              <button class="btn btn-sm" @click="doAction('unban')">Unban</button>
              <button class="btn btn-sm btn-red" @click="doAction('mute', {duration: 3600})">Mute 1h</button>
              <button class="btn btn-sm" @click="doAction('unmute')">Unmute</button>
              <button class="btn btn-sm" @click="doAction('kick')">Kick</button>
              <button class="btn btn-sm" @click="doAction('warn')">Warn</button>
            </div>
            <div v-if="actionResult" class="action-result" :class="actionResult.ok ? 'text-green' : 'text-red'">
              {{ actionResult.message }}
            </div>
          </div>
        </template>

        <!-- Give items tab -->
        <template v-if="tab === 'Give'">
          <div class="panel">
            <div class="panel-title">Give / Set</div>
            <div class="give-grid">
              <div class="field">
                <label>Target Player</label>
                <input v-model="giveTarget" placeholder="Username…" />
              </div>
              <div class="field">
                <label>Item Name</label>
                <input v-model="giveItem" placeholder="Item name…" />
              </div>
              <div class="field">
                <label>Amount</label>
                <input v-model.number="giveAmount" type="number" min="1" value="1" />
              </div>
              <div class="field">
                <label>Gold Amount</label>
                <input v-model.number="giveGold" type="number" />
              </div>
            </div>
            <div class="flex gap-1 mt-1 flex-wrap">
              <button class="btn btn-sm btn-gold" @click="doGive" :disabled="busy">Give Item</button>
              <button class="btn btn-sm" @click="doGiveGold" :disabled="busy">Give Gold</button>
              <button class="btn btn-sm" @click="doHeal" :disabled="busy">Heal Player</button>
              <button class="btn btn-sm" @click="doCheckPlayer" :disabled="busy">Check Player</button>
            </div>
            <div v-if="giveResult" class="action-result" :class="giveResult.ok ? 'text-green' : 'text-red'">{{ giveResult.message }}</div>
            <pre v-if="playerInfo" class="player-info scroll-y">{{ JSON.stringify(playerInfo, null, 2) }}</pre>
          </div>
        </template>

        <!-- Online players tab -->
        <template v-if="tab === 'Online'">
          <div class="panel">
            <div class="panel-title">Online Players ({{ onlinePlayers.length }})</div>
            <div v-if="!onlinePlayers.length" class="text-dim">No data.</div>
            <div v-for="u in onlinePlayers" :key="u" class="online-row">
              <span class="text-gold">{{ u }}</span>
            </div>
          </div>
        </template>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth.js'
import { useGameStore } from '@/stores/game.js'
import { api } from '@/api/index.js'

const auth = useAuthStore()
const game = useGameStore()

const status = ref({})
const tab = ref('Moderation')
const tabs = ['Moderation', 'Give', 'Online']
const busy = ref(false)

const target = ref('')
const reason = ref('')
const actionResult = ref(null)

const giveTarget = ref('')
const giveItem = ref('')
const giveAmount = ref(1)
const giveGold = ref(0)
const giveResult = ref(null)
const playerInfo = ref(null)
const onlinePlayers = ref([])

const isAdmin = computed(() => {
  const s = status.value
  return s.is_admin || s.is_owner || s.is_mod
})

async function load() {
  const r = await api.adminStatus().catch(() => ({}))
  status.value = r
  const d = await api.adminData().catch(() => ({}))
  onlinePlayers.value = d.online_players || []
}

async function doAction(action, extra = {}) {
  if (!target.value.trim()) { game.showToast('Enter a username.', 'var(--red)'); return }
  busy.value = true
  let r
  const payload = { username: target.value.trim(), reason: reason.value, ...extra }
  if (action === 'ban') r = await api.adminBan(payload)
  else if (action === 'unban') r = await api.adminUnban(payload)
  else if (action === 'mute') r = await api.adminMute({ ...payload, duration_secs: extra.duration || 3600 })
  else if (action === 'unmute') r = await api.adminUnmute(payload)
  else if (action === 'kick') r = await api.adminKick(payload)
  else if (action === 'warn') r = await api.adminWarn(payload)
  busy.value = false
  actionResult.value = r
  setTimeout(() => { actionResult.value = null }, 4000)
}

async function doGive() {
  if (!giveTarget.value || !giveItem.value) return
  busy.value = true
  const r = await api.adminGameGive({ username: giveTarget.value, item_name: giveItem.value, amount: giveAmount.value })
  busy.value = false
  giveResult.value = r
}

async function doGiveGold() {
  if (!giveTarget.value) return
  busy.value = true
  const r = await api.adminGameSet({ username: giveTarget.value, field: 'gold', value: giveGold.value, mode: 'add' })
  busy.value = false
  giveResult.value = r
}

async function doHeal() {
  if (!giveTarget.value) return
  busy.value = true
  const r = await api.adminGameHeal({ username: giveTarget.value })
  busy.value = false
  giveResult.value = r
}

async function doCheckPlayer() {
  if (!giveTarget.value) return
  busy.value = true
  const r = await api.adminGameStats(giveTarget.value)
  busy.value = false
  playerInfo.value = r.player || r
}

onMounted(load)
</script>

<style scoped>
.admin-page { flex: 1; padding: 1rem; overflow-y: auto; }
.admin-container { max-width: 780px; margin: 0 auto; display: flex; flex-direction: column; gap: 0.75rem; }
.page-title { font-family: 'Cinzel', serif; color: var(--gold); font-size: 1.3rem; }
.status-grid { display: flex; gap: 1.5rem; flex-wrap: wrap; font-size: 0.9rem; }
.tab-bar { display: flex; gap: 0.5rem; }
.tab-btn { padding: 0.35rem 0.8rem; font-size: 0.85rem; border: 1px solid var(--border); background: var(--bg-panel-dark); color: var(--text-dim); border-radius: 3px; cursor: pointer; }
.tab-btn.active { background: var(--wood-dark); border-color: var(--gold-dim); color: var(--gold); }
.admin-row { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.input-sm { flex: 1; min-width: 120px; }
.action-result { padding: 0.4rem 0.6rem; background: var(--bg-panel-dark); border-radius: 3px; font-size: 0.85rem; margin-top: 0.5rem; }
.give-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem; }
.field { display: flex; flex-direction: column; gap: 0.2rem; }
.field label { font-size: 0.78rem; color: var(--text-dim); }
.field input { width: 100%; }
.player-info { font-size: 0.72rem; background: var(--bg-panel-dark); border: 1px solid var(--border); border-radius: 3px; padding: 0.5rem; max-height: 250px; color: var(--text-dim); margin-top: 0.5rem; white-space: pre-wrap; word-break: break-all; }
.online-row { padding: 0.3rem 0; border-bottom: 1px solid rgba(78,62,46,0.3); font-size: 0.88rem; }
</style>
