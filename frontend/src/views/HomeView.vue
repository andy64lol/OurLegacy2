<template>
  <div class="home">
    <div class="home-bg"></div>
    <div class="home-content">
      <div class="crest">⚔</div>
      <h1 class="title">Our Legacy</h1>
      <p class="subtitle">{{ splash }}</p>
      <div class="home-actions" v-if="!auth.user">
        <router-link to="/login" class="btn btn-gold">Enter the Realm</router-link>
      </div>
      <div class="home-actions" v-else>
        <router-link to="/game" class="btn btn-gold">Continue Your Legend</router-link>
        <button class="btn" @click="doLogout">Leave</button>
      </div>
      <p v-if="auth.user" class="welcome">Welcome back, <span class="text-gold">{{ auth.user.username }}</span></p>
      <div class="version">v0.0.2b &nbsp;|&nbsp; Medieval Fantasy RPG</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth.js'
import { useGameStore } from '@/stores/game.js'
import { useRouter } from 'vue-router'
import { api } from '@/api/index.js'

const auth = useAuthStore()
const game = useGameStore()
const router = useRouter()
const splash = ref('Every legend begins with a single step…')

onMounted(async () => {
  const r = await api.announcements().catch(() => null)
  if (r?.announcements?.length) splash.value = r.announcements[r.announcements.length - 1]?.text || splash.value
})

async function doLogout() {
  await auth.logout()
  game.clearState()
  router.push('/')
}
</script>

<style scoped>
.home {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.home-bg {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at center, #2a1a08 0%, #18140c 60%, #0e0a06 100%);
  z-index: 0;
}
.home-content {
  position: relative;
  z-index: 1;
  text-align: center;
  padding: 2rem;
  max-width: 500px;
  width: 100%;
}
.crest {
  font-size: 4rem;
  color: var(--gold);
  display: block;
  margin-bottom: 0.5rem;
  text-shadow: 0 0 40px rgba(212,176,80,0.5);
}
.title {
  font-family: 'Cinzel', serif;
  font-size: 2.8rem;
  color: var(--gold-bright);
  margin-bottom: 0.75rem;
  letter-spacing: 0.08em;
  text-shadow: 0 2px 12px rgba(212,176,80,0.3);
}
.subtitle {
  color: var(--text-dim);
  font-style: italic;
  margin-bottom: 2rem;
  font-size: 0.95rem;
  min-height: 1.4rem;
}
.home-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-bottom: 1rem;
}
.home-actions .btn {
  padding: 0.65rem 1.8rem;
  font-size: 1rem;
}
.welcome {
  margin-top: 0.5rem;
  color: var(--text-dim);
  font-size: 0.9rem;
}
.version {
  margin-top: 3rem;
  color: var(--text-dim);
  font-size: 0.75rem;
  opacity: 0.6;
}
</style>
