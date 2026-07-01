<script setup>
import { computed } from 'vue'

const props = defineProps({
  steps: {
    type: Array,
    default: () => []
  }
})

const normalizedSteps = computed(() => {
  const fallback = [
    { label: 'Current', title: 'Prepare to focus' },
    { label: 'Next', title: 'Push the core task' },
    { label: 'Optional', title: 'Run a short review' }
  ]

  const incoming = props.steps.slice(0, 3)
  if (!incoming.length) return fallback
  while (incoming.length < 3) incoming.push(fallback[incoming.length])
  return incoming
})
</script>

<template>
  <section class="rounded-2xl border border-sky-300/20 bg-slate-950/45 p-4 backdrop-blur-md">
    <p class="text-lg font-semibold text-slate-200">Timeline</p>

    <ol class="mt-4 grid gap-2">
      <li
        v-for="(step, index) in normalizedSteps"
        :key="`${step.title}-${index}`"
        class="rounded-xl border p-3 transition duration-200 ease-out"
        :class="index === 0
          ? 'border-sky-300/45 bg-sky-500/12'
          : index === 1
            ? 'border-sky-300/25 bg-slate-900/60'
            : 'border-sky-300/20 bg-slate-900/45 opacity-75'"
      >
        <span class="inline-flex min-h-6 items-center rounded-full bg-sky-500/20 px-2 text-xs font-medium text-sky-200">{{ step.label }}</span>
        <p class="mt-2 text-sm font-medium text-slate-100">{{ step.title }}</p>
      </li>
    </ol>
  </section>
</template>
