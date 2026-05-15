<template>
  <div class="dungeon-page">
    <div class="dungeon-container">
      <div class="dungeon-header">
        <h2 class="page-title">🗝 {{ activeDungeon?.dungeon?.name || 'Dungeon' }}</h2>
        <div class="room-progress text-dim" v-if="roomData">
          Room {{ roomData.room_num }}/{{ roomData.total_rooms }}
        </div>
      </div>

      <!-- No active dungeon -->
      <template v-if="!roomData && !loading">
        <div class="panel">
          <div class="panel-title">Available Dungeons</div>
          <div v-if="!dungeons.length" class="text-dim">No dungeons available yet. Explore the world first.</div>
          <div class="dungeon-list">
            <div v-for="d in dungeons" :key="d.id" class="dungeon-card panel">
              <div class="dg-name text-gold">{{ d.name }}</div>
              <div class="dg-desc text-dim">{{ d.description }}</div>
              <div class="dg-meta">
                <span class="tag tag-gold">{{ d.rooms }} rooms</span>
                <span class="tag" style="background:var(--bg-panel-dark);border:1px solid var(--border)">Lv.{{ d.min_level }}+</span>
              </div>
              <button class="btn btn-gold btn-sm" @click="enterDungeon(d.id)" :disabled="busy">Enter</button>
            </div>
          </div>
        </div>
        <router-link to="/game" class="btn mt-2">← Back to Game</router-link>
      </template>

      <!-- Active dungeon room -->
      <template v-else-if="roomData">
        <div class="panel room-panel">
          <div class="room-type" :class="'room-' + roomData.room?.type">
            {{ roomIcon(roomData.room?.type) }} {{ roomLabel(roomData.room?.type) }}
          </div>
          <p class="room-desc">{{ roomData.room?.description || 'You enter the next chamber…' }}</p>

          <!-- Messages -->
          <div v-if="messages.length" class="dungeon-messages">
            <div v-for="(m, i) in messages" :key="i" class="dg-msg">{{ m }}</div>
          </div>

          <!-- Question challenge -->
          <div v-if="roomData.current_challenge && !challenge_done" class="challenge-box">
            <div class="challenge-q text-gold">{{ roomData.current_challenge.question }}</div>
            <div v-if="roomData.room?.type === 'question'" class="challenge-input">
              <input v-model="answerText" placeholder="Your answer…" @keydown.enter="submitAnswer" />
              <button class="btn btn-gold" @click="submitAnswer" :disabled="busy">Answer</button>
            </div>
            <div v-else class="challenge-choices">
              <button v-for="(ch, i) in roomData.current_challenge.choices" :key="i"
                class="btn" @click="submitChoice(i)" :disabled="busy">
                {{ ch }}
              </button>
            </div>
          </div>

          <!-- Actions -->
          <div class="room-actions" v-if="!roomData.current_challenge || challenge_done">
            <button class="btn btn-gold" @click="proceedRoom" :disabled="busy">
              {{ roomData.room_num >= roomData.total_rooms ? '🏆 Complete Dungeon' : '→ Proceed' }}
            </button>
            <button class="btn btn-red btn-sm" @click="abandonDungeon" :disabled="busy">Abandon</button>
          </div>
        </div>

        <!-- Player stats -->
        <div class="panel" v-if="game.player">
          <PlayerStats :p="game.player" />
        </div>
      </template>

      <div v-if="loading" class="loading-state text-dim">Loading…</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/game.js'
import { api } from '@/api/index.js'
import PlayerStats from '@/components/PlayerStats.vue'

const game = useGameStore()
const router = useRouter()
const dungeons = ref([])
const roomData = ref(null)
const activeDungeon = ref(null)
const loading = ref(false)
const busy = ref(false)
const answerText = ref('')
const challenge_done = ref(false)
const messages = ref([])

function roomIcon(type) {
  const icons = { battle: '⚔', chest: '📦', trap_chest: '⚠', shrine: '🕯', empty: '…', question: '❓', multi_choice: '🔀', ambush: '💀', boss: '👑' }
  return icons[type] || '◆'
}
function roomLabel(type) {
  const labels = { battle: 'Battle Room', chest: 'Treasure Chest', trap_chest: 'Trapped Chest', shrine: 'Ancient Shrine', empty: 'Empty Chamber', question: 'Riddle Chamber', multi_choice: 'Choice Chamber', ambush: 'Ambush!', boss: 'Boss Chamber' }
  return labels[type] || type?.replace('_', ' ') || 'Chamber'
}

async function load() {
  loading.value = true
  const r = await api.dungeonRoom().catch(() => null)
  if (r?.ok) {
    roomData.value = r
    activeDungeon.value = r
  } else {
    const cr = await fetch('/api/catalog/dungeon_list', { credentials: 'include' }).then(r => r.json()).catch(() => null)
    dungeons.value = (cr?.dungeons || []).filter(d => d.discovered)
  }
  loading.value = false
}

async function enterDungeon(id) {
  busy.value = true
  const r = await api.dungeonEnter(id)
  busy.value = false
  if (r.ok) {
    messages.value = r.messages || []
    await loadRoom()
  } else {
    game.showToast(r.message || 'Cannot enter dungeon.', 'var(--red)')
  }
}

async function loadRoom() {
  const r = await api.dungeonRoom().catch(() => null)
  if (r?.ok) {
    roomData.value = r
    challenge_done.value = false
  } else {
    roomData.value = null
  }
}

async function proceedRoom() {
  busy.value = true
  messages.value = []
  const r = await api.dungeonProceed()
  busy.value = false
  if (r.ok) {
    messages.value = r.messages || []
    if (r.outcome === 'battle_started') {
      game.showToast('Battle started in dungeon!', 'var(--red)')
      await game.refresh()
      router.push('/battle')
      return
    }
    if (r.outcome === 'dungeon_complete' || r.completed) {
      game.showToast(r.message || 'Dungeon complete!', 'var(--gold)')
      roomData.value = null
      await game.refresh()
      return
    }
    if (r.room) {
      roomData.value = r
      challenge_done.value = false
    } else {
      await loadRoom()
    }
  } else {
    game.showToast(r.message || 'Error.', 'var(--red)')
  }
}

async function submitAnswer() {
  busy.value = true
  const r = await api.dungeonAnswer(answerText.value)
  busy.value = false
  answerText.value = ''
  messages.value = r.messages || []
  if (r.ok) { challenge_done.value = true; game.showToast(r.message || 'Answered!', 'var(--green-bright)') }
  else game.showToast(r.message || 'Wrong answer.', 'var(--red)')
  if (r.player) game.state && (game.state.player = r.player)
}

async function submitChoice(i) {
  busy.value = true
  const r = await api.dungeonChoose(i)
  busy.value = false
  messages.value = r.messages || []
  if (r.ok) { challenge_done.value = true; game.showToast(r.message || 'Choice made.', 'var(--green-bright)') }
  else game.showToast(r.message || 'Error.', 'var(--red)')
  if (r.player) game.state && (game.state.player = r.player)
}

async function abandonDungeon() {
  if (!confirm('Abandon the dungeon?')) return
  busy.value = true
  await api.dungeonAbandon()
  busy.value = false
  roomData.value = null
  game.showToast('Dungeon abandoned.', 'var(--text-dim)')
  await load()
}

onMounted(load)
</script>

<style scoped>
.dungeon-page { flex: 1; padding: 1rem; overflow-y: auto; }
.dungeon-container { max-width: 680px; margin: 0 auto; display: flex; flex-direction: column; gap: 0.75rem; }
.dungeon-header { display: flex; align-items: center; justify-content: space-between; }
.page-title { font-family: 'Cinzel', serif; color: var(--gold); font-size: 1.3rem; }
.room-progress { font-size: 0.85rem; }
.dungeon-list { display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.5rem; }
.dungeon-card { display: flex; flex-direction: column; gap: 0.35rem; }
.dg-name { font-family: 'Cinzel', serif; font-size: 0.95rem; }
.dg-desc { font-size: 0.82rem; font-style: italic; }
.dg-meta { display: flex; gap: 0.4rem; flex-wrap: wrap; }
.room-panel { display: flex; flex-direction: column; gap: 0.75rem; }
.room-type { font-family: 'Cinzel', serif; font-size: 1rem; color: var(--text-bright); }
.room-battle { color: var(--red) !important; }
.room-chest, .room-trap_chest { color: var(--gold) !important; }
.room-shrine { color: var(--mana-bright) !important; }
.room-boss { color: var(--red) !important; }
.room-desc { font-style: italic; color: var(--text-dim); font-size: 0.9rem; }
.dungeon-messages { display: flex; flex-direction: column; gap: 0.2rem; padding: 0.5rem; background: var(--bg-panel-dark); border-radius: 3px; }
.dg-msg { font-size: 0.85rem; color: var(--text-light); }
.challenge-box { display: flex; flex-direction: column; gap: 0.5rem; padding: 0.75rem; background: var(--bg-panel-dark); border: 1px solid var(--gold-dim); border-radius: 4px; }
.challenge-q { font-size: 0.95rem; }
.challenge-input { display: flex; gap: 0.5rem; }
.challenge-input input { flex: 1; }
.challenge-choices { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.room-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.loading-state { text-align: center; padding: 2rem; }
</style>
