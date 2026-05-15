<template>
  <transition name="toast-fade">
    <div v-if="game.toast" class="toast-box" :style="{ color: game.toast.color }">
      {{ game.toast.msg }}
    </div>
  </transition>
</template>

<script setup>
import { useGameStore } from '@/stores/game.js'
const game = useGameStore()
</script>

<style scoped>
.toast-box {
  position: fixed;
  bottom: 1.5rem;
  left: 50%;
  transform: translateX(-50%);
  background: var(--bg-panel);
  border: 1px solid var(--border-bright);
  padding: 0.6rem 1.2rem;
  border-radius: 4px;
  font-size: 0.95rem;
  z-index: 9999;
  max-width: 420px;
  text-align: center;
  box-shadow: 0 4px 16px rgba(0,0,0,0.6);
  pointer-events: none;
}
.toast-fade-enter-active, .toast-fade-leave-active { transition: opacity 0.3s; }
.toast-fade-enter-from, .toast-fade-leave-to { opacity: 0; }
</style>
