<script setup>
import { ref, watch } from 'vue'
import { circleApi } from '../../api'
import SpaceButton from '../base/SpaceButton.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  username: { type: String, default: 'guest' }
})

const emit = defineEmits(['update:visible', 'created'])

const content = ref('')
const visibility = ref('friends')
const submitting = ref(false)
const selectedFiles = ref([])
const previewUrls = ref([])
const fileInput = ref(null)

const visibilityOptions = [
  { value: 'friends', label: '好友可见', icon: '👥' },
  { value: 'public', label: '公开', icon: '🌐' }
]

const close = () => {
  emit('update:visible', false)
}

const pickImages = () => {
  if (selectedFiles.value.length >= 9) return
  fileInput.value?.click()
}

const onFilesSelected = (event) => {
  const files = Array.from(event.target.files || [])
  const remaining = 9 - selectedFiles.value.length
  const toAdd = files.slice(0, remaining).filter(f => {
    if (f.size > 5 * 1024 * 1024) {
      alert(`${f.name} 超过5MB限制`)
      return false
    }
    return f.type.startsWith('image/')
  })
  toAdd.forEach(f => {
    selectedFiles.value.push(f)
    previewUrls.value.push(URL.createObjectURL(f))
  })
  event.target.value = ''
}

const removeImage = (index) => {
  URL.revokeObjectURL(previewUrls.value[index])
  selectedFiles.value.splice(index, 1)
  previewUrls.value.splice(index, 1)
}

const submit = async () => {
  if (!content.value.trim() && selectedFiles.value.length === 0) {
    alert('请输入动态内容或选择图片')
    return
  }

  submitting.value = true
  try {
    // Upload images first
    const uploadedUrls = []
    for (const file of selectedFiles.value) {
      const res = await circleApi.uploadImage(file)
      if (res.data?.url) uploadedUrls.push(res.data.url)
    }

    // Create post with image URLs
    await circleApi.create(
      props.username,
      content.value.trim(),
      uploadedUrls,
      visibility.value
    )

    content.value = ''
    previewUrls.value.forEach(u => URL.revokeObjectURL(u))
    selectedFiles.value = []
    previewUrls.value = []
    emit('created')
    close()
  } catch (error) {
    console.error('发布失败:', error)
    alert(error.response?.data?.detail || '发布失败')
  } finally {
    submitting.value = false
  }
}

watch(() => props.visible, (val) => {
  if (!val) {
    content.value = ''
    visibility.value = 'friends'
    previewUrls.value.forEach(u => URL.revokeObjectURL(u))
    selectedFiles.value = []
    previewUrls.value = []
  }
})
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="modal-overlay" @click.self="close">
        <div class="modal-content">
          <header class="modal-header">
            <h3>发布动态</h3>
            <button type="button" class="close-btn" @click="close">×</button>
          </header>

          <div class="modal-body">
            <textarea
              v-model="content"
              class="content-input"
              placeholder="分享你的学习心得、今日感悟..."
              rows="4"
              maxlength="1000"
            ></textarea>
            <div class="char-count">{{ content.length }}/1000</div>

            <!-- Image picker -->
            <div class="image-section">
              <span class="section-label">图片 (最多9张)</span>
              <div class="image-grid">
                <div v-for="(url, idx) in previewUrls" :key="idx" class="image-preview">
                  <img :src="url" class="preview-thumb" />
                  <button type="button" class="remove-image" @click="removeImage(idx)">×</button>
                </div>
                <button
                  v-if="previewUrls.length < 9"
                  type="button"
                  class="add-image-btn"
                  @click="pickImages"
                >
                  <span class="add-icon">+</span>
                  <span class="add-text">添加图片</span>
                </button>
              </div>
              <input
                ref="fileInput"
                type="file"
                accept="image/jpeg,image/png,image/gif,image/webp"
                multiple
                style="display: none"
                @change="onFilesSelected"
              />
            </div>

            <div class="visibility-section">
              <span class="section-label">可见范围</span>
              <div class="visibility-options">
                <button
                  v-for="opt in visibilityOptions"
                  :key="opt.value"
                  type="button"
                  class="visibility-btn"
                  :class="{ active: visibility === opt.value }"
                  @click="visibility = opt.value"
                >
                  <span class="vis-icon">{{ opt.icon }}</span>
                  <span>{{ opt.label }}</span>
                </button>
              </div>
            </div>
          </div>

          <footer class="modal-footer">
            <SpaceButton variant="secondary" @click="close">取消</SpaceButton>
            <SpaceButton variant="primary" @click="submit">
              {{ submitting ? '发布中...' : '发布' }}
            </SpaceButton>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
  border: 2px solid rgba(59, 130, 246, 0.4);
  border-radius: 20px;
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(115, 224, 255, 0.15);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.1em;
  color: #eef7ff;
}

.close-btn {
  width: 32px;
  height: 32px;
  background: rgba(255, 255, 255, 0.05);
  border: none;
  border-radius: 8px;
  color: rgba(222, 240, 255, 0.7);
  font-size: 20px;
  cursor: pointer;
  transition: all 0.2s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #eef7ff;
}

.modal-body {
  padding: 20px;
}

.content-input {
  width: 100%;
  min-height: 120px;
  padding: 14px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(115, 224, 255, 0.15);
  border-radius: 12px;
  color: #eef7ff;
  font-size: 0.95em;
  line-height: 1.6;
  resize: vertical;
  font-family: inherit;
}

.content-input:focus {
  outline: none;
  border-color: rgba(115, 224, 255, 0.4);
}

.content-input::placeholder {
  color: rgba(222, 240, 255, 0.4);
}

.char-count {
  text-align: right;
  font-size: 0.8em;
  color: rgba(222, 240, 255, 0.5);
  margin-top: 6px;
}

/* Image section */
.image-section {
  margin-top: 16px;
}

.section-label {
  display: block;
  font-size: 0.85em;
  color: rgba(222, 240, 255, 0.6);
  margin-bottom: 10px;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.image-preview {
  position: relative;
  aspect-ratio: 1;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(115, 224, 255, 0.15);
}

.preview-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.remove-image {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 24px;
  height: 24px;
  background: rgba(0, 0, 0, 0.6);
  border: none;
  border-radius: 50%;
  color: #ff6b6b;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-image-btn {
  aspect-ratio: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: rgba(255, 255, 255, 0.03);
  border: 2px dashed rgba(115, 224, 255, 0.2);
  border-radius: 12px;
  color: rgba(222, 240, 255, 0.5);
  cursor: pointer;
  transition: all 0.2s;
}

.add-image-btn:hover {
  border-color: rgba(115, 224, 255, 0.4);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(222, 240, 255, 0.8);
}

.add-icon {
  font-size: 24px;
  font-weight: 300;
}

.add-text {
  font-size: 11px;
}

/* Visibility */
.visibility-section {
  margin-top: 16px;
}

.visibility-options {
  display: flex;
  gap: 12px;
}

.visibility-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(115, 224, 255, 0.15);
  border-radius: 12px;
  color: rgba(222, 240, 255, 0.7);
  cursor: pointer;
  transition: all 0.2s;
}

.visibility-btn:hover {
  background: rgba(255, 255, 255, 0.06);
}

.visibility-btn.active {
  background: linear-gradient(180deg, rgba(49, 120, 255, 0.25), rgba(18, 35, 78, 0.9));
  border-color: rgba(59, 130, 246, 0.5);
  color: #eef7ff;
}

.vis-icon {
  font-size: 18px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid rgba(115, 224, 255, 0.15);
}

/* Transition */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.25s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-content,
.modal-leave-to .modal-content {
  transform: scale(0.95);
}
</style>
