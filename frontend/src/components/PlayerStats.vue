<template>
  <div class="stats-block">
    <div class="stat-name">{{ p.name }} <span class="text-dim">Lv.{{ p.level }}</span> <span class="text-dim" style="font-size:0.8rem">{{ p.class }} {{ p.race }}</span></div>
    <div class="stat-row">
      <span class="text-red">HP</span>
      <div class="bar-wrap flex-1"><div class="bar-fill bar-hp" :style="{ width: pct(p.hp, p.max_hp) }"></div></div>
      <span class="stat-val text-red">{{ p.hp }}/{{ p.max_hp }}</span>
    </div>
    <div class="stat-row">
      <span class="text-mana">MP</span>
      <div class="bar-wrap flex-1"><div class="bar-fill bar-mp" :style="{ width: pct(p.mp, p.max_mp) }"></div></div>
      <span class="stat-val text-mana">{{ p.mp }}/{{ p.max_mp }}</span>
    </div>
    <div class="stat-row">
      <span style="color:var(--exp-purple)">XP</span>
      <div class="bar-wrap flex-1"><div class="bar-fill bar-xp" :style="{ width: pct(p.xp, p.xp_needed) }"></div></div>
      <span class="stat-val" style="color:var(--exp-purple)">{{ p.xp }}/{{ p.xp_needed }}</span>
    </div>
    <div class="stat-chips">
      <span class="chip text-gold">⚙ {{ p.attack }} ATK</span>
      <span class="chip">🛡 {{ p.defense }} DEF</span>
      <span class="chip">⚡ {{ p.speed }} SPD</span>
      <span class="chip text-gold">💰 {{ p.gold }}g</span>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({ p: Object })
const pct = (v, m) => m > 0 ? Math.min(100, Math.round(v / m * 100)) + '%' : '0%'
</script>

<style scoped>
.stats-block { display: flex; flex-direction: column; gap: 0.4rem; }
.stat-name { font-family: 'Cinzel', serif; font-size: 0.95rem; color: var(--gold); margin-bottom: 0.2rem; }
.stat-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8rem; }
.stat-row > span:first-child { width: 1.8rem; flex-shrink: 0; font-size: 0.75rem; }
.bar-wrap { flex: 1; }
.stat-val { width: 5rem; text-align: right; font-size: 0.75rem; flex-shrink: 0; }
.stat-chips { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.3rem; }
.chip { font-size: 0.75rem; padding: 0.15rem 0.5rem; background: var(--bg-panel-dark); border: 1px solid var(--border); border-radius: 3px; color: var(--text-dim); }
</style>
