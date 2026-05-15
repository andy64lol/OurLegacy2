import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api/index.js'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const checked = ref(false)

  async function check() {
    try {
      const r = await api.sessionCheck()
      if (r.logged_in) {
        user.value = { username: r.username, user_id: r.user_id }
      } else {
        user.value = null
      }
    } catch {
      user.value = null
    }
    checked.value = true
  }

  async function login(username, password) {
    const r = await api.login({ username, password })
    if (r.ok) {
      user.value = { username: r.username || username, user_id: r.user_id }
    }
    return r
  }

  async function register(username, password, email) {
    const r = await api.register({ username, password, email })
    if (r.ok) {
      user.value = { username: r.username || username, user_id: r.user_id }
    }
    return r
  }

  async function logout() {
    await api.logout()
    user.value = null
  }

  return { user, checked, check, login, register, logout }
})
