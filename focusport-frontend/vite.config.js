import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  base: './',  // GitHub Pages 相对路径
  server: {
    host: '0.0.0.0',  // 允许局域网访问
    port: 5174,
    proxy: {
      // 本地开发时代理 API 请求到后端
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets'
  }
})
