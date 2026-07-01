<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useTaskStore, type AIAnalysisPayload } from '../stores/useTaskStore'

type ModalStage = 'form' | 'loading' | 'result' | 'error'

const props = defineProps<{
  open: boolean
  taskId: string | null
  taskTitle?: string
}>()

const emit = defineEmits<{
  (event: 'update:open', value: boolean): void
  (event: 'close'): void
  (event: 'submitted'): void
  (event: 'reward-trigger', payload: AIAnalysisPayload): void
}>()

const AUTO_CLOSE_DELAY_MS = 1200

const taskStore = useTaskStore()
const stage = ref<ModalStage>('form')
const note = ref('')
const result = ref<AIAnalysisPayload | null>(null)
const errorMessage = ref('')
const autoCloseTimer = ref<number | null>(null)

const canSubmit = computed(() => Boolean(props.open && props.taskId && stage.value !== 'loading'))

const clearAutoCloseTimer = (): void => {
  if (autoCloseTimer.value !== null && typeof window !== 'undefined') {
    window.clearTimeout(autoCloseTimer.value)
    autoCloseTimer.value = null
  }
}

const resetInnerState = (): void => {
  clearAutoCloseTimer()
  stage.value = 'form'
  note.value = ''
  result.value = null
  errorMessage.value = ''
}

const closeModal = (): void => {
  clearAutoCloseTimer()
  emit('update:open', false)
  emit('close')
}

const scheduleAutoClose = (payload: AIAnalysisPayload): void => {
  clearAutoCloseTimer()
  autoCloseTimer.value = window.setTimeout(() => {
    emit('reward-trigger', payload)
    emit('submitted')
    emit('update:open', false)
    emit('close')
    clearAutoCloseTimer()
  }, AUTO_CLOSE_DELAY_MS)
}

const submit = async (): Promise<void> => {
  if (!canSubmit.value || !props.taskId) return

  stage.value = 'loading'
  errorMessage.value = ''

  try {
    const normalizedNote = String(note.value || '').trim() || undefined
    taskStore.completeTask(props.taskId, normalizedNote)

    const updatedTask = taskStore.getTaskById(props.taskId)
    const payload = await taskStore.triggerAIAnalysis(props.taskId, {
      note: normalizedNote,
      completedAt: updatedTask?.completedAt ?? Date.now(),
      totalFocusSeconds: updatedTask?.totalFocusSeconds ?? 0,
      actualPomodoros: updatedTask?.actualPomodoros ?? 0
    })

    result.value = payload
    stage.value = 'result'
    scheduleAutoClose(payload)
  } catch (error) {
    stage.value = 'error'
    errorMessage.value = error instanceof Error ? error.message : 'AI 解析暂时不可用，请重试。'
  }
}

const retry = async (): Promise<void> => {
  await submit()
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      resetInnerState()
      return
    }
    clearAutoCloseTimer()
  }
)

onBeforeUnmount(() => {
  clearAutoCloseTimer()
})
</script>

<template>
  <Teleport to="body">
    <Transition name="task-complete-modal">
      <div v-if="open" class="task-complete-modal-overlay" @click.self="closeModal">
        <div class="task-complete-modal" role="dialog" aria-modal="true" aria-label="Task completion settlement">
          <header class="modal-header">
            <div>
              <p class="kicker">MISSION SETTLEMENT</p>
              <h3>{{ taskTitle || '任务结算' }}</h3>
            </div>
            <button type="button" class="close-btn" @click="closeModal">关闭</button>
          </header>

          <section v-if="stage === 'form'" class="modal-section">
            <p class="hint">可选填写本轮成果摘要，然后提交 AI 算力解析。</p>
            <textarea
              v-model="note"
              class="note-input"
              maxlength="300"
              placeholder="例如：完成章节复盘并整理错题策略。"
            />
            <div class="actions">
              <button type="button" class="primary-btn" :disabled="!canSubmit" @click="submit">任务完成并结算</button>
            </div>
          </section>

          <section v-else-if="stage === 'loading'" class="modal-section">
            <div class="loading-block">
              <div class="skeleton-line large"></div>
              <div class="skeleton-line"></div>
              <div class="skeleton-line"></div>
            </div>
            <p class="hint">AI 算力解析中...</p>
          </section>

          <section v-else-if="stage === 'result' && result" class="modal-section">
            <div class="result-grid">
              <article class="result-chip">
                <span>评分</span>
                <strong>{{ result.score }}</strong>
              </article>
              <article class="result-chip">
                <span>专注等级</span>
                <strong>{{ result.focusLevel }}</strong>
              </article>
              <article class="result-chip">
                <span>倍率</span>
                <strong>x{{ result.multiplier.toFixed(2) }}</strong>
              </article>
              <article class="result-chip">
                <span>分心检测</span>
                <strong>{{ result.distractionDetected ? '是' : '否' }}</strong>
              </article>
              <article class="result-chip">
                <span>EXP</span>
                <strong>+{{ result.expGained }}</strong>
              </article>
              <article class="result-chip">
                <span>算力 CU</span>
                <strong>+{{ result.computePowerGained }}</strong>
              </article>
            </div>
            <p class="summary">{{ result.summary }}</p>
            <p class="encouragement">{{ result.encouragement }}</p>
          </section>

          <section v-else class="modal-section">
            <p class="error-text">{{ errorMessage || '结算失败，请稍后再试。' }}</p>
            <div class="actions">
              <button type="button" class="primary-btn" :disabled="!canSubmit" @click="retry">重试</button>
            </div>
          </section>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.task-complete-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1300;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(5, 12, 24, 0.7);
  backdrop-filter: blur(4px);
}

.task-complete-modal {
  width: min(560px, calc(100% - 28px));
  border-radius: 18px;
  border: 1px solid rgba(90, 157, 255, 0.5);
  background: linear-gradient(145deg, #09162c 0%, #0d213d 100%);
  color: #eaf4ff;
  box-shadow: 0 14px 38px rgba(4, 15, 33, 0.5);
  padding: 18px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 14px;
}

.modal-header h3 {
  margin: 4px 0 0;
  font-size: 22px;
}

.kicker {
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.14em;
  color: rgba(133, 199, 255, 0.9);
}

.close-btn {
  border: 1px solid rgba(255, 255, 255, 0.22);
  background: transparent;
  color: #d8e9ff;
  border-radius: 10px;
  padding: 6px 10px;
  cursor: pointer;
}

.modal-section {
  display: grid;
  gap: 12px;
}

.hint {
  margin: 0;
  color: rgba(214, 233, 255, 0.9);
}

.note-input {
  resize: vertical;
  min-height: 110px;
  border-radius: 12px;
  border: 1px solid rgba(137, 187, 255, 0.45);
  background: rgba(6, 14, 28, 0.7);
  color: #f2f8ff;
  padding: 12px;
  font: inherit;
}

.actions {
  display: flex;
  justify-content: flex-end;
}

.primary-btn {
  border: 0;
  border-radius: 10px;
  padding: 10px 16px;
  color: #081426;
  background: linear-gradient(135deg, #7de2ff, #9dffbe);
  font-weight: 700;
  cursor: pointer;
}

.primary-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.loading-block {
  display: grid;
  gap: 10px;
}

.skeleton-line {
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(102, 156, 255, 0.25), rgba(180, 219, 255, 0.45), rgba(102, 156, 255, 0.25));
  background-size: 220% 100%;
  animation: shimmer 1.2s linear infinite;
}

.skeleton-line.large {
  height: 14px;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.result-chip {
  border: 1px solid rgba(127, 190, 255, 0.4);
  border-radius: 12px;
  padding: 10px;
  background: rgba(7, 20, 38, 0.62);
  display: grid;
  gap: 6px;
}

.result-chip span {
  font-size: 12px;
  color: rgba(198, 224, 255, 0.85);
}

.result-chip strong {
  font-size: 22px;
}

.summary,
.encouragement {
  margin: 0;
  line-height: 1.5;
}

.error-text {
  margin: 0;
  color: #ffd2d2;
}

.task-complete-modal-enter-active,
.task-complete-modal-leave-active {
  transition: opacity 0.2s ease;
}

.task-complete-modal-enter-from,
.task-complete-modal-leave-to {
  opacity: 0;
}

@keyframes shimmer {
  from { background-position: 200% 0; }
  to { background-position: -50% 0; }
}
</style>
