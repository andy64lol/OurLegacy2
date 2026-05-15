<template>
  <div class="lb-page">
    <div class="lb-container">
      <h2 class="page-title">⚜ Hall of Legends</h2>
      <div v-if="loading" class="text-dim">Loading…</div>
      <div v-else>
        <div class="lb-table-wrap panel">
          <table class="lb-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Hero</th>
                <th>Level</th>
                <th>Class</th>
                <th>Gold</th>
                <th>Kills</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in rows" :key="row.username" :class="{ 'my-row': row.username === myName }">
                <td class="rank">
                  <span v-if="i === 0">👑</span>
                  <span v-else-if="i === 1">🥈</span>
                  <span v-else-if="i === 2">🥉</span>
                  <span v-else class="text-dim">{{ i + 1 }}</span>
                </td>
                <td class="username">{{ row.username }}</td>
                <td class="text-gold">{{ row.level }}</td>
                <td class="text-dim">{{ row.class }}</td>
                <td class="text-gold">{{ row.gold?.toLocaleString() }}</td>
                <td class="text-dim">{{ row.total_kills }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth.js'
import { api } from '@/api/index.js'

const auth = useAuthStore()
const rows = ref([])
const loading = ref(true)
const myName = auth.user?.username

onMounted(async () => {
  const r = await api.leaderboard().catch(() => null)
  rows.value = r?.leaderboard || r?.players || []
  loading.value = false
})
</script>

<style scoped>
.lb-page { flex: 1; padding: 1rem; overflow-y: auto; }
.lb-container { max-width: 800px; margin: 0 auto; }
.page-title { font-family: 'Cinzel', serif; color: var(--gold); font-size: 1.4rem; margin-bottom: 1rem; }
.lb-table-wrap { padding: 0; overflow-x: auto; }
.lb-table { width: 100%; border-collapse: collapse; }
.lb-table th {
  padding: 0.6rem 0.75rem;
  background: var(--bg-panel-dark);
  color: var(--gold-dim);
  font-size: 0.8rem;
  text-align: left;
  font-family: 'Cinzel', serif;
  border-bottom: 1px solid var(--border);
}
.lb-table td { padding: 0.5rem 0.75rem; border-bottom: 1px solid rgba(78,62,46,0.4); font-size: 0.9rem; }
.lb-table tr:hover td { background: rgba(255,255,255,0.02); }
.my-row td { background: rgba(212,176,80,0.06); }
.rank { width: 2.5rem; text-align: center; }
.username { color: var(--text-bright); font-weight: 600; }
</style>
