<template>
  <div class="reset-page">
    <div class="reset-box panel">
      <h2 class="panel-title">Reset Password</h2>
      <div v-if="!token" class="text-red">Invalid or missing reset token.</div>
      <form v-else @submit.prevent="submit" class="reset-form">
        <div class="field">
          <label>New Password</label>
          <input v-model="password" type="password" required placeholder="••••••••" />
        </div>
        <div class="field">
          <label>Confirm Password</label>
          <input v-model="confirm" type="password" required placeholder="••••••••" />
        </div>
        <div v-if="error" class="text-red">{{ error }}</div>
        <div v-if="success" class="text-green">{{ success }}</div>
        <button type="submit" class="btn btn-gold w-full" :disabled="busy">Reset Password</button>
      </form>
      <router-link to="/login" class="btn mt-1">Back to Login</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/index.js'

const route = useRoute()
const token = ref('')
const password = ref('')
const confirm = ref('')
const error = ref('')
const success = ref('')
const busy = ref(false)

onMounted(() => { token.value = route.query.token || '' })

async function submit() {
  error.value = ''
  if (password.value !== confirm.value) { error.value = 'Passwords do not match.'; return }
  busy.value = true
  const r = await api.resetPassword({ token: token.value, new_password: password.value }).catch(() => ({ ok: false }))
  busy.value = false
  if (r.ok) success.value = 'Password reset! You may now log in.'
  else error.value = r.message || 'Reset failed.'
}
</script>

<style scoped>
.reset-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 1rem; }
.reset-box { max-width: 380px; width: 100%; display: flex; flex-direction: column; gap: 1rem; }
.reset-form { display: flex; flex-direction: column; gap: 0.75rem; }
.field { display: flex; flex-direction: column; gap: 0.25rem; }
.field label { font-size: 0.85rem; color: var(--text-dim); }
.field input { width: 100%; }
.w-full { width: 100%; }
</style>
