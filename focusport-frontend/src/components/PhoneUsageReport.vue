<script setup>
import { ref } from 'vue'
import { phoneApi, growthApi } from '../api'

const props = defineProps({
  username: { type: String, required: true }
})

const emit = defineEmits(['reported'])

const showPanel = ref(false)
const isAnalyzing = ref(false)
const showSuccess = ref(false)
const previewImage = ref(null)
const selectedFile = ref(null)
const analyzeResult = ref(null)
const manualMinutes = ref(0)
const category = ref('娱乐')
const notes = ref('')

const categories = ['娱乐', '社交', '游戏', '学习', '工作', '其他']

// 选择文件
const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    selectedFile.value = file
    // 创建预览
    const reader = new FileReader()
    reader.onload = (e) => {
      previewImage.value = e.target.result
    }
    reader.readAsDataURL(file)
    analyzeResult.value = null
  }
}

// AI识别截图
const analyzeScreenshot = async () => {
  if (!selectedFile.value) return

  isAnalyzing.value = true
  try {
    const res = await phoneApi.analyzeScreenshot(selectedFile.value, props.username)

    analyzeResult.value = res.data

    // 如果识别成功，自动填充
    if (res.data.total_minutes) {
      manualMinutes.value = res.data.total_minutes
    }
    if (res.data.top_category) {
      category.value = res.data.top_category
    }
  } catch (error) {
    console.error('AI识别失败:', error)
    alert('识别失败，请手动填写')
  } finally {
    isAnalyzing.value = false
  }
}

// 提交上报
const submitReport = async () => {
  const minutes = manualMinutes.value
  if (minutes <= 0) {
    alert('请先上传截图识别或手动填写使用时长')
    return
  }

  isAnalyzing.value = true
  try {
    await phoneApi.report(props.username, minutes, category.value, notes.value)

    // 更新自律指数
    await growthApi.updateDiscipline(props.username, minutes)

    showSuccess.value = true
    emit('reported')

    setTimeout(() => {
      showSuccess.value = false
      resetForm()
      showPanel.value = false
    }, 2000)
  } catch (error) {
    console.error('上报失败:', error)
    alert('上报失败，请稍后重试')
  } finally {
    isAnalyzing.value = false
  }
}

const resetForm = () => {
  previewImage.value = null
  selectedFile.value = null
  analyzeResult.value = null
  manualMinutes.value = 0
  notes.value = ''
}

const formatTime = (minutes) => {
  if (!minutes) return '--'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h > 0) return `${h}小时${m}分钟`
  return `${m}分钟`
}
</script>

<template>
  <div class="phone-usage-container">
    <!-- 触发按钮 -->
    <button class="toggle-btn" @click="showPanel = !showPanel">
      <span class="icon">📱</span>
      <span class="label">手机上报</span>
    </button>

    <!-- 上报面板 -->
    <div v-if="showPanel" class="phone-usage-panel">
      <h3>📱 手机使用截图识别</h3>
      <p class="hint">上传手机屏幕使用时间截图，AI自动识别</p>

      <!-- 上传区域 -->
      <div class="upload-section">
        <input
          type="file"
          accept="image/*"
          @change="handleFileSelect"
          id="screenshot-input"
          style="display: none"
        />

        <label
          v-if="!previewImage"
          for="screenshot-input"
          class="upload-area"
        >
          <span class="upload-icon">📸</span>
          <span>点击上传截图</span>
          <span class="upload-hint">支持 iOS/Android 屏幕使用时间截图</span>
        </label>

        <div v-else class="preview-area">
          <img :src="previewImage" alt="截图预览" />
          <button class="change-btn" @click="selectedFile = null; previewImage = null; analyzeResult = null">
            换一张
          </button>
        </div>
      </div>

      <!-- AI识别按钮 -->
      <button
        v-if="previewImage && !analyzeResult"
        class="analyze-btn"
        @click="analyzeScreenshot"
        :disabled="isAnalyzing"
      >
        {{ isAnalyzing ? '🔍 AI识别中...' : '🤖 AI识别截图' }}
      </button>

      <!-- 识别结果 -->
      <div v-if="analyzeResult" class="result-section">
        <div class="result-header">
          <span class="success-icon">✅</span>
          <span>AI识别结果</span>
        </div>

        <div class="result-item">
          <span class="result-label">总使用时长</span>
          <span class="result-value highlight">{{ formatTime(analyzeResult.total_minutes) }}</span>
        </div>

        <div v-if="analyzeResult.apps?.length" class="apps-section">
          <div class="result-label">应用使用情况</div>
          <div v-for="app in analyzeResult.apps.slice(0, 5)" :key="app.name" class="app-item">
            <span class="app-name">{{ app.name }}</span>
            <span class="app-time">{{ formatTime(app.minutes) }}</span>
          </div>
        </div>

        <div class="result-tip">
          💡 已自动填充，可手动调整后提交
        </div>
      </div>

      <!-- 手动输入 / 确认 -->
      <div class="manual-section">
        <div class="input-group">
          <label>使用时长 (分钟)</label>
          <input
            type="number"
            v-model="manualMinutes"
            min="1"
            max="720"
            placeholder="手动输入或AI识别自动填充"
          />
        </div>

        <div class="input-group">
          <label>分类</label>
          <select v-model="category">
            <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
          </select>
        </div>

        <div class="input-group">
          <label>备注 (可选)</label>
          <textarea
            v-model="notes"
            placeholder="记录一下..."
            rows="2"
          />
        </div>
      </div>

      <button
        class="submit-btn"
        @click="submitReport"
        :disabled="isAnalyzing || manualMinutes <= 0"
      >
        {{ isAnalyzing ? '提交中...' : '确认上报' }}
      </button>

      <button class="close-btn" @click="showPanel = false; resetForm()">取消</button>
    </div>

    <!-- 成功提示 -->
    <div v-if="showSuccess" class="success-toast">
      ✅ 上报成功！今日手机使用已记录
    </div>
  </div>
</template>

<style scoped>
.phone-usage-container {
  position: relative;
  pointer-events: auto !important;
  z-index: 999;
}

.toggle-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(30, 40, 60, 0.85);
  backdrop-filter: blur(20px);
  border: 2px solid rgba(100, 180, 255, 0.5);
  border-radius: 16px;
  color: white;
  padding: 14px 22px;
  cursor: pointer !important;
  font-size: 15px;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.toggle-btn:hover {
  background: rgba(50, 70, 100, 0.9);
  border-color: rgba(100, 200, 255, 0.8);
  transform: translateY(-2px);
}

.icon { font-size: 18px; }

.phone-usage-panel {
  position: absolute;
  right: auto;
  left: -360px;
  top: 0;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 24px;
  padding: 24px;
  width: 340px;
  z-index: 10000;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  max-height: 80vh;
  overflow-y: auto;
}

h3 {
  color: white;
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: 600;
}

.hint {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  margin: 0 0 16px 0;
}

.upload-section {
  margin-bottom: 16px;
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px 20px;
  background: rgba(255, 255, 255, 0.1);
  border: 2px dashed rgba(255, 255, 255, 0.3);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-area:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.5);
}

.upload-icon {
  font-size: 40px;
  margin-bottom: 8px;
}

.upload-area span:nth-child(2) {
  color: white;
  font-size: 14px;
  font-weight: 500;
}

.upload-hint {
  color: rgba(255, 255, 255, 0.5);
  font-size: 11px;
  margin-top: 6px;
}

.preview-area {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
}

.preview-area img {
  width: 100%;
  max-height: 200px;
  object-fit: contain;
  border-radius: 12px;
}

.change-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.6);
  border: none;
  color: white;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 12px;
  cursor: pointer;
}

.analyze-btn {
  width: 100%;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.4), rgba(139, 92, 246, 0.4));
  border: 1px solid rgba(139, 92, 246, 0.5);
  color: white;
  padding: 14px;
  border-radius: 14px;
  cursor: pointer;
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 16px;
  transition: all 0.3s;
}

.analyze-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(139, 92, 246, 0.3);
}

.analyze-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.result-section {
  background: rgba(74, 222, 128, 0.1);
  border: 1px solid rgba(74, 222, 128, 0.3);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 16px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: white;
  margin-bottom: 12px;
}

.success-icon { font-size: 16px; }

.result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  margin-bottom: 8px;
}

.result-label {
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
}

.result-value {
  color: white;
  font-size: 14px;
}

.result-value.highlight {
  color: #4ade80;
  font-weight: 700;
  font-size: 18px;
}

.apps-section {
  margin-top: 12px;
}

.app-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  margin-bottom: 4px;
}

.app-name {
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
}

.app-time {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
}

.result-tip {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  margin-top: 12px;
  text-align: center;
}

.manual-section {
  margin-bottom: 16px;
}

.input-group {
  margin-bottom: 12px;
}

.input-group label {
  display: block;
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
  margin-bottom: 6px;
}

.input-group input,
.input-group select,
.input-group textarea {
  width: 100%;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 12px;
  padding: 12px 14px;
  color: white;
  font-size: 14px;
  box-sizing: border-box;
}

.input-group input:focus,
.input-group select:focus,
.input-group textarea:focus {
  outline: none;
  border-color: rgba(255, 255, 255, 0.5);
}

.input-group select option {
  background: #1a1a2e;
}

.submit-btn {
  width: 100%;
  background: rgba(74, 222, 128, 0.3);
  border: 1px solid rgba(74, 222, 128, 0.5);
  color: white;
  padding: 14px;
  border-radius: 50px;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
  transition: all 0.3s;
  margin-bottom: 10px;
}

.submit-btn:hover:not(:disabled) {
  background: rgba(74, 222, 128, 0.5);
  transform: translateY(-2px);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.close-btn {
  width: 100%;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: rgba(255, 255, 255, 0.8);
  padding: 10px;
  border-radius: 50px;
  cursor: pointer;
  font-size: 13px;
}

.success-toast {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(74, 222, 128, 0.95);
  color: white;
  padding: 20px 40px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 16px;
  z-index: 10001;
  animation: fadeInOut 2s ease;
  box-shadow: 0 10px 40px rgba(74, 222, 128, 0.4);
}

@keyframes fadeInOut {
  0% { opacity: 0; transform: translate(-50%, -50%) scale(0.9); }
  20% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  80% { opacity: 1; }
  100% { opacity: 0; }
}
</style>
