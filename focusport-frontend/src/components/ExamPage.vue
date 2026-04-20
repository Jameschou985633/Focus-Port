<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { examApi } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const exams = ref([])
const selectedExam = ref(null)
const examConfig = ref(null)
const answers = ref({})
const isSubmitting = ref(false)
const isLoading = ref(false)
const showResult = ref(false)
const result = ref(null)
const timeLeft = ref(0)
let timer = null

// AI批改相关
const aiGradingStatus = ref('idle') // idle, pending, completed
const aiFeedback = ref(null)
const aiSubmissionId = ref(null)
let gradingPollTimer = null

const loadExams = async () => {
  isLoading.value = true
  try {
    const res = await examApi.list()
    exams.value = res.data.exams || []
  } catch (error) {
    console.error('加载考试列表失败:', error)
  } finally {
    isLoading.value = false
  }
}

const selectExam = (exam) => {
  selectedExam.value = exam
  examConfig.value = exam.config_json
  answers.value = {}
  showResult.value = false
  result.value = null
  aiGradingStatus.value = 'idle'
  aiFeedback.value = null
  timeLeft.value = exam.time_limit || 60

  if (examConfig.value?.sections) {
    examConfig.value.sections.forEach(section => {
      if (section.questions) {
        section.questions.forEach(q => {
          answers.value[q.id] = ''
        })
      }
    })
  }

  startTimer()
}

const startTimer = () => {
  if (timer) clearInterval(timer)
  timer = setInterval(() => {
    if (timeLeft.value > 0) {
      timeLeft.value--
    } else {
      submitExam()
    }
  }, 1000)
}

const formatTime = (seconds) => {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

const submitExam = async () => {
  if (timer) clearInterval(timer)
  isSubmitting.value = true

  try {
    const res = await examApi.submit(
      selectedExam.value.exam_code,
      userStore.username,
      answers.value,
      (selectedExam.value.time_limit || 60) * 60 - timeLeft.value
    )

    result.value = res.data
    showResult.value = true

    // 如果有主观题，开始轮询AI批改状态
    if (res.data.has_subjective && res.data.submission_id) {
      aiSubmissionId.value = res.data.submission_id
      aiGradingStatus.value = 'pending'
      startGradingPoll()
    }

    if (res.data.exp_gained) {
      await userStore.loadGrowth()
    }
  } catch (error) {
    alert('提交失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    isSubmitting.value = false
  }
}

// 轮询AI批改状态
const startGradingPoll = () => {
  if (gradingPollTimer) clearInterval(gradingPollTimer)
  gradingPollTimer = setInterval(async () => {
    if (!aiSubmissionId.value) return
    try {
      const res = await examApi.gradingStatus(aiSubmissionId.value)
      if (res.data.status === 'completed') {
        aiGradingStatus.value = 'completed'
        aiFeedback.value = res.data
        clearInterval(gradingPollTimer)
      }
    } catch (error) {
      console.error('查询批改状态失败:', error)
    }
  }, 3000)

  // 最多等待60秒
  setTimeout(() => {
    if (gradingPollTimer) clearInterval(gradingPollTimer)
  }, 60000)
}

// AI错题解析
const analyzeMistake = async (mistake) => {
  mistake.analyzing = true
  try {
    const res = await examApi.aiAnalysis(
      mistake.question,
      mistake.user,
      mistake.correct,
      selectedExam.value.title
    )
    mistake.aiAnalysis = res.data.analysis
    mistake.showAnalysis = true
  } catch (error) {
    alert('AI分析失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    mistake.analyzing = false
  }
}

const goBack = () => {
  if (timer) clearInterval(timer)
  if (gradingPollTimer) clearInterval(gradingPollTimer)
  if (showResult.value) {
    showResult.value = false
    result.value = null
    selectedExam.value = null
    examConfig.value = null
    aiGradingStatus.value = 'idle'
    aiFeedback.value = null
  } else if (selectedExam.value) {
    if (confirm('确定要退出考试吗？当前进度将丢失。')) {
      selectedExam.value = null
      examConfig.value = null
      if (timer) clearInterval(timer)
    }
  } else {
    router.push('/')
  }
}

const getScoreColor = (score) => {
  if (score >= 90) return '#4ade80'
  if (score >= 70) return '#fbbf24'
  if (score >= 60) return '#fb923c'
  return '#f87171'
}

// 格式化AI解析结果（换行转HTML、高亮关键词）
const formatAIAnalysis = (text) => {
  if (!text) return ''
  return text
    .replace(/\n/g, '<br>')
    .replace(/【([^】]+)】/g, '<strong class="highlight-tag">【$1】</strong>')
}

onMounted(() => {
  loadExams()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (gradingPollTimer) clearInterval(gradingPollTimer)
})
</script>

<template>
  <div class="exam-container">
    <!-- 顶部导航 -->
    <div class="exam-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h1>📝 语言考核站</h1>
      <div v-if="selectedExam && !showResult" class="timer" :class="{ warning: timeLeft < 300 }">
        ⏱️ {{ formatTime(timeLeft) }}
      </div>
      <div v-else class="header-spacer"></div>
    </div>

    <!-- 考试列表 -->
    <div v-if="!selectedExam" class="exam-list">
      <div class="section-title">选择试卷</div>
      <div class="exams-grid">
        <div
          v-for="exam in exams"
          :key="exam.exam_code"
          class="exam-card"
          @click="selectExam(exam)"
        >
          <div class="exam-icon">📄</div>
          <div class="exam-info">
            <h3>{{ exam.title }}</h3>
            <p>限时 {{ exam.time_limit || 60 }} 分钟</p>
          </div>
          <button class="start-btn">开始答题</button>
        </div>
      </div>

      <div v-if="exams.length === 0 && !isLoading" class="empty-state">
        <span class="empty-icon">📭</span>
        <p>暂无可用试卷</p>
      </div>
    </div>

    <!-- 答题界面 -->
    <div v-else-if="selectedExam && !showResult" class="question-panel">
      <div class="exam-title-bar">
        <h2>{{ selectedExam.title }}</h2>
      </div>

      <div class="sections-container">
        <div v-for="(section, sIdx) in examConfig?.sections" :key="sIdx" class="section-block">
          <h3 class="section-title">{{ section.name }}</h3>
          <p v-if="section.instruction" class="section-instruction">{{ section.instruction }}</p>

          <div v-for="(q, qIdx) in section.questions" :key="q.id" class="question-item">
            <div class="question-header">
              <span class="question-number">{{ qIdx + 1 }}</span>
              <span class="question-text">{{ q.question }}</span>
            </div>

            <!-- 选择题 -->
            <div v-if="q.type === 'choice'" class="options-list">
              <label
                v-for="(opt, optKey) in q.options"
                :key="optKey"
                class="option-item"
                :class="{ selected: answers[q.id] === optKey }"
              >
                <input
                  type="radio"
                  :name="q.id"
                  :value="optKey"
                  v-model="answers[q.id]"
                />
                <span class="option-key">{{ optKey }}</span>
                <span class="option-text">{{ opt }}</span>
              </label>
            </div>

            <!-- 填空题 -->
            <div v-else-if="q.type === 'fill'" class="fill-input">
              <input
                type="text"
                v-model="answers[q.id]"
                placeholder="请输入答案"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="submit-bar">
        <button class="submit-btn" @click="submitExam" :disabled="isSubmitting">
          {{ isSubmitting ? '提交中...' : '提交试卷' }}
        </button>
      </div>
    </div>

    <!-- 成绩展示 -->
    <div v-else-if="showResult && result" class="result-panel">
      <div class="result-header">
        <div class="score-circle" :style="{ borderColor: getScoreColor(result.objective_score || result.score || 0) }">
          <span class="score-value" :style="{ color: getScoreColor(result.objective_score || result.score || 0) }">
            {{ result.objective_score || result.score || 0 }}
          </span>
          <span class="score-label">分</span>
        </div>
        <h2>{{ (result.objective_score || result.score || 0) >= 90 ? '优秀！' : (result.objective_score || result.score) >= 70 ? '良好！' : (result.objective_score || result.score) >= 60 ? '及格' : '继续加油！' }}</h2>
        <p v-if="result.exp_gained">获得 {{ result.exp_gained }} 经验值</p>
      </div>

      <div class="result-details">
        <div class="result-stat">
          <span class="stat-label">客观题得分</span>
          <span class="stat-value">{{ result.objective_score?.toFixed(1) || 0 }}</span>
        </div>
        <div class="result-stat">
          <span class="stat-label">题目总数</span>
          <span class="stat-value">{{ result.total_questions || 0 }}</span>
        </div>
      </div>

      <!-- AI批改状态卡片 -->
      <div v-if="result.has_subjective" class="ai-grading-card">
        <div v-if="aiGradingStatus === 'pending'" class="ai-pending">
          <div class="ai-spinner"></div>
          <span>🤖 AI 正在批改主观题...</span>
        </div>
        <div v-else-if="aiGradingStatus === 'completed' && aiFeedback" class="ai-completed">
          <div class="ai-header">
            <span class="ai-icon">🤖</span>
            <span class="ai-title">AI 批改反馈</span>
          </div>
          <div class="ai-score-row">
            <span>主观题得分</span>
            <span class="ai-score">{{ aiFeedback.subjective_score || 0 }}</span>
          </div>
          <div class="ai-feedback" v-html="(aiFeedback.feedback || '').replace(/\n/g, '<br>')"></div>
        </div>
      </div>

      <!-- 错题本（增强版：带解析） -->
      <div v-if="result.mistakes?.length > 0" class="mistakes-section">
        <h3>📖 错题本</h3>
        <div v-for="(m, idx) in result.mistakes" :key="idx" class="mistake-card">
          <div class="mistake-header">
            <span class="mistake-num">{{ m.question }}</span>
            <span class="mistake-status">❌ 错误</span>
          </div>
          <div class="mistake-answers">
            <div class="your-answer">
              <span class="label">你的答案</span>
              <span class="value wrong">{{ m.user || '未作答' }}</span>
            </div>
            <div class="correct-answer">
              <span class="label">正确答案</span>
              <span class="value correct">{{ m.correct }}</span>
            </div>
          </div>
          <div v-if="m.analysis" class="mistake-analysis">
            <span class="analysis-icon">💡</span>
            <span class="analysis-text">{{ m.analysis }}</span>
          </div>
          <button class="ai-analysis-btn" @click="analyzeMistake(m)" :disabled="m.analyzing">
            {{ m.analyzing ? '⏳ 分析中...' : '🤖 AI 深度解析' }}
          </button>
          <div v-if="m.showAnalysis && m.aiAnalysis" class="ai-analysis-result">
            <div class="analysis-title">🔍 AI 详细解析</div>
            <div class="analysis-content" v-html="formatAIAnalysis(m.aiAnalysis)"></div>
          </div>
        </div>
      </div>

      <button class="back-btn-large" @click="goBack">返回试卷列表</button>
    </div>

    <div v-if="isLoading" class="loading-overlay">
      <div class="spinner"></div>
    </div>
  </div>
</template>

<style scoped>
.exam-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  padding: 20px;
  color: white;
  padding-bottom: 100px;
}

.exam-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  margin-bottom: 20px;
}

.back-btn {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 10px 20px;
  border-radius: 12px;
  cursor: pointer;
}

h1 { margin: 0; font-size: 24px; }
.header-spacer { width: 100px; }

.timer {
  font-size: 18px;
  font-weight: 700;
  padding: 8px 16px;
  background: rgba(74, 222, 128, 0.2);
  border-radius: 12px;
}

.timer.warning {
  background: rgba(248, 113, 113, 0.3);
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: rgba(255, 255, 255, 0.9);
}

.exams-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.exam-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
}

.exam-card:hover {
  background: rgba(255, 255, 255, 0.12);
  transform: translateX(4px);
}

.exam-icon { font-size: 40px; }
.exam-info { flex: 1; }
.exam-info h3 { margin: 0 0 4px 0; font-size: 18px; }
.exam-info p { margin: 0; font-size: 13px; color: rgba(255, 255, 255, 0.6); }

.start-btn {
  padding: 10px 20px;
  background: rgba(74, 222, 128, 0.25);
  border: 1px solid rgba(74, 222, 128, 0.4);
  color: white;
  border-radius: 12px;
  cursor: pointer;
}

.empty-state { text-align: center; padding: 60px; }
.empty-icon { font-size: 48px; display: block; margin-bottom: 12px; }

.question-panel { max-width: 800px; margin: 0 auto; }
.exam-title-bar { margin-bottom: 24px; }
.exam-title-bar h2 { margin: 0; font-size: 22px; }

.sections-container { display: flex; flex-direction: column; gap: 24px; }

.section-block {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  padding: 24px;
}

.section-instruction {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  margin: 0 0 20px 0;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
}

.question-item {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.question-item:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.question-header { display: flex; gap: 12px; margin-bottom: 12px; }

.question-number {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(74, 222, 128, 0.25);
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
}

.question-text { flex: 1; font-size: 15px; line-height: 1.6; }

.options-list { display: flex; flex-direction: column; gap: 8px; padding-left: 40px; }

.option-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.option-item:hover { background: rgba(255, 255, 255, 0.1); }
.option-item.selected { background: rgba(74, 222, 128, 0.2); border: 1px solid rgba(74, 222, 128, 0.4); }
.option-item input { display: none; }

.option-key {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
}

.option-text { flex: 1; font-size: 14px; }

.fill-input input {
  width: 100%;
  max-width: 300px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  color: white;
  font-size: 15px;
  outline: none;
}

.submit-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 16px 20px;
  background: rgba(30, 40, 60, 0.95);
  backdrop-filter: blur(20px);
  display: flex;
  justify-content: center;
}

.submit-btn {
  padding: 14px 48px;
  background: rgba(74, 222, 128, 0.3);
  border: 1px solid rgba(74, 222, 128, 0.5);
  color: white;
  border-radius: 14px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
}

.submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.result-panel { max-width: 600px; margin: 0 auto; text-align: center; }

.result-header {
  padding: 40px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  margin-bottom: 24px;
}

.score-circle {
  width: 140px;
  height: 140px;
  margin: 0 auto 20px;
  border-radius: 50%;
  border: 6px solid;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.score-value { font-size: 48px; font-weight: 800; line-height: 1; }
.score-label { font-size: 16px; color: rgba(255, 255, 255, 0.6); }
.result-header h2 { margin: 0 0 8px 0; font-size: 24px; }
.result-header p { margin: 0; color: rgba(255, 255, 255, 0.7); }

.result-details { display: flex; justify-content: center; gap: 40px; margin-bottom: 24px; }
.result-stat { text-align: center; }
.stat-label { display: block; font-size: 13px; color: rgba(255, 255, 255, 0.6); margin-bottom: 4px; }
.stat-value { font-size: 24px; font-weight: 700; color: #4ade80; }

/* AI批改卡片 */
.ai-grading-card {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(168, 85, 247, 0.1));
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 20px;
  padding: 24px;
  margin-bottom: 24px;
}

.ai-pending {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #a5b4fc;
}

.ai-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(165, 180, 252, 0.3);
  border-top-color: #a5b4fc;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.ai-completed { text-align: left; }

.ai-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.ai-icon { font-size: 24px; }
.ai-title { font-size: 18px; font-weight: 600; }

.ai-score-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  margin-bottom: 16px;
}

.ai-score {
  font-size: 28px;
  font-weight: 700;
  color: #a5b4fc;
}

.ai-feedback {
  font-size: 14px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.85);
  background: rgba(255, 255, 255, 0.05);
  padding: 16px;
  border-radius: 12px;
  max-height: 300px;
  overflow-y: auto;
}

.mistakes-section {
  background: rgba(248, 113, 113, 0.08);
  border: 1px solid rgba(248, 113, 113, 0.2);
  border-radius: 20px;
  padding: 24px;
  text-align: left;
  margin-bottom: 24px;
}

.mistakes-section h3 {
  margin: 0 0 16px 0;
  font-size: 18px;
  color: #f87171;
}

/* 增强版错题卡片 */
.mistake-card {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 18px;
  margin-bottom: 16px;
  border-left: 3px solid #f87171;
}

.mistake-card .mistake-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.mistake-card .mistake-num {
  font-weight: 700;
  font-size: 15px;
  color: #3b82f6;
}

.mistake-card .mistake-status {
  font-size: 12px;
  color: #f87171;
  background: rgba(248, 113, 113, 0.15);
  padding: 2px 8px;
  border-radius: 6px;
}

.mistake-card .mistake-answers {
  display: flex;
  gap: 20px;
  margin-bottom: 12px;
}

.mistake-card .your-answer,
.mistake-card .correct-answer {
  flex: 1;
}

.mistake-card .label {
  display: block;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 4px;
}

.mistake-card .value {
  font-size: 14px;
  font-weight: 600;
}

.mistake-card .value.wrong { color: #f87171; }
.mistake-card .value.correct { color: #4ade80; }

.mistake-card .mistake-analysis {
  background: rgba(251, 191, 36, 0.1);
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 12px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.mistake-card .analysis-icon {
  font-size: 16px;
}

.mistake-card .analysis-text {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.5;
}

.ai-analysis-btn {
  padding: 8px 16px;
  background: rgba(99, 102, 241, 0.2);
  border: 1px solid rgba(99, 102, 241, 0.4);
  color: #a5b4fc;
  border-radius: 10px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  width: 100%;
}

.ai-analysis-btn:hover:not(:disabled) {
  background: rgba(99, 102, 241, 0.35);
  transform: translateY(-1px);
}

.ai-analysis-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.ai-analysis-result {
  margin-top: 14px;
  padding: 16px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(168, 85, 247, 0.1));
  border-radius: 12px;
  border: 1px solid rgba(99, 102, 241, 0.3);
}

.ai-analysis-result .analysis-title {
  font-size: 14px;
  font-weight: 600;
  color: #a5b4fc;
  margin-bottom: 10px;
}

.ai-analysis-result .analysis-content {
  font-size: 13px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.85);
}

.ai-analysis-result .highlight-tag {
  color: #fbbf24;
  font-weight: 600;
}

/* 旧版兼容 */
.mistake-item {
  padding: 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  margin-bottom: 12px;
}

.mistake-question { font-size: 14px; margin-bottom: 8px; }
.mistake-answer { display: flex; gap: 16px; font-size: 13px; margin-bottom: 12px; }
.wrong { color: #f87171; }
.correct { color: #4ade80; }

.back-btn-large {
  padding: 14px 32px;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  border-radius: 14px;
  font-size: 16px;
  cursor: pointer;
}

.loading-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.spinner {
  width: 40px; height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: #4ade80;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
