<template>
  <nav class="navbar">
    <div class="nav-brand">
      <router-link to="/game">⚔ Our Legacy</router-link>
    </div>
    <div class="nav-links">
      <router-link to="/game">Game</router-link>
      <router-link to="/friends">Friends</router-link>
      <router-link to="/groups">Groups</router-link>
      <router-link to="/leaderboard">Board</router-link>
      <router-link v-if="isAdmin" to="/admin">Admin</router-link>
    </div>
    <div class="nav-user">
      <span class="nav-username">{{ auth.user?.username }}</span>
      <button class="btn btn-sm" @click="doLogout">Logout</button>
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'
import { useGameStore } from '@/stores/game.js'

const auth = useAuthStore()
const game = useGameStore()
const router = useRouter()

const isAdmin = computed(() => {
  const u = auth.user?.username?.toLowerCase()
  return u && (game.state?.is_admin || false)
})

async function doLogout() {
  await auth.logout()
  game.clearState()
  router.push('/')
}
</script>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 1.2rem;
  background: var(--bg-panel-dark);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.nav-brand a {
  font-family: 'Cinzel', serif;
  font-size: 1.1rem;
  color: var(--gold);
  font-weight: 700;
  letter-spacing: 0.05em;
}
.nav-links { display: flex; gap: 1rem; }
.nav-links a { color: var(--text-dim); font-size: 0.9rem; transition: color 0.15s; }
.nav-links a:hover, .nav-links a.router-link-active { color: var(--gold); }
.nav-user { display: flex; align-items: center; gap: 0.75rem; }
.nav-username { color: var(--text-dim); font-size: 0.85rem; }
@media (max-width: 600px) {
  .nav-links { gap: 0.5rem; font-size: 0.8rem; }
}
</style>
