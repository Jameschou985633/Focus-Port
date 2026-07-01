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
  },
  mode: { type: String, default: 'focus' },
  completedSessions: { type: Number, default: 0 }
})

const emit = defineEmits([
  'start-focus',
  'change-duration',
  'change-difficulty'
])

const isBreak = computed(() => props.mode === 'break')
const progressLabel = computed(() => `${Math.round((props.focusProgress || 0) * 100)}%`)

const ringRadius = 44
const ringCircumference = 2 * Math.PI * ringRadius
const ringOffset = computed(() => ringCircumference * (1 - Math.max(0, Math.min(1, props.focusProgress))))
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

      <!-- Duration pills (hidden during break) -->
      <div v-if="!isBreak" class="duration-pills">
        <button
          v-for="minutes in durationOptions"
          :key="minutes"
          type="button"
          class="pill"
          :class="{ active: selectedDuration === minutes }"
          :disabled="isRunning"
          @click="emit('change-duration', minutes)"
        >
          {{ minutes }}
        </button>
      </div>

      <!-- Timer ring -->
      <div class="timer-row">
        <div class="ring-wrap">
          <svg class="ring-svg" viewBox="0 0 120 120" aria-hidden="true">
            <defs>
              <linearGradient v-if="!isBreak" id="sbGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#5ce3ff" />
                <stop offset="100%" stop-color="#63ffad" />
              </linearGradient>
              <linearGradient v-else id="sbGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffb757" />
                <stop offset="100%" stop-color="#ff7147" />
              </linearGradient>
            </defs>
            <circle class="ring-base" cx="60" cy="60" :r="ringRadius" />
            <circle
              class="ring-progress"
              cx="60"
              cy="60"
              :r="ringRadius"
              :stroke-dasharray="ringCircumference"
              :stroke-dashoffset="ringOffset"
            />
          </svg>
          <div class="ring-inner">
            <span class="ring-pct">{{ progressLabel }}</span>
          </div>
        </div>
        <div class="timer-info">
          <strong class="timer-value">{{ formattedTime }}</strong>
          <span class="timer-mode">{{ isBreak ? '休息恢复' : '专注推进' }}</span>
          <span v-if="completedSessions > 0" class="timer-sessions">今日 {{ completedSessions }} 轮</span>
        </div>
      </div>

      <!-- Difficulty (hidden during break) -->
      <div v-if="!isBreak" class="diff-row">
        <button
          type="button"
          class="diff-btn"
          :class="{ active: selectedDifficulty === 'L1' }"
          :disabled="isRunning"
          @click="emit('change-difficulty', 'L1')"
        >
          L1 日常
        </button>
        <button
          type="button"
          class="diff-btn"
          :class="{ active: selectedDifficulty === 'L2' }"
          :disabled="isRunning"
          @click="emit('change-difficulty', 'L2')"
        >
          L2 硬核
        </button>
      </div>

      <!-- Growth stats -->
      <div class="growth-row">
        <div class="growth-item">
          <span class="label">Lv</span>
          <strong>{{ userGrowth.level || 1 }}</strong>
        </div>
        <div class="growth-item">
          <span class="label">连续</span>
          <strong>{{ userGrowth.streak_days || 0 }}d</strong>
        </div>
        <div class="growth-item">
          <span class="label">自律</span>
          <strong>{{ userGrowth.discipline_score || 0 }}</strong>
        </div>
      </div>

      <!-- Launch -->
      <button
        v-if="!isBreak"
        type="button"
        class="launch-btn"
        :disabled="isRunning"
        @click="emit('start-focus')"
      >
        {{ isRunning ? '脉冲点火中...' : '启动脉冲点火' }}
      </button>
      <button
        v-else
        type="button"
        class="launch-btn break-btn"
        disabled
      >
        休息恢复中...
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
  width: min(340px, calc(100vw - 44px));
  display: flex;
  flex-direction: column;
  gap: 14px;
  z-index: 9;
  pointer-events: auto;
}

.sidebar-card {
  border-radius: 24px;
  padding: 16px;
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
  margin-bottom: 12px;
}

.card-header h2 {
  margin: 0;
  font-size: 20px;
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
  padding: 5px 10px;
  background: rgba(92, 193, 255, 0.12);
  border: 1px solid rgba(115, 224, 255, 0.24);
  font-size: 11px;
  font-weight: 700;
}

/* Duration pills */
.duration-pills {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
}

.pill {
  border: none;
  border-radius: 999px;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.08);
  color: #dbeeff;
  cursor: pointer;
  font-weight: 700;
  font-size: 12px;
}

.pill.active {
  background: linear-gradient(180deg, #48b7ff, #2e6fff);
  color: #fff;
}

.pill:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* Timer row: ring + info side by side */
.timer-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 10px;
}

.ring-wrap {
  position: relative;
  flex-shrink: 0;
  width: 100px;
  height: 100px;
}

.ring-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
  filter: drop-shadow(0 0 10px rgba(72, 183, 255, 0.18));
}

.ring-base,
.ring-progress {
  fill: none;
  stroke-width: 7;
}

.ring-base {
  stroke: rgba(255, 255, 255, 0.08);
}

.ring-progress {
  stroke: url(#sbGrad);
  stroke-linecap: round;
  transition: stroke-dashoffset 320ms linear;
}

.ring-inner {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
}

.ring-pct {
  font-size: 14px;
  font-weight: 800;
  color: rgba(219, 238, 255, 0.72);
  font-family: var(--font-mono, 'Roboto Mono', monospace);
}

.timer-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.timer-value {
  font-size: 38px;
  line-height: 1;
  font-weight: 900;
  letter-spacing: 0.04em;
  font-family: var(--font-mono, 'Roboto Mono', monospace);
  text-shadow: 0 0 18px rgba(95, 231, 255, 0.16);
}

.timer-mode {
  font-size: 12px;
  color: rgba(219, 238, 255, 0.55);
  letter-spacing: 0.08em;
}

.timer-sessions {
  font-size: 11px;
  color: #83e7ff;
}

/* Difficulty row */
.diff-row {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.diff-btn {
  flex: 1;
  border: 1px solid rgba(115, 224, 255, 0.18);
  border-radius: 12px;
  padding: 8px 10px;
  background: rgba(7, 16, 34, 0.8);
  color: #dbeeff;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  text-align: center;
}

.diff-btn.active {
  border-color: rgba(115, 224, 255, 0.42);
  background: linear-gradient(180deg, rgba(49, 120, 255, 0.34), rgba(18, 35, 78, 0.94));
}

.diff-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* Growth row */
.growth-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.growth-item {
  border-radius: 12px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.05);
  text-align: center;
}

.growth-item .label {
  display: block;
  margin-bottom: 4px;
  font-size: 10px;
  color: rgba(222, 240, 255, 0.6);
}

.growth-item strong {
  font-size: 14px;
}

/* Launch button */
.launch-btn {
  width: 100%;
  min-height: 44px;
  border: none;
  border-radius: 14px;
  background: linear-gradient(180deg, #2fd8ff, #2d74ff);
  color: #fff;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
}

.launch-btn:disabled {
  opacity: 0.58;
  cursor: not-allowed;
}

.break-btn {
  background: linear-gradient(180deg, #ffb757, #ff7147);
}

@media (max-width: 768px) {
  .left-sidebar {
    top: 70px;
    left: 12px;
    width: calc(100vw - 24px);
  }

  .growth-row {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
