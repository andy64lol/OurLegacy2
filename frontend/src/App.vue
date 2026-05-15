<template>
  <div class="app-root">
    <NavBar v-if="showNav" />
    <router-view v-if="authChecked" />
    <div v-else class="loading-screen">
      <div class="loading-crest">⚔</div>
      <div class="loading-text">Our Legacy</div>
    </div>
    <ToastMsg />
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'
import NavBar from '@/components/NavBar.vue'
import ToastMsg from '@/components/ToastMsg.vue'

const auth = useAuthStore()
const route = useRoute()

const authChecked = computed(() => auth.checked)
const showNav = computed(() => auth.user && !['Login', 'Home', 'VerifyEmail', 'ResetPassword'].includes(route.name))

onMounted(() => auth.check())
</script>

<style>
:root {
  --slate-darkest: #1e1e26;
  --slate-dark: #2e2e38;
  --slate-mid: #484858;
  --slate-light: #686878;
  --slate-bright: #8888a0;
  --wood-darkest: #241408;
  --wood-dark: #46240e;
  --wood-mid: #70421c;
  --wood-light: #a06030;
  --wood-bright: #c47c40;
  --gold: #d4b050;
  --gold-bright: #e8c860;
  --gold-dim: #907020;
  --text-light: #ddc89e;
  --text-bright: #f0e8d8;
  --text-dim: #847868;
  --text-dark: #281c0e;
  --red: #cc4e4e;
  --red-dark: #7a2828;
  --green: #547848;
  --green-bright: #7abc58;
  --mana-blue: #3c78b8;
  --mana-bright: #5898dc;
  --exp-purple: #8858b4;
  --border: #4e3e2e;
  --border-bright: #6e4e38;
  --bg-main: #18140c;
  --bg-panel: #24201a;
  --bg-panel-dark: #1c1814;
  --rarity-common: #909090;
  --rarity-uncommon: #50a850;
  --rarity-rare: #3888c8;
  --rarity-epic: #a840cc;
  --rarity-legendary: #d8bc30;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg-main);
  color: var(--text-light);
  font-family: 'IM Fell English', serif;
  min-height: 100vh;
}
a { color: var(--gold); text-decoration: none; }
a:hover { color: var(--gold-bright); }
button { cursor: pointer; font-family: inherit; }
input, select, textarea {
  font-family: inherit;
  background: var(--bg-panel-dark);
  border: 1px solid var(--border);
  color: var(--text-light);
  padding: 0.4rem 0.6rem;
  border-radius: 3px;
  outline: none;
}
input:focus, select:focus, textarea:focus { border-color: var(--gold-dim); }
.btn {
  padding: 0.45rem 1.1rem;
  border: 1px solid var(--border-bright);
  background: var(--bg-panel);
  color: var(--text-light);
  border-radius: 3px;
  font-size: 0.9rem;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.btn:hover { background: var(--wood-dark); border-color: var(--gold-dim); color: var(--gold-bright); }
.btn-gold { background: var(--gold-dim); border-color: var(--gold); color: #fff8e0; }
.btn-gold:hover { background: var(--gold); border-color: var(--gold-bright); }
.btn-red { background: var(--red-dark); border-color: var(--red); color: #ffe0e0; }
.btn-red:hover { background: var(--red); }
.btn-sm { padding: 0.25rem 0.65rem; font-size: 0.8rem; }
.panel {
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1rem;
}
.panel-title {
  font-family: 'Cinzel', serif;
  color: var(--gold);
  font-size: 1rem;
  margin-bottom: 0.75rem;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.4rem;
  letter-spacing: 0.05em;
}
.bar-wrap { background: #111; border-radius: 4px; overflow: hidden; height: 12px; }
.bar-fill { height: 100%; border-radius: 4px; transition: width 0.3s; }
.bar-hp { background: var(--red); }
.bar-mp { background: var(--mana-blue); }
.bar-xp { background: var(--exp-purple); }
.tag { display: inline-block; padding: 0.1rem 0.45rem; border-radius: 10px; font-size: 0.75rem; margin: 0.1rem; }
.tag-boss { background: var(--red-dark); color: #ffc0c0; border: 1px solid var(--red); }
.tag-gold { background: #3a2800; color: var(--gold-bright); border: 1px solid var(--gold-dim); }
.text-gold { color: var(--gold); }
.text-green { color: var(--green-bright); }
.text-red { color: var(--red); }
.text-dim { color: var(--text-dim); }
.text-mana { color: var(--mana-bright); }
.text-bright { color: var(--text-bright); }
.mt-1 { margin-top: 0.5rem; }
.mt-2 { margin-top: 1rem; }
.mb-1 { margin-bottom: 0.5rem; }
.mb-2 { margin-bottom: 1rem; }
.gap-1 { gap: 0.5rem; }
.gap-2 { gap: 1rem; }
.flex { display: flex; }
.flex-wrap { flex-wrap: wrap; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }
.grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; }
.loading-screen {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100vh; gap: 1rem;
}
.loading-crest { font-size: 3rem; color: var(--gold); animation: pulse 1.5s infinite; }
.loading-text { font-family: 'Cinzel', serif; font-size: 1.5rem; color: var(--gold-dim); }
@keyframes pulse { 0%,100% { opacity: 0.4; } 50% { opacity: 1; } }
.app-root { min-height: 100vh; display: flex; flex-direction: column; }
.scroll-y { overflow-y: auto; }
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg-panel-dark); }
::-webkit-scrollbar-thumb { background: var(--border-bright); border-radius: 3px; }
</style>
