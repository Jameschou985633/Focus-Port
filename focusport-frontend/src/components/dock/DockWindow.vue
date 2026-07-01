<script setup>
const props = defineProps({
  title: { type: String, required: true },
  icon: { type: String, default: '◆' },
  accent: { type: String, default: 'cyan' }
})

defineEmits(['close'])
</script>

<template>
  <section class="dock-window" :class="`accent-${props.accent}`">
    <header class="dock-header">
      <div class="dock-title">
        <span class="dock-icon">{{ icon }}</span>
        <span>{{ title }}</span>
      </div>
      <button class="dock-close" type="button" @click="$emit('close')">×</button>
    </header>
    <div class="dock-body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.dock-window {
  width: min(360px, calc(100vw - 24px));
  max-height: min(72vh, 760px);
  overflow: hidden;
  border-radius: 22px;
  border: 1.5px solid rgba(125, 220, 255, 0.45);
  background:
    linear-gradient(180deg, rgba(10, 20, 46, 0.96), rgba(5, 11, 28, 0.96)),
    rgba(8, 14, 28, 0.92);
  box-shadow: 0 26px 80px rgba(2, 8, 24, 0.58);
  backdrop-filter: blur(22px);
  color: #eef7ff;
}

.dock-window.accent-gold {
  border-color: rgba(255, 214, 102, 0.45);
}

.dock-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid rgba(125, 220, 255, 0.16);
  background: linear-gradient(180deg, rgba(37, 82, 160, 0.32), rgba(10, 20, 46, 0.12));
}

.dock-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0.03em;
}

.dock-icon {
  font-size: 16px;
}

.dock-close {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.08);
  color: #eef7ff;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}

.dock-body {
  max-height: calc(min(72vh, 760px) - 54px);
  overflow: auto;
  padding: 14px;
}

@media (max-width: 768px) {
  .dock-window {
    width: 100%;
    max-height: min(64vh, 620px);
    border-radius: 20px 20px 0 0;
  }
}
</style>
