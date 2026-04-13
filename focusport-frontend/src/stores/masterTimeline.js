import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { previewSequencePlan } from '../api/qwenService'

const STORAGE_PREFIX = 'fc'

const currentUsername = () => {
  if (typeof window === 'undefined') return 'guest'
  return window.localStorage.getItem('username') || 'guest'
}

const todayKey = () => {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const scopedKey = (scope, username = currentUsername(), dateKey = todayKey()) =>
  `${STORAGE_PREFIX}.${scope}.${username}.${dateKey}`

const safeParseArray = (raw) => {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch (error) {
    console.warn(`Failed to parse timeline storage: ${raw}`, error)
    return []
  }
}

const generateId = (prefix = 'seq') => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}-${crypto.randomUUID()}`
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

const clampMinutes = (value) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return 25
  return Math.min(180, Math.max(5, Math.round(numeric)))
}

const normalizePriority = (value, fallback = 1) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return fallback
  return Math.max(1, Math.round(numeric))
}

const normalizeDraftItem = (item = {}, index = 0) => ({
  id: String(item.id || generateId('draft')),
  task: String(item.task || '').trim(),
  minutes: clampMinutes(item.minutes),
  priority: normalizePriority(item.priority, index + 1),
  source: item.source || 'ai'
})

const normalizeTimelineTask = (item = {}, index = 0) => ({
  id: String(item.id || generateId('task')),
  task: String(item.task || '').trim(),
  minutes: clampMinutes(item.minutes),
  priority: normalizePriority(item.priority, index + 1),
  source: item.source || 'ai',
  status: ['pending', 'deployed', 'completed'].includes(item.status) ? item.status : 'pending',
  createdAt: item.createdAt || new Date().toISOString(),
  deployedAt: item.deployedAt || '',
  completedAt: item.completedAt || ''
})

export const useMasterTimelineStore = defineStore('masterTimeline', () => {
  const hydratedUsername = ref('')
  const hydratedDate = ref(todayKey())
  const previewGoal = ref('')
  const preflightDraft = ref([])
  const masterTimeline = ref([])
  const timelineOrder = ref([])
  const isGenerating = ref(false)
  const generationError = ref('')
  const activeTaskId = ref('')

  const persistArray = (scope, payload, username = hydratedUsername.value || currentUsername(), dateKey = hydratedDate.value || todayKey()) => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(scopedKey(scope, username, dateKey), JSON.stringify(payload))
  }

  const persistGoal = (username = hydratedUsername.value || currentUsername(), dateKey = hydratedDate.value || todayKey()) => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(scopedKey('sequenceGoal', username, dateKey), previewGoal.value)
  }

  const rehydrateOrder = () => {
    const orderSet = new Set(timelineOrder.value)
    const ordered = timelineOrder.value.filter((id) => masterTimeline.value.some((task) => task.id === id))
    const missing = masterTimeline.value
      .map((task) => task.id)
      .filter((id) => !orderSet.has(id))
    timelineOrder.value = [...ordered, ...missing]
  }

  const hydrateToday = (username = currentUsername()) => {
    if (typeof window === 'undefined') return
    const dateKey = todayKey()
    hydratedUsername.value = username
    hydratedDate.value = dateKey
    preflightDraft.value = safeParseArray(window.localStorage.getItem(scopedKey('sequenceDraft', username, dateKey)))
      .map((item, index) => normalizeDraftItem(item, index))
    masterTimeline.value = safeParseArray(window.localStorage.getItem(scopedKey('masterTimeline', username, dateKey)))
      .map((item, index) => normalizeTimelineTask(item, index))
    timelineOrder.value = safeParseArray(window.localStorage.getItem(scopedKey('timelineOrder', username, dateKey)))
      .map((id) => String(id))
    previewGoal.value = window.localStorage.getItem(scopedKey('sequenceGoal', username, dateKey)) || ''
    rehydrateOrder()
    activeTaskId.value = masterTimeline.value.find((task) => task.status === 'deployed')?.id || ''
  }

  watch(preflightDraft, (nextValue) => {
    if (!hydratedUsername.value) return
    persistArray('sequenceDraft', nextValue, hydratedUsername.value, hydratedDate.value)
  }, { deep: true })

  watch(masterTimeline, (nextValue) => {
    if (!hydratedUsername.value) return
    persistArray('masterTimeline', nextValue, hydratedUsername.value, hydratedDate.value)
  }, { deep: true })

  watch(timelineOrder, (nextValue) => {
    if (!hydratedUsername.value) return
    persistArray('timelineOrder', nextValue, hydratedUsername.value, hydratedDate.value)
  }, { deep: true })

  watch(previewGoal, () => {
    if (!hydratedUsername.value) return
    persistGoal(hydratedUsername.value, hydratedDate.value)
  })

  const orderedTimeline = computed(() => {
    const orderMap = new Map(timelineOrder.value.map((id, index) => [id, index]))
    return [...masterTimeline.value].sort((left, right) => {
      const leftOrder = orderMap.has(left.id) ? orderMap.get(left.id) : Number.MAX_SAFE_INTEGER
      const rightOrder = orderMap.has(right.id) ? orderMap.get(right.id) : Number.MAX_SAFE_INTEGER
      if (leftOrder !== rightOrder) return leftOrder - rightOrder
      if (left.priority !== right.priority) return left.priority - right.priority
      return String(left.createdAt).localeCompare(String(right.createdAt))
    })
  })

  const pendingTasks = computed(() => orderedTimeline.value.filter((task) => task.status === 'pending'))
  const deployedTasks = computed(() => orderedTimeline.value.filter((task) => task.status === 'deployed'))
  const completedTasks = computed(() => orderedTimeline.value.filter((task) => task.status === 'completed'))
  const progressPercent = computed(() => {
    const total = masterTimeline.value.length
    if (!total) return 0
    return Math.round((completedTasks.value.length / total) * 100)
  })

  const requestAIPreview = async (goal) => {
    const normalizedGoal = String(goal || '').trim()
    previewGoal.value = normalizedGoal
    generationError.value = ''
    if (!normalizedGoal) {
      preflightDraft.value = []
      generationError.value = '请输入需要拆解的目标。'
      return []
    }

    isGenerating.value = true
    try {
      const response = await previewSequencePlan({ goal: normalizedGoal })
      const plan = Array.isArray(response?.plan) ? response.plan : []
      const normalized = plan.map((item, index) => normalizeDraftItem(item, index)).filter((item) => item.task)
      preflightDraft.value = normalized
      if (!normalized.length) {
        generationError.value = 'AI 没有给出可部署的步序，请重试或手动补充。'
      }
      return normalized
    } catch (error) {
      console.error('Failed to preview sequence plan', error)
      generationError.value = '逻辑预演失败，请稍后重试。'
      preflightDraft.value = []
      return []
    } finally {
      isGenerating.value = false
    }
  }

  const updateDraftItem = (id, patch) => {
    preflightDraft.value = preflightDraft.value.map((item, index) => {
      if (item.id !== id) return item
      const next = { ...item, ...patch }
      return normalizeDraftItem(next, index)
    })
  }

  const addDraftItem = () => {
    preflightDraft.value = [
      ...preflightDraft.value,
      normalizeDraftItem(
        {
          id: generateId('draft'),
          task: '',
          minutes: 25,
          priority: preflightDraft.value.length + 1,
          source: 'manual'
        },
        preflightDraft.value.length
      )
    ]
  }

  const removeDraftItem = (id) => {
    preflightDraft.value = preflightDraft.value
      .filter((item) => item.id !== id)
      .map((item, index) => normalizeDraftItem({ ...item, priority: index + 1 }, index))
  }

  const confirmDraftToTimeline = () => {
    const createdAt = new Date().toISOString()
    const incoming = preflightDraft.value
      .map((item, index) => normalizeTimelineTask({
        id: generateId('task'),
        task: item.task,
        minutes: item.minutes,
        priority: item.priority || index + 1,
        source: item.source || 'ai',
        status: 'pending',
        createdAt
      }, index))
      .filter((item) => item.task)

    if (!incoming.length) return []

    masterTimeline.value = [...masterTimeline.value, ...incoming]
    timelineOrder.value = [...timelineOrder.value, ...incoming.map((item) => item.id)]
    preflightDraft.value = []
    return incoming.map((item) => item.id)
  }

  const reorderTimeline = (fromId, toId) => {
    const source = String(fromId || '')
    const target = String(toId || '')
    if (!source || !target || source === target) return
    const order = [...timelineOrder.value]
    const fromIndex = order.indexOf(source)
    const toIndex = order.indexOf(target)
    if (fromIndex < 0 || toIndex < 0) return
    order.splice(fromIndex, 1)
    order.splice(toIndex, 0, source)
    timelineOrder.value = order
  }

  const sortTimelineByPriority = () => {
    timelineOrder.value = orderedTimeline.value
      .slice()
      .sort((left, right) => left.priority - right.priority)
      .map((task) => task.id)
  }

  const deployTask = (taskId) => {
    const targetId = String(taskId || '')
    if (!targetId) return
    const timestamp = new Date().toISOString()
    masterTimeline.value = masterTimeline.value.map((task) => {
      if (task.id === targetId) {
        return { ...task, status: 'deployed', deployedAt: timestamp, completedAt: '' }
      }
      if (task.status === 'deployed') {
        return { ...task, status: 'pending', deployedAt: '' }
      }
      return task
    })
    activeTaskId.value = targetId
  }

  const completeTask = (taskId) => {
    const targetId = String(taskId || '')
    if (!targetId) return
    const timestamp = new Date().toISOString()
    masterTimeline.value = masterTimeline.value.map((task) => (
      task.id === targetId
        ? { ...task, status: 'completed', completedAt: timestamp }
        : task
    ))
    if (activeTaskId.value === targetId) activeTaskId.value = ''
  }

  const returnTaskToPending = (taskId) => {
    const targetId = String(taskId || '')
    if (!targetId) return
    masterTimeline.value = masterTimeline.value.map((task) => (
      task.id === targetId
        ? { ...task, status: 'pending', deployedAt: '' }
        : task
    ))
    if (activeTaskId.value === targetId) activeTaskId.value = ''
  }

  const clearTodayTimeline = () => {
    preflightDraft.value = []
    masterTimeline.value = []
    timelineOrder.value = []
    previewGoal.value = ''
    activeTaskId.value = ''
  }

  return {
    previewGoal,
    preflightDraft,
    masterTimeline,
    timelineOrder,
    pendingTasks,
    deployedTasks,
    completedTasks,
    orderedTimeline,
    progressPercent,
    activeTaskId,
    isGenerating,
    generationError,
    hydrateToday,
    requestAIPreview,
    updateDraftItem,
    addDraftItem,
    removeDraftItem,
    confirmDraftToTimeline,
    reorderTimeline,
    sortTimelineByPriority,
    deployTask,
    completeTask,
    returnTaskToPending,
    clearTodayTimeline
  }
})
