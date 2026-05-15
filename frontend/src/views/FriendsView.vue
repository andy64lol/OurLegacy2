<template>
  <div class="friends-page">
    <div class="friends-container">
      <h2 class="page-title">👥 Friends & Messages</h2>

      <!-- Tabs -->
      <div class="tab-bar">
        <button v-for="t in tabs" :key="t.id" class="tab-btn" :class="{ active: tab === t.id }" @click="tab = t.id">{{ t.label }}</button>
      </div>

      <!-- Friends list -->
      <template v-if="tab === 'friends'">
        <div class="panel">
          <div class="panel-title">Friends</div>
          <div class="add-friend">
            <input v-model="addTarget" placeholder="Username…" @keydown.enter="sendRequest" />
            <button class="btn btn-sm" @click="sendRequest" :disabled="busy">Add Friend</button>
          </div>
          <div v-if="!friends.length && !pendingIn.length" class="text-dim mt-1">No friends yet.</div>

          <!-- Pending incoming -->
          <div v-if="pendingIn.length" class="friend-section">
            <div class="section-label text-dim">Requests Received</div>
            <div v-for="f in pendingIn" :key="f.username" class="friend-row">
              <span class="friend-name">{{ f.username }}</span>
              <div class="friend-actions">
                <button class="btn btn-sm btn-gold" @click="respond(f.username, 'accept')">Accept</button>
                <button class="btn btn-sm btn-red" @click="respond(f.username, 'decline')">Decline</button>
              </div>
            </div>
          </div>

          <!-- Active friends -->
          <div v-if="friends.length" class="friend-section">
            <div class="section-label text-dim">Friends ({{ friends.length }})</div>
            <div v-for="f in friends" :key="f.username" class="friend-row">
              <span class="friend-name text-gold">{{ f.username }}</span>
              <div class="friend-actions">
                <button class="btn btn-sm" @click="openDm(f.username)">Message</button>
                <button class="btn btn-sm btn-red" @click="removeFriend(f.username)">Remove</button>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- DM -->
      <template v-if="tab === 'dm'">
        <div class="panel dm-panel">
          <div class="panel-title">Direct Messages</div>
          <div class="dm-target-row">
            <input v-model="dmTarget" placeholder="Username…" @keydown.enter="loadDm" />
            <button class="btn btn-sm" @click="loadDm" :disabled="busy">Open</button>
          </div>
          <div v-if="dmTarget && dmMessages.length" class="dm-messages scroll-y" ref="dmEl">
            <div v-for="(m, i) in dmMessages" :key="i" class="dm-msg" :class="{ mine: m.from_username === myName }">
              <span class="dm-sender text-dim">{{ m.from_username }}</span>
              <span class="dm-text">{{ m.message }}</span>
            </div>
          </div>
          <div v-if="dmTarget" class="dm-input-row">
            <input v-model="dmText" placeholder="Message…" @keydown.enter="sendDm" />
            <button class="btn btn-sm btn-gold" @click="sendDm" :disabled="busy">Send</button>
          </div>
        </div>
      </template>

      <!-- Block list -->
      <template v-if="tab === 'blocked'">
        <div class="panel">
          <div class="panel-title">Blocked Users</div>
          <div class="add-friend">
            <input v-model="blockTarget" placeholder="Username to block…" />
            <button class="btn btn-sm btn-red" @click="doBlock" :disabled="busy">Block</button>
          </div>
          <div v-if="!blocked.length" class="text-dim mt-1">No blocked users.</div>
          <div v-for="u in blocked" :key="u" class="friend-row">
            <span class="friend-name text-dim">{{ u }}</span>
            <button class="btn btn-sm" @click="doUnblock(u)">Unblock</button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useAuthStore } from '@/stores/auth.js'
import { useGameStore } from '@/stores/game.js'
import { api } from '@/api/index.js'

const auth = useAuthStore()
const game = useGameStore()
const myName = auth.user?.username

const tab = ref('friends')
const tabs = [
  { id: 'friends', label: '👥 Friends' },
  { id: 'dm', label: '💬 Messages' },
  { id: 'blocked', label: '🚫 Blocked' },
]

const friends = ref([])
const pendingIn = ref([])
const addTarget = ref('')
const busy = ref(false)

const dmTarget = ref('')
const dmMessages = ref([])
const dmText = ref('')
const dmEl = ref(null)

const blocked = ref([])
const blockTarget = ref('')

async function loadFriends() {
  const r = await api.friends().catch(() => null)
  if (r?.ok) {
    friends.value = (r.friends || []).filter(f => f.status === 'accepted')
    pendingIn.value = (r.friends || []).filter(f => f.status === 'pending' && f.direction === 'incoming')
  }
}

async function sendRequest() {
  if (!addTarget.value.trim()) return
  busy.value = true
  const r = await api.friendRequest(addTarget.value.trim())
  busy.value = false
  game.showToast(r.message || (r.ok ? 'Request sent.' : 'Failed.'), r.ok ? 'var(--green-bright)' : 'var(--red)')
  addTarget.value = ''
  await loadFriends()
}

async function respond(username, action) {
  busy.value = true
  await api.friendRespond(username, action)
  busy.value = false
  await loadFriends()
}

async function removeFriend(username) {
  if (!confirm(`Remove ${username}?`)) return
  await api.friendRemove(username)
  await loadFriends()
}

function openDm(username) {
  dmTarget.value = username
  tab.value = 'dm'
  loadDm()
}

async function loadDm() {
  if (!dmTarget.value.trim()) return
  busy.value = true
  const r = await api.dmGet(dmTarget.value.trim())
  busy.value = false
  if (r?.ok) {
    dmMessages.value = r.messages || []
    await nextTick()
    if (dmEl.value) dmEl.value.scrollTop = dmEl.value.scrollHeight
  }
}

async function sendDm() {
  if (!dmText.value.trim() || !dmTarget.value) return
  busy.value = true
  const r = await api.dmSend(dmTarget.value, dmText.value.trim())
  busy.value = false
  if (r.ok) { dmText.value = ''; await loadDm() }
  else game.showToast(r.message || 'Failed to send.', 'var(--red)')
}

async function loadBlocked() {
  const r = await api.blockList().catch(() => null)
  blocked.value = r?.blocked || []
}

async function doBlock() {
  if (!blockTarget.value.trim()) return
  await api.block(blockTarget.value.trim(), 'block')
  blockTarget.value = ''
  await loadBlocked()
}

async function doUnblock(u) {
  await api.block(u, 'unblock')
  await loadBlocked()
}

onMounted(() => { loadFriends(); loadBlocked() })
</script>

<style scoped>
.friends-page { flex: 1; padding: 1rem; overflow-y: auto; }
.friends-container { max-width: 680px; margin: 0 auto; display: flex; flex-direction: column; gap: 0.75rem; }
.page-title { font-family: 'Cinzel', serif; color: var(--gold); font-size: 1.3rem; }
.tab-bar { display: flex; gap: 0.5rem; }
.tab-btn { padding: 0.35rem 0.8rem; font-size: 0.85rem; border: 1px solid var(--border); background: var(--bg-panel-dark); color: var(--text-dim); border-radius: 3px; cursor: pointer; }
.tab-btn.active { background: var(--wood-dark); border-color: var(--gold-dim); color: var(--gold); }
.add-friend { display: flex; gap: 0.5rem; margin-bottom: 0.75rem; }
.add-friend input { flex: 1; }
.friend-section { display: flex; flex-direction: column; gap: 0.35rem; margin-top: 0.5rem; }
.section-label { font-size: 0.8rem; border-bottom: 1px solid var(--border); padding-bottom: 0.25rem; margin-bottom: 0.35rem; }
.friend-row { display: flex; align-items: center; justify-content: space-between; padding: 0.4rem 0; border-bottom: 1px solid rgba(78,62,46,0.3); }
.friend-name { font-size: 0.9rem; }
.friend-actions { display: flex; gap: 0.4rem; }
.dm-panel { display: flex; flex-direction: column; gap: 0.75rem; }
.dm-target-row { display: flex; gap: 0.5rem; }
.dm-target-row input { flex: 1; }
.dm-messages { max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 0.35rem; padding: 0.5rem; background: var(--bg-panel-dark); border-radius: 3px; }
.dm-msg { display: flex; flex-direction: column; max-width: 80%; }
.dm-msg.mine { align-self: flex-end; }
.dm-sender { font-size: 0.72rem; }
.dm-text { font-size: 0.88rem; background: var(--bg-panel); padding: 0.3rem 0.6rem; border-radius: 3px; border: 1px solid var(--border); }
.mine .dm-text { background: var(--wood-darkest); border-color: var(--gold-dim); }
.dm-input-row { display: flex; gap: 0.5rem; }
.dm-input-row input { flex: 1; }
</style>
