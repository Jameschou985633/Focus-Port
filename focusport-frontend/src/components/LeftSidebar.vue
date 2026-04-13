<script setup>
import { computed } from 'vue'
import ExternalDatalink from './ExternalDatalink.vue'
import { WORLD_NAMES, composeWorldLabel } from '../constants/worldNames'

const props = defineProps({
  formattedTime: { type: String, default: '25:00' },
  isRunning: { type: Boolean, default: false },
  focusProgress: { type: Number, default: 0 },
  durationOptions: { type: Array, default: () => [15, 25, 30, 45, 60] },
  selectedDuration: { type: Number, default: 25 },
  selectedDifficulty: { type: String, default: 'L1' },
  focusEnergy: { type: Number, default: 0 },
  userGrowth: {
    type: Object,
    default: () => ({
      exp: 0,
      level: 1,
      discipline_score: 50,
      streak_days: 0,
      total_focus_minutes: 0
    })
  }
})

const emit = defineEmits([
  'start-focus',
  'change-duration',
  'change-difficulty'
])

const progressLabel = computed(() => `${Math.round((props.focusProgress || 0) * 100)}%`)
</script>

<template>
  <aside class="left-sidebar">
    <section class="sidebar-card pulse-card">
      <header class="card-header">
        <div>
          <p class="card-kicker">{{ WORLD_NAMES.pulseCore.en }}</p>
          <h2>{{ composeWorldLabel(WORLD_NAMES.pulseCore) }}</h2>
        </div>
        <span class="card-badge">{{ WORLD_NAMES.currency.zh }} {{ focusEnergy }}</span>
      </header>

      <div class="duration-pills">
        <button
          v-for="minutes in durationOptions"
          :key="minutes"
          type="button"
          class="pill"
          :class="{ active: selectedDuration === minutes }"
          :disabled="isRunning"
          @click="emit('change-duration', minutes)"
        >
          {{ minutes }}m
        </button>
      </div>

      <div class="time-display">{{ formattedTime }}</div>

      <div class="difficulty-panel">
        <div class="difficulty-header">
          <span>脑力负载</span>
          <strong>{{ selectedDifficulty === 'L2' ? 'High / L2' : 'Low / L1' }}</strong>
        </div>
        <div class="difficulty-options">
          <button
            type="button"
            class="difficulty-btn"
            :class="{ active: selectedDifficulty === 'L1' }"
            :disabled="isRunning"
            @click="emit('change-difficulty', 'L1')"
          >
            <span>Low (L1)</span>
            <small>日常阅读 / 整理笔记</small>
          </button>
          <button
            type="button"
            class="difficulty-btn"
            :class="{ active: selectedDifficulty === 'L2' }"
            :disabled="isRunning"
            @click="emit('change-difficulty', 'L2')"
          >
            <span>High (L2)</span>
            <small>刷题 / 写代码 / 深度复盘</small>
          </button>
        </div>
      </div>

      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${Math.max(0, Math.min(1, focusProgress)) * 100}%` }"></div>
      </div>
      <div class="status-line">
        <span>当前脉冲推进</span>
        <strong>{{ progressLabel }}</strong>
      </div>

      <div class="growth-grid">
        <div class="growth-item">
          <span class="label">等级</span>
          <strong>Lv.{{ userGrowth.level || 1 }}</strong>
        </div>
        <div class="growth-item">
          <span class="label">连续体</span>
          <strong>{{ userGrowth.streak_days || 0 }} 天</strong>
        </div>
        <div class="growth-item">
          <span class="label">自律值</span>
          <strong>{{ userGrowth.discipline_score || 0 }}</strong>
        </div>
      </div>

      <button type="button" class="launch-btn" :disabled="isRunning" @click="emit('start-focus')">
        {{ isRunning ? '脉冲点火中...' : '启动脉冲点火' }}
      </button>
    </section>

    <ExternalDatalink />
  </aside>
</template>

<style scoped>
.left-sidebar {
  position: absolute;
  top: 78px;
  left: 22px;
  width: min(380px, calc(100vw - 44px));
  display: flex;
  flex-direction: column;
  gap: 14px;
  z-index: 9;
  pointer-events: auto;
}

.sidebar-card {
  border-radius: 24px;
  padding: 18px;
  background:
    linear-gradient(180deg, rgba(16, 34, 74, 0.95), rgba(8, 16, 36, 0.96)),
    rgba(11, 18, 32, 0.86);
  border: 1.5px solid rgba(129, 214, 255, 0.34);
  box-shadow: 0 20px 54px rgba(4, 8, 22, 0.44);
  backdrop-filter: blur(18px);
  color: #eef7ff;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 14px;
}

.card-header h2 {
  margin: 0;
  font-size: 22px;
  text-shadow: 0 0 18px rgba(0, 255, 255, 0.16);
}

.card-kicker {
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(156, 223, 255, 0.72);
}

.card-badge {
  border-radius: 999px;
  padding: 6px 10px;
  background: rgba(92, 193, 255, 0.12);
  border: 1px solid rgba(115, 224, 255, 0.24);
  font-size: 12px;
  font-weight: 700;
}

.duration-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pill {
  border: none;
  border-radius: 999px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.08);
  color: #dbeeff;
  cursor: pointer;
  font-weight: 700;
}

.pill.active {
  background: linear-gradient(180deg, #48b7ff, #2e6fff);
  color: #fff;
}

.pill:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.time-display {
  margin: 18px 0 10px;
  font-size: 54px;
  line-height: 1;
  font-weight: 900;
  letter-spacing: 0.04em;
}

.difficulty-panel {
  margin: 0 0 14px;
  border-radius: 18px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(115, 224, 255, 0.16);
}

.difficulty-header {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 12px;
  color: rgba(222, 240, 255, 0.76);
}

.difficulty-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.difficulty-btn {
  border: 1px solid rgba(115, 224, 255, 0.18);
  border-radius: 14px;
  background: rgba(7, 16, 34, 0.8);
  color: #dbeeff;
  padding: 10px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  cursor: pointer;
  text-align: left;
}

.difficulty-btn span {
  font-size: 13px;
  font-weight: 800;
}

.difficulty-btn small {
  color: rgba(222, 240, 255, 0.66);
  line-height: 1.4;
}

.difficulty-btn.active {
  border-color: rgba(115, 224, 255, 0.42);
  background: linear-gradient(180deg, rgba(49, 120, 255, 0.34), rgba(18, 35, 78, 0.94));
  box-shadow: inset 0 0 0 1px rgba(129, 214, 255, 0.18);
}

.difficulty-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.progress-track {
  height: 14px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #7c74ff, #48d5ff);
}

.status-line {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: rgba(222, 240, 255, 0.76);
}

.growth-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin: 14px 0 16px;
}

.growth-item {
  border-radius: 16px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.05);
}

.growth-item .label {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  color: rgba(222, 240, 255, 0.7);
}

.launch-btn {
  width: 100%;
  min-height: 48px;
  border: none;
  border-radius: 16px;
  background: linear-gradient(180deg, #2fd8ff, #2d74ff);
  color: #fff;
  font-size: 15px;
  font-weight: 800;
  cursor: pointer;
}

.launch-btn:disabled {
  opacity: 0.58;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .left-sidebar {
    top: 70px;
    left: 12px;
    width: calc(100vw - 24px);
  }

  .difficulty-options,
  .growth-grid {
    grid-template-columns: 1fr;
  }
}
</style>
