<template>
  <div class="battle-page">
    <div class="battle-container">
      <div v-if="!battleData && !loading" class="no-battle panel">
        <p class="text-dim">You are not in battle.</p>
        <router-link to="/game" class="btn btn-gold mt-2">Return to Game</router-link>
      </div>

      <template v-else-if="battleData">
        <!-- Header -->
        <div class="battle-header">
          <h2 class="battle-title">⚔ Combat</h2>
          <span v-if="battleData.enemy?.is_boss" class="tag tag-boss">BOSS</span>
        </div>

        <!-- Combatants -->
        <div class="combatants">
          <!-- Player side -->
          <div class="combatant-card panel">
            <div class="comb-name text-gold">{{ player?.name }}</div>
            <div class="comb-level text-dim">Lv.{{ player?.level }} {{ player?.class }}</div>
            <div class="bar-row">
              <span class="text-red bar-lbl">HP</span>
              <div class="bar-wrap"><div class="bar-fill bar-hp" :style="{ width: hpPct(player?.hp, player?.max_hp) }"></div></div>
              <span class="text-red bar-val">{{ player?.hp }}/{{ player?.max_hp }}</span>
            </div>
            <div class="bar-row">
              <span class="text-mana bar-lbl">MP</span>
              <div class="bar-wrap"><div class="bar-fill bar-mp" :style="{ width: hpPct(player?.mp, player?.max_mp) }"></div></div>
              <span class="text-mana bar-val">{{ player?.mp }}/{{ player?.max_mp }}</span>
            </div>
          </div>

          <div class="vs-divider">VS</div>

          <!-- Enemy side -->
          <div class="combatant-card panel enemy-card" :class="{ 'boss-glow': battleData.enemy?.is_boss }">
            <div class="comb-name" :class="battleData.enemy?.is_boss ? 'text-red' : 'text-bright'">
              {{ battleData.enemy?.name }}
            </div>
            <div class="comb-level text-dim">{{ battleData.enemy?.is_boss ? '⚠ Boss Encounter' : 'Enemy' }}</div>
            <div class="bar-row">
              <span class="text-red bar-lbl">HP</span>
              <div class="bar-wrap"><div class="bar-fill bar-hp" :style="{ width: hpPct(battleData.enemy?.hp, battleData.enemy?.max_hp) }"></div></div>
              <span class="text-red bar-val">{{ battleData.enemy?.hp }}/{{ battleData.enemy?.max_hp }}</span>
            </div>
            <div class="comb-stats text-dim">
              ATK {{ battleData.enemy?.attack }} | DEF {{ battleData.enemy?.defense }}
            </div>
          </div>
        </div>

        <!-- Battle log -->
        <div class="panel battle-log-panel">
          <div class="panel-title">Battle Log</div>
          <div class="battle-log scroll-y" ref="logEl">
            <div v-for="(line, i) in battleData.log" :key="i" class="log-line">{{ line }}</div>
          </div>
        </div>

        <!-- Companions -->
        <div v-if="battleData.companions?.length" class="panel companions-panel">
          <div class="panel-title">Allies</div>
          <div class="companions-row">
            <div v-for="c in battleData.companions" :key="c.key" class="companion-chip">
              <span class="text-gold">{{ c.name }}</span>
              <span class="text-dim"> HP {{ c.hp }}/{{ c.max_hp }}</span>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="battle-actions panel">
          <div class="panel-title">Actions</div>
          <div class="action-grid">
            <button class="btn btn-gold" @click="doAttack" :disabled="busy">⚔ Attack</button>
            <button class="btn" @click="doDefend" :disabled="busy">🛡 Defend</button>
            <button class="btn" @click="showSpells = !showSpells" :disabled="busy">✨ Spells</button>
            <button class="btn" @click="showItems = !showItems" :disabled="busy">🎒 Items</button>
            <button class="btn btn-red" @click="doFlee" :disabled="busy">🏃 Flee</button>
          </div>

          <!-- Spell picker -->
          <div v-if="showSpells" class="sub-picker">
            <div class="sub-title text-dim">Choose Spell (MP: {{ player?.mp }})</div>
            <div v-if="!spells.length" class="text-dim">No spells available.</div>
            <button
              v-for="sp in spells" :key="sp.name"
              class="btn btn-sm"
              :disabled="busy || (player?.mp || 0) < (sp.cost || 0)"
              @click="doSpell(sp.name)"
              :title="`Cost: ${sp.cost} MP | ${sp.description || ''}`"
            >
              {{ sp.name }} <span class="text-mana">({{ sp.cost }}MP)</span>
            </button>
          </div>

          <!-- Item picker -->
          <div v-if="showItems" class="sub-picker">
            <div class="sub-title text-dim">Use item from inventory</div>
            <div v-if="!consumables.length" class="text-dim">No usable items.</div>
            <button
              v-for="item in consumables" :key="item"
              class="btn btn-sm"
              :disabled="busy"
              @click="doUseItem(item)"
            >{{ item }}</button>
          </div>
        </div>
      </template>

      <div v-if="loading" class="loading-state">
        <span class="loading-crest">⚔</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game.js'
import { api } from '@/api/index.js'

const game = useGameStore()
const router = useRouter()

const battleData = ref(null)
const player = computed(() => battleData.value?.player || game.player)
const loading = ref(false)
const busy = ref(false)
const showSpells = ref(false)
const showItems = ref(false)
const spells = ref([])
const logEl = ref(null)

const consumables = computed(() => {
  const inv = battleData.value?.inventory || game.inventory || []
  const usable = ['Health Potion', 'Mana Potion', 'Elixir', 'Antidote', 'Tonic', 'Salve', 'Remedy']
  return inv.filter(i => usable.some(u => i.toLowerCase().includes(u.toLowerCase())))
})

function hpPct(v, m) { return m > 0 ? Math.min(100, Math.round(v / m * 100)) + '%' : '0%' }

async function load() {
  loading.value = true
  const r = await api.battleState()
  loading.value = false
  if (r.ok && r.in_battle) {
    battleData.value = { ...r.battle, player: r.player, inventory: game.inventory }
    scrollLog()
  } else {
    router.push('/game')
  }
}

async function battleAction(fn) {
  busy.value = true
  showSpells.value = false
  showItems.value = false
  const r = await fn().catch(() => ({ ok: false, message: 'Error' }))
  busy.value = false
  if (r.outcome === 'victory') {
    game.showToast(r.message || 'Victory!', 'var(--gold)')
    await game.refresh()
    router.push('/game')
    return
  }
  if (r.outcome === 'defeat') {
    game.showToast('You have been defeated…', 'var(--red)')
    await game.refresh()
    router.push('/game')
    return
  }
  if (r.outcome === 'fled') {
    game.showToast(r.message || 'You fled!', 'var(--text-dim)')
    await game.refresh()
    router.push('/game')
    return
  }
  if (r.ok !== false) {
    if (r.battle) {
      battleData.value = { ...r.battle, player: r.player || battleData.value?.player, inventory: game.inventory }
    }
    if (r.player) {
      battleData.value = { ...battleData.value, player: r.player }
      game.state && (game.state.player = r.player)
    }
    scrollLog()
  } else {
    game.showToast(r.message || 'Action failed.', 'var(--red)')
  }
}

const doAttack = () => battleAction(api.battleAttack)
const doDefend = () => battleAction(api.battleDefend)
const doFlee = () => battleAction(api.battleFlee)
const doSpell = (name) => battleAction(() => api.battleSpell(name))
const doUseItem = (name) => battleAction(() => api.battleUseItem(name))

async function scrollLog() {
  await nextTick()
  if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight
}

async function loadSpells() {
  const r = await api.catalogSpells().catch(() => null)
  if (r?.spells) spells.value = Object.entries(r.spells).map(([name, d]) => ({ name, ...d }))
}

watch(showSpells, v => { if (v && !spells.value.length) loadSpells() })

onMounted(load)
</script>

<style scoped>
.battle-page { flex: 1; padding: 1rem; overflow-y: auto; }
.battle-container { max-width: 700px; margin: 0 auto; display: flex; flex-direction: column; gap: 0.75rem; }
.battle-header { display: flex; align-items: center; gap: 0.75rem; }
.battle-title { font-family: 'Cinzel', serif; font-size: 1.3rem; color: var(--gold); }
.combatants { display: flex; align-items: stretch; gap: 0.75rem; }
.combatant-card { flex: 1; display: flex; flex-direction: column; gap: 0.4rem; }
.vs-divider { display: flex; align-items: center; font-family: 'Cinzel', serif; color: var(--red); font-size: 1.1rem; font-weight: 700; flex-shrink: 0; }
.boss-glow { border-color: var(--red); box-shadow: 0 0 20px rgba(204,78,78,0.2); }
.comb-name { font-family: 'Cinzel', serif; font-size: 1rem; font-weight: 600; }
.comb-level { font-size: 0.8rem; }
.bar-row { display: flex; align-items: center; gap: 0.4rem; font-size: 0.75rem; }
.bar-lbl { width: 1.5rem; flex-shrink: 0; }
.bar-wrap { flex: 1; background: #111; border-radius: 4px; height: 10px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 4px; transition: width 0.4s; }
.bar-val { width: 5rem; text-align: right; font-size: 0.72rem; flex-shrink: 0; }
.comb-stats { font-size: 0.78rem; margin-top: 0.2rem; }
.battle-log-panel { padding: 0.75rem; }
.battle-log { max-height: 160px; overflow-y: auto; display: flex; flex-direction: column; gap: 0.2rem; }
.log-line { font-size: 0.85rem; color: var(--text-light); padding: 0.15rem 0; border-bottom: 1px solid rgba(78,62,46,0.3); }
.log-line:last-child { color: var(--gold-bright); font-weight: 600; }
.companions-panel { padding: 0.75rem; }
.companions-row { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.companion-chip { font-size: 0.8rem; background: var(--bg-panel-dark); border: 1px solid var(--border); border-radius: 3px; padding: 0.25rem 0.6rem; }
.battle-actions { padding: 0.75rem; display: flex; flex-direction: column; gap: 0.75rem; }
.action-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.5rem; }
.sub-picker { display: flex; flex-wrap: wrap; gap: 0.4rem; padding-top: 0.5rem; border-top: 1px solid var(--border); }
.sub-title { width: 100%; font-size: 0.8rem; }
.no-battle { text-align: center; padding: 2rem; }
.loading-state { display: flex; justify-content: center; padding: 2rem; }
.loading-crest { font-size: 2rem; color: var(--gold); animation: pulse 1.5s infinite; }
@keyframes pulse { 0%,100% { opacity: 0.3; } 50% { opacity: 1; } }
@media (max-width: 500px) {
  .action-grid { grid-template-columns: repeat(3, 1fr); }
  .combatants { flex-direction: column; }
  .vs-divider { justify-content: center; }
}
</style>
