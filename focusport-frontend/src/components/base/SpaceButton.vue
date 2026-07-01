<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'secondary', 'success', 'danger', 'warning'].includes(v)
  },
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md', 'lg'].includes(v)
  },
  disabled: {
    type: Boolean,
    default: false
  },
  glow: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click'])

const buttonClass = computed(() => [
  'space-button',
  `variant-${props.variant}`,
  `size-${props.size}`,
  { disabled: props.disabled, glow: props.glow }
])
</script>

<template>
  <button
    :class="buttonClass"
    :disabled="disabled"
    @click="!disabled && $emit('click')"
  >
    <slot></slot>
  </button>
</template>

<style scoped>
.space-button {
  background: linear-gradient(145deg, #1a2b3c 0%, #0a1824 100%);
  border: 2px solid #3b82f6;
  color: white;
  font-family: 'Segoe UI', sans-serif;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  position: relative;
  overflow: hidden;
}

.space-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
  transition: left 0.5s;
}

.space-button:hover:not(.disabled)::before {
  left: 100%;
}

.space-button:hover:not(.disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.space-button:active:not(.disabled) {
  transform: translateY(0);
}

/* Variants */
.variant-primary {
  background: linear-gradient(145deg, #1e3a5f 0%, #0f2744 100%);
  border-color: #3b82f6;
}

.variant-primary:hover:not(.disabled) {
  border-color: #60a5fa;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.5);
}

.variant-secondary {
  background: linear-gradient(145deg, #1f2937 0%, #111827 100%);
  border-color: #6b7280;
}

.variant-secondary:hover:not(.disabled) {
  border-color: #9ca3af;
  box-shadow: 0 4px 12px rgba(107, 114, 128, 0.4);
}

.variant-success {
  background: linear-gradient(145deg, #064e3b 0%, #022c22 100%);
  border-color: #10b981;
}

.variant-success:hover:not(.disabled) {
  border-color: #34d399;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.5);
}

.variant-danger {
  background: linear-gradient(145deg, #7f1d1d 0%, #450a0a 100%);
  border-color: #ef4444;
}

.variant-danger:hover:not(.disabled) {
  border-color: #f87171;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.5);
}

.variant-warning {
  background: linear-gradient(145deg, #78350f 0%, #451a03 100%);
  border-color: #f59e0b;
}

.variant-warning:hover:not(.disabled) {
  border-color: #fbbf24;
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.5);
}

/* Sizes */
.size-sm {
  padding: 6px 12px;
  font-size: 12px;
  border-radius: 4px;
}

.size-md {
  padding: 10px 20px;
  font-size: 14px;
  border-radius: 6px;
}

.size-lg {
  padding: 14px 28px;
  font-size: 16px;
  border-radius: 8px;
}

/* States */
.space-button.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.space-button.glow {
  animation: glow-pulse 2s infinite;
}

@keyframes glow-pulse {
  0%, 100% {
    box-shadow: 0 0 5px rgba(59, 130, 246, 0.5);
  }
  50% {
    box-shadow: 0 0 20px rgba(59, 130, 246, 0.8);
  }
}
</style>
