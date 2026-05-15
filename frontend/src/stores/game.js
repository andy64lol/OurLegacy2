import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/index.js'

export const useGameStore = defineStore('game', () => {
  const state = ref(null)
  const loading = ref(false)
  const messages = ref([])
  const toast = ref(null)
  let toastTimer = null

  const player = computed(() => state.value?.player || null)
  const area = computed(() => state.value?.area || null)
  const inBattle = computed(() => state.value?.in_battle || false)
  const inventory = computed(() => state.value?.inventory || [])

  function showToast(msg, color = 'var(--gold)', duration = 3500) {
    if (toastTimer) clearTimeout(toastTimer)
    toast.value = { msg, color }
    toastTimer = setTimeout(() => { toast.value = null }, duration)
  }

  async function refresh() {
    loading.value = true
    try {
      const r = await api.gameState()
      if (r.ok) {
        state.value = r
        if (r.messages) messages.value = r.messages
      }
    } finally {
      loading.value = false
    }
  }

  async function act(fn, successColor = 'var(--green-bright)') {
    loading.value = true
    try {
      const r = await fn()
      if (r.ok !== false) {
        if (r.player) {
          if (state.value) {
            state.value.player = r.player
            if (r.inventory !== undefined) state.value.inventory = r.inventory
            if (r.in_battle !== undefined) state.value.in_battle = r.in_battle
            if (r.battle !== undefined) state.value.battle = r.battle
            if (r.area !== undefined) state.value.area = r.area
          }
        }
        const msg = r.message || r.msg || ''
        if (msg) showToast(msg, successColor)
      } else {
        showToast(r.message || 'Action failed.', 'var(--red)')
      }
      return r
    } catch (e) {
      showToast('Network error.', 'var(--red)')
      return { ok: false }
    } finally {
      loading.value = false
    }
  }

  function clearState() {
    state.value = null
    messages.value = []
  }

  return { state, loading, messages, toast, player, area, inBattle, inventory, refresh, act, showToast, clearState }
})
