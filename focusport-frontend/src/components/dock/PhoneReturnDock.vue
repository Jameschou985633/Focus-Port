<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { growthApi } from '../../api'

const props = defineProps({
  username: { type: String, required: true }
})

const emit = defineEmits(['reported'])

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

const isAnalyzing = ref(false)
const previewImage = ref('')
const selectedFile = ref(null)
const analyzeResult = ref(null)
const manualMinutes = ref(0)
const category = ref('学习')
const notes = ref('')
const submitState = ref('')

const categories = ['学习', '工作', '社交', '娱乐', '游戏', '其他']

const resetForm = () => {
  previewImage.value = ''
  selectedFile.value = null
  analyzeResult.value = null
  manualMinutes.value = 0
  notes.value = ''
  submitState.value = ''
}

const handleFileSelect = (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  selectedFile.value = file
  const reader = new FileReader()
  reader.onload = (e) => {
    previewImage.value = e.target?.result || ''
  }
  reader.readAsDataURL(file)
  analyzeResult.value = null
  submitState.value = ''
}

const formatMinutes = (minutes) => {
  if (!minutes) return '--'
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return hours > 0 ? `${hours}小时${mins}分钟` : `${mins}分钟`
}

const analyzeScreenshot = async () => {
  if (!selectedFile.value || isAnalyzing.value) return
  isAnalyzing.value = true
  submitState.value = ''
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('username', props.username)
    const res = await axios.post(`${API_BASE}/api/phone-usage/analyze-screenshot`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    analyzeResult.value = res.data || {}
    manualMinutes.value = res.data?.total_minutes || 0
    category.value = res.data?.top_category || category.value
  } catch (error) {
    submitState.value = error.response?.data?.detail || '识别失败，请手动校正后提交'
  } finally {
    isAnalyzing.value = false
  }
}

const submitReport = async () => {
  if (manualMinutes.value <= 0 || isAnalyzing.value) return
  isAnalyzing.value = true
  submitState.value = ''
  try {
    await axios.post(`${API_BASE}/api/phone-usage/report`, {
      username: props.username,
      usage_minutes: manualMinutes.value,
      category: category.value,
      notes: notes.value,
      screenshot_data: previewImage.value || ''
    })
    await growthApi.updateDiscipline(props.username, manualMinutes.value)
    submitState.value = '回传成功，舰桥记录已更新'
    emit('reported')
    setTimeout(() => {
      resetForm()
    }, 1200)
  } catch (error) {
    submitState.value = error.response?.data?.detail || '回传失败，请稍后再试'
  } finally {
    isAnalyzing.value = false
  }
}
</script>

<template>
  <div class="phone-dock">
    <p class="dock-hint">上传手机使用截图，AI 会生成精简摘要，你可以手动修正后再回传。</p>

    <label class="upload-zone" :class="{ ready: previewImage }">
      <input type="file" accept="image/*" @change="handleFileSelect" />
      <template v-if="previewImage">
        <img :src="previewImage" alt="终端截图预览" class="preview-image" />
        <span class="replace-text">重新选择截图</span>
      </template>
      <template v-else>
        <span class="upload-icon">⌁</span>
        <span class="upload-title">上传终端截图</span>
        <span class="upload-subtitle">支持 iOS / Android 屏幕使用时间截图</span>
      </template>
    </label>

    <button class="action-btn primary" type="button" :disabled="!selectedFile || isAnalyzing" @click="analyzeScreenshot">
      {{ isAnalyzing ? '识别中...' : 'AI 识别摘要' }}
    </button>

    <div v-if="analyzeResult" class="result-card">
      <div class="result-row">
        <span>识别总时长</span>
        <strong>{{ formatMinutes(analyzeResult.total_minutes) }}</strong>
      </div>
      <div class="result-row" v-if="analyzeResult.top_category">
        <span>主要类别</span>
        <strong>{{ analyzeResult.top_category }}</strong>
      </div>
      <div v-if="analyzeResult.apps?.length" class="app-summary">
        <span class="summary-title">摘要</span>
        <div v-for="app in analyzeResult.apps.slice(0, 3)" :key="app.name" class="app-item">
          <span>{{ app.name }}</span>
          <span>{{ formatMinutes(app.minutes) }}</span>
        </div>
      </div>
    </div>

    <div class="form-grid">
      <label class="input-group">
        <span>使用时长</span>
        <input v-model.number="manualMinutes" type="number" min="0" max="1440" placeholder="分钟数" />
      </label>

      <label class="input-group">
        <span>分类</span>
        <select v-model="category">
          <option v-for="item in categories" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
    </div>

    <label class="input-group full">
      <span>备注</span>
      <textarea v-model="notes" rows="2" placeholder="可选：补充这次终端使用说明" />
    </label>

    <div class="dock-actions">
      <button class="action-btn primary" type="button" :disabled="manualMinutes <= 0 || isAnalyzing" @click="submitReport">
        {{ isAnalyzing ? '回传中...' : '确认回传' }}
      </button>
      <button class="action-btn secondary" type="button" @click="resetForm">清空</button>
    </div>

    <p v-if="submitState" class="dock-state">{{ submitState }}</p>
  </div>
</template>

<style scoped>
.phone-dock {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dock-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: rgba(222, 240, 255, 0.76);
}

.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 148px;
  padding: 14px;
  border-radius: 18px;
  border: 1.5px dashed rgba(115, 224, 255, 0.42);
  background: rgba(6, 16, 38, 0.76);
  cursor: pointer;
  text-align: center;
}

.upload-zone input {
  display: none;
}

.upload-zone.ready {
  padding: 10px;
}

.upload-icon {
  font-size: 24px;
}

.upload-title {
  font-weight: 700;
}

.upload-subtitle,
.replace-text {
  font-size: 12px;
  color: rgba(222, 240, 255, 0.72);
}

.preview-image {
  width: 100%;
  max-height: 220px;
  object-fit: contain;
  border-radius: 14px;
}

.result-card {
  padding: 12px;
  border-radius: 16px;
  background: rgba(12, 29, 66, 0.82);
  border: 1px solid rgba(115, 224, 255, 0.18);
}

.result-row,
.app-item {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 13px;
}

.result-row + .result-row,
.app-summary {
  margin-top: 8px;
}

.summary-title {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  color: rgba(222, 240, 255, 0.68);
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: rgba(222, 240, 255, 0.74);
}

.input-group input,
.input-group select,
.input-group textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid rgba(115, 224, 255, 0.22);
  border-radius: 12px;
  background: rgba(6, 16, 38, 0.82);
  color: #eef7ff;
  padding: 10px 12px;
  outline: none;
}

.full {
  width: 100%;
}

.dock-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
  flex: 1;
  min-height: 40px;
  border-radius: 12px;
  border: none;
  color: #eef7ff;
  font-weight: 700;
  cursor: pointer;
}

.action-btn.primary {
  background: linear-gradient(180deg, #2f8dff, #2565d8);
}

.action-btn.secondary {
  background: rgba(255, 255, 255, 0.08);
}

.action-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.dock-state {
  margin: 0;
  font-size: 12px;
  color: #8fe8ff;
}

@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
