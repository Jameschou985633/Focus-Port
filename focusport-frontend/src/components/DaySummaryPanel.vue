<script setup lang="ts">
import { computed } from 'vue'
import { useTaskStore } from '../stores/useTaskStore'

const props = withDefaults(defineProps<{
  open?: boolean
}>(), {
  open: false
})

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'preload-seed-task', taskId: string): void
}>()

const taskStore = useTaskStore()

const summary = computed(() => taskStore.getDaySummary())
const seedTask = computed(() => taskStore.getNextDaySeedTask())

const displayDate = computed(() => {
  const [year, month, day] = summary.value.dateKey.split('-')
  return `${year}/${month}/${day}`
})

const formatFocusDuration = (seconds: number): string => {
  const totalMinutes = Math.floor(Math.max(0, seconds) / 60)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (hours <= 0) return `${totalMinutes} 分钟`
  return `${hours}小时 ${minutes}分钟`
}

const onPreloadSeedTask = (): void => {
  if (!seedTask.value) return
  emit('preload-seed-task', seedTask.value.id)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="day-summary-panel">
      <div v-if="props.open" class="summary-overlay">
        <section class="summary-shell" role="dialog" aria-modal="true" aria-label="Day summary panel">
          <header class="summary-header">
            <div>
              <p class="kicker">STARPORT DAILY REPORT</p>
              <h2>战报汇总</h2>
              <p class="date">{{ displayDate }}</p>
            </div>
            <button type="button" class="close-btn" @click="emit('close')">关闭</button>
          </header>

          <section class="metrics-grid">
            <article class="metric-card">
              <span>已完成任务</span>
              <strong>{{ summary.completedCount }}</strong>
            </article>
            <article class="metric-card">
              <span>总专注时长</span>
              <strong>{{ formatFocusDuration(summary.totalFocusSeconds) }}</strong>
            </article>
            <article class="metric-card">
              <span>总番茄数</span>
              <strong>{{ summary.totalPomodoros }}</strong>
            </article>
            <article class="metric-card">
              <span>今日算力产出</span>
              <strong>+{{ summary.totalComputePowerGained }}</strong>
            </article>
          </section>

          <section class="list-panel">
            <h3>今日已完成任务</h3>
            <ul v-if="summary.completedTasks.length" class="task-list">
              <li v-for="task in summary.completedTasks" :key="task.id">{{ task.title }}</li>
            </ul>
            <p v-else class="empty-text">今日暂无已完成任务。</p>
          </section>

          <section class="list-panel">
            <h3>未完成 / 顺延任务</h3>
            <ul v-if="summary.pendingTasks.length" class="task-list">
              <li v-for="task in summary.pendingTasks" :key="task.id">
                <span>{{ task.title }}</span>
                <small v-if="task.isCarriedOver">
                  已顺延<span v-if="(task.carryOverCount || 0) > 0"> x{{ task.carryOverCount }}</span>
                </small>
              </li>
            </ul>
            <p v-else class="empty-text">当前没有待处理任务。</p>
          </section>

          <footer class="seed-footer">
            <div>
              <p class="kicker">NEXT DAY SEED</p>
              <h3>明日首任务</h3>
              <p class="seed-title">{{ seedTask?.title || '暂无可预装填任务' }}</p>
              <p v-if="seedTask" class="seed-meta">优先级 {{ seedTask.priority || 0 }} · 顺延 {{ seedTask.carryOverCount || 0 }}</p>
            </div>
            <button type="button" class="preload-btn" :disabled="!seedTask" @click="onPreloadSeedTask">
              主引擎预装填
            </button>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.summary-overlay {
  position: fixed;
  inset: 0;
  z-index: 1400;
  display: grid;
  place-items: center;
  background: rgba(6, 14, 28, 0.72);
  backdrop-filter: blur(3px);
}

.summary-shell {
  width: min(960px, calc(100% - 28px));
  max-height: calc(100vh - 28px);
  overflow: auto;
  border-radius: 22px;
  border: 1px solid rgba(137, 191, 255, 0.45);
  background: linear-gradient(145deg, rgba(8, 20, 42, 0.98), rgba(9, 27, 54, 0.98));
  color: var(--color-text-primary);
  padding: 20px;
  display: grid;
  gap: 14px;
}

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
}

.kicker {
  margin: 0;
  color: rgba(152, 206, 255, 0.9);
  letter-spacing: 0.14em;
  font-size: 11px;
}

.summary-header h2 {
  margin: 5px 0;
  font-size: 30px;
}

.date {
  margin: 0;
  color: var(--color-text-secondary);
}

.close-btn {
  border: 1px solid rgba(150, 198, 255, 0.5);
  background: rgba(8, 20, 40, 0.72);
  color: var(--color-text-primary);
  border-radius: 10px;
  padding: 7px 12px;
  cursor: pointer;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.metric-card {
  border-radius: 12px;
  border: 1px solid rgba(137, 191, 255, 0.35);
  background: rgba(9, 23, 46, 0.72);
  padding: 10px;
  display: grid;
  gap: 5px;
}

.metric-card span {
  color: var(--color-text-secondary);
  font-size: 12px;
}

.metric-card strong {
  font-size: 20px;
}

.list-panel {
  border-radius: 12px;
  border: 1px solid rgba(137, 191, 255, 0.28);
  padding: 10px;
}

.list-panel h3 {
  margin: 0 0 8px;
  font-size: 16px;
}

.task-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 6px;
}

.task-list li {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  border-radius: 8px;
  padding: 8px;
  background: rgba(9, 22, 43, 0.66);
  color: var(--color-text-primary);
}

.task-list small {
  color: rgba(158, 228, 176, 0.92);
}

.empty-text {
  margin: 0;
  color: var(--color-text-secondary);
}

.seed-footer {
  border-radius: 14px;
  border: 1px solid rgba(143, 238, 175, 0.42);
  background: rgba(9, 30, 36, 0.56);
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.seed-footer h3 {
  margin: 5px 0;
}

.seed-title {
  margin: 0;
  color: var(--color-text-primary);
}

.seed-meta {
  margin: 5px 0 0;
  color: var(--color-text-secondary);
  font-size: 12px;
}

.preload-btn {
  border: 0;
  border-radius: 10px;
  padding: 10px 14px;
  background: linear-gradient(135deg, #81dfff, #9cf3bf);
  color: #071526;
  font-weight: 700;
  cursor: pointer;
}

.preload-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.day-summary-panel-enter-active,
.day-summary-panel-leave-active {
  transition: opacity 0.2s ease;
}

.day-summary-panel-enter-from,
.day-summary-panel-leave-to {
  opacity: 0;
}

@media (max-width: 900px) {
  .metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .seed-footer {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
