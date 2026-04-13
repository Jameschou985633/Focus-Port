<script setup>
import { nextTick, ref } from 'vue'
import { useMasterTimelineStore } from '../stores/masterTimeline'
import { WORLD_NAMES, composeWorldLabel } from '../constants/worldNames'

const emit = defineEmits(['draft-deployed'])

const timelineStore = useMasterTimelineStore()
const draftListRef = ref(null)

const handlePreview = async () => {
  await timelineStore.requestAIPreview(timelineStore.previewGoal, {
    style: timelineStore.decomposeStyle,
    mode: 'replace'
  })
}

const captureSourceRects = () => {
  const cards = Array.from(draftListRef.value?.querySelectorAll('[data-sequence-draft-card]') || [])
  return cards.map((element) => ({
    id: element.getAttribute('data-sequence-draft-card'),
    rect: element.getBoundingClientRect()
  }))
}

const handleConfirm = async () => {
  const sourceRects = captureSourceRects()
  const addedIds = timelineStore.confirmDraftToTimeline()
  await nextTick()
  if (addedIds.length) {
    emit('draft-deployed', { sourceRects, addedIds })
  }
}

const addDraftStep = () => {
  timelineStore.addDraftItem()
}

const removeDraftStep = (id) => {
  timelineStore.removeDraftItem(id)
}

const moveDraftStep = (id, direction) => {
  timelineStore.moveDraftItem(id, direction)
}

const updateTitle = (id, event) => {
  timelineStore.updateDraftItem(id, { title: event.target.value })
}

const updateEstimatedPomodoros = (id, event) => {
  timelineStore.updateDraftItem(id, { estimatedPomodoros: Number(event.target.value) || 1 })
}
</script>

<template>
  <section class="sequence-panel">
    <header class="panel-header">
      <div>
        <p class="panel-eyebrow">{{ WORLD_NAMES.globalSequence.en }}</p>
        <h3>{{ composeWorldLabel(WORLD_NAMES.sequenceMatrix) }}</h3>
      </div>
      <button
        type="button"
        class="sequence-btn primary"
        :disabled="timelineStore.isGenerating"
        @click="handlePreview"
      >
        {{ timelineStore.isGenerating ? 'AI 拆解中...' : 'AI 拆解' }}
      </button>
    </header>

    <div class="goal-input-shell">
      <label class="field-label">任务目标 / Mission Goal</label>
      <textarea
        v-model="timelineStore.previewGoal"
        class="goal-input"
        placeholder="输入今天要推进的目标，例如：完成高数第二章错题并复盘。"
      />
    </div>

    <div class="style-shell">
      <label class="field-label">拆解风格</label>
      <div class="style-row">
        <button
          type="button"
          class="style-btn"
          :class="{ active: timelineStore.decomposeStyle === 'conservative' }"
          @click="timelineStore.decomposeStyle = 'conservative'"
        >
          conservative
        </button>
        <button
          type="button"
          class="style-btn"
          :class="{ active: timelineStore.decomposeStyle === 'balanced' }"
          @click="timelineStore.decomposeStyle = 'balanced'"
        >
          balanced
        </button>
        <button
          type="button"
          class="style-btn"
          :class="{ active: timelineStore.decomposeStyle === 'sprint' }"
          @click="timelineStore.decomposeStyle = 'sprint'"
        >
          sprint
        </button>
      </div>
    </div>

    <p v-if="timelineStore.generationError" class="error-line">{{ timelineStore.generationError }}</p>

    <div ref="draftListRef" class="draft-list">
      <article
        v-for="(item, index) in timelineStore.preflightDraft"
        :key="item.id"
        class="draft-card"
        :data-sequence-draft-card="item.id"
      >
        <button type="button" class="remove-btn" @click="removeDraftStep(item.id)">×</button>
        <div class="draft-fields">
          <input
            :value="item.title"
            type="text"
            class="ghost-input task-input"
            placeholder="可直接执行的任务动作"
            @input="updateTitle(item.id, $event)"
          />
          <div class="meta-row">
            <label>
              <span>预计番茄</span>
              <input
                :value="item.estimatedPomodoros"
                type="number"
                min="1"
                max="3"
                class="ghost-input minutes-input"
                @input="updateEstimatedPomodoros(item.id, $event)"
              />
            </label>
            <label>
              <span>优先级</span>
              <input :value="item.priority" type="number" class="ghost-input priority-input" disabled />
            </label>
          </div>
          <p v-if="item.reason" class="reason-line">原因：{{ item.reason }}</p>
          <p v-if="item.doneDefinition" class="done-line">完成标准：{{ item.doneDefinition }}</p>
          <div class="sort-row">
            <button type="button" class="mini-btn" :disabled="index === 0" @click="moveDraftStep(item.id, 'up')">上移</button>
            <button
              type="button"
              class="mini-btn"
              :disabled="index === timelineStore.preflightDraft.length - 1"
              @click="moveDraftStep(item.id, 'down')"
            >
              下移
            </button>
          </div>
        </div>
      </article>
    </div>

    <div class="action-row">
      <button type="button" class="sequence-btn secondary" @click="addDraftStep">+ 新增步骤</button>
      <button
        type="button"
        class="sequence-btn confirm"
        :disabled="!timelineStore.preflightDraft.length"
        @click="handleConfirm"
      >
        确认部署至总轴
      </button>
    </div>
  </section>
</template>

<style scoped>
.sequence-panel {
  border-radius: 24px;
  padding: 18px;
  background:
    linear-gradient(180deg, rgba(10, 26, 46, 0.96), rgba(6, 13, 30, 0.98)),
    rgba(4, 9, 20, 0.92);
  border: 1px solid rgba(0, 255, 255, 0.18);
  box-shadow: 0 24px 56px rgba(2, 8, 18, 0.4);
  margin-bottom: 14px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.panel-eyebrow {
  margin: 0 0 6px;
  font-size: 11px;
  color: rgba(164, 245, 255, 0.68);
  letter-spacing: 0.22em;
}

.panel-header h3 {
  margin: 0;
  font-size: 20px;
  color: #eefcff;
  text-shadow: 0 0 16px rgba(0, 255, 255, 0.22);
}

.goal-input-shell,
.style-shell {
  margin-top: 14px;
}

.field-label {
  display: block;
  margin-bottom: 8px;
  color: rgba(206, 244, 255, 0.7);
  font-size: 12px;
}

.goal-input {
  width: 100%;
  min-height: 88px;
  box-sizing: border-box;
  border-radius: 18px;
  border: 1px solid rgba(0, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.03);
  color: #eefcff;
  padding: 12px 14px;
  resize: vertical;
  outline: none;
  line-height: 1.6;
}

.goal-input:focus {
  border-color: rgba(0, 255, 255, 0.42);
  box-shadow: 0 0 0 1px rgba(0, 255, 255, 0.16), 0 0 20px rgba(0, 255, 255, 0.08);
}

.style-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.style-btn {
  border: 1px solid rgba(0, 255, 255, 0.18);
  border-radius: 12px;
  min-height: 36px;
  background: rgba(255, 255, 255, 0.04);
  color: #effcff;
  cursor: pointer;
}

.style-btn.active {
  border-color: rgba(16, 216, 255, 0.6);
  box-shadow: 0 0 0 1px rgba(16, 216, 255, 0.25) inset;
}

.error-line {
  margin: 10px 0 0;
  color: #ff9aa7;
  font-size: 13px;
}

.draft-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 14px;
  max-height: 400px;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding-right: 6px;
  scrollbar-color: #00ffff rgba(10, 25, 47, 0.9);
  scrollbar-width: thin;
}

.draft-list::-webkit-scrollbar {
  width: 6px;
}

.draft-list::-webkit-scrollbar-track {
  background: rgba(10, 25, 47, 0.9);
  border-radius: 999px;
}

.draft-list::-webkit-scrollbar-thumb {
  background: #00ffff;
  border-radius: 999px;
  box-shadow: 0 0 10px rgba(0, 255, 255, 0.45);
}

.draft-card {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 12px;
  border-radius: 18px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(0, 255, 255, 0.12);
}

.remove-btn {
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 12px;
  background: rgba(255, 98, 128, 0.14);
  color: #ffd5dd;
  cursor: pointer;
}

.draft-fields {
  min-width: 0;
}

.ghost-input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid transparent;
  border-radius: 14px;
  background: transparent;
  color: #effcff;
  padding: 8px 10px;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.ghost-input::placeholder {
  color: rgba(214, 247, 255, 0.4);
}

.ghost-input:focus {
  border-color: rgba(0, 255, 255, 0.42);
  background: rgba(255, 255, 255, 0.03);
  box-shadow: 0 0 0 1px rgba(0, 255, 255, 0.14), 0 0 18px rgba(0, 255, 255, 0.08);
}

.task-input {
  font-size: 15px;
  font-weight: 600;
}

.meta-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 8px;
}

.meta-row label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: rgba(206, 244, 255, 0.68);
}

.reason-line,
.done-line {
  margin: 8px 0 0;
  font-size: 12px;
  color: rgba(204, 242, 255, 0.72);
  line-height: 1.5;
}

.sort-row {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.mini-btn {
  border: 1px solid rgba(0, 255, 255, 0.18);
  border-radius: 10px;
  min-height: 30px;
  padding: 0 10px;
  background: rgba(255, 255, 255, 0.04);
  color: #effcff;
  cursor: pointer;
}

.mini-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.action-row {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}

.sequence-btn {
  border: none;
  border-radius: 16px;
  min-height: 42px;
  padding: 0 16px;
  cursor: pointer;
  color: #eefcff;
  font-weight: 700;
}

.sequence-btn.primary,
.sequence-btn.confirm {
  background: linear-gradient(180deg, #10d8ff, #236dff);
}

.sequence-btn.secondary {
  background: rgba(255, 255, 255, 0.07);
}

.sequence-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .panel-header,
  .action-row,
  .meta-row {
    grid-template-columns: 1fr;
    flex-direction: column;
  }

  .style-row {
    grid-template-columns: 1fr;
  }
}
</style>
