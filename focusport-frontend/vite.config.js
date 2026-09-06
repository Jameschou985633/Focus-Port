import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

const devApiTarget = process.env.VITE_DEV_API_TARGET || 'http://127.0.0.1:8005'
const devWsTarget = devApiTarget.replace(/^http/, 'ws')

export default defineConfig({
  plugins: [
    vue({
      template: {
        compilerOptions: {
          isCustomElement: (tag) =>
            ((/^Tres[A-Z]/.test(tag) || tag.startsWith('tres-')) &&
              !['TresCanvas', 'TresCanvasContext', 'TresLeches', 'TresScene'].includes(tag)) ||
            tag === 'primitive'
        }
      }
    }),
    tailwindcss()
  ],
  base: './',
  server: {
    host: '0.0.0.0',
    port: 5174,
    proxy: {
      '/api': {
        target: devApiTarget,
        changeOrigin: true
      },
      '/ws': {
        target: devWsTarget,
        ws: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets'
  }
})
