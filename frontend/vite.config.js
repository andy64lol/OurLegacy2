import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: '../static/dist',
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    proxy: {
      '/api': { target: 'http://localhost:5000', changeOrigin: true, credentials: true },
      '/socket.io': { target: 'http://localhost:5000', ws: true, changeOrigin: true },
      '/game_assets': { target: 'http://localhost:5000', changeOrigin: true },
      '/ping': { target: 'http://localhost:5000', changeOrigin: true },
    },
  },
})
