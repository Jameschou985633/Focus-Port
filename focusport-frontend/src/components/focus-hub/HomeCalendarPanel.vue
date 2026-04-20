<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  selectedDate: {
    type: String,
    default: ''
  },
  dayStats: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['select-date'])

const weekdayLabels = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']

const toDateKey = (date) => {
  const d = new Date(date)
  if (Number.isNaN(d.getTime())) return ''
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const buildTodayKey = () => toDateKey(new Date())

const monthCursor = ref(new Date())

watch(
  () => props.selectedDate,
  (value) => {
    if (!value) return
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return
    if (
      d.getFullYear() !== monthCursor.value.getFullYear() ||
      d.getMonth() !== monthCursor.value.getMonth()
    ) {
      monthCursor.value = new Date(d.getFullYear(), d.getMonth(), 1)
    }
  },
  { immediate: true }
)

const monthTitle = computed(() => {
  const year = monthCursor.value.getFullYear()
  const month = monthCursor.value.getMonth() + 1
  return `${year}-${String(month).padStart(2, '0')}`
})

const dayCells = computed(() => {
  const y = monthCursor.value.getFullYear()
  const m = monthCursor.value.getMonth()
  const firstDay = new Date(y, m, 1)
  const mondayIndex = (firstDay.getDay() + 6) % 7
  const gridStart = new Date(y, m, 1 - mondayIndex)
  const todayKey = buildTodayKey()

  return Array.from({ length: 42 }, (_, index) => {
    const current = new Date(gridStart)
    current.setDate(gridStart.getDate() + index)
    const dateKey = toDateKey(current)
    const stats = props.dayStats[dateKey] || { created: 0, completed: 0 }
    return {
      dateKey,
      day: current.getDate(),
      inMonth: current.getMonth() === m,
      isToday: dateKey === todayKey,
      isSelected: dateKey === props.selectedDate,
      created: Number(stats.created || 0),
      completed: Number(stats.completed || 0)
    }
  })
})

const shiftMonth = (delta) => {
  const next = new Date(monthCursor.value)
  next.setMonth(monthCursor.value.getMonth() + delta)
  monthCursor.value = new Date(next.getFullYear(), next.getMonth(), 1)
}

const pickDate = (dateKey) => {
  emit('select-date', dateKey)
}

const selectToday = () => {
  const today = buildTodayKey()
  emit('select-date', today)
}
</script>

<template>
  <section class="rounded-2xl border border-sky-300/25 bg-[#0F1525]/85 p-5 shadow-[0_18px_40px_rgba(2,6,23,0.45)] backdrop-blur-xl">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <p class="text-[11px] uppercase tracking-[0.14em] text-sky-200/70">Calendar</p>
        <h2 class="mt-1 text-xl font-semibold text-slate-100">Month View</h2>
      </div>

      <div class="flex items-center gap-2">
        <button
          type="button"
          class="grid h-9 w-9 place-items-center rounded-lg border border-slate-700 bg-slate-900/70 text-slate-200 transition hover:border-sky-300/45"
          @click="shiftMonth(-1)"
        >
          &lt;
        </button>
        <span class="min-w-24 text-center text-sm font-semibold text-slate-100">{{ monthTitle }}</span>
        <button
          type="button"
          class="grid h-9 w-9 place-items-center rounded-lg border border-slate-700 bg-slate-900/70 text-slate-200 transition hover:border-sky-300/45"
          @click="shiftMonth(1)"
        >
          &gt;
        </button>
        <button
          type="button"
          class="rounded-lg border border-sky-300/35 bg-sky-500/10 px-3 py-1.5 text-xs text-sky-100 transition hover:bg-sky-500/20"
          @click="selectToday"
        >
          Today
        </button>
      </div>
    </header>

    <div class="mt-4 grid grid-cols-7 gap-1">
      <div
        v-for="label in weekdayLabels"
        :key="label"
        class="rounded-md bg-slate-900/70 px-2 py-1 text-center text-xs font-semibold text-slate-300"
      >
        {{ label }}
      </div>
    </div>

    <div class="mt-1 grid grid-cols-7 gap-1">
      <button
        v-for="cell in dayCells"
        :key="cell.dateKey"
        type="button"
        class="min-h-[5.2rem] rounded-lg border p-1.5 text-left transition"
        :class="cell.isSelected
          ? 'border-sky-300/65 bg-sky-500/15'
          : cell.inMonth
            ? 'border-slate-700/65 bg-slate-900/45 hover:border-sky-300/45'
            : 'border-slate-800/55 bg-slate-950/40 text-slate-500'"
        @click="pickDate(cell.dateKey)"
      >
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold" :class="cell.isToday ? 'text-sky-200' : 'text-slate-300'">
            {{ cell.day }}
          </span>
          <span
            v-if="cell.isToday"
            class="rounded-full border border-sky-300/40 bg-sky-500/15 px-1.5 text-[10px] text-sky-100"
          >
            now
          </span>
        </div>

        <div class="mt-1 space-y-1">
          <p v-if="cell.created" class="rounded bg-blue-500/15 px-1.5 py-0.5 text-[10px] text-blue-200">
            +{{ cell.created }} created
          </p>
          <p v-if="cell.completed" class="rounded bg-emerald-500/15 px-1.5 py-0.5 text-[10px] text-emerald-200">
            +{{ cell.completed }} done
          </p>
        </div>
      </button>
    </div>
  </section>
</template>
