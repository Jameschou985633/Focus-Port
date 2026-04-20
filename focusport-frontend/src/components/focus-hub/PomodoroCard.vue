<script setup>
defineProps({
  formattedRemaining: {
    type: String,
    default: '25:00'
  },
  isRunning: {
    type: Boolean,
    default: false
  },
  durationOptions: {
    type: Array,
    default: () => [15, 25, 45]
  },
  selectedDuration: {
    type: Number,
    default: 25
  },
  durationLocked: {
    type: Boolean,
    default: false
  },
  startDisabled: {
    type: Boolean,
    default: false
  },
  startLabel: {
    type: String,
    default: 'Start Focus'
  },
  currentGoal: {
    type: String,
    default: 'System Standby'
  },
  nextAction: {
    type: String,
    default: 'No executable phase in current task.'
  },
  linkedTaskTitle: {
    type: String,
    default: ''
  }
})

defineEmits(['select-duration', 'start-focus'])
</script>

<template>
  <article class="rounded-2xl border border-sky-300/25 bg-[#0F1525]/85 p-5 shadow-[0_18px_40px_rgba(2,6,23,0.45)] backdrop-blur-xl">
    <div class="flex items-center justify-between gap-3">
      <div>
        <p class="text-[11px] uppercase tracking-[0.14em] text-sky-200/70">Pomodoro</p>
        <h2 class="mt-1 text-xl font-semibold text-slate-100">Focus Timer</h2>
      </div>
      <span
        class="rounded-full border px-2 py-1 text-xs"
        :class="isRunning
          ? 'border-rose-300/40 bg-rose-500/10 text-rose-200'
          : 'border-sky-300/35 bg-sky-500/10 text-sky-100'"
      >
        {{ isRunning ? 'In Focus' : 'Ready' }}
      </span>
    </div>

    <p class="mt-4 font-mono text-[3rem] leading-none tracking-widest text-sky-300">{{ formattedRemaining }}</p>

    <p class="mt-3 text-xs uppercase tracking-[0.12em] text-sky-200/70">Current Goal</p>
    <p class="mt-1 truncate text-sm font-semibold text-slate-100">{{ currentGoal }}</p>

    <p class="mt-3 text-xs uppercase tracking-[0.12em] text-sky-200/70">Next Action</p>
    <p class="mt-1 text-sm text-slate-200">{{ nextAction }}</p>

    <div class="mt-4 flex items-center gap-2">
      <button
        v-for="m in durationOptions"
        :key="m"
        type="button"
        class="min-h-10 min-w-[3.2rem] rounded-full border px-3 text-sm font-semibold transition"
        :class="selectedDuration === m
          ? 'border-sky-300/70 bg-sky-500/15 text-sky-100 shadow-[0_0_14px_rgba(14,165,233,0.25)]'
          : 'border-slate-700 text-slate-300 hover:border-sky-300/45 hover:text-white'"
        :disabled="durationLocked"
        @click="$emit('select-duration', m)"
      >
        {{ m }}
      </button>
    </div>

    <button
      type="button"
      class="mt-5 min-h-12 w-full rounded-xl bg-gradient-to-r from-blue-600 to-sky-500 text-base font-bold text-white transition hover:-translate-y-0.5 hover:shadow-[0_14px_24px_rgba(37,99,235,0.35)] disabled:cursor-not-allowed disabled:opacity-55 disabled:hover:translate-y-0"
      :disabled="startDisabled"
      @click="$emit('start-focus')"
    >
      {{ startLabel }}
    </button>

    <p class="mt-3 text-xs text-slate-400">
      {{ linkedTaskTitle || 'No linked phase' }}
    </p>
  </article>
</template>

