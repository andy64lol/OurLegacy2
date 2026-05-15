<template>
  <div class="verify-page">
    <div class="verify-box panel">
      <h2 class="panel-title">Email Verification</h2>
      <div v-if="checking" class="text-dim">Verifying…</div>
      <div v-else-if="result" :class="result.ok ? 'text-green' : 'text-red'">{{ result.message }}</div>
      <div v-else class="text-dim">No token provided.</div>
      <router-link to="/login" class="btn mt-2">Back to Login</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/index.js'

const route = useRoute()
const checking = ref(true)
const result = ref(null)

onMounted(async () => {
  const token = route.query.token
  if (!token) { checking.value = false; return }
  const r = await fetch(`/verify-email?token=${token}`, { credentials: 'include' }).then(r => r.json()).catch(() => null)
  result.value = r || { ok: false, message: 'Verification failed.' }
  checking.value = false
})
</script>

<style scoped>
.verify-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 1rem; }
.verify-box { max-width: 400px; width: 100%; text-align: center; display: flex; flex-direction: column; gap: 1rem; }
</style>
