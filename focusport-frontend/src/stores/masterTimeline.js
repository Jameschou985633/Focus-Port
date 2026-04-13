import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { useGoalDecomposer } from '../composables/useGoalDecomposer'
import { StalePlanningRequestError } from '../composables/useAIPlanning'

const STORAGE_PREFIX = 'fc'
const DEFAULT_STYLE = 'balanced'

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

const safeParseObject = (raw, fallback = {}) => {
  if (!raw) return fallback
  try {
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : fallback
  } catch (error) {
    console.warn(`Failed to parse object storage: ${raw}`, error)
    return fallback
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

const clampPomodoros = (value) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return 1
  return Math.min(3, Math.max(1, Math.round(numeric)))
}

const normalizePriority = (value, fallback = 1) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return fallback
  return Math.max(1, Math.round(numeric))
}

const normalizeStyle = (value) => {
  if (value === 'conservative' || value === 'sprint') return value
  return 'balanced'
}

const normalizeDraftItem = (item = {}, index = 0) => {
  const title = String(item.title || item.task || '').trim()
  const estimatedPomodoros = clampPomodoros(item.estimatedPomodoros ?? Math.max(1, Math.round(clampMinutes(item.minutes) / 25)))
  return {
    id: String(item.id || generateId('draft')),
    title,
    task: title,
    description: String(item.description || '').trim(),
    doneDefinition: String(item.doneDefinition || '').trim(),
    estimatedPomodoros,
    minutes: clampMinutes(item.minutes ?? estimatedPomodoros * 25),
    priority: normalizePriority(item.priority, index + 1),
    difficulty: ['low', 'medium', 'high'].includes(item.difficulty) ? item.difficulty : 'medium',
    category: item.category ? String(item.category) : '',
    reason: item.reason ? String(item.reason) : '',
    actionable: item.actionable !== false,
    source: item.source || 'ai_generated'
  }
}

const normalizeTimelineTask = (item = {}, index = 0) => {
  const title = String(item.title || item.task || '').trim()
  const estimatedPomodoros = clampPomodoros(item.estimatedPomodoros ?? Math.max(1, Math.round(clampMinutes(item.minutes) / 25)))
  return {
    id: String(item.id || generateId('task')),
    title,
    task: title,
    description: String(item.description || '').trim(),
    doneDefinition: String(item.doneDefinition || '').trim(),
    estimatedPomodoros,
    minutes: clampMinutes(item.minutes ?? estimatedPomodoros * 25),
    priority: normalizePriority(item.priority, index + 1),
    difficulty: ['low', 'medium', 'high'].includes(item.difficulty) ? item.difficulty : 'medium',
    category: item.category ? String(item.category) : '',
    reason: item.reason ? String(item.reason) : '',
    actionable: item.actionable !== false,
    source: item.source || 'ai_generated',
    status: ['pending', 'deployed', 'completed'].includes(item.status) ? item.status : 'pending',
    createdAt: item.createdAt || new Date().toISOString(),
    deployedAt: item.deployedAt || '',
    completedAt: item.completedAt || ''
  }
}

const normalizeDraftPriorities = (items) => {
  return items.map((item, index) => normalizeDraftItem({ ...item, priority: index + 1 }, index))
}

const normalizeDraftStepToTimelineItem = (step, createdAt = new Date().toISOString()) => {
  const normalized = normalizeDraftItem(step, 0)
  return normalizeTimelineTask({
    id: generateId('task'),
    title: normalized.title,
    task: normalized.title,
    description: normalized.description,
    doneDefinition: normalized.doneDefinition,
    estimatedPomodoros: normalized.estimatedPomodoros,
    minutes: normalized.estimatedPomodoros * 25,
    priority: normalized.priority,
    difficulty: normalized.difficulty,
    category: normalized.category,
    reason: normalized.reason,
    actionable: normalized.actionable,
    source: normalized.source || 'ai_generated',
    status: 'pending',
    createdAt
  })
}

export const useMasterTimelineStore = defineStore('masterTimeline', () => {
  const { decomposeGoal } = useGoalDecomposer()

  const hydratedUsername = ref('')
  const hydratedDate = ref(todayKey())
  const previewGoal = ref('')
  const decomposeStyle = ref(DEFAULT_STYLE)
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

  const persistMeta = (username = hydratedUsername.value || currentUsername(), dateKey = hydratedDate.value || todayKey()) => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(scopedKey('sequenceGoal', username, dateKey), previewGoal.value)
    window.localStorage.setItem(scopedKey('sequenceMeta', username, dateKey), JSON.stringify({
      decomposeStyle: decomposeStyle.value
    }))
  }

  const rehydrateOrder = () => {
    const ordered = timelineOrder.value.filter((id) => masterTimeline.value.some((task) => task.id === id))
    const orderedSet = new Set(ordered)
    const missing = masterTimeline.value.map((task) => task.id).filter((id) => !orderedSet.has(id))
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
    const meta = safeParseObject(window.localStorage.getItem(scopedKey('sequenceMeta', username, dateKey)), {})
    decomposeStyle.value = normalizeStyle(meta.decomposeStyle)

    preflightDraft.value = normalizeDraftPriorities(preflightDraft.value)
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

  watch([previewGoal, decomposeStyle], () => {
    if (!hydratedUsername.value) return
    persistMeta(hydratedUsername.value, hydratedDate.value)
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

  const applyAIDraftSteps = (steps, mode = 'replace') => {
    const normalized = (Array.isArray(steps) ? steps : [])
      .map((step, index) => normalizeDraftItem({
        ...step,
        source: step?.source || 'ai_generated',
        priority: step?.priority || index + 1
      }, index))
      .filter((item) => item.title)

    if (mode === 'append') {
      preflightDraft.value = normalizeDraftPriorities([...preflightDraft.value, ...normalized])
      return preflightDraft.value
    }

    preflightDraft.value = normalizeDraftPriorities(normalized)
    return preflightDraft.value
  }

  const requestAIPreview = async (goal, options = {}) => {
    const normalizedGoal = String(goal || '').trim()
    previewGoal.value = normalizedGoal
    generationError.value = ''

    if (!normalizedGoal) {
      preflightDraft.value = []
      generationError.value = '请输入需要拆解的任务目标。'
      return []
    }

    isGenerating.value = true
    try {
      const steps = await decomposeGoal({
        goal: normalizedGoal,
        style: normalizeStyle(options.style || decomposeStyle.value),
        availableMinutes: options.availableMinutes,
        weakPoints: options.weakPoints
      })
      const applied = applyAIDraftSteps(steps, options.mode || 'replace')
      if (!applied.length) {
        generationError.value = '暂未生成可执行步骤，请调整目标后重试。'
      }
      return applied
    } catch (error) {
      if (error instanceof StalePlanningRequestError || error?.name === 'StalePlanningRequestError') {
        return preflightDraft.value
      }
      console.error('Failed to generate sequence draft', error)
      generationError.value = 'AI 拆解失败，请稍后重试。'
      preflightDraft.value = []
      return []
    } finally {
      isGenerating.value = false
    }
  }

  const updateDraftItem = (id, patch) => {
    preflightDraft.value = normalizeDraftPriorities(
      preflightDraft.value.map((item, index) => {
        if (item.id !== id) return normalizeDraftItem(item, index)
        return normalizeDraftItem({ ...item, ...patch }, index)
      })
    )
  }

  const addDraftItem = () => {
    preflightDraft.value = normalizeDraftPriorities([
      ...preflightDraft.value,
      normalizeDraftItem(
        {
          id: generateId('draft'),
          title: '',
          estimatedPomodoros: 1,
          priority: preflightDraft.value.length + 1,
          difficulty: 'medium',
          actionable: true,
          source: 'manual'
        },
        preflightDraft.value.length
      )
    ])
  }

  const removeDraftItem = (id) => {
    preflightDraft.value = normalizeDraftPriorities(preflightDraft.value.filter((item) => item.id !== id))
  }

  const moveDraftItem = (id, direction) => {
    const index = preflightDraft.value.findIndex((item) => item.id === id)
    if (index < 0) return
    const targetIndex = direction === 'up' ? index - 1 : index + 1
    if (targetIndex < 0 || targetIndex >= preflightDraft.value.length) return
    const next = [...preflightDraft.value]
    const [moved] = next.splice(index, 1)
    next.splice(targetIndex, 0, moved)
    preflightDraft.value = normalizeDraftPriorities(next)
  }

  const confirmDraftToTimeline = () => {
    const createdAt = new Date().toISOString()
    const incoming = preflightDraft.value
      .map((item) => normalizeDraftStepToTimelineItem(item, createdAt))
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
    decomposeStyle.value = DEFAULT_STYLE
  }

  return {
    previewGoal,
    decomposeStyle,
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
    applyAIDraftSteps,
    updateDraftItem,
    addDraftItem,
    removeDraftItem,
    moveDraftItem,
    confirmDraftToTimeline,
    normalizeDraftStepToTimelineItem,
    reorderTimeline,
    sortTimelineByPriority,
    deployTask,
    completeTask,
    returnTaskToPending,
    clearTodayTimeline
  }
})
