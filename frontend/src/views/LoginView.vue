<template>
  <div class="login-page">
    <div class="login-box panel">
      <div class="login-crest">⚔</div>
      <h2 class="login-title">{{ mode === 'login' ? 'Sign In' : 'Create Account' }}</h2>

      <form @submit.prevent="submit" class="login-form">
        <div class="field">
          <label>Username</label>
          <input v-model="username" type="text" required autocomplete="username" placeholder="Your name…" />
        </div>
        <div class="field">
          <label>Password</label>
          <input v-model="password" type="password" required autocomplete="current-password" placeholder="••••••••" />
        </div>
        <div class="field" v-if="mode === 'register'">
          <label>Email <span class="text-dim">(optional)</span></label>
          <input v-model="email" type="email" placeholder="for password recovery" />
        </div>
        <div v-if="error" class="error-msg">{{ error }}</div>
        <button type="submit" class="btn btn-gold w-full" :disabled="busy">
          {{ busy ? 'Please wait…' : (mode === 'login' ? 'Enter' : 'Create Hero') }}
        </button>
      </form>

      <div class="login-switch">
        <span v-if="mode === 'login'">
          New to the realm? <a href="#" @click.prevent="mode='register'">Create account</a>
        </span>
        <span v-else>
          Already a hero? <a href="#" @click.prevent="mode='login'">Sign in</a>
        </span>
      </div>

      <div class="forgot-link" v-if="mode === 'login'">
        <a href="#" @click.prevent="showForgot = !showForgot">Forgot password?</a>
      </div>
      <div v-if="showForgot" class="forgot-form">
        <input v-model="forgotEmail" type="email" placeholder="Your email…" />
        <button class="btn btn-sm" @click="sendReset" :disabled="busy">Send Reset</button>
        <div v-if="resetMsg" class="text-green" style="font-size:0.8rem;margin-top:0.3rem">{{ resetMsg }}</div>
      </div>

      <router-link to="/" class="back-link">← Back to home</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'
import { api } from '@/api/index.js'

const auth = useAuthStore()
const router = useRouter()
const mode = ref('login')
const username = ref('')
const password = ref('')
const email = ref('')
const error = ref('')
const busy = ref(false)
const showForgot = ref(false)
const forgotEmail = ref('')
const resetMsg = ref('')

async function submit() {
  error.value = ''
  busy.value = true
  try {
    let r
    if (mode.value === 'login') {
      r = await auth.login(username.value, password.value)
    } else {
      r = await auth.register(username.value, password.value, email.value)
    }
    if (r.ok) {
      router.push('/game')
    } else {
      error.value = r.message || 'Something went wrong.'
    }
  } finally {
    busy.value = false
  }
}

async function sendReset() {
  if (!forgotEmail.value) return
  busy.value = true
  const r = await api.forgotPassword(forgotEmail.value).catch(() => ({ ok: false }))
  busy.value = false
  resetMsg.value = r.message || (r.ok ? 'Reset email sent!' : 'Failed to send.')
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(ellipse at center, #2a1a08 0%, #18140c 60%);
  padding: 1rem;
}
.login-box {
  width: 100%;
  max-width: 380px;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.login-crest { font-size: 2rem; color: var(--gold); text-align: center; }
.login-title {
  font-family: 'Cinzel', serif;
  font-size: 1.3rem;
  color: var(--gold);
  text-align: center;
}
.login-form { display: flex; flex-direction: column; gap: 0.75rem; }
.field { display: flex; flex-direction: column; gap: 0.25rem; }
.field label { font-size: 0.85rem; color: var(--text-dim); }
.field input { width: 100%; }
.error-msg {
  color: var(--red);
  font-size: 0.85rem;
  background: rgba(204,78,78,0.1);
  border: 1px solid var(--red-dark);
  padding: 0.4rem 0.6rem;
  border-radius: 3px;
}
.w-full { width: 100%; }
.login-switch { text-align: center; font-size: 0.85rem; color: var(--text-dim); }
.forgot-link { text-align: center; font-size: 0.8rem; }
.forgot-form { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
.forgot-form input { flex: 1; }
.back-link { display: block; text-align: center; font-size: 0.8rem; color: var(--text-dim); }
</style>
