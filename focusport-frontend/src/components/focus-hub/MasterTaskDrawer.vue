<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

const props = defineProps({
  open: {
    type: Boolean,
    default: false
  },
  masterTask: {
    type: Object,
    default: null
  },
  phases: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits([
  'close',
  'add-phase',
  'update-phase',
  'remove-phase',
  'move-phase',
  'start-phase'
])

const newPhaseTitle = ref('')

const sortedPhases = computed(() => {
  return [...props.phases].sort((left, right) => {
    if (left.phaseOrder !== right.phaseOrder) return left.phaseOrder - right.phaseOrder
    if (left.priority !== right.priority) return left.priority - right.priority
    return String(left.createdAt || '').localeCompare(String(right.createdAt || ''))
  })
})

const phaseLabel = (phase, index) => {
  if (phase.status === 'deployed') return 'Current'
  if (phase.status === 'completed') return 'Done'
  if (index === 0) return 'Next'
  return 'Optional'
}

const statusClass = (status) => {
  if (status === 'deployed') return 'border-amber-300/40 bg-amber-500/10 text-amber-100'
  if (status === 'completed') return 'border-emerald-300/40 bg-emerald-500/10 text-emerald-100'
  return 'border-sky-300/35 bg-slate-900/60 text-sky-100'
}

const submitPhase = () => {
  const title = String(newPhaseTitle.value || '').trim()
  if (!title) return
  emit('add-phase', { title })
  newPhaseTitle.value = ''
}

const updateTitle = (phaseId, event) => {
  emit('update-phase', {
    id: phaseId,
    title: String(event.target.value || '').trim()
  })
}

const handleEscape = (event) => {
  if (event.key === 'Escape' && props.open) {
    emit('close')
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleEscape)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleEscape)
})
</script>

<template>
  <transition
    enter-active-class="transition duration-220 ease-out"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition duration-180 ease-out"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="open"
      class="fixed inset-0 z-[150] flex justify-end bg-slate-950/65 backdrop-blur-sm"
      @click.self="$emit('close')"
    >
      <transition
        enter-active-class="transition duration-220 ease-out"
        enter-from-class="translate-x-6 opacity-0"
        enter-to-class="translate-x-0 opacity-100"
        leave-active-class="transition duration-180 ease-out"
        leave-from-class="translate-x-0 opacity-100"
        leave-to-class="translate-x-6 opacity-0"
      >
        <aside
          v-if="open"
          class="h-full w-full max-w-xl border-l border-sky-300/30 bg-[#0F1525]/95 p-4 shadow-[-18px_0_36px_rgba(2,6,23,0.45)] backdrop-blur-xl md:p-5"
        >
          <header class="flex items-start justify-between gap-3 rounded-2xl border border-sky-300/25 bg-slate-900/65 p-3">
            <div>
              <p class="text-[11px] uppercase tracking-[0.14em] text-sky-200/70">Master Task</p>
              <h3 class="mt-1 text-xl font-semibold text-slate-100">{{ masterTask?.title || 'No master task selected' }}</h3>
            </div>
            <button
              type="button"
              class="grid h-9 w-9 place-items-center rounded-xl border border-sky-300/30 bg-slate-800/80 text-slate-200 transition hover:bg-sky-500/20"
              @click="$emit('close')"
            >
              x
            </button>
          </header>

          <section class="mt-3 rounded-2xl border border-sky-300/20 bg-slate-950/60 p-3">
            <p class="text-xs uppercase tracking-[0.12em] text-slate-400">Add Phase</p>
            <div class="mt-2 flex gap-2">
              <input
                v-model="newPhaseTitle"
                type="text"
                class="min-h-10 flex-1 rounded-xl border border-sky-300/25 bg-slate-900/70 px-3 text-sm text-slate-100 outline-none transition focus:border-sky-300/55 focus:ring-2 focus:ring-sky-400/20"
                placeholder="Type a phase action"
                @keydown.enter.prevent="submitPhase"
              >
              <button
                type="button"
                class="min-h-10 rounded-xl border border-sky-300/45 bg-sky-500/15 px-4 text-sm font-semibold text-sky-100 transition hover:bg-sky-500/25"
                @click="submitPhase"
              >
                Add
              </button>
            </div>
          </section>

          <section class="mt-3 max-h-[calc(100vh-220px)] space-y-2 overflow-y-auto pr-1">
            <article
              v-for="(phase, index) in sortedPhases"
              :key="phase.id"
              class="rounded-2xl border p-3"
              :class="statusClass(phase.status)"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="rounded-full border border-current/40 px-2 py-0.5 text-[11px] uppercase tracking-wide">{{ phaseLabel(phase, index) }}</span>
                <span class="text-xs opacity-80">{{ phase.estimatedPomodoros }} pomodoro</span>
              </div>

              <input
                :value="phase.title"
                type="text"
                class="mt-2 w-full rounded-lg border border-transparent bg-transparent px-2 py-1 text-sm font-medium text-slate-100 outline-none transition focus:border-sky-300/45 focus:bg-slate-900/40"
                @change="updateTitle(phase.id, $event)"
              >

              <div class="mt-3 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  class="rounded-lg border border-slate-500/40 px-2.5 py-1 text-xs text-slate-200 transition hover:border-slate-300/60"
                  :disabled="index === 0"
                  @click="$emit('move-phase', { id: phase.id, direction: 'up' })"
                >
                  Up
                </button>
                <button
                  type="button"
                  class="rounded-lg border border-slate-500/40 px-2.5 py-1 text-xs text-slate-200 transition hover:border-slate-300/60"
                  :disabled="index === sortedPhases.length - 1"
                  @click="$emit('move-phase', { id: phase.id, direction: 'down' })"
                >
                  Down
                </button>
                <button
                  type="button"
                  class="rounded-lg border border-emerald-300/45 bg-emerald-500/15 px-2.5 py-1 text-xs font-semibold text-emerald-100 transition hover:bg-emerald-500/25 disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="phase.status === 'completed'"
                  @click="$emit('start-phase', phase.id)"
                >
                  Start
                </button>
                <button
                  type="button"
                  class="rounded-lg border border-rose-300/45 bg-rose-500/15 px-2.5 py-1 text-xs text-rose-100 transition hover:bg-rose-500/25"
                  @click="$emit('remove-phase', phase.id)"
                >
                  Delete
                </button>
              </div>
            </article>

            <div
              v-if="!sortedPhases.length"
              class="rounded-2xl border border-slate-700/60 bg-slate-900/50 p-4 text-sm text-slate-400"
            >
              No phases yet. Add the first action.
            </div>
          </section>
        </aside>
      </transition>
    </div>
  </transition>
</template>
