<script setup>
import { Teleport, Transition } from 'vue'

defineProps({
  visible: { type: Boolean, default: false },
  message: { type: String, default: '' },
  spinnerColor: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'accent', 'gold'].includes(v)
  },
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md', 'lg'].includes(v)
  },
  fullscreen: { type: Boolean, default: true }
})
</script>

<template>
  <Teleport to="body" :disabled="!fullscreen">
    <Transition name="fade">
      <div
        v-if="visible"
        :class="['loading-overlay', { 'is-fullscreen': fullscreen }]"
      >
        <div class="loading-content">
          <div :class="['spinner', `spinner-${size}`, `spinner-${spinnerColor}`]" />
          <p v-if="message" class="loading-message">{{ message }}</p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.loading-overlay {
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
}

.loading-overlay.is-fullscreen {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(var(--blur-sm));
  -webkit-backdrop-filter: blur(var(--blur-sm));
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
}

.spinner {
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.spinner-sm {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-surface);
}

.spinner-md {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-surface);
}

.spinner-lg {
  width: 56px;
  height: 56px;
  border: 4px solid var(--color-surface);
}

.spinner-primary {
  border-top-color: var(--color-primary-400);
}

.spinner-accent {
  border-top-color: var(--color-accent-400);
}

.spinner-gold {
  border-top-color: var(--color-gold-400);
}

.loading-message {
  color: var(--color-text-secondary);
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  text-align: center;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Fade transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--duration-normal) var(--ease-out);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
