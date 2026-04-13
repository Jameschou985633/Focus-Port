<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const menuItems = [
  { id: 'shop', icon: '🛒', label: '物质交换港', route: '/shop' },
  { id: 'vault', icon: '📦', label: '全息蓝图库', route: '/vault' },
  { id: 'collab', icon: '🤝', label: '舰队枢纽', route: '/collab' },
  { id: 'exam', icon: '📝', label: '协议编译站', route: '/exam' },
  { id: 'stats', icon: '📊', label: '数据档案', route: '/stats' },
  { id: 'more', icon: '⚙️', label: '更多功能', route: '/more' }
]

const handleNav = (route) => {
  if (route) router.push(route)
}
</script>

<template>
  <nav class="top-action-bar">
    <div class="bar-inner">
      <button
        v-for="item in menuItems"
        :key="item.id"
        type="button"
        class="action-btn"
        :title="item.label"
        @click="handleNav(item.route)"
      >
        <span class="action-icon">{{ item.icon }}</span>
        <span class="action-label">{{ item.label }}</span>
      </button>
    </div>
  </nav>
</template>

<style scoped>
.top-action-bar {
  position: fixed;
  bottom: 22px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 20;
  pointer-events: auto;
}

.bar-inner {
  display: flex;
  gap: 8px;
  padding: 10px 16px;
  background: linear-gradient(180deg, rgba(16, 34, 74, 0.92), rgba(8, 16, 36, 0.95));
  border: 1.5px solid rgba(129, 214, 255, 0.34);
  border-radius: 20px;
  box-shadow: 0 12px 40px rgba(4, 8, 22, 0.5);
  backdrop-filter: blur(18px);
}

.action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(115, 224, 255, 0.12);
  border-radius: 12px;
  color: #dbeeff;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 64px;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(115, 224, 255, 0.35);
  box-shadow: 0 0 16px rgba(72, 183, 255, 0.2);
}

.action-btn:active {
  transform: scale(0.96);
}

.action-icon {
  font-size: 20px;
  line-height: 1;
}

.action-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.03em;
  color: rgba(222, 240, 255, 0.8);
  text-align: center;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .top-action-bar {
    bottom: 12px;
    width: calc(100vw - 24px);
  }

  .bar-inner {
    width: 100%;
    justify-content: space-around;
    padding: 8px 10px;
  }

  .action-btn {
    min-width: 0;
    padding: 6px 8px;
  }

  .action-label {
    font-size: 9px;
  }
}
</style>
