<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || (import.meta.env.PROD ? '' : 'http://127.0.0.1:8000') })

const isLoading = ref(false)
const aiLoading = ref(false)

const selectedFile = ref(null)
const fileName = ref('')
const exams = ref([])
const submissions = ref([])
const filterExamCode = ref('')

const examCode = ref('')
const examTitle = ref('')
const timeLimit = ref(120)
const audioFile = ref('')
const pdfFile = ref('')
const aiPrompt = ref('')
const apiKey = ref(localStorage.getItem('adminApiKey') || '')
const targetExam = ref('全部')

const currentTemplate = ref('neccs')
const currentModules = ref([])
const answers = ref({})
const weights = ref({})
const showAnswerGrid = ref(false)

const DB_TEMPLATES = {
  cet6: [
    { id: 'c1', title: 'Part I. Writing', start: 1, end: 1, type: 'textarea', hasObj: false },
    { id: 'c2', title: 'Part II. Listening A&B', start: 2, end: 16, type: 'choice', defaultWeight: 7.1, hasObj: true },
    { id: 'c3', title: 'Part II. Listening C', start: 17, end: 26, type: 'choice', defaultWeight: 14.2, hasObj: true },
    { id: 'c4', title: 'Part III. Blank', start: 27, end: 36, type: 'blank', defaultWeight: 3.55, hasObj: true },
    { id: 'c5', title: 'Part III. Match', start: 37, end: 46, type: 'blank', defaultWeight: 7.1, hasObj: true },
    { id: 'c6', title: 'Part III. Reading', start: 47, end: 56, type: 'choice', defaultWeight: 14.2, hasObj: true },
    { id: 'c7', title: 'Part IV. Translation', start: 57, end: 57, type: 'textarea', hasObj: false }
  ],
  neccs: [
    { id: 'n1', title: 'I. Listening Choice', start: 1, end: 20, type: 'choice', defaultWeight: 1, hasObj: true },
    { id: 'n2', title: 'I. Listening Blanks', start: 21, end: 25, type: 'blank', defaultWeight: 1, hasObj: true },
    { id: 'n3', title: 'II. Vocab & Culture', start: 26, end: 40, type: 'choice', defaultWeight: 1, hasObj: true },
    { id: 'n4', title: 'III. Cloze', start: 41, end: 50, type: 'blank', defaultWeight: 1, hasObj: true },
    { id: 'n5', title: 'IV. Reading Choice', start: 51, end: 55, type: 'choice_extended', defaultWeight: 1, hasObj: true },
    { id: 'n6', title: 'IV. Reading Short', start: 56, end: 65, type: 'blank', defaultWeight: 2, hasObj: true },
    { id: 'n7', title: 'V. Translation', start: 66, end: 67, type: 'textarea', hasObj: false },
    { id: 'n8', title: 'VI. IQ Test', start: 68, end: 72, type: 'blank', defaultWeight: 1, hasObj: true },
    { id: 'n9', title: 'VII. Error Correction', start: 73, end: 82, type: 'blank', defaultWeight: 1, hasObj: true },
    { id: 'n10', title: 'VIII. Writing', start: 83, end: 84, type: 'textarea', hasObj: false }
  ],
  mini: [
    { id: 'm1', title: '翻译小练习', start: 1, end: 1, type: 'textarea', hasObj: false }
  ]
}

const objectiveQuestions = computed(() => {
  const result = []
  currentModules.value.forEach((mod) => {
    if (mod.checked && mod.hasObj) {
      for (let i = mod.start; i <= mod.end; i += 1) {
        result.push({ num: i, weight: mod.defaultWeight || 1 })
      }
    }
  })
  return result
})

function goBack() {
  router.push('/more')
}

function handleFileSelect(event) {
  const file = event.target.files?.[0]
  if (file) {
    selectedFile.value = file
    fileName.value = file.name
  }
}

async function uploadResource() {
  if (!selectedFile.value) {
    alert('请先选择文件')
    return
  }

  isLoading.value = true
  const formData = new FormData()
  formData.append('file', selectedFile.value)

  try {
    const res = await api.post('/api/admin/upload', formData)
    alert(res.data.message || '上传成功')
    selectedFile.value = null
    fileName.value = ''
  } catch (error) {
    alert(error.response?.data?.detail || '上传失败')
  } finally {
    isLoading.value = false
  }
}

function switchTemplate(type) {
  currentTemplate.value = type
  currentModules.value = DB_TEMPLATES[type].map((item) => ({ ...item, checked: true }))
  showAnswerGrid.value = false
  answers.value = {}
  weights.value = {}

  if (type === 'cet6') {
    examCode.value = 'cet6_2024'
    examTitle.value = '大学英语六级模考'
    timeLimit.value = 130
    aiPrompt.value = '请根据标准答案对主观题进行评分，并给出简明评语。'
    targetExam.value = '全部'
  } else if (type === 'neccs') {
    examCode.value = 'neccs_2024_pre'
    examTitle.value = '大英赛初赛'
    timeLimit.value = 120
    aiPrompt.value = '请根据标准答案对主观题进行评分，并附上参考范文。'
    targetExam.value = '初赛'
  } else {
    examCode.value = 'mini_test_01'
    examTitle.value = '每日特训'
    timeLimit.value = 40
    aiPrompt.value = '请按照 15 分制为翻译题评分。'
    targetExam.value = '全部'
  }
}

function generateAnswerGrid() {
  objectiveQuestions.value.forEach((q) => {
    if (!weights.value[q.num]) {
      weights.value[q.num] = q.weight
    }
  })
  showAnswerGrid.value = true
}

function saveApiKey() {
  localStorage.setItem('adminApiKey', apiKey.value)
}

async function callAIParser() {
  if (!apiKey.value.trim()) {
    alert('请先填写 AI API Key')
    return
  }
  if (!pdfFile.value.trim()) {
    alert('请填写解析文档文件名')
    return
  }

  saveApiKey()
  aiLoading.value = true

  try {
    const res = await api.post('/api/admin/parse_answers', {
      api_key: apiKey.value,
      pdf_filename: pdfFile.value,
      target_exam: targetExam.value
    })
    const data = res.data || {}
    let fillCount = 0

    Object.entries(data.obj_answers || {}).forEach(([key, value]) => {
      const pureNumber = String(key).replace(/[^0-9]/g, '')
      if (pureNumber) {
        answers.value[`q${pureNumber}`] = value
        fillCount += 1
      }
    })

    if (data.subj_prompt) {
      aiPrompt.value = `${aiPrompt.value}\n\n${data.subj_prompt}`.trim()
    }

    showAnswerGrid.value = true
    alert(`提取成功，已自动填入 ${fillCount} 道客观题答案`)
  } catch (error) {
    alert(error.response?.data?.detail || 'AI 解析失败')
  } finally {
    aiLoading.value = false
  }
}

async function saveExam() {
  if (!examCode.value.trim() || !examTitle.value.trim()) {
    alert('代号和名称不能为空')
    return
  }

  const finalConfig = currentModules.value.filter((m) => m.checked)
  const finalAnsKey = {}

  objectiveQuestions.value.forEach((q) => {
    const ans = answers.value[`q${q.num}`]
    if (ans) {
      finalAnsKey[`q${q.num}`] = {
        ans,
        weight: weights.value[q.num] || q.weight
      }
    }
  })

  try {
    const res = await api.post('/api/admin/save_exam', {
      exam_code: examCode.value.trim(),
      title: examTitle.value.trim(),
      audio_file: audioFile.value.trim(),
      pdf_file: pdfFile.value.trim(),
      time_limit: parseInt(timeLimit.value, 10) || 120,
      config_json: JSON.stringify(finalConfig),
      answer_key_json: JSON.stringify(finalAnsKey),
      ai_prompt: aiPrompt.value.trim()
    })
    alert(res.data.message || '保存成功')
    await loadExams()
  } catch (error) {
    alert(error.response?.data?.detail || '保存失败')
  }
}

async function loadExams() {
  try {
    const res = await api.get('/api/admin/exams')
    exams.value = res.data.exams || []
  } catch (error) {
    console.error('加载考试列表失败:', error)
  }
}

async function deleteExam(code) {
  if (!confirm(`确定要删除考试 ${code} 吗？`)) return

  try {
    await api.delete(`/api/admin/exam/${code}`)
    await loadExams()
  } catch (error) {
    alert(error.response?.data?.detail || '删除失败')
  }
}

async function loadSubmissions() {
  try {
    const url = filterExamCode.value
      ? `/api/admin/submissions?exam_code=${filterExamCode.value}`
      : '/api/admin/submissions'
    const res = await api.get(url)
    submissions.value = res.data.submissions || []
  } catch (error) {
    console.error('加载提交记录失败:', error)
  }
}

async function batchGrade() {
  isLoading.value = true
  try {
    const url = filterExamCode.value
      ? `/api/admin/batch_grade?exam_code=${filterExamCode.value}`
      : '/api/admin/batch_grade'
    const res = await api.post(url)
    alert(res.data.message || '批改完成')
    await loadSubmissions()
  } catch (error) {
    alert(error.response?.data?.detail || '批量批改失败')
  } finally {
    isLoading.value = false
  }
}

onMounted(async () => {
  switchTemplate('neccs')
  await loadExams()
  await loadSubmissions()
})
</script>

<template>
  <div class="admin-container">
    <header class="admin-header">
      <button class="back-btn" @click="goBack">返回</button>
      <h1>开发者控制台</h1>
      <div class="header-badge">Admin</div>
    </header>

    <div class="admin-body">
      <main class="main-area">
        <section class="panel">
          <h2>资源上传</h2>
          <div class="upload-box">
            <input id="file-input" type="file" accept=".pdf,.doc,.docx,.mp3,.wav" @change="handleFileSelect" />
            <label for="file-input" class="upload-label">选择 PDF / Word / 音频文件</label>
            <div class="file-status">{{ fileName || '当前未选择任何文件' }}</div>
            <button class="btn btn-green" :disabled="!selectedFile || isLoading" @click="uploadResource">上传资源</button>
          </div>
        </section>

        <section class="panel">
          <h2>全真考场生成器</h2>
          <div class="template-buttons">
            <button class="btn btn-purple" @click="switchTemplate('cet6')">载入标准六级考场</button>
            <button class="btn btn-purple" @click="switchTemplate('neccs')">载入标准大英赛</button>
            <button class="btn btn-orange" @click="switchTemplate('mini')">载入每日专项小测</button>
          </div>

          <div class="form-row">
            <div class="form-item">
              <label>试卷代号</label>
              <input v-model="examCode" type="text" placeholder="如：cet6_2024" />
            </div>
            <div class="form-item">
              <label>试卷名称</label>
              <input v-model="examTitle" type="text" placeholder="如：大学英语六级模考" />
            </div>
            <div class="form-item">
              <label>考试时长（分钟）</label>
              <input v-model.number="timeLimit" type="number" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-item">
              <label>音频文件</label>
              <input v-model="audioFile" type="text" placeholder="如：cet6_audio.mp3" />
            </div>
            <div class="form-item">
              <label>解析文档</label>
              <input v-model="pdfFile" type="text" placeholder="如：2024_答案解析.pdf" />
            </div>
          </div>

          <div class="module-section">
            <label class="section-label">勾选组卷模块</label>
            <div class="module-grid">
              <label v-for="mod in currentModules" :key="mod.id" class="module-card">
                <input v-model="mod.checked" type="checkbox" />
                <span class="module-title">{{ mod.title }}</span>
                <span class="module-range">(Q{{ mod.start }}-Q{{ mod.end }})</span>
              </label>
            </div>
          </div>

          <button class="btn btn-blue full-btn" @click="generateAnswerGrid">生成客观题录入网格</button>

          <div v-if="showAnswerGrid" class="answer-section">
            <label class="section-label">客观题答案录入</label>
            <div class="ans-grid">
              <div v-for="q in objectiveQuestions" :key="q.num" class="ans-cell">
                <span class="q-num">Q{{ q.num }}</span>
                <input v-model="answers[`q${q.num}`]" class="ans-input" placeholder="答案" autocomplete="off" />
                <input v-model.number="weights[q.num]" type="number" step="0.01" class="weight-input" title="分值" />
              </div>
            </div>

            <label class="section-label">AI 主观题评分标准</label>
            <textarea v-model="aiPrompt" rows="8" placeholder="输入 AI 评分标准或参考范文"></textarea>

            <button class="btn btn-green full-btn" @click="saveExam">保存试卷并发布</button>
          </div>
        </section>

        <section class="panel">
          <h2>考试管理</h2>
          <div class="panel-actions">
            <button class="btn btn-blue" @click="loadExams">刷新列表</button>
            <button class="btn btn-orange" :disabled="isLoading" @click="batchGrade">
              {{ isLoading ? '批改中...' : '批量 AI 批改' }}
            </button>
          </div>
          <div class="exam-list">
            <div v-for="exam in exams" :key="exam.exam_code" class="exam-row">
              <div class="exam-info">
                <div class="exam-title">{{ exam.title }}</div>
                <div class="exam-meta">代号: {{ exam.exam_code }} | 时长: {{ exam.time_limit }} 分钟</div>
              </div>
              <button class="btn btn-red btn-sm" @click="deleteExam(exam.exam_code)">删除</button>
            </div>
            <div v-if="exams.length === 0" class="empty-msg">暂无考试</div>
          </div>
        </section>

        <section class="panel">
          <h2>学生提交记录</h2>
          <select v-model="filterExamCode" class="filter-select" @change="loadSubmissions">
            <option value="">全部考试</option>
            <option v-for="exam in exams" :key="exam.exam_code" :value="exam.exam_code">
              {{ exam.title }}
            </option>
          </select>
          <div class="submission-list">
            <div v-for="item in submissions" :key="item.id" class="submission-row">
              <div class="sub-info">
                <div class="sub-name">{{ item.username }}</div>
                <div class="sub-exam">{{ item.exam_title || item.exam_code }}</div>
              </div>
              <div class="sub-scores">
                <span>客观: {{ (item.obj_score || 0).toFixed(1) }}</span>
                <span>主观: {{ item.subj_score || '待批改' }}</span>
              </div>
              <div class="sub-time">{{ item.submit_time?.split('T')[0] }}</div>
            </div>
            <div v-if="submissions.length === 0" class="empty-msg">暂无提交记录</div>
          </div>
        </section>
      </main>

      <aside class="ai-sidebar">
        <h2>AI 文档解析</h2>
        <p class="sidebar-desc">
          填好解析文档文件名后，可以直接让 AI 从整份文档里提取客观题答案，并把主观题参考内容追加到评分提示中。
        </p>

        <label>AI API Key</label>
        <input v-model="apiKey" type="password" placeholder="sk-..." @blur="saveApiKey" />

        <label>提取目标</label>
        <select v-model="targetExam" class="target-select">
          <option value="初赛">仅提取初赛答案</option>
          <option value="决赛">仅提取决赛答案</option>
          <option value="全部">直接提取全部</option>
        </select>

        <button class="btn btn-orange full-btn" :disabled="aiLoading" @click="callAIParser">
          {{ aiLoading ? 'AI 正在读取整份试卷...' : 'AI 智能读取文档并自动填充' }}
        </button>
      </aside>
    </div>

    <div v-if="isLoading" class="loading-overlay">
      <div class="spinner"></div>
    </div>
  </div>
</template>

<style scoped>
.admin-container {
  min-height: 100vh;
  background: #1e1e2f;
  color: #d4d4d8;
  padding: 20px;
}

.admin-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.back-btn,
.btn {
  border: none;
  border-radius: 12px;
  cursor: pointer;
  font-weight: 700;
}

.back-btn {
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.header-badge {
  margin-left: auto;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(56, 189, 248, 0.14);
  color: #7dd3fc;
}

.admin-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 20px;
}

.main-area {
  display: grid;
  gap: 20px;
}

.panel,
.ai-sidebar {
  padding: 20px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.panel h2,
.ai-sidebar h2 {
  margin: 0 0 16px;
}

.upload-box,
.module-section,
.answer-section {
  display: grid;
  gap: 14px;
}

.file-status,
.sidebar-desc,
.exam-meta,
.sub-exam,
.empty-msg {
  color: #a1a1aa;
}

.upload-label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 12px 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.06);
  cursor: pointer;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 14px;
}

.form-item,
.ai-sidebar {
  display: grid;
  gap: 8px;
}

input,
textarea,
select {
  width: 100%;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}

.template-buttons,
.panel-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
}

.btn {
  padding: 12px 16px;
}

.btn-blue {
  background: #2563eb;
  color: #fff;
}

.btn-purple {
  background: #7c3aed;
  color: #fff;
}

.btn-orange {
  background: #f97316;
  color: #111827;
}

.btn-green {
  background: #10b981;
  color: #032a21;
}

.btn-red {
  background: #ef4444;
  color: #fff;
}

.btn-sm {
  padding: 8px 12px;
}

.full-btn {
  width: 100%;
}

.module-grid,
.ans-grid {
  display: grid;
  gap: 10px;
}

.module-grid {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.module-card,
.ans-cell,
.exam-row,
.submission-row {
  padding: 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.module-card {
  display: grid;
  gap: 6px;
}

.ans-grid {
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
}

.ans-cell {
  display: grid;
  gap: 8px;
}

.exam-row,
.submission-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.exam-list,
.submission-list {
  display: grid;
  gap: 10px;
}

.sub-scores {
  display: flex;
  gap: 14px;
}

.loading-overlay {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, 0.6);
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid rgba(255, 255, 255, 0.2);
  border-top-color: #38bdf8;
  border-radius: 999px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 960px) {
  .admin-body {
    grid-template-columns: 1fr;
  }

  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
