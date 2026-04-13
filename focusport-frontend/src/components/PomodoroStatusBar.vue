<script setup lang="ts">
const props = defineProps<{
  taskName: string
  timeText: string
  mode: 'focus' | 'break'
  status: 'idle' | 'running' | 'paused'
}>()
</script>

<template>
  <section class="pomodoro-status-bar" :class="[mode, status]">
    <div class="left">
      <span class="label">绑定任务</span>
      <strong class="task-name">{{ taskName }}</strong>
    </div>
    <div class="middle">
      <span class="timer">{{ timeText }}</span>
    </div>
    <div class="right">
      <span class="pulse" aria-hidden="true"></span>
      <span class="state">{{ mode.toUpperCase() }} / {{ status.toUpperCase() }}</span>
    </div>
  </section>
</template>

<style scoped>
.pomodoro-status-bar {
  display: grid;
  grid-template-columns: 1.4fr 0.8fr 1fr;
  align-items: center;
  gap: 10px;
  border-radius: 14px;
  border: 1px solid rgba(137, 185, 255, 0.45);
  background: linear-gradient(135deg, rgba(7, 22, 46, 0.72), rgba(13, 35, 71, 0.78));
  padding: 10px 12px;
  color: #eff7ff;
}

.pomodoro-status-bar.break {
  border-color: rgba(125, 236, 175, 0.6);
}

.label {
  display: block;
  font-size: 11px;
  color: rgba(183, 216, 255, 0.84);
}

.task-name {
  display: block;
  margin-top: 2px;
  font-size: 14px;
}

.middle {
  text-align: center;
}

.timer {
  font-family: var(--font-mono);
  font-size: 26px;
  letter-spacing: 0.06em;
  font-weight: 800;
}

.right {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.state {
  font-size: 11px;
  color: rgba(198, 224, 255, 0.9);
}

.pulse {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: #87d3ff;
}

.pomodoro-status-bar.running .pulse {
  animation: pulse 1.05s ease-in-out infinite;
}

.pomodoro-status-bar.break .pulse {
  background: #91f0bf;
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(0.85);
    opacity: 0.55;
  }
  50% {
    transform: scale(1.15);
    opacity: 1;
  }
}

@media (max-width: 860px) {
  .pomodoro-status-bar {
    grid-template-columns: 1fr;
    text-align: left;
  }

  .middle {
    text-align: left;
  }

  .right {
    justify-content: flex-start;
  }
}
</style>
