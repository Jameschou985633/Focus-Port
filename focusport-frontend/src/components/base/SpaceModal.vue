<script setup>
defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: ''
  },
  width: {
    type: String,
    default: '450px'
  }
})

const emit = defineEmits(['close'])
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
        <div class="modal-container" :style="{ maxWidth: width }">
          <div class="modal-header">
            <h3>{{ title }}</h3>
            <button class="close-btn" @click="$emit('close')">×</button>
          </div>
          <div class="modal-body">
            <slot></slot>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
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

.modal-container {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  border: 2px solid #3b82f6;
  border-radius: 12px;
  padding: 24px;
  color: white;
  font-family: 'Segoe UI', sans-serif;
  max-height: 90vh;
  overflow-y: auto;
  width: 90%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.3);
  margin-bottom: 16px;
}

.modal-header h3 {
  font-size: 1.3em;
  font-weight: 600;
  margin: 0;
  color: #3b82f6;
}

.close-btn {
  background: transparent;
  border: 1px solid rgba(239, 68, 68, 0.5);
  color: #ef4444;
  font-size: 1.5em;
  cursor: pointer;
  padding: 4px 12px;
  border-radius: 4px;
  transition: all 0.2s;
  line-height: 1;
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: #ef4444;
}

.modal-body {
  /* Body styling */
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

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: translateY(-20px);
}
</style>
