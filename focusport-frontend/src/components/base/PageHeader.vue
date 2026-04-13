<script setup>
import BackButton from './BackButton.vue'

defineProps({
  title: { type: String, required: true },
  icon: { type: String, default: '' },
  backTo: { type: String, default: '/' },
  backLabel: { type: String, default: '返回' }
})
</script>

<template>
  <header class="page-header glass">
    <BackButton :to="backTo" :label="backLabel" />
    <h1 class="page-title">
      <span v-if="icon" class="title-icon">{{ icon }}</span>
      {{ title }}
    </h1>
    <div class="header-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  border-radius: 0 0 var(--radius-2xl) var(--radius-2xl);
  margin-bottom: var(--space-4);
}

.page-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.title-icon {
  font-size: var(--text-2xl);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 80px;
  justify-content: flex-end;
}

/* Responsive */
@media (max-width: 767px) {
  .page-header {
    padding: var(--space-3) var(--space-4);
  }

  .page-title {
    font-size: var(--text-lg);
  }

  .header-actions {
    min-width: 60px;
  }
}
</style>
