<script setup lang="ts">
import { computed } from 'vue'
import type { Task } from '../stores/useTaskStore'

const props = defineProps<{
  task: Task
  isActive?: boolean
}>()

const emit = defineEmits<{
  (event: 'start-engine', taskId: string): void
  (event: 'complete-task', taskId: string): void
}>()

const focusMinutes = computed(() => Math.floor(props.task.totalFocusSeconds / 60))
const focusSeconds = computed(() => props.task.totalFocusSeconds % 60)

const focusText = computed(() => {
  const minutes = String(focusMinutes.value).padStart(2, '0')
  const seconds = String(focusSeconds.value).padStart(2, '0')
  return `${minutes}:${seconds}`
})

const handleStartEngine = (): void => {
  emit('start-engine', props.task.id)
}

const handleCompleteTask = (): void => {
  emit('complete-task', props.task.id)
}
</script>

<template>
  <article class="task-item" :class="{ active: isActive, done: task.status === 'done' }">
    <div class="task-copy">
      <p class="title">{{ task.title }}</p>
      <p class="meta">
        <span>Pomodoros {{ task.actualPomodoros }}</span>
        <span>Focus {{ focusText }}</span>
        <span v-if="task.isCarriedOver">Carried Over</span>
      </p>
    </div>
    <div class="actions">
      <button type="button" class="btn secondary" :disabled="task.status === 'done'" @click="handleStartEngine">
        主引擎点火
      </button>
      <button type="button" class="btn primary" :disabled="task.status === 'done'" @click="handleCompleteTask">
        任务完成
      </button>
    </div>
  </article>
</template>

<style scoped>
.task-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid rgba(125, 175, 255, 0.34);
  background: rgba(9, 21, 44, 0.55);
}

.task-item.active {
  border-color: rgba(139, 244, 167, 0.8);
  box-shadow: 0 0 0 1px rgba(139, 244, 167, 0.5) inset;
}

.task-item.done {
  opacity: 0.72;
}

.task-copy {
  min-width: 0;
}

.title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #f0f7ff;
}

.meta {
  margin: 6px 0 0;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  color: rgba(188, 218, 255, 0.9);
  font-size: 12px;
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.btn {
  border: 0;
  padding: 7px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.btn.secondary {
  color: #eaf4ff;
  border: 1px solid rgba(137, 184, 255, 0.6);
  background: rgba(8, 24, 50, 0.72);
}

.btn.primary {
  color: #061529;
  background: linear-gradient(135deg, #83e1ff, #a7ffb9);
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
