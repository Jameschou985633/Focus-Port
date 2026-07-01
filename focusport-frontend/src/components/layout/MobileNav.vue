<script setup>
import { useRoute, useRouter } from 'vue-router'
import '../../assets/focus-hud.css'

const router = useRouter()
const route = useRoute()

const mainNavItems = [
  { path: '/island', icon: 'DOCK', label: '实体工程坞' },
  { path: '/shop', icon: 'EX', label: '交换港' },
  { path: '/exam', icon: 'PR', label: '协议编译站' },
  { path: '/more', icon: 'CTRL', label: '舰长档案' }
]

const isActive = (path) => route.path.startsWith(path)
</script>

<template>
  <nav class="mobile-nav focus-hud-panel">
    <button
      v-for="item in mainNavItems"
      :key="item.path"
      type="button"
      :class="['nav-item', { active: isActive(item.path) }]"
      @click="router.push(item.path)"
    >
      <span class="nav-icon">{{ item.icon }}</span>
      <span class="nav-label">{{ item.label }}</span>
    </button>
  </nav>
</template>

<style scoped>
.mobile-nav {
  position: fixed;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  width: min(420px, calc(100vw - 24px));
  min-height: 80px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  border-radius: 22px;
  padding: 10px;
  z-index: 12;
}

.nav-item {
  min-height: 56px;
  border: 1px solid rgba(132, 211, 255, 0.45);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(35, 113, 202, 0.9), rgba(12, 46, 111, 0.95));
  color: #d8f3ff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  cursor: pointer;
  box-shadow: 0 0 0 2px rgba(3, 14, 36, 0.28) inset;
}

.nav-item.active {
  color: #ffffff;
  filter: brightness(1.12);
}

.nav-icon {
  font-size: 12px;
  font-weight: 800;
}

.nav-label {
  font-size: 10px;
  font-weight: 700;
  text-align: center;
}

@media (min-width: 769px) {
  .mobile-nav {
    display: none;
  }
}
</style>
