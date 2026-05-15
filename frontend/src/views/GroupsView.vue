<template>
  <div class="groups-page">
    <div class="groups-container">
      <h2 class="page-title">⚜ Guilds & Groups</h2>

      <div v-if="myGroup" class="panel my-group">
        <div class="panel-title">{{ myGroup.name }}</div>
        <div class="group-stats">
          <span class="text-gold">Treasury: {{ myGroup.gold?.toLocaleString() }}g</span>
          <span class="text-dim">Members: {{ myGroup.members?.length || 0 }}</span>
        </div>

        <div class="member-list">
          <div v-for="m in myGroup.members" :key="m.username" class="member-row">
            <span class="member-name" :class="m.username === myGroup.leader ? 'text-gold' : ''">
              {{ m.username }} {{ m.username === myGroup.leader ? '👑' : '' }}
            </span>
            <button v-if="isLeader && m.username !== auth.user?.username" class="btn btn-sm btn-red" @click="kick(m.username)">Kick</button>
          </div>
        </div>

        <div class="group-actions">
          <button class="btn btn-gold btn-sm" @click="collectGold" :disabled="busy">Collect Gold</button>
          <button class="btn btn-red btn-sm" @click="leaveGroup" :disabled="busy">Leave Group</button>
        </div>
      </div>

      <div v-else class="panel">
        <div class="panel-title">Join or Create a Guild</div>
        <div class="group-form">
          <input v-model="groupName" placeholder="Guild name…" />
          <button class="btn btn-sm btn-gold" @click="createGroup" :disabled="busy">Create</button>
          <button class="btn btn-sm" @click="joinGroup" :disabled="busy">Join</button>
        </div>
        <p class="text-dim" style="font-size:0.82rem;margin-top:0.5rem">Create a new guild or type an existing name to join.</p>
      </div>

      <!-- Group leaderboard -->
      <div class="panel" v-if="groupLb.length">
        <div class="panel-title">Group Leaderboard</div>
        <table class="lb-table">
          <thead><tr><th>#</th><th>Guild</th><th>Gold</th><th>Members</th></tr></thead>
          <tbody>
            <tr v-for="(g, i) in groupLb" :key="g.name" :class="{ 'my-row': g.name === myGroup?.name }">
              <td class="text-dim">{{ i + 1 }}</td>
              <td class="text-gold">{{ g.name }}</td>
              <td>{{ g.gold?.toLocaleString() }}g</td>
              <td class="text-dim">{{ g.member_count }}</td>
            </tr>
          </tbody>
        </table>
      </div>
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
const myGroup = ref(null)
const groupLb = ref([])
const groupName = ref('')
const busy = ref(false)

const isLeader = computed(() => myGroup.value?.leader === auth.user?.username)

async function load() {
  const r = await api.groupMy().catch(() => null)
  if (r?.ok && r.group) myGroup.value = r.group
  const lb = await api.leaderboard().catch(() => null)
  groupLb.value = lb?.groups || []
}

async function createGroup() {
  if (!groupName.value.trim()) return
  busy.value = true
  const r = await api.groupCreate(groupName.value.trim())
  busy.value = false
  game.showToast(r.message || (r.ok ? 'Guild created!' : 'Failed.'), r.ok ? 'var(--gold)' : 'var(--red)')
  if (r.ok) { groupName.value = ''; await load() }
}

async function joinGroup() {
  if (!groupName.value.trim()) return
  busy.value = true
  const r = await api.groupJoin(groupName.value.trim())
  busy.value = false
  game.showToast(r.message || (r.ok ? 'Joined!' : 'Failed.'), r.ok ? 'var(--green-bright)' : 'var(--red)')
  if (r.ok) { groupName.value = ''; await load() }
}

async function leaveGroup() {
  if (!confirm('Leave your guild?')) return
  busy.value = true
  const r = await api.groupLeave()
  busy.value = false
  game.showToast(r.message || (r.ok ? 'Left guild.' : 'Failed.'), r.ok ? 'var(--text-dim)' : 'var(--red)')
  if (r.ok) { myGroup.value = null; await load() }
}

async function kick(username) {
  if (!confirm(`Kick ${username}?`)) return
  busy.value = true
  const r = await api.groupKick(username)
  busy.value = false
  game.showToast(r.message || '', r.ok ? 'var(--green-bright)' : 'var(--red)')
  await load()
}

async function collectGold() {
  busy.value = true
  const r = await api.groupCollect()
  busy.value = false
  game.showToast(r.message || (r.ok ? 'Gold collected!' : 'Nothing to collect.'), r.ok ? 'var(--gold)' : 'var(--text-dim)')
  if (r.ok) await game.refresh()
}

onMounted(load)
</script>

<style scoped>
.groups-page { flex: 1; padding: 1rem; overflow-y: auto; }
.groups-container { max-width: 680px; margin: 0 auto; display: flex; flex-direction: column; gap: 0.75rem; }
.page-title { font-family: 'Cinzel', serif; color: var(--gold); font-size: 1.3rem; }
.my-group { display: flex; flex-direction: column; gap: 0.75rem; }
.group-stats { display: flex; gap: 1rem; font-size: 0.9rem; }
.member-list { display: flex; flex-direction: column; gap: 0.3rem; }
.member-row { display: flex; align-items: center; justify-content: space-between; padding: 0.3rem 0; border-bottom: 1px solid rgba(78,62,46,0.3); }
.member-name { font-size: 0.9rem; }
.group-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.group-form { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.group-form input { flex: 1; min-width: 150px; }
.lb-table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
.lb-table th { padding: 0.4rem 0.6rem; background: var(--bg-panel-dark); color: var(--gold-dim); font-size: 0.78rem; text-align: left; border-bottom: 1px solid var(--border); }
.lb-table td { padding: 0.4rem 0.6rem; border-bottom: 1px solid rgba(78,62,46,0.3); }
.my-row td { background: rgba(212,176,80,0.06); }
</style>
