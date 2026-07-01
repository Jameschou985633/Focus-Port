<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { examApi } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const exams = ref([])
const selectedExam = ref(null)
const answers = ref({})
const isLoading = ref(false)
const isSubmitting = ref(false)
const showResult = ref(false)
const result = ref(null)
const timeLeft = ref(0)
let timer = null

const examConfig = computed(() => selectedExam.value?.config_json || { sections: [] })

const allQuestions = computed(() =>
  (examConfig.value.sections || []).flatMap((section) => section.questions || [])
)

const answeredCount = computed(() =>
  allQuestions.value.filter((question) => String(answers.value[question.id] || '').trim()).length
)

const loadExams = async () => {
  isLoading.value = true
  try {
    const res = await examApi.list()
    exams.value = res.data.exams || []
  } catch (error) {
    console.error('加载试卷列表失败:', error)
  } finally {
    isLoading.value = false
  }
}

const startTimer = () => {
  if (timer) clearInterval(timer)
  timer = setInterval(() => {
    if (timeLeft.value > 0) {
      timeLeft.value -= 1
      return
    }
    submitExam()
  }, 1000)
}

const selectExam = (exam) => {
  selectedExam.value = exam
  answers.value = {}
  result.value = null
  showResult.value = false
  timeLeft.value = (exam.time_limit || 60) * 60

  allQuestions.value.forEach((question) => {
    answers.value[question.id] = ''
  })
  startTimer()
}

const formatTime = (seconds) => {
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}

const submitExam = async () => {
  if (!selectedExam.value || isSubmitting.value) return
  if (timer) clearInterval(timer)
  isSubmitting.value = true

  try {
    const usedSeconds = (selectedExam.value.time_limit || 60) * 60 - timeLeft.value
    const res = await examApi.submit(
      selectedExam.value.exam_code,
      userStore.username,
      answers.value,
      usedSeconds
    )
    result.value = res.data
    showResult.value = true
    if (res.data.exp_gained) {
      await userStore.loadGrowth()
    }
  } catch (error) {
    alert('提交失败：' + (error.response?.data?.detail || error.message))
    startTimer()
  } finally {
    isSubmitting.value = false
  }
}

const goBack = () => {
  if (showResult.value) {
    showResult.value = false
    selectedExam.value = null
    result.value = null
    return
  }

  if (selectedExam.value) {
    if (!confirm('确定要退出答题吗？当前进度将丢失。')) return
    selectedExam.value = null
    answers.value = {}
    if (timer) clearInterval(timer)
    return
  }

  router.push('/')
}

const getScoreColor = (score) => {
  if (score >= 90) return '#4ade80'
  if (score >= 70) return '#fbbf24'
  if (score >= 60) return '#fb923c'
  return '#f87171'
}

const scoreTitle = computed(() => {
  const score = Number(result.value?.objective_score || result.value?.score || 0)
  if (score >= 90) return '优秀'
  if (score >= 70) return '良好'
  if (score >= 60) return '及格'
  return '继续加油'
})

onMounted(loadExams)

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div class="exam-container">
    <header class="exam-header">
      <button class="back-btn" type="button" @click="goBack">返回</button>
      <div>
        <p class="eyebrow">在线答题</p>
        <h1>语言考核站</h1>
      </div>
      <div v-if="selectedExam && !showResult" class="timer" :class="{ warning: timeLeft < 300 }">
        {{ formatTime(timeLeft) }}
      </div>
      <div v-else class="header-spacer"></div>
    </header>

    <section v-if="!selectedExam" class="exam-list">
      <div class="section-title">选择试卷</div>
      <div v-if="isLoading" class="empty-state">正在加载试卷...</div>

      <div v-else-if="exams.length" class="exams-grid">
        <article
          v-for="exam in exams"
          :key="exam.exam_code"
          class="exam-card"
          @click="selectExam(exam)"
        >
          <div class="exam-icon">卷</div>
          <div class="exam-info">
            <h3>{{ exam.title }}</h3>
            <p>限时 {{ exam.time_limit || 60 }} 分钟</p>
          </div>
          <button class="start-btn" type="button">开始答题</button>
        </article>
      </div>

      <div v-else class="empty-state">暂无可用试卷</div>
    </section>

    <section v-else-if="selectedExam && !showResult" class="question-panel">
      <div class="exam-title-bar">
        <div>
          <p class="eyebrow">答题中</p>
          <h2>{{ selectedExam.title }}</h2>
        </div>
        <span>{{ answeredCount }}/{{ allQuestions.length }} 已答</span>
      </div>

      <div class="sections-container">
        <section v-for="(section, sectionIndex) in examConfig.sections" :key="sectionIndex" class="section-block">
          <h3>{{ section.name }}</h3>
          <p v-if="section.instruction" class="section-instruction">{{ section.instruction }}</p>

          <article v-for="(question, questionIndex) in section.questions" :key="question.id" class="question-item">
            <div class="question-header">
              <span class="question-number">{{ questionIndex + 1 }}</span>
              <span class="question-text">{{ question.question }}</span>
            </div>

            <div v-if="question.type === 'choice'" class="options-list">
              <label
                v-for="(option, optionKey) in question.options"
                :key="optionKey"
                class="option-item"
                :class="{ selected: answers[question.id] === optionKey }"
              >
                <input v-model="answers[question.id]" type="radio" :name="question.id" :value="optionKey">
                <span class="option-key">{{ optionKey }}</span>
                <span class="option-text">{{ option }}</span>
              </label>
            </div>

            <div v-else class="fill-input">
              <input v-model="answers[question.id]" type="text" placeholder="请输入答案">
            </div>
          </article>
        </section>
      </div>

      <div class="submit-bar">
        <button class="submit-btn" type="button" :disabled="isSubmitting" @click="submitExam">
          {{ isSubmitting ? '提交中...' : '提交试卷' }}
        </button>
      </div>
    </section>

    <section v-else-if="showResult && result" class="result-panel">
      <div class="result-header">
        <div class="score-circle" :style="{ borderColor: getScoreColor(result.objective_score || result.score || 0) }">
          <span class="score-value" :style="{ color: getScoreColor(result.objective_score || result.score || 0) }">
            {{ result.objective_score || result.score || 0 }}
          </span>
          <span class="score-label">分</span>
        </div>
        <h2>{{ scoreTitle }}</h2>
        <p v-if="result.exp_gained">获得 {{ result.exp_gained }} 经验值</p>
      </div>

      <div class="result-details">
        <div class="result-stat">
          <span class="stat-label">客观题得分</span>
          <span class="stat-value">{{ Number(result.objective_score || 0).toFixed(1) }}</span>
        </div>
        <div class="result-stat">
          <span class="stat-label">题目总数</span>
          <span class="stat-value">{{ result.total_questions || 0 }}</span>
        </div>
      </div>

      <div v-if="result.mistakes?.length" class="mistakes-section">
        <h3>错题本</h3>
        <article v-for="(mistake, index) in result.mistakes" :key="index" class="mistake-card">
          <strong>{{ mistake.question }}</strong>
          <div class="mistake-answers">
            <span>你的答案：<b class="wrong">{{ mistake.user || '未作答' }}</b></span>
            <span>正确答案：<b class="correct">{{ mistake.correct }}</b></span>
          </div>
          <p v-if="mistake.analysis">{{ mistake.analysis }}</p>
        </article>
      </div>

      <button class="back-btn-large" type="button" @click="goBack">返回试卷列表</button>
    </section>
  </div>
</template>

<style scoped>
.exam-container {
  min-height: 100vh;
  padding: 20px;
  padding-bottom: 100px;
  color: white;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}

.exam-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 24px;
  margin-bottom: 20px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
}

.back-btn,
.start-btn,
.submit-btn,
.back-btn-large {
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  color: white;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.15);
}

.back-btn {
  padding: 10px 20px;
}

.eyebrow {
  margin: 0 0 4px;
  color: rgba(255, 255, 255, 0.62);
  font-size: 12px;
  letter-spacing: 0.12em;
}

h1,
h2,
h3 {
  margin: 0;
}

.header-spacer {
  width: 100px;
}

.timer {
  padding: 8px 16px;
  border-radius: 12px;
  background: rgba(74, 222, 128, 0.2);
  font-size: 18px;
  font-weight: 700;
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
  margin-bottom: 16px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 16px;
  font-weight: 600;
}

.exams-grid,
.sections-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.exam-card,
.question-panel,
.result-panel,
.section-block,
.question-item,
.mistake-card,
.empty-state {
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
}

.exam-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  cursor: pointer;
  transition: transform 0.2s, background 0.2s;
}

.exam-card:hover {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.12);
}

.exam-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: rgba(96, 165, 250, 0.22);
  color: #bfdbfe;
  font-weight: 800;
}

.exam-info {
  flex: 1;
}

.exam-info h3 {
  margin-bottom: 4px;
  font-size: 18px;
}

.exam-info p {
  margin: 0;
  color: rgba(255, 255, 255, 0.6);
  font-size: 13px;
}

.start-btn {
  padding: 10px 16px;
  background: rgba(59, 130, 246, 0.72);
}

.question-panel,
.result-panel {
  padding: 24px;
}

.exam-title-bar,
.result-details,
.mistake-answers {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.exam-title-bar {
  margin-bottom: 24px;
}

.section-block {
  padding: 18px;
}

.section-block h3 {
  margin-bottom: 8px;
}

.section-instruction {
  margin: 0 0 14px;
  color: rgba(255, 255, 255, 0.65);
}

.question-item {
  padding: 16px;
  margin-top: 12px;
}

.question-header {
  display: flex;
  gap: 12px;
  margin-bottom: 14px;
}

.question-number {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: rgba(96, 165, 250, 0.28);
  color: #bfdbfe;
  font-weight: 700;
}

.options-list {
  display: grid;
  gap: 10px;
}

.option-item {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 14px;
  cursor: pointer;
}

.option-item.selected {
  border-color: rgba(96, 165, 250, 0.78);
  background: rgba(96, 165, 250, 0.16);
}

.option-key {
  font-weight: 800;
  color: #93c5fd;
}

.fill-input input {
  width: 100%;
  box-sizing: border-box;
  padding: 12px 14px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 14px;
  color: white;
  background: rgba(255, 255, 255, 0.1);
}

.submit-bar {
  position: sticky;
  bottom: 20px;
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.submit-btn,
.back-btn-large {
  padding: 14px 22px;
  background: rgba(34, 197, 94, 0.72);
  font-weight: 700;
}

.submit-btn:disabled {
  opacity: 0.55;
  cursor: wait;
}

.result-header {
  display: grid;
  justify-items: center;
  gap: 12px;
  margin-bottom: 24px;
  text-align: center;
}

.score-circle {
  display: grid;
  place-items: center;
  width: 120px;
  height: 120px;
  border: 6px solid #4ade80;
  border-radius: 999px;
}

.score-value {
  font-size: 36px;
  font-weight: 900;
}

.score-label {
  color: rgba(255, 255, 255, 0.62);
}

.result-stat {
  flex: 1;
  padding: 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.08);
}

.stat-label {
  display: block;
  margin-bottom: 8px;
  color: rgba(255, 255, 255, 0.62);
}

.stat-value {
  font-size: 24px;
  font-weight: 800;
}

.mistakes-section {
  margin-top: 24px;
}

.mistake-card {
  padding: 16px;
  margin-top: 12px;
}

.wrong {
  color: #fca5a5;
}

.correct {
  color: #86efac;
}

.back-btn-large {
  width: 100%;
  margin-top: 24px;
  background: rgba(59, 130, 246, 0.72);
}

.empty-state {
  padding: 32px;
  text-align: center;
  color: rgba(255, 255, 255, 0.72);
}

@media (max-width: 680px) {
  .exam-header,
  .exam-card,
  .exam-title-bar,
  .result-details,
  .mistake-answers {
    align-items: stretch;
    flex-direction: column;
  }

  .header-spacer {
    display: none;
  }
}
</style>
