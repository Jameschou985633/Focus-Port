<script setup>
defineProps({
  currentGoal: {
    type: String,
    default: 'No Active Goal'
  },
  selectedDuration: {
    type: Number,
    default: 25
  },
  durationOptions: {
    type: Array,
    default: () => [15, 25, 45]
  },
  aiState: {
    type: Object,
    default: () => ({
      status: 'fallback',
      text: '[System Standby] No active process',
      hint: 'Fallback · 25 min'
    })
  },
  isHydrating: {
    type: Boolean,
    default: false
  },
  showStandbyAction: {
    type: Boolean,
    default: false
  },
  durationLocked: {
    type: Boolean,
    default: false
  },
  startDisabled: {
    type: Boolean,
    default: false
  }
})

defineEmits(['start-focus', 'select-duration', 'call-ai'])
</script>

<template>
  <section class="rounded-[1.7rem] border border-sky-300/30 bg-slate-950/60 p-5 shadow-[0_24px_50px_rgba(2,6,23,0.5)] backdrop-blur-xl md:p-7">
    <p class="text-xs uppercase tracking-[0.15em] text-sky-200/80">Current Goal</p>
    <h2 class="mt-2 text-[clamp(1.9rem,4.2vw,3.1rem)] font-semibold leading-[1.15] tracking-tight text-slate-50">
      {{ currentGoal }}
    </h2>

    <transition
      mode="out-in"
      enter-active-class="transition duration-220 ease-out"
      enter-from-class="translate-y-1 opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition duration-150 ease-out"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="isHydrating" key="skeleton" class="mt-5 rounded-3xl border border-sky-300/25 bg-slate-900/70 p-4">
        <div class="animate-pulse space-y-3">
          <div class="flex items-center justify-between">
            <div class="h-4 w-24 rounded bg-slate-700/70" />
            <div class="h-4 w-28 rounded bg-slate-700/60" />
          </div>
          <div class="h-8 w-full rounded bg-slate-700/60" />
          <div class="h-8 w-5/6 rounded bg-slate-700/50" />
          <div class="h-4 w-36 rounded bg-slate-700/60" />
        </div>
      </div>

      <article
        v-else
        key="content"
        class="mt-5 rounded-3xl border border-sky-300/35 bg-gradient-to-br from-slate-900/85 to-blue-950/70 p-4 shadow-[0_0_0_1px_rgba(125,211,252,0.12)_inset,0_0_28px_rgba(14,165,233,0.14)] transition duration-200 ease-out hover:border-sky-200/55 hover:shadow-[0_0_0_1px_rgba(125,211,252,0.18)_inset,0_0_34px_rgba(14,165,233,0.24)]"
      >
        <div class="flex items-start justify-between gap-4">
          <p class="text-sm font-semibold text-sky-100">Next Action</p>
          <span class="text-[11px] uppercase tracking-[0.1em] text-sky-200/75">Protocol Forge</span>
        </div>
        <p class="mt-3 text-[clamp(1.15rem,2.5vw,1.95rem)] leading-relaxed text-slate-100">{{ aiState.text }}</p>
        <p class="mt-3 text-sm text-sky-200/80">{{ aiState.hint }}</p>
      </article>
    </transition>

    <button
      v-if="showStandbyAction && !isHydrating"
      type="button"
      class="mt-4 inline-flex min-h-9 items-center rounded-full border border-sky-300/45 bg-sky-500/15 px-4 text-sm font-medium text-sky-100 transition duration-200 ease-out hover:-translate-y-0.5 hover:bg-sky-500/25"
      @click="$emit('call-ai')"
    >
      Call AI Planner
    </button>

    <div class="mt-4 flex items-center gap-2" role="radiogroup" aria-label="Focus duration">
      <button
        v-for="minutes in durationOptions"
        :key="minutes"
        type="button"
        class="min-h-10 min-w-[3.3rem] rounded-full border px-3 text-sm font-semibold transition duration-200 ease-out"
        :class="selectedDuration === minutes
          ? 'border-sky-300/70 bg-gradient-to-r from-blue-600 to-sky-500 text-white shadow-[0_0_18px_rgba(56,189,248,0.35)]'
          : 'border-sky-300/30 bg-slate-900/70 text-slate-300 hover:border-sky-200/55 hover:text-slate-100'"
        :disabled="durationLocked"
        @click="$emit('select-duration', minutes)"
      >
        {{ minutes }}
      </button>
    </div>

    <button
      type="button"
      class="mt-5 inline-flex min-h-14 w-full max-w-xl items-center justify-center rounded-2xl bg-gradient-to-r from-blue-600 to-sky-500 px-6 text-xl font-bold text-white transition duration-200 ease-out hover:-translate-y-0.5 hover:shadow-[0_16px_28px_rgba(37,99,235,0.35)] active:translate-y-0 active:scale-[0.995] disabled:cursor-not-allowed disabled:opacity-55 disabled:hover:translate-y-0"
      :disabled="startDisabled"
      @click="$emit('start-focus')"
    >
      Start Focus
    </button>
  </section>
</template>
