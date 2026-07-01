<script setup>
import RealIsland3D from './RealIsland3D.vue'
import { WORLD_NAMES, composeWorldLabel } from '../constants/worldNames'

defineProps({
  title: {
    type: String,
    default: composeWorldLabel(WORLD_NAMES.physical)
  }
})

const emit = defineEmits(['activate'])
</script>

<template>
  <button type="button" class="preview-dock" @click="emit('activate')">
    <div class="preview-copy">
      <span class="eyebrow">3D DIMENSION NAVIGATION</span>
      <strong>{{ title }}</strong>
      <span>点击切入完整的 3D 实体工程坞。</span>
    </div>
    <div class="preview-window">
      <div class="preview-frame">
        <RealIsland3D preview-mode />
      </div>
      <div class="preview-sheen"></div>
    </div>
  </button>
</template>

<style scoped>
.preview-dock {
  position: relative;
  width: min(360px, calc(100vw - 28px));
  border: 1px solid rgba(115, 224, 255, 0.24);
  border-radius: 22px;
  padding: 14px;
  background:
    linear-gradient(180deg, rgba(12, 27, 59, 0.95), rgba(6, 12, 28, 0.96)),
    #08101e;
  color: #eef7ff;
  text-align: left;
  cursor: pointer;
  box-shadow: 0 24px 50px rgba(0, 0, 0, 0.34);
}

.preview-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.eyebrow {
  font-family: 'Roboto Mono', 'Consolas', monospace;
  font-size: 10px;
  letter-spacing: 0.22em;
  color: rgba(156, 230, 255, 0.82);
}

.preview-copy strong {
  font-size: 18px;
}

.preview-copy span:last-child {
  font-size: 12px;
  color: rgba(230, 246, 255, 0.72);
}

.preview-window {
  position: relative;
  height: 210px;
  border-radius: 18px;
  overflow: hidden;
  background: rgba(2, 8, 18, 0.9);
}

.preview-frame {
  position: absolute;
  inset: 0;
}

.preview-frame :deep(.city-scene-page) {
  pointer-events: none;
}

.preview-sheen {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(120deg, transparent 0%, rgba(115, 224, 255, 0.1) 38%, transparent 60%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.03), transparent 24%);
  pointer-events: none;
}
</style>
