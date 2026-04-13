<script setup>
import { ref, computed } from 'vue'
import { planApi } from '../api'
import { useUserStore } from '../stores/user'

const emit = defineEmits(['close', 'plan-created'])

const userStore = useUserStore()

const goal = ref('')
const durationDays = ref(30)
const dailyHours = ref(2)
const difficulty = ref('intermediate')
const isGenerating = ref(false)
const errorMessage = ref('')
const showResult = ref(false)
const generatedPlan = ref(null)

const difficultyLabels = {
  beginner: '零基础',
  intermediate: '有一定基础',
  advanced: '基础扎实'
}

const canGenerate = computed(() => {
  return goal.value.trim().length >= 5 && durationDays.value > 0 && dailyHours.value > 0
})

const generatePlan = async () => {
  if (!canGenerate.value || isGenerating.value) return

  isGenerating.value = true
  errorMessage.value = ''

  try {
    const res = await planApi.aiGenerate({
      username: userStore.username,
      goal: goal.value,
      duration_days: durationDays.value,
      daily_hours: dailyHours.value,
      difficulty: difficulty.value
    })

    if (res.data.success) {
      generatedPlan.value = res.data.result
      showResult.value = true
    } else {
      errorMessage.value = res.data.error || '生成失败，请重试'
    }
  } catch (error) {
    console.error('AI生成失败:', error)
    errorMessage.value = '网络错误，请检查连接'
  } finally {
    isGenerating.value = false
  }
}

const confirmPlan = () => {
  emit('plan-created', generatedPlan.value)
  emit('close')
}

const closeModal = () => {
  emit('close')
}
</script>

<template>
  <div class="modal-overlay" @click.self="closeModal">
    <div class="modal-content">
      <!-- 头部 -->
      <div class="modal-header">
        <h3>AI 智能规划助手</h3>
        <button class="close-btn" @click="closeModal">×</button>
      </div>

      <!-- 输入区域 -->
      <div v-if="!showResult" class="input-section">
        <!-- 目标输入 -->
        <div class="form-group">
          <label>你的学习目标是什么？</label>
          <textarea
            v-model="goal"
            placeholder="例如：在一个月内完成高数期末复习，目标85分以上"
            rows="3"
          />
        </div>

        <!-- 时间设置 -->
        <div class="form-row">
          <div class="form-group">
            <label>可用天数</label>
            <input type="number" v-model="durationDays" min="1" max="365" />
          </div>
          <div class="form-group">
            <label>每日学习(小时)</label>
            <input type="number" v-model="dailyHours" min="0.5" max="12" step="0.5" />
          </div>
        </div>

        <!-- 难度选择 -->
        <div class="form-group">
          <label>基础水平</label>
          <div class="difficulty-options">
            <button
              v-for="(label, key) in difficultyLabels"
              :key="key"
              :class="['diff-btn', { active: difficulty === key }]"
              @click="difficulty = key"
            >
              {{ label }}
            </button>
          </div>
        </div>

        <!-- 错误提示 -->
        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>

        <!-- 生成按钮 -->
        <div class="action-buttons">
          <button class="cancel-btn" @click="closeModal">取消</button>
          <button
            class="generate-btn"
            :disabled="!canGenerate || isGenerating"
            @click="generatePlan"
          >
            <span v-if="isGenerating" class="loading">AI 思考中...</span>
            <span v-else>生成计划</span>
          </button>
        </div>
      </div>

      <!-- 结果预览 -->
      <div v-else class="result-section">
        <div class="result-header">
          <span class="success-icon">✅</span>
          <h4>{{ generatedPlan?.title || '学习计划' }}</h4>
        </div>

        <!-- 阶段预览 -->
        <div class="stages-preview">
          <div
            v-for="(stage, idx) in generatedPlan?.stages || []"
            :key="idx"
            class="stage-preview-item"
          >
            <div class="stage-num">{{ idx + 1 }}</div>
            <div class="stage-info">
              <strong>{{ stage.title }}</strong>
              <span class="stage-tasks">{{ stage.tasks?.length || 0 }} 个任务</span>
            </div>
          </div>
        </div>

        <!-- 里程碑 -->
        <div v-if="generatedPlan?.milestones?.length" class="milestones-preview">
          <div class="preview-label">里程碑</div>
          <div class="milestone-tags">
            <span v-for="(ms, idx) in generatedPlan.milestones" :key="idx" class="ms-tag">
              🏁 {{ ms.title }}
            </span>
          </div>
        </div>

        <!-- 建议 -->
        <div v-if="generatedPlan?.suggestions" class="suggestions">
          <div class="preview-label">AI 建议</div>
          <p>{{ generatedPlan.suggestions }}</p>
        </div>

        <!-- 确认按钮 -->
        <div class="action-buttons">
          <button class="cancel-btn" @click="showResult = false">重新生成</button>
          <button class="confirm-btn" @click="confirmPlan">确认使用</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: linear-gradient(180deg, rgba(16, 34, 74, 0.98), rgba(8, 16, 36, 0.99));
  border: 1.5px solid rgba(129, 214, 255, 0.34);
  border-radius: 24px;
  padding: 24px;
  width: 90%;
  max-width: 440px;
  max-height: 85vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(4, 8, 22, 0.5);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.modal-header h3 {
  margin: 0;
  font-size: 20px;
  color: #eef7ff;
}

.close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 50%;
  color: rgba(255, 255, 255, 0.7);
  font-size: 20px;
  cursor: pointer;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 13px;
  color: rgba(222, 240, 255, 0.7);
  margin-bottom: 6px;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 12px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  color: #eef7ff;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: rgba(72, 183, 255, 0.5);
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

.form-row {
  display: flex;
  gap: 12px;
}

.form-row .form-group {
  flex: 1;
}

.difficulty-options {
  display: flex;
  gap: 8px;
}

.diff-btn {
  flex: 1;
  padding: 10px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  color: rgba(222, 240, 255, 0.8);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.diff-btn.active {
  background: linear-gradient(135deg, rgba(124, 116, 255, 0.3), rgba(72, 213, 255, 0.3));
  border-color: rgba(124, 116, 255, 0.5);
  color: #fff;
}

.error-message {
  padding: 12px;
  background: rgba(248, 113, 113, 0.15);
  border: 1px solid rgba(248, 113, 113, 0.3);
  border-radius: 10px;
  color: #f87171;
  font-size: 13px;
  margin-bottom: 16px;
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.cancel-btn,
.generate-btn,
.confirm-btn {
  flex: 1;
  padding: 14px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  border: none;
}

.cancel-btn {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(222, 240, 255, 0.8);
}

.generate-btn {
  background: linear-gradient(135deg, #7c74ff, #48d5ff);
  color: #fff;
}

.generate-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.generate-btn .loading {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.confirm-btn {
  background: linear-gradient(135deg, #4ade80, #22d3ee);
  color: #fff;
}

/* 结果预览样式 */
.result-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.success-icon {
  font-size: 24px;
}

.result-header h4 {
  margin: 0;
  font-size: 18px;
  color: #eef7ff;
}

.stages-preview {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stage-preview-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
}

.stage-num {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(124, 116, 255, 0.3), rgba(72, 213, 255, 0.3));
  border-radius: 50%;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
}

.stage-info {
  flex: 1;
}

.stage-info strong {
  display: block;
  font-size: 14px;
  color: #eef7ff;
}

.stage-tasks {
  font-size: 12px;
  color: rgba(222, 240, 255, 0.6);
}

.milestones-preview,
.suggestions {
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
}

.preview-label {
  font-size: 12px;
  color: rgba(222, 240, 255, 0.6);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.milestone-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ms-tag {
  padding: 4px 10px;
  background: rgba(251, 191, 36, 0.15);
  border-radius: 8px;
  font-size: 12px;
  color: #fbbf24;
}

.suggestions p {
  margin: 0;
  font-size: 13px;
  color: rgba(222, 240, 255, 0.8);
  line-height: 1.6;
}
</style>
