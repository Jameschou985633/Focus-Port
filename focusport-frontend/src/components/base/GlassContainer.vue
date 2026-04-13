<script setup>
defineProps({
  variant: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'light', 'strong', 'dark'].includes(v)
  },
  interactive: { type: Boolean, default: false },
  glow: { type: Boolean, default: false },
  padding: {
    type: String,
    default: 'md',
    validator: (v) => ['none', 'sm', 'md', 'lg'].includes(v)
  },
  radius: {
    type: String,
    default: 'xl',
    validator: (v) => ['sm', 'md', 'lg', 'xl', '2xl', 'full'].includes(v)
  },
  tag: { type: String, default: 'div' }
})
</script>

<template>
  <component
    :is="tag"
    :class="[
      'glass-container',
      variant,
      { interactive, glow },
      `padding-${padding}`,
      `radius-${radius}`
    ]"
  >
    <slot />
  </component>
</template>

<style scoped>
.glass-container {
  border: 1px solid var(--color-border);
  transition: all var(--duration-normal) var(--ease-out);
}

/* Variants */
.default {
  background: var(--color-surface);
  backdrop-filter: blur(var(--blur-md));
  -webkit-backdrop-filter: blur(var(--blur-md));
}

.light {
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(var(--blur-sm));
  -webkit-backdrop-filter: blur(var(--blur-sm));
  border-color: rgba(255, 255, 255, 0.1);
}

.strong {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(var(--blur-lg));
  -webkit-backdrop-filter: blur(var(--blur-lg));
  border-color: rgba(255, 255, 255, 0.25);
}

.dark {
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(var(--blur-lg));
  -webkit-backdrop-filter: blur(var(--blur-lg));
  border-color: rgba(255, 255, 255, 0.1);
}

/* Padding */
.padding-none { padding: 0; }
.padding-sm { padding: var(--space-3); }
.padding-md { padding: var(--space-5); }
.padding-lg { padding: var(--space-6); }

/* Border Radius */
.radius-sm { border-radius: var(--radius-sm); }
.radius-md { border-radius: var(--radius-md); }
.radius-lg { border-radius: var(--radius-lg); }
.radius-xl { border-radius: var(--radius-xl); }
.radius-2xl { border-radius: var(--radius-2xl); }
.radius-full { border-radius: var(--radius-full); }

/* Interactive */
.interactive {
  cursor: pointer;
}

.interactive:hover {
  background: var(--color-surface-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

/* Glow */
.glow:hover {
  box-shadow: var(--shadow-glow-primary);
}
</style>
