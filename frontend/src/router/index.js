import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'

const routes = [
  { path: '/', name: 'Home', component: () => import('@/views/HomeView.vue') },
  { path: '/login', name: 'Login', component: () => import('@/views/LoginView.vue') },
  { path: '/game', name: 'Game', component: () => import('@/views/GameView.vue'), meta: { requiresAuth: true } },
  { path: '/battle', name: 'Battle', component: () => import('@/views/BattleView.vue'), meta: { requiresAuth: true } },
  { path: '/dungeon', name: 'Dungeon', component: () => import('@/views/DungeonView.vue'), meta: { requiresAuth: true } },
  { path: '/friends', name: 'Friends', component: () => import('@/views/FriendsView.vue'), meta: { requiresAuth: true } },
  { path: '/groups', name: 'Groups', component: () => import('@/views/GroupsView.vue'), meta: { requiresAuth: true } },
  { path: '/leaderboard', name: 'Leaderboard', component: () => import('@/views/LeaderboardView.vue') },
  { path: '/admin', name: 'Admin', component: () => import('@/views/AdminView.vue'), meta: { requiresAuth: true } },
  { path: '/verify-email', name: 'VerifyEmail', component: () => import('@/views/VerifyEmailView.vue') },
  { path: '/reset-password', name: 'ResetPassword', component: () => import('@/views/ResetPasswordView.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  if (to.meta.requiresAuth) {
    const auth = useAuthStore()
    if (!auth.checked) await auth.check()
    if (!auth.user) return { name: 'Login' }
  }
})

export default router
