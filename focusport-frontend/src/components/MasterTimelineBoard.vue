<script setup>
import { computed, ref } from 'vue'
import { useMasterTimelineStore } from '../stores/masterTimeline'
import { WORLD_NAMES, composeWorldLabel } from '../constants/worldNames'

const emit = defineEmits(['start-task'])

const timelineStore = useMasterTimelineStore()
const draggingId = ref('')

const sections = computed(() => ([
  { key: 'pending', label: 'Pending / 待命', items: timelineStore.pendingTasks },
  { key: 'deployed', label: 'Deployed / 部署中', items: timelineStore.deployedTasks },
  { key: 'completed', label: 'Completed / 已归档', items: timelineStore.completedTasks }
]))

const handleDragStart = (taskId) => {
  draggingId.value = String(taskId)
}

const handleDrop = (targetTaskId) => {
  if (!draggingId.value || !targetTaskId) return
  timelineStore.reorderTimeline(draggingId.value, targetTaskId)
  draggingId.value = ''
}

const startTask = (task) => {
  emit('start-task', task)
}

const sendBackToPending = (taskId) => {
  timelineStore.returnTaskToPending(taskId)
}
</script>

<template>
  <section class="timeline-board" data-master-timeline-dropzone>
    <header class="board-header">
      <div>
        <p class="board-eyebrow">{{ WORLD_NAMES.masterTimeline.en }}</p>
        <h3>{{ composeWorldLabel(WORLD_NAMES.masterTimeline) }}</h3>
      </div>
      <button type="button" class="sort-btn" @click="timelineStore.sortTimelineByPriority()">按 AI 优先级排序</button>
    </header>

    <div class="progress-shell">
      <div class="progress-copy">
        <span>全天进度</span>
        <strong>{{ timelineStore.progressPercent }}%</strong>
      </div>
      <div class="micro-track">
        <div class="micro-fill" :style="{ width: `${timelineStore.progressPercent}%` }"></div>
      </div>
      <small>{{ timelineStore.completedTasks.length }} / {{ timelineStore.masterTimeline.length || 0 }} 已归档</small>
    </div>

    <div class="section-list">
      <section v-for="section in sections" :key="section.key" class="timeline-section">
        <header class="section-header">
          <h4>{{ section.label }}</h4>
          <span>{{ section.items.length }}</span>
        </header>

        <div v-if="section.items.length" class="task-list">
          <article
            v-for="task in section.items"
            :key="task.id"
            class="timeline-card"
            :class="task.status"
            :draggable="task.status !== 'deployed'"
            :data-timeline-task-id="task.id"
            @dragstart="handleDragStart(task.id)"
            @dragover.prevent
            @drop.prevent="handleDrop(task.id)"
          >
            <div class="card-main">
              <strong>{{ task.task }}</strong>
              <span>{{ task.minutes }} 分钟 · P{{ task.priority }}</span>
            </div>

            <div class="card-actions">
              <button
                v-if="task.status === 'pending'"
                type="button"
                class="timeline-btn launch"
                @click="startTask(task)"
              >
                送入脉冲动力核
              </button>
              <button
                v-else-if="task.status === 'deployed'"
                type="button"
                class="timeline-btn secondary"
                @click="sendBackToPending(task.id)"
              >
                退回待命
              </button>
              <span v-else class="completed-tag">已归档</span>
            </div>
          </article>
        </div>

        <div v-else class="section-empty">当前区段暂无任务。</div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.timeline-board {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  border-radius: 24px;
  padding: 18px;
  background:
    linear-gradient(180deg, rgba(10, 24, 44, 0.96), rgba(5, 12, 26, 0.98)),
    rgba(4, 9, 20, 0.9);
  border: 1px solid rgba(0, 255, 255, 0.16);
  box-shadow: 0 24px 56px rgba(2, 8, 18, 0.38);
}

.board-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.board-eyebrow {
  margin: 0 0 6px;
  font-size: 11px;
  letter-spacing: 0.22em;
  color: rgba(164, 245, 255, 0.68);
}

.board-header h3 {
  margin: 0;
  font-size: 20px;
  color: #eefcff;
  text-shadow: 0 0 16px rgba(0, 255, 255, 0.2);
}

.sort-btn {
  border: none;
  border-radius: 14px;
  min-height: 40px;
  padding: 0 14px;
  background: rgba(255, 255, 255, 0.08);
  color: #eefcff;
  cursor: pointer;
}

.progress-shell {
  margin-top: 14px;
  border-radius: 18px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.04);
}

.progress-copy {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.micro-track {
  height: 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.micro-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #00f5ff, #2684ff);
}

.progress-shell small {
  display: block;
  margin-top: 8px;
  color: rgba(214, 247, 255, 0.66);
}

.section-list {
  display: grid;
  flex: 1;
  min-height: 0;
  gap: 12px;
  margin-top: 14px;
  overflow-y: auto;
  padding-right: 6px;
  scrollbar-color: #00ffff rgba(10, 25, 47, 0.9);
  scrollbar-width: thin;
}

.section-list::-webkit-scrollbar {
  width: 6px;
}

.section-list::-webkit-scrollbar-track {
  background: rgba(10, 25, 47, 0.9);
  border-radius: 999px;
}

.section-list::-webkit-scrollbar-thumb {
  background: #00ffff;
  border-radius: 999px;
  box-shadow: 0 0 10px rgba(0, 255, 255, 0.45);
}

.timeline-section {
  border-radius: 18px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(0, 255, 255, 0.08);
}

.section-header {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  margin-bottom: 10px;
}

.section-header h4 {
  margin: 0;
  font-size: 15px;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.timeline-card {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
  align-items: center;
  border-radius: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.timeline-card.pending {
  border-color: rgba(0, 255, 255, 0.12);
}

.timeline-card.deployed {
  border-color: rgba(255, 201, 76, 0.18);
  box-shadow: inset 0 0 0 1px rgba(255, 201, 76, 0.1);
}

.timeline-card.completed {
  border-color: rgba(118, 255, 179, 0.16);
  opacity: 0.86;
}

.card-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card-main strong {
  font-size: 14px;
}

.card-main span {
  font-size: 12px;
  color: rgba(214, 247, 255, 0.7);
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.timeline-btn {
  border: none;
  border-radius: 12px;
  min-height: 38px;
  padding: 0 12px;
  cursor: pointer;
  color: #eefcff;
}

.timeline-btn.launch {
  background: linear-gradient(180deg, #10d8ff, #236dff);
}

.timeline-btn.secondary {
  background: rgba(255, 255, 255, 0.08);
}

.completed-tag {
  color: #9af0b6;
  font-size: 12px;
  font-weight: 700;
}

.section-empty {
  color: rgba(214, 247, 255, 0.54);
  font-size: 13px;
}

@media (max-width: 768px) {
  .board-header,
  .timeline-card {
    grid-template-columns: 1fr;
    flex-direction: column;
  }

  .card-actions {
    justify-content: flex-start;
  }
}
</style>
