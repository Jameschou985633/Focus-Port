<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  to: { type: String, default: '/' },
  label: { type: String, default: '返回' }
})

const router = useRouter()

const goBack = () => {
  router.push(props.to)
}
</script>

<template>
  <button class="back-button" @click="goBack">
    <span class="icon">←</span>
    <span class="label">{{ label }}</span>
  </button>
</template>

<style scoped>
.back-button {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
  padding: var(--space-3) var(--space-5);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: inherit;
  font-size: var(--text-base);
  transition: all var(--duration-normal) var(--ease-out);
}

.back-button:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-border-hover);
  transform: translateX(-2px);
}

.back-button:active {
  transform: translateX(0);
}

.icon {
  font-size: var(--text-lg);
  transition: transform var(--duration-fast) var(--ease-out);
}

.back-button:hover .icon {
  transform: translateX(-3px);
}

.label {
  font-weight: var(--font-medium);
}
</style>
