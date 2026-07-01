<script setup>
defineProps({
  title: {
    type: String,
    default: ''
  },
  closable: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close'])
</script>

<template>
  <div class="space-panel">
    <div v-if="title || closable" class="panel-header">
      <h3>{{ title }}</h3>
      <button v-if="closable" class="close-btn" @click="$emit('close')">×</button>
    </div>
    <div class="panel-content">
      <slot></slot>
    </div>
  </div>
</template>

<style scoped>
.space-panel {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  border: 2px solid #3b82f6;
  border-radius: 8px;
  padding: 16px;
  color: white;
  font-family: 'Segoe UI', sans-serif;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.3);
  margin-bottom: 12px;
}

.panel-header h3 {
  font-size: 1.2em;
  font-weight: 600;
  margin: 0;
  color: #3b82f6;
}

.close-btn {
  background: transparent;
  border: 1px solid rgba(239, 68, 68, 0.5);
  color: #ef4444;
  font-size: 1.2em;
  cursor: pointer;
  padding: 4px 12px;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: #ef4444;
}

.panel-content {
  /* Content styling */
}
</style>
