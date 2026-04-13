<script setup>
import { computed } from 'vue'
import { useDimensionStore } from '../stores/dimension'

const dimensionStore = useDimensionStore()

const targetLabel = computed(() => (
  dimensionStore.transitionTarget === 'PHYSICAL'
    ? '[ 物理实体舱 · PHYSICAL BAY ]'
    : '[ 盖亚演算仓 · GAIA ENGINE ]'
))
</script>

<template>
  <div v-if="dimensionStore.isTransitioning" class="dimension-overlay" aria-hidden="true">
    <div class="pixel-grid"></div>
    <div class="scan-lines"></div>
    <div class="transition-core">
      <span class="eyebrow">DIMENSION SHIFT</span>
      <strong>{{ targetLabel }}</strong>
      <p>扫描中，准备跨越到新的城市维度。</p>
    </div>
  </div>
</template>

<style scoped>
.dimension-overlay {
  position: fixed;
  inset: 0;
  z-index: 999;
  overflow: hidden;
  pointer-events: all;
  background:
    radial-gradient(circle at 50% 50%, rgba(47, 216, 255, 0.2), transparent 30%),
    linear-gradient(180deg, rgba(10, 25, 47, 0.28), rgba(10, 25, 47, 0.95)),
    #0a192f;
  animation: overlayPulse 420ms ease forwards;
}

.pixel-grid,
.scan-lines {
  position: absolute;
  inset: 0;
}

.pixel-grid {
  background-image:
    linear-gradient(rgba(115, 224, 255, 0.12) 1px, transparent 1px),
    linear-gradient(90deg, rgba(115, 224, 255, 0.12) 1px, transparent 1px);
  background-size: 18px 18px;
  transform: scale(1.18);
  filter: blur(0.2px);
  opacity: 0.55;
}

.scan-lines {
  background: repeating-linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.12) 0,
    rgba(255, 255, 255, 0.12) 2px,
    transparent 2px,
    transparent 9px
  );
  mix-blend-mode: screen;
  animation: scanMove 420ms linear forwards;
}

.transition-core {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  text-align: center;
  color: #e6f6ff;
}

.transition-core > * {
  grid-column: 1;
  grid-row: 1;
}

.transition-core strong {
  display: block;
  margin-top: 18px;
  font-size: clamp(24px, 4.2vw, 48px);
  letter-spacing: 0.04em;
}

.transition-core p {
  margin-top: 110px;
  font-size: 14px;
  color: rgba(230, 246, 255, 0.72);
}

.eyebrow {
  margin-top: -110px;
  font-size: 12px;
  letter-spacing: 0.32em;
  color: rgba(156, 230, 255, 0.88);
}

@keyframes overlayPulse {
  0% {
    opacity: 0;
    transform: scale(1.04);
  }
  20% {
    opacity: 1;
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes scanMove {
  0% {
    opacity: 0;
    transform: translateY(-18%);
  }
  20% {
    opacity: 0.95;
  }
  100% {
    opacity: 0.3;
    transform: translateY(12%);
  }
}
</style>
