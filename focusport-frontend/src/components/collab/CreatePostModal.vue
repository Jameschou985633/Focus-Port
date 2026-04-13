<script setup>
import { ref, watch } from 'vue'
import axios from 'axios'
import SpaceButton from '../base/SpaceButton.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  username: { type: String, default: 'guest' }
})

const emit = defineEmits(['update:visible', 'created'])

const content = ref('')
const visibility = ref('friends')
const submitting = ref(false)

const visibilityOptions = [
  { value: 'friends', label: '好友可见', icon: '👥' },
  { value: 'public', label: '公开', icon: '🌐' }
]

const close = () => {
  emit('update:visible', false)
}

const submit = async () => {
  if (!content.value.trim()) {
    alert('请输入动态内容')
    return
  }

  submitting.value = true
  try {
    await axios.post('/api/circle/posts', {
      username: props.username,
      content: content.value.trim(),
      image_urls: [],
      visibility: visibility.value
    })
    content.value = ''
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
  }
})
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="modal-overlay" @click.self="close">
        <div class="modal-content">
          <header class="modal-header">
            <h3>✏️ 发布动态</h3>
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
            <SpaceButton variant="primary" :loading="submitting" @click="submit">
              发布
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
  overflow: hidden;
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

.visibility-section {
  margin-top: 16px;
}

.section-label {
  display: block;
  font-size: 0.85em;
  color: rgba(222, 240, 255, 0.6);
  margin-bottom: 10px;
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
