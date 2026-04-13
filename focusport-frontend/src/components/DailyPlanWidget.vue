<script setup>
import { computed } from 'vue'

const props = defineProps({
  activePlan: { type: Object, default: null },
  todayTasks: { type: Array, default: () => [] },
  milestoneAlerts: { type: Array, default: () => [] },
  focusSuggestion: { type: String, default: '' }
})

const emit = defineEmits([
  'open-ai-generator',
  'complete-task',
  'start-focus',
  'view-plan-detail',
  'quick-add-task'
])

const completedCount = computed(() => props.todayTasks.filter(t => t.status === 'completed').length)
const totalCount = computed(() => props.todayTasks.length)
const progressPercent = computed(() => {
  if (!props.activePlan) return 0
  return props.activePlan.progress_percent || 0
})

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

const handleTaskAction = (task) => {
  if (task.status === 'completed') return
  emit('start-focus', task)
}
</script>

<template>
  <section class="sidebar-card plan-widget">
    <header class="card-header">
      <div>
        <p class="card-kicker">Mission Plan</p>
        <h2>分阶段计划舱</h2>
      </div>
      <span class="card-badge" v-if="totalCount">{{ completedCount }}/{{ totalCount }}</span>
    </header>

    <!-- 快捷操作 -->
    <div class="plan-actions">
      <button class="ai-btn" @click="emit('open-ai-generator')">
        <span class="icon">AI</span> 生成计划
      </button>
      <button class="quick-btn" @click="emit('quick-add-task')">
        <span class="icon">+</span> 快速添加
      </button>
    </div>

    <!-- 今日任务 -->
    <div class="today-section">
      <div class="section-title">今日任务</div>
      <div class="task-list" v-if="todayTasks.length">
        <div
          v-for="task in todayTasks"
          :key="task.id"
          :class="['task-item', { completed: task.status === 'completed' }]"
        >
          <button
            class="task-check"
            @click="emit('complete-task', task.id)"
          >
            {{ task.status === 'completed' ? '✓' : '○' }}
          </button>
          <div class="task-info" @click="handleTaskAction(task)">
            <span class="task-title">{{ task.title }}</span>
            <span class="task-meta" v-if="task.stage_title">
              {{ task.stage_title }} · {{ task.estimated_minutes }}min
            </span>
          </div>
          <button
            v-if="task.status !== 'completed'"
            class="focus-btn"
            @click="emit('start-focus', task)"
          >
            启动
          </button>
        </div>
      </div>
      <div class="empty-state" v-else>
        <p>今天没有安排任务</p>
        <p class="hint">点击上方按钮生成AI计划</p>
      </div>
    </div>

    <!-- 当前进度 -->
    <div class="progress-section" v-if="activePlan">
      <div class="progress-header">
        <span class="plan-title">{{ activePlan.title }}</span>
        <strong class="progress-value">{{ progressPercent }}%</strong>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
      </div>
      <div class="stage-dots" v-if="activePlan.stages">
        <span
          v-for="(stage, idx) in activePlan.stages.slice(0, 6)"
          :key="stage.id"
          :class="['stage-dot', stage.status]"
          :title="stage.title"
        >
          {{ idx + 1 }}
        </span>
        <span v-if="activePlan.stages.length > 6" class="stage-dot more">+{{ activePlan.stages.length - 6 }}</span>
      </div>
    </div>

    <!-- 里程碑提醒 -->
    <div class="milestone-section" v-if="milestoneAlerts.length">
      <div class="section-title">临近里程碑</div>
      <div class="milestone-list">
        <div
          v-for="ms in milestoneAlerts.slice(0, 2)"
          :key="ms.id"
          class="milestone-item"
        >
          <span class="ms-icon">{{ ms.is_checkpoint ? '📍' : '🏁' }}</span>
          <span class="ms-title">{{ ms.title }}</span>
          <span class="ms-date">{{ formatDate(ms.target_date) }}</span>
        </div>
      </div>
    </div>

    <!-- 专注建议 -->
    <div class="focus-suggestion" v-if="focusSuggestion && !todayTasks.length">
      <span class="suggestion-icon">💡</span>
      <span class="suggestion-text">{{ focusSuggestion }}</span>
    </div>

    <!-- 查看完整计划 -->
    <button
      class="view-all-btn"
      v-if="activePlan"
      @click="emit('view-plan-detail', activePlan.id)"
    >
      查看完整计划
    </button>
  </section>
</template>

<style scoped>
.plan-widget {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.card-kicker {
  margin: 0 0 4px;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(156, 223, 255, 0.72);
}

.card-header h2 {
  margin: 0;
  font-size: 22px;
}

.card-badge {
  border-radius: 999px;
  padding: 6px 10px;
  background: rgba(92, 193, 255, 0.12);
  border: 1px solid rgba(115, 224, 255, 0.24);
  font-size: 12px;
  font-weight: 700;
}

.plan-actions {
  display: flex;
  gap: 10px;
}

.ai-btn, .quick-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px;
  border: none;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.ai-btn {
  background: linear-gradient(135deg, rgba(124, 116, 255, 0.3), rgba(72, 213, 255, 0.3));
  color: #eef7ff;
  border: 1px solid rgba(124, 116, 255, 0.4);
}

.quick-btn {
  background: rgba(255, 255, 255, 0.08);
  color: #dbeeff;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.section-title {
  font-size: 12px;
  color: rgba(222, 240, 255, 0.7);
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(115, 224, 255, 0.12);
  border-radius: 14px;
}

.task-item.completed {
  opacity: 0.6;
  border-color: rgba(110, 255, 186, 0.2);
}

.task-check {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: #eef7ff;
  font-size: 16px;
  cursor: pointer;
  padding: 0;
}

.task-info {
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.task-title {
  display: block;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-meta {
  display: block;
  font-size: 11px;
  color: rgba(222, 240, 255, 0.6);
  margin-top: 2px;
}

.focus-btn {
  padding: 6px 12px;
  background: linear-gradient(135deg, rgba(47, 216, 255, 0.3), rgba(45, 116, 255, 0.3));
  border: 1px solid rgba(47, 216, 255, 0.4);
  border-radius: 8px;
  color: #eef7ff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.empty-state {
  text-align: center;
  padding: 20px;
  color: rgba(222, 240, 255, 0.6);
}

.empty-state p {
  margin: 0;
}

.empty-state .hint {
  font-size: 12px;
  margin-top: 6px;
  color: rgba(222, 240, 255, 0.4);
}

.progress-section {
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 14px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.plan-title {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.progress-value {
  font-size: 13px;
  color: #4ade80;
}

.progress-track {
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 10px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #7c74ff, #48d5ff);
  border-radius: 3px;
  transition: width 0.5s ease;
}

.stage-dots {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.stage-dot {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 10px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.5);
}

.stage-dot.pending {
  background: rgba(255, 255, 255, 0.1);
}

.stage-dot.in_progress {
  background: rgba(72, 183, 255, 0.3);
  border: 1px solid rgba(72, 183, 255, 0.5);
  color: #48b7ff;
}

.stage-dot.completed {
  background: rgba(74, 222, 128, 0.3);
  border: 1px solid rgba(74, 222, 128, 0.5);
  color: #4ade80;
}

.stage-dot.more {
  width: auto;
  padding: 0 8px;
  border-radius: 11px;
}

.milestone-section {
  padding-top: 4px;
}

.milestone-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.milestone-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: rgba(251, 191, 36, 0.1);
  border: 1px solid rgba(251, 191, 36, 0.2);
  border-radius: 10px;
  font-size: 12px;
}

.ms-icon {
  font-size: 14px;
}

.ms-title {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ms-date {
  color: rgba(251, 191, 36, 0.8);
  font-weight: 600;
}

.focus-suggestion {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  background: rgba(72, 183, 255, 0.1);
  border-radius: 10px;
  font-size: 13px;
  color: rgba(222, 240, 255, 0.8);
}

.suggestion-icon {
  font-size: 16px;
}

.view-all-btn {
  width: 100%;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 12px;
  color: rgba(222, 240, 255, 0.8);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.view-all-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.25);
}
</style>
