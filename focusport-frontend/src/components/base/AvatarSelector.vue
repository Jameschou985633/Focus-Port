<script setup>
import { ref, defineProps, defineEmits } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: '👨‍🚀'
  },
  visible: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'update:visible', 'select'])

// 预设头像列表 - 太空主题
const presetAvatars = [
  '👨‍🚀', '👩‍🚀', '🧑‍🚀', '👽', '🤖', '🦸',
  '🧙', '🧛', '🧜', '🧚', '🦹', '🥷',
  '👨‍🔬', '👩‍🔬', '🧑‍🔬', '👨‍💻', '👩‍💻', '🧑‍💻',
  '🦊', '🐱', '🐶', '🦁', '🐼', '🦋'
]

const selectedAvatar = ref(props.modelValue)
const activeCategory = ref('space')

const categories = [
  { id: 'space', label: '太空', icons: ['👨‍🚀', '👩‍🚀', '🧑‍🚀', '👽', '🤖', '🦸'] },
  { id: 'fantasy', label: '奇幻', icons: ['🧙', '🧛', '🧜', '🧚', '🦹', '🥷'] },
  { id: 'jobs', label: '职业', icons: ['👨‍🔬', '👩‍🔬', '🧑‍🔬', '👨‍💻', '👩‍💻', '🧑‍💻'] },
  { id: 'animals', label: '动物', icons: ['🦊', '🐱', '🐶', '🦁', '🐼', '🦋'] }
]

const filteredAvatars = ref(presetAvatars)

const filterByCategory = (categoryId) => {
  activeCategory.value = categoryId
  const category = categories.find(c => c.id === categoryId)
  filteredAvatars.value = category ? category.icons : presetAvatars
}

const selectAvatar = (avatar) => {
  selectedAvatar.value = avatar
  emit('update:modelValue', avatar)
  emit('select', avatar)
}

const close = () => {
  emit('update:visible', false)
}

const confirm = () => {
  emit('update:modelValue', selectedAvatar.value)
  emit('update:visible', false)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="avatar-selector-overlay" @click.self="close">
        <div class="avatar-selector-modal">
          <div class="modal-header">
            <h3>🚀 选择头像</h3>
            <button class="close-btn" @click="close">×</button>
          </div>

          <div class="modal-body">
            <!-- 当前头像预览 -->
            <div class="current-avatar">
              <div class="avatar-preview">
                {{ selectedAvatar }}
              </div>
              <span class="preview-label">当前头像</span>
            </div>

            <!-- 分类标签 -->
            <div class="category-tabs">
              <button
                v-for="cat in categories"
                :key="cat.id"
                :class="['category-tab', { active: activeCategory === cat.id }]"
                @click="filterByCategory(cat.id)"
              >
                {{ cat.label }}
              </button>
            </div>

            <!-- 头像网格 -->
            <div class="avatar-grid">
              <div
                v-for="avatar in filteredAvatars"
                :key="avatar"
                :class="['avatar-item', { selected: selectedAvatar === avatar }]"
                @click="selectAvatar(avatar)"
              >
                {{ avatar }}
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button class="cancel-btn" @click="close">取消</button>
            <button class="confirm-btn" @click="confirm">确认</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.avatar-selector-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.avatar-selector-modal {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  border: 2px solid #3b82f6;
  border-radius: 12px;
  width: 90%;
  max-width: 400px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.3);
}

.modal-header h3 {
  margin: 0;
  color: #3b82f6;
  font-size: 1.1em;
}

.close-btn {
  background: transparent;
  border: 1px solid rgba(239, 68, 68, 0.5);
  color: #ef4444;
  font-size: 1.5em;
  cursor: pointer;
  padding: 4px 12px;
  border-radius: 4px;
  line-height: 1;
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
}

.modal-body {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}

.current-avatar {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 20px;
}

.avatar-preview {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, #1e3a5f 0%, #0f2744 100%);
  border: 3px solid #3b82f6;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  margin-bottom: 8px;
}

.preview-label {
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.85em;
}

.category-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.category-tab {
  padding: 8px 16px;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.85em;
}

.category-tab:hover {
  border-color: #475569;
}

.category-tab.active {
  background: rgba(59, 130, 246, 0.2);
  border-color: #3b82f6;
  color: #3b82f6;
}

.avatar-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
}

.avatar-item {
  aspect-ratio: 1;
  background: #0f172a;
  border: 2px solid #334155;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  cursor: pointer;
  transition: all 0.2s;
}

.avatar-item:hover {
  border-color: #475569;
  transform: scale(1.05);
}

.avatar-item.selected {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.2);
  box-shadow: 0 0 10px rgba(59, 130, 246, 0.5);
}

.modal-footer {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid rgba(59, 130, 246, 0.3);
}

.cancel-btn,
.confirm-btn {
  flex: 1;
  padding: 12px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.cancel-btn {
  background: #1e293b;
  border: 1px solid #475569;
  color: rgba(255, 255, 255, 0.8);
}

.cancel-btn:hover {
  background: #334155;
}

.confirm-btn {
  background: linear-gradient(145deg, #1e3a5f 0%, #0f2744 100%);
  border: 2px solid #3b82f6;
  color: white;
}

.confirm-btn:hover {
  box-shadow: 0 0 15px rgba(59, 130, 246, 0.5);
}

/* Transitions */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .avatar-selector-modal,
.modal-leave-to .avatar-selector-modal {
  transform: scale(0.9);
}
</style>
