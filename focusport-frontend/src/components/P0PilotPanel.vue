<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import TaskItem from './TaskItem.vue'
import PomodoroStatusBar from './PomodoroStatusBar.vue'
import TaskCompleteModal from './TaskCompleteModal.vue'
import { useTaskStore, type AIAnalysisPayload } from '../stores/useTaskStore'
import { usePomodoroStore } from '../stores/usePomodoroStore'

const taskStore = useTaskStore()
const pomodoroStore = usePomodoroStore()

const inputTitle = ref('')
const modalOpen = ref(false)
const selectedTaskId = ref<string | null>(null)
const lastReward = ref<AIAnalysisPayload | null>(null)

const selectedTask = computed(() => {
  if (!selectedTaskId.value) return undefined
  return taskStore.getTaskById(selectedTaskId.value)
})

const statusTaskName = computed(() => {
  if (pomodoroStore.activeTask?.title) return pomodoroStore.activeTask.title
  return pomodoroStore.mode === 'break' ? 'Recovery Window' : 'Standby'
})

const timeText = computed(() => {
  const total = Math.max(0, pomodoroStore.remainingSeconds)
  const minutes = Math.floor(total / 60)
  const seconds = total % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

const addTask = (): void => {
  const task = taskStore.addTask(inputTitle.value)
  if (!task) return
  inputTitle.value = ''
}

const handleStartEngine = (taskId: string): void => {
  if (pomodoroStore.mode === 'break' && pomodoroStore.status === 'running') return

  if (pomodoroStore.mode === 'focus' && (pomodoroStore.status === 'running' || pomodoroStore.status === 'paused')) {
    pomodoroStore.interruptFocus()
  }
  pomodoroStore.startFocus(taskId)
}

const handleCompleteTask = (taskId: string): void => {
  selectedTaskId.value = taskId
  modalOpen.value = true
}

const handleRewardTrigger = (payload: AIAnalysisPayload): void => {
  lastReward.value = payload
}

onMounted(() => {
  taskStore.rolloverPendingTasks()
})
</script>

<template>
  <section class="p0-pilot-panel card glass animate-fade-in">
    <div class="panel-head">
      <div>
        <p class="eyebrow">P0 Pilot</p>
        <h2>新链路灰度验证</h2>
      </div>
      <span class="pilot-tag">EXPERIMENTAL</span>
    </div>

    <PomodoroStatusBar
      :task-name="statusTaskName"
      :time-text="timeText"
      :mode="pomodoroStore.mode"
      :status="pomodoroStore.status"
    />

    <div class="engine-actions">
      <button type="button" class="btn ghost" :disabled="!pomodoroStore.canPauseFocus" @click="pomodoroStore.pauseFocus()">
        暂停
      </button>
      <button
        type="button"
        class="btn ghost"
        :disabled="!(pomodoroStore.mode === 'focus' && pomodoroStore.status === 'paused')"
        @click="pomodoroStore.resumeFocus()"
      >
        继续
      </button>
      <button
        type="button"
        class="btn danger"
        :disabled="!(pomodoroStore.mode === 'focus' && (pomodoroStore.status === 'running' || pomodoroStore.status === 'paused'))"
        @click="pomodoroStore.interruptFocus()"
      >
        中断本轮
      </button>
    </div>

    <form class="task-create" @submit.prevent="addTask">
      <input
        v-model="inputTitle"
        class="input"
        maxlength="72"
        placeholder="输入任务并回车，开始 P0 新链路验证"
      />
      <button type="submit" class="btn primary">新增任务</button>
    </form>

    <div v-if="taskStore.tasks.length" class="task-list">
      <TaskItem
        v-for="task in taskStore.tasks"
        :key="task.id"
        :task="task"
        :is-active="pomodoroStore.activeTaskId === task.id"
        @start-engine="handleStartEngine"
        @complete-task="handleCompleteTask"
      />
    </div>
    <p v-else class="empty-text">暂无任务，先创建一条任务验证完整闭环。</p>

    <div v-if="lastReward" class="reward-preview">
      <strong>Latest Reward:</strong>
      <span>Score {{ lastReward.score }} · {{ lastReward.focusLevel }} · EXP +{{ lastReward.expGained }}</span>
    </div>

    <TaskCompleteModal
      v-model:open="modalOpen"
      :task-id="selectedTaskId"
      :task-title="selectedTask?.title"
      @reward-trigger="handleRewardTrigger"
    />
  </section>
</template>

<style scoped>
.p0-pilot-panel {
  margin-bottom: 18px;
  border-radius: 22px;
  padding: 18px;
  display: grid;
  gap: 14px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.panel-head h2 {
  margin: 6px 0 0;
  font-size: 24px;
}

.pilot-tag {
  padding: 5px 9px;
  border-radius: 999px;
  border: 1px solid rgba(143, 241, 171, 0.5);
  color: #b9f5ca;
  font-size: 11px;
  font-weight: 700;
}

.engine-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.task-create {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

.task-list {
  display: grid;
  gap: 8px;
}

.empty-text {
  margin: 0;
  color: var(--color-text-secondary);
}

.btn {
  border: 0;
  border-radius: 10px;
  padding: 8px 12px;
  font-weight: 700;
  cursor: pointer;
}

.btn.primary {
  color: #081427;
  background: linear-gradient(135deg, #80deff, #9ef2bf);
}

.btn.ghost {
  color: #ddecff;
  border: 1px solid rgba(148, 193, 255, 0.55);
  background: rgba(8, 21, 44, 0.72);
}

.btn.danger {
  color: #ffe6e6;
  border: 1px solid rgba(255, 129, 129, 0.6);
  background: rgba(58, 17, 17, 0.8);
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.reward-preview {
  display: inline-flex;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 12px;
  color: rgba(198, 223, 255, 0.9);
}

@media (max-width: 860px) {
  .task-create {
    grid-template-columns: 1fr;
  }
}
</style>
