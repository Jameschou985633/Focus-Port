import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { differenceInCalendarDays, format, isValid, parseISO } from 'date-fns'
import { focusApi } from '../api'

const STORAGE_PREFIX = 'fc.focusHub'

const currentUsername = () => {
  if (typeof window === 'undefined') return 'guest'
  return window.localStorage.getItem('username') || 'guest'
}

const todayKey = (date = new Date()) => format(date, 'yyyy-MM-dd')

const storageKey = (username = currentUsername()) => `${STORAGE_PREFIX}.${username || 'guest'}`

const createDefaultPomodoro = () => ({
  mode: 'focus',
  focusMinutes: 25,
  breakMinutes: 5,
  remainingSeconds: 25 * 60,
  isRunning: false,
  startedAt: '',
  endsAt: '',
  completedFocusSessions: 0,
  taskDifficulty: 'L1',
  linkedTaskId: '',
  linkedTaskTitle: '',
  pendingSettlement: false
})

const safeParse = (raw) => {
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch (error) {
    console.warn('Failed to parse focus hub storage', error)
    return null
  }
}

const generateId = (prefix = 'hub') => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}-${crypto.randomUUID()}`
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

const normalizePomodoro = (value = {}) => {
  const focusMinutes = Number(value.focusMinutes) > 0 ? Number(value.focusMinutes) : 25
  const breakMinutes = Number(value.breakMinutes) > 0 ? Number(value.breakMinutes) : 5
  const mode = value.mode === 'break' ? 'break' : 'focus'
  const defaultRemaining = mode === 'break' ? breakMinutes * 60 : focusMinutes * 60
  const remainingSeconds = Number(value.remainingSeconds)

  return {
    mode,
    focusMinutes,
    breakMinutes,
    remainingSeconds: Number.isFinite(remainingSeconds) && remainingSeconds >= 0
      ? Math.round(remainingSeconds)
      : defaultRemaining,
    isRunning: Boolean(value.isRunning),
    startedAt: String(value.startedAt || ''),
    endsAt: String(value.endsAt || ''),
    completedFocusSessions: Number.isFinite(Number(value.completedFocusSessions))
      ? Math.max(0, Math.round(Number(value.completedFocusSessions)))
      : 0,
    taskDifficulty: value.taskDifficulty === 'L2' ? 'L2' : 'L1',
    linkedTaskId: String(value.linkedTaskId || ''),
    linkedTaskTitle: String(value.linkedTaskTitle || ''),
    pendingSettlement: Boolean(value.pendingSettlement)
  }
}

const normalizeTask = (value = {}) => ({
  id: String(value.id || generateId('task')),
  title: String(value.title || '').trim(),
  completed: Boolean(value.completed),
  createdAt: String(value.createdAt || new Date().toISOString()),
  completedAt: value.completed ? String(value.completedAt || '') : '',
  isDeferred: Boolean(value.isDeferred),
  deferredFrom: String(value.deferredFrom || ''),
  deferredCount: Number.isFinite(Number(value.deferredCount))
    ? Math.max(0, Math.round(Number(value.deferredCount)))
    : 0
})

const normalizeArchiveTask = (value = {}) => ({
  id: String(value.id || generateId('archive')),
  title: String(value.title || '').trim(),
  completedAt: String(value.completedAt || ''),
  archivedOn: String(value.archivedOn || todayKey()),
  originalCreatedAt: String(value.originalCreatedAt || '')
})

const normalizeWeekNode = (value = {}) => ({
  date: String(value.date || ''),
  notes: Array.isArray(value.notes)
    ? value.notes.map((note) => String(note || '')).slice(0, 2)
    : []
})

const normalizeCountdown = (value = {}) => ({
  id: String(value.id || generateId('countdown')),
  title: String(value.title || '').trim(),
  targetDate: String(value.targetDate || ''),
  createdAt: String(value.createdAt || new Date().toISOString())
})

const normalizeState = (value = {}) => ({
  lastAccessDate: String(value.lastAccessDate || ''),
  pomodoro: normalizePomodoro(value.pomodoro),
  todayTasks: Array.isArray(value.todayTasks)
    ? value.todayTasks.map(normalizeTask).filter((task) => task.title)
    : [],
  archiveTasks: Array.isArray(value.archiveTasks)
    ? value.archiveTasks.map(normalizeArchiveTask).filter((task) => task.title)
    : [],
  weekNodes: Array.isArray(value.weekNodes)
    ? value.weekNodes.map(normalizeWeekNode).filter((entry) => entry.date)
    : [],
  countdowns: Array.isArray(value.countdowns)
    ? value.countdowns.map(normalizeCountdown).filter((item) => item.title && item.targetDate)
    : []
})

export const useFocusHubStore = defineStore('focusHub', () => {
  const hydratedUsername = ref('')
  const isHydrating = ref(false)

  const lastAccessDate = ref('')
  const pomodoro = ref(createDefaultPomodoro())
  const todayTasks = ref([])
  const archiveTasks = ref([])
  const weekNodes = ref([])
  const countdowns = ref([])

  let tickHandle = null

  const persist = () => {
    if (typeof window === 'undefined' || !hydratedUsername.value || isHydrating.value) return

    window.localStorage.setItem(storageKey(hydratedUsername.value), JSON.stringify({
      lastAccessDate: lastAccessDate.value,
      pomodoro: pomodoro.value,
      todayTasks: todayTasks.value,
      archiveTasks: archiveTasks.value,
      weekNodes: weekNodes.value,
      countdowns: countdowns.value
    }))
  }

  const stopTicker = () => {
    if (tickHandle) {
      window.clearInterval(tickHandle)
      tickHandle = null
    }
  }

  const phaseDurationSeconds = (mode = pomodoro.value.mode) => (
    mode === 'break'
      ? pomodoro.value.breakMinutes * 60
      : pomodoro.value.focusMinutes * 60
  )

  const moveToNextPomodoroPhase = () => {
    if (pomodoro.value.mode === 'focus') {
      pomodoro.value = {
        ...pomodoro.value,
        mode: 'break',
        remainingSeconds: pomodoro.value.breakMinutes * 60,
        isRunning: false,
        startedAt: '',
        endsAt: '',
        completedFocusSessions: pomodoro.value.completedFocusSessions + 1
      }
      return
    }

    pomodoro.value = {
      ...pomodoro.value,
      mode: 'focus',
      remainingSeconds: pomodoro.value.focusMinutes * 60,
      isRunning: false,
      startedAt: '',
      endsAt: ''
    }
  }

  const syncRunningPomodoro = () => {
    if (!pomodoro.value.isRunning || !pomodoro.value.endsAt) return

    const endTime = new Date(pomodoro.value.endsAt)
    if (Number.isNaN(endTime.getTime())) {
      pomodoro.value = {
        ...pomodoro.value,
        isRunning: false,
        endsAt: '',
        startedAt: ''
      }
      return
    }

    const diffMs = endTime.getTime() - Date.now()
    if (diffMs <= 0) {
      stopTicker()
      if (pomodoro.value.mode === 'focus') {
        pomodoro.value = {
          ...pomodoro.value,
          remainingSeconds: 0,
          isRunning: false,
          pendingSettlement: true
        }
      } else {
        moveToNextPomodoroPhase()
      }
      return
    }

    pomodoro.value = {
      ...pomodoro.value,
      remainingSeconds: Math.max(0, Math.ceil(diffMs / 1000))
    }
  }

  const runTicker = () => {
    stopTicker()
    if (typeof window === 'undefined' || !pomodoro.value.isRunning) return

    syncRunningPomodoro()
    if (!pomodoro.value.isRunning) return

    tickHandle = window.setInterval(() => {
      syncRunningPomodoro()
    }, 1000)
  }

  const performDailyRollover = () => {
    const today = todayKey()

    if (!lastAccessDate.value) {
      lastAccessDate.value = today
      return
    }

    if (lastAccessDate.value === today) return

    let daysPassed = 1
    const previousDate = parseISO(lastAccessDate.value)
    if (isValid(previousDate)) {
      daysPassed = Math.max(1, differenceInCalendarDays(parseISO(today), previousDate))
    }

    const completed = todayTasks.value
      .filter((task) => task.completed)
      .map((task) => normalizeArchiveTask({
        id: task.id,
        title: task.title,
        completedAt: task.completedAt,
        archivedOn: today,
        originalCreatedAt: task.createdAt
      }))

    const pending = todayTasks.value
      .filter((task) => !task.completed)
      .map((task) => normalizeTask({
        ...task,
        completed: false,
        completedAt: '',
        isDeferred: true,
        deferredFrom: lastAccessDate.value,
        deferredCount: Number(task.deferredCount || 0) + daysPassed
      }))

    archiveTasks.value = [...completed, ...archiveTasks.value]
    todayTasks.value = pending
    lastAccessDate.value = today
  }

  const hydrate = (username = currentUsername()) => {
    if (typeof window === 'undefined') return

    isHydrating.value = true
    stopTicker()

    const nextUsername = username || currentUsername()
    const rawState = safeParse(window.localStorage.getItem(storageKey(nextUsername)))
    const normalized = normalizeState(rawState || {})

    hydratedUsername.value = nextUsername
    lastAccessDate.value = normalized.lastAccessDate
    pomodoro.value = normalized.pomodoro
    todayTasks.value = normalized.todayTasks
    archiveTasks.value = normalized.archiveTasks
    weekNodes.value = normalized.weekNodes
    countdowns.value = normalized.countdowns

    performDailyRollover()
    syncRunningPomodoro()
    isHydrating.value = false
    persist()
    runTicker()
  }

  const addTask = (title) => {
    const trimmed = String(title || '').trim()
    if (!trimmed) return false

    todayTasks.value = [
      {
        id: generateId('task'),
        title: trimmed,
        completed: false,
        createdAt: new Date().toISOString(),
        completedAt: '',
        isDeferred: false,
        deferredFrom: '',
        deferredCount: 0
      },
      ...todayTasks.value
    ]
    return true
  }

  const toggleTask = (taskId) => {
    const timestamp = new Date().toISOString()
    todayTasks.value = todayTasks.value.map((task) => {
      if (task.id !== taskId) return task
      const completed = !task.completed
      return normalizeTask({
        ...task,
        completed,
        completedAt: completed ? timestamp : ''
      })
    })
  }

  const deleteTask = (taskId) => {
    todayTasks.value = todayTasks.value.filter((task) => task.id !== taskId)
  }

  const startPomodoro = () => {
    if (pomodoro.value.isRunning) return

    const remainingSeconds = pomodoro.value.remainingSeconds > 0
      ? pomodoro.value.remainingSeconds
      : phaseDurationSeconds()

    pomodoro.value = {
      ...pomodoro.value,
      remainingSeconds,
      isRunning: true,
      startedAt: new Date().toISOString(),
      endsAt: new Date(Date.now() + (remainingSeconds * 1000)).toISOString()
    }
    runTicker()
  }

  const pausePomodoro = () => {
    if (!pomodoro.value.isRunning) return

    syncRunningPomodoro()
    pomodoro.value = {
      ...pomodoro.value,
      isRunning: false,
      startedAt: '',
      endsAt: ''
    }
    stopTicker()
  }

  const resetPomodoro = () => {
    pomodoro.value = {
      ...pomodoro.value,
      remainingSeconds: phaseDurationSeconds(),
      isRunning: false,
      startedAt: '',
      endsAt: ''
    }
    stopTicker()
  }

  const addWeekNote = (date) => {
    const dateKeyValue = String(date || '')
    if (!dateKeyValue) return

    const existing = weekNodes.value.find((entry) => entry.date === dateKeyValue)
    if (!existing) {
      weekNodes.value = [...weekNodes.value, { date: dateKeyValue, notes: [''] }]
      return
    }
    if (existing.notes.length >= 2) return

    weekNodes.value = weekNodes.value.map((entry) => (
      entry.date === dateKeyValue
        ? { ...entry, notes: [...entry.notes, ''] }
        : entry
    ))
  }

  const updateWeekNote = (date, noteIndex, nextValue) => {
    const dateKeyValue = String(date || '')
    if (!dateKeyValue) return

    const normalizedValue = String(nextValue || '').trim()
    const existing = weekNodes.value.find((entry) => entry.date === dateKeyValue)
    if (!existing) {
      if (!normalizedValue) return
      weekNodes.value = [...weekNodes.value, { date: dateKeyValue, notes: [normalizedValue] }]
      return
    }

    const nextNotes = [...existing.notes]
    if (!normalizedValue) {
      nextNotes.splice(noteIndex, 1)
    } else {
      nextNotes[noteIndex] = normalizedValue
    }

    weekNodes.value = weekNodes.value
      .map((entry) => (
        entry.date === dateKeyValue
          ? { ...entry, notes: nextNotes.slice(0, 2) }
          : entry
      ))
      .filter((entry) => entry.notes.length)
  }

  const deleteWeekNote = (date, noteIndex) => {
    updateWeekNote(date, noteIndex, '')
  }

  const getNotesForDate = (date) => {
    const dateKeyValue = String(date || '')
    return weekNodes.value.find((entry) => entry.date === dateKeyValue)?.notes || []
  }

  const addCountdown = (title, targetDate) => {
    const trimmedTitle = String(title || '').trim()
    const normalizedDate = String(targetDate || '').trim()
    if (!trimmedTitle || !normalizedDate) return false

    countdowns.value = [
      ...countdowns.value,
      {
        id: generateId('countdown'),
        title: trimmedTitle,
        targetDate: normalizedDate,
        createdAt: new Date().toISOString()
      }
    ]
    return true
  }

  const deleteCountdown = (countdownId) => {
    countdowns.value = countdowns.value.filter((item) => item.id !== countdownId)
  }

  const clearTicker = () => {
    stopTicker()
  }

  const setFocusMinutes = (minutes) => {
    if (pomodoro.value.isRunning) return
    const mins = Number(minutes) > 0 ? Number(minutes) : 25
    pomodoro.value = {
      ...pomodoro.value,
      focusMinutes: mins,
      remainingSeconds: mins * 60,
      startedAt: '',
      endsAt: ''
    }
  }

  const setTaskDifficulty = (level) => {
    if (pomodoro.value.isRunning) return
    pomodoro.value = {
      ...pomodoro.value,
      taskDifficulty: level === 'L2' ? 'L2' : 'L1'
    }
  }

  const linkTimelineTask = (task) => {
    if (!task) return
    const minutes = Number(task.minutes || 25) > 0 ? Number(task.minutes) : 25
    pomodoro.value = {
      ...pomodoro.value,
      focusMinutes: minutes,
      remainingSeconds: pomodoro.value.isRunning ? pomodoro.value.remainingSeconds : minutes * 60,
      linkedTaskId: String(task.id || ''),
      linkedTaskTitle: String(task.task || task.title || '')
    }
  }

  const clearLinkedTask = () => {
    pomodoro.value = {
      ...pomodoro.value,
      linkedTaskId: '',
      linkedTaskTitle: ''
    }
  }

  const completeFocusSession = async ({ username, duration, subject, sessionLog, taskDifficulty }) => {
    const response = await focusApi.complete(
      username || hydratedUsername.value || currentUsername(),
      duration || pomodoro.value.focusMinutes,
      subject || 'Focus Session',
      sessionLog || '',
      taskDifficulty || pomodoro.value.taskDifficulty
    )

    pomodoro.value = {
      ...pomodoro.value,
      completedFocusSessions: pomodoro.value.completedFocusSessions + 1
    }

    if (pomodoro.value.linkedTaskId) {
      try {
        const { useMasterTimelineStore } = await import('./masterTimeline')
        const timelineStore = useMasterTimelineStore()
        timelineStore.completeTask(pomodoro.value.linkedTaskId)
      } catch (e) {
        console.warn('Failed to complete timeline task', e)
      }
      pomodoro.value = {
        ...pomodoro.value,
        linkedTaskId: '',
        linkedTaskTitle: ''
      }
    }

    return response.data
  }

  const resolveFocusCompletion = () => {
    pomodoro.value = {
      ...pomodoro.value,
      pendingSettlement: false
    }
    moveToNextPomodoroPhase()
  }

  const skipSettlement = () => {
    pomodoro.value = {
      ...pomodoro.value,
      pendingSettlement: false,
      mode: 'focus',
      remainingSeconds: pomodoro.value.focusMinutes * 60,
      isRunning: false,
      startedAt: '',
      endsAt: ''
    }
  }

  watch([lastAccessDate, pomodoro, todayTasks, archiveTasks, weekNodes, countdowns], () => {
    persist()
  }, { deep: true })

  const completedTaskCount = computed(() => todayTasks.value.filter((task) => task.completed).length)

  return {
    lastAccessDate,
    pomodoro,
    todayTasks,
    archiveTasks,
    weekNodes,
    countdowns,
    completedTaskCount,
    hydrate,
    addTask,
    toggleTask,
    deleteTask,
    startPomodoro,
    pausePomodoro,
    resetPomodoro,
    addWeekNote,
    updateWeekNote,
    deleteWeekNote,
    getNotesForDate,
    addCountdown,
    deleteCountdown,
    clearTicker,
    setFocusMinutes,
    setTaskDifficulty,
    linkTimelineTask,
    clearLinkedTask,
    completeFocusSession,
    resolveFocusCompletion,
    skipSettlement
  }
})
