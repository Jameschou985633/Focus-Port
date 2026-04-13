<script setup>
defineProps({
  title: {
    type: String,
    default: ''
  },
  subtitle: {
    type: String,
    default: ''
  },
  icon: {
    type: String,
    default: ''
  },
  variant: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'primary', 'success', 'warning', 'danger'].includes(v)
  },
  clickable: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click'])
</script>

<template>
  <div
    :class="['space-card', `variant-${variant}`, { clickable }]"
    @click="clickable && $emit('click')"
  >
    <div v-if="icon" class="card-icon">{{ icon }}</div>
    <div class="card-content">
      <h3 v-if="title" class="card-title">{{ title }}</h3>
      <p v-if="subtitle" class="card-subtitle">{{ subtitle }}</p>
      <slot></slot>
    </div>
  </div>
</template>

<style scoped>
.space-card {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  border: 2px solid #334155;
  border-radius: 8px;
  padding: 16px;
  color: white;
  font-family: 'Segoe UI', sans-serif;
  transition: all 0.2s ease;
}

.space-card.clickable {
  cursor: pointer;
}

.space-card.clickable:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.3);
}

/* Variants */
.variant-default {
  border-color: #334155;
}

.variant-default:hover {
  border-color: #475569;
}

.variant-primary {
  border-color: #3b82f6;
}

.variant-primary:hover {
  border-color: #60a5fa;
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.3);
}

.variant-success {
  border-color: #10b981;
}

.variant-success:hover {
  border-color: #34d399;
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.3);
}

.variant-warning {
  border-color: #f59e0b;
}

.variant-warning:hover {
  border-color: #fbbf24;
  box-shadow: 0 8px 24px rgba(245, 158, 11, 0.3);
}

.variant-danger {
  border-color: #ef4444;
}

.variant-danger:hover {
  border-color: #f87171;
  box-shadow: 0 8px 24px rgba(239, 68, 68, 0.3);
}

.card-icon {
  font-size: 2.5em;
  margin-bottom: 12px;
  text-align: center;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-title {
  font-size: 1.1em;
  font-weight: 600;
  margin: 0;
  color: white;
}

.card-subtitle {
  font-size: 0.85em;
  color: rgba(255, 255, 255, 0.6);
  margin: 0;
}
</style>
