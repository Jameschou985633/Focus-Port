<script setup>
import { computed } from 'vue'

const props = defineProps({
  dateLabel: {
    type: String,
    default: ''
  },
  tasks: {
    type: Array,
    default: () => []
  },
  selectedTaskId: {
    type: String,
    default: ''
  },
  draftTitle: {
    type: String,
    default: ''
  },
  isGenerating: {
    type: Boolean,
    default: false
  },
  generationError: {
    type: String,
    default: ''
  },
  formattedRemaining: {
    type: String,
    default: '25:00'
  },
  remainingSeconds: {
    type: Number,
    default: 1500
  },
  focusMinutes: {
    type: Number,
    default: 25
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
  focusActionDisabled: {
    type: Boolean,
    default: false
  },
  focusActionLabel: {
    type: String,
    default: 'Start Focus'
  }
})

const emit = defineEmits([
  'update:draftTitle',
  'create-task',
  'ai-decompose',
  'open-task',
  'back-to-today',
  'select-duration',
  'toggle-focus'
])

const onInput = (event) => {
  emit('update:draftTitle', String(event.target.value || ''))
}

const safeTotalSeconds = computed(() => {
  const total = Number(props.focusMinutes || props.selectedDuration || 25) * 60
  return Math.max(60, Number.isFinite(total) ? total : 1500)
})

const safeRemainingSeconds = computed(() => {
  const value = Number(props.remainingSeconds || 0)
  return Math.max(0, Number.isFinite(value) ? value : 0)
})

const ringRadius = 30
const ringCircumference = 2 * Math.PI * ringRadius

const ringOffset = computed(() => {
  const ratio = Math.min(1, Math.max(0, safeRemainingSeconds.value / safeTotalSeconds.value))
  return ringCircumference * (1 - ratio)
})
</script>

<template>
  <article class="rounded-2xl border border-sky-300/25 bg-[#0F1525]/85 p-5 shadow-[0_18px_40px_rgba(2,6,23,0.45)] backdrop-blur-xl">
    <section class="relative overflow-hidden rounded-2xl border border-indigo-300/35 bg-gradient-to-r from-[#5f33e1] to-[#4f2fca] p-4 text-white shadow-[0_12px_28px_rgba(63,33,138,0.38)]">
      <button
        type="button"
        class="absolute right-3 top-3 inline-flex items-center gap-1 rounded-md border border-white/35 bg-white/15 px-2 py-1 text-[11px] font-semibold transition hover:bg-white/25 disabled:opacity-60"
        :disabled="isGenerating"
        @click="$emit('ai-decompose')"
      >
        <span>AI</span>
        <span>{{ isGenerating ? '...' : '拆解' }}</span>
      </button>

      <div class="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-center">
        <div>
          <p class="text-xs uppercase tracking-[0.12em] text-white/75">Today Focus</p>
          <h2 class="mt-1 text-lg font-semibold">Your mission is almost done</h2>
          <button
            type="button"
            class="mt-3 inline-flex min-h-9 items-center rounded-lg bg-white/90 px-3 text-sm font-semibold text-[#4f2fca] transition hover:bg-white"
            @click="$emit('create-task')"
          >
            Add Task
          </button>
        </div>

        <div class="flex items-center gap-3 sm:flex-col sm:items-end">
          <div class="relative h-[76px] w-[76px]">
            <svg viewBox="0 0 76 76" class="h-full w-full -rotate-90">
              <circle cx="38" cy="38" :r="ringRadius" stroke="rgba(255,255,255,0.25)" stroke-width="6" fill="none" />
              <circle
                cx="38"
                cy="38"
                :r="ringRadius"
                stroke="white"
                stroke-width="6"
                fill="none"
                stroke-linecap="round"
                :stroke-dasharray="ringCircumference"
                :stroke-dashoffset="ringOffset"
              />
            </svg>
            <div class="absolute inset-0 grid place-items-center text-[12px] font-semibold tracking-wide">
              {{ formattedRemaining }}
            </div>
          </div>

          <button
            type="button"
            class="min-h-8 rounded-lg border border-white/35 bg-white/15 px-3 text-xs font-semibold text-white transition hover:bg-white/25 disabled:cursor-not-allowed disabled:opacity-55"
            :disabled="focusActionDisabled"
            @click="$emit('toggle-focus')"
          >
            {{ focusActionLabel }}
          </button>
        </div>
      </div>

      <div class="mt-3 flex flex-wrap items-center gap-2">
        <button
          v-for="m in durationOptions"
          :key="m"
          type="button"
          class="min-h-8 rounded-full border px-3 text-xs font-semibold transition"
          :class="selectedDuration === m
            ? 'border-white/80 bg-white/20 text-white'
            : 'border-white/35 text-white/85 hover:bg-white/15'"
          :disabled="durationLocked"
          @click="$emit('select-duration', m)"
        >
          {{ m }} min
        </button>
      </div>
    </section>

    <div class="mt-4 flex items-center justify-between gap-3">
      <div>
        <p class="text-[11px] uppercase tracking-[0.14em] text-sky-200/70">Today Tasks</p>
        <h3 class="mt-1 text-xl font-semibold text-slate-100">Master Tasks</h3>
      </div>
      <div class="flex items-center gap-2">
        <span class="rounded-full border border-slate-700/70 bg-slate-900/70 px-2 py-1 text-xs text-slate-300">{{ dateLabel }}</span>
        <button
          type="button"
          class="rounded-lg border border-slate-600/70 bg-slate-900/80 px-2 py-1 text-xs text-slate-200 transition hover:border-sky-300/45"
          @click="$emit('back-to-today')"
        >
          Today
        </button>
      </div>
    </div>

    <div class="mt-4 grid gap-2 sm:grid-cols-[1fr_auto]">
      <input
        :value="draftTitle"
        type="text"
        class="min-h-10 rounded-xl border border-sky-300/25 bg-slate-900/70 px-3 text-sm text-slate-100 outline-none transition focus:border-sky-300/55 focus:ring-2 focus:ring-sky-400/20"
        placeholder="Type a master task title"
        @input="onInput"
        @keydown.enter.prevent="$emit('create-task')"
      >
      <button
        type="button"
        class="min-h-10 rounded-xl border border-sky-300/45 bg-sky-500/15 px-4 text-sm font-semibold text-sky-100 transition hover:bg-sky-500/25"
        @click="$emit('create-task')"
      >
        Create Task
      </button>
    </div>

    <p v-if="generationError" class="mt-3 text-sm text-rose-300">{{ generationError }}</p>

    <div v-if="tasks.length" class="mt-4 space-y-2">
      <button
        v-for="task in tasks"
        :key="task.id"
        type="button"
        class="w-full rounded-xl border p-3 text-left transition hover:-translate-y-0.5"
        :class="selectedTaskId === task.id
          ? 'border-sky-300/60 bg-sky-500/10 shadow-[0_0_18px_rgba(14,165,233,0.2)]'
          : 'border-slate-700/70 bg-slate-900/50 hover:border-sky-300/35'"
        @click="$emit('open-task', task.id)"
      >
        <div class="flex items-center justify-between gap-2">
          <p class="truncate text-sm font-semibold text-slate-100">{{ task.title }}</p>
          <span
            class="rounded-full border px-2 py-0.5 text-[11px]"
            :class="task.status === 'in_progress'
              ? 'border-amber-300/40 bg-amber-500/10 text-amber-200'
              : task.status === 'completed'
                ? 'border-emerald-300/40 bg-emerald-500/10 text-emerald-200'
                : task.status === 'empty'
                  ? 'border-slate-600/60 bg-slate-700/30 text-slate-300'
                  : 'border-sky-300/40 bg-sky-500/10 text-sky-100'"
          >
            {{ task.status === 'in_progress' ? 'Running' : task.status === 'completed' ? 'Done' : task.status === 'empty' ? 'Empty' : 'Pending' }}
          </span>
        </div>

        <div class="mt-2 h-2 w-full rounded-full bg-slate-800/80">
          <div class="h-2 rounded-full bg-gradient-to-r from-blue-500 to-sky-400" :style="{ width: `${task.progress}%` }" />
        </div>

        <p class="mt-2 text-xs text-slate-400">{{ task.completedCount }}/{{ task.totalCount }} phases complete</p>
        <p class="mt-1 truncate text-xs text-slate-300">{{ task.nextPhaseTitle || 'No phase yet, click to manage' }}</p>
      </button>
    </div>

    <div
      v-else
      class="mt-4 rounded-xl border border-slate-700/70 bg-slate-900/50 p-4 text-sm text-slate-400"
    >
      No matched task under this date yet. Create a task first, then use AI to generate executable phases.
    </div>
  </article>
</template>

