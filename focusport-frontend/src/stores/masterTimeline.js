import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { useGoalDecomposer } from '../composables/useGoalDecomposer'
import { StalePlanningRequestError } from '../composables/useAIPlanning'

const STORAGE_PREFIX = 'fc'
const DEFAULT_STYLE = 'balanced'
const DEFAULT_IMPORTED_MASTER_TASK_TITLE = 'Imported Legacy Tasks'
const DEFAULT_NEW_MASTER_TASK_TITLE = 'New Master Task'

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

const normalizeMasterTask = (task = {}, index = 0) => {
  const now = new Date().toISOString()
  const title = String(task.title || '').trim() || `${DEFAULT_NEW_MASTER_TASK_TITLE} ${index + 1}`
  return {
    id: String(task.id || generateId('master')),
    title,
    createdAt: String(task.createdAt || now),
    updatedAt: String(task.updatedAt || task.createdAt || now)
  }
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

const normalizeTimelineTask = (item = {}, index = 0, fallbackMasterTaskId = '') => {
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
    completedAt: item.completedAt || '',
    masterTaskId: String(item.masterTaskId || fallbackMasterTaskId || ''),
    phaseOrder: Number.isFinite(Number(item.phaseOrder)) ? Math.max(1, Math.round(Number(item.phaseOrder))) : index + 1
  }
}

const normalizeDraftPriorities = (items) => {
  return items.map((item, index) => normalizeDraftItem({ ...item, priority: index + 1 }, index))
}

const normalizeDraftStepToTimelineItem = (
  step,
  createdAt = new Date().toISOString(),
  masterTaskId = '',
  phaseOrder = 1
) => {
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
    createdAt,
    masterTaskId,
    phaseOrder
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
  const masterTasks = ref([])
  const selectedMasterTaskId = ref('')
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

  const persistSelectedMasterTaskId = (username = hydratedUsername.value || currentUsername(), dateKey = hydratedDate.value || todayKey()) => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(scopedKey('selectedMasterTaskId', username, dateKey), String(selectedMasterTaskId.value || ''))
  }

  const rehydrateOrder = () => {
    const ordered = timelineOrder.value.filter((id) => masterTimeline.value.some((task) => task.id === id))
    const orderedSet = new Set(ordered)
    const missing = masterTimeline.value.map((task) => task.id).filter((id) => !orderedSet.has(id))
    timelineOrder.value = [...ordered, ...missing]
  }

  const orderedTimeline = computed(() => {
    const orderMap = new Map(timelineOrder.value.map((id, index) => [id, index]))
    return [...masterTimeline.value].sort((left, right) => {
      const leftOrder = orderMap.has(left.id) ? orderMap.get(left.id) : Number.MAX_SAFE_INTEGER
      const rightOrder = orderMap.has(right.id) ? orderMap.get(right.id) : Number.MAX_SAFE_INTEGER
      if (leftOrder !== rightOrder) return leftOrder - rightOrder
      if (left.phaseOrder !== right.phaseOrder) return left.phaseOrder - right.phaseOrder
      if (left.priority !== right.priority) return left.priority - right.priority
      return String(left.createdAt).localeCompare(String(right.createdAt))
    })
  })

  const listPhasesByMaster = (masterTaskId) => {
    const targetId = String(masterTaskId || '')
    if (!targetId) return []
    return orderedTimeline.value
      .filter((task) => task.masterTaskId === targetId)
      .sort((left, right) => {
        if (left.phaseOrder !== right.phaseOrder) return left.phaseOrder - right.phaseOrder
        if (left.priority !== right.priority) return left.priority - right.priority
        return String(left.createdAt).localeCompare(String(right.createdAt))
      })
  }

  const selectedMasterTask = computed(() => (
    masterTasks.value.find((task) => task.id === selectedMasterTaskId.value) || null
  ))

  const masterTaskSummaries = computed(() => {
    return masterTasks.value.map((task) => {
      const phases = listPhasesByMaster(task.id)
      const completedCount = phases.filter((phase) => phase.status === 'completed').length
      const deployedPhase = phases.find((phase) => phase.status === 'deployed') || null
      const pendingPhase = phases.find((phase) => phase.status === 'pending') || null
      const nextPhase = deployedPhase || pendingPhase || null
      const totalCount = phases.length
      const progress = totalCount ? Math.round((completedCount / totalCount) * 100) : 0
      const status = deployedPhase
        ? 'in_progress'
        : totalCount > 0 && completedCount === totalCount
          ? 'completed'
          : totalCount === 0
            ? 'empty'
            : 'pending'

      return {
        id: task.id,
        title: task.title,
        createdAt: task.createdAt,
        updatedAt: task.updatedAt,
        totalCount,
        completedCount,
        progress,
        status,
        nextPhaseTitle: nextPhase?.title || ''
      }
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

  const touchMasterTask = (masterTaskId) => {
    const targetId = String(masterTaskId || '')
    if (!targetId) return
    const now = new Date().toISOString()
    masterTasks.value = masterTasks.value.map((task) => (
      task.id === targetId
        ? { ...task, updatedAt: now }
        : task
    ))
  }

  const normalizePhaseOrders = (targetMasterTaskIds = null) => {
    const targets = targetMasterTaskIds
      ? new Set((Array.isArray(targetMasterTaskIds) ? targetMasterTaskIds : [targetMasterTaskIds]).map((id) => String(id || '')))
      : null

    const counters = new Map()
    const orderById = new Map()

    orderedTimeline.value.forEach((task) => {
      if (targets && !targets.has(task.masterTaskId)) return
      const next = (counters.get(task.masterTaskId) || 0) + 1
      counters.set(task.masterTaskId, next)
      orderById.set(task.id, next)
    })

    masterTimeline.value = masterTimeline.value.map((task) => {
      if (!orderById.has(task.id)) return task
      const nextOrder = orderById.get(task.id)
      return task.phaseOrder === nextOrder
        ? task
        : { ...task, phaseOrder: nextOrder }
    })
  }

  const ensureSelectedMasterTask = () => {
    const exists = masterTasks.value.some((task) => task.id === selectedMasterTaskId.value)
    if (exists) return
    selectedMasterTaskId.value = masterTasks.value[0]?.id || ''
  }

  const createMasterTask = (title = '', options = {}) => {
    const now = new Date().toISOString()
    const normalized = normalizeMasterTask({
      id: generateId('master'),
      title: String(title || '').trim() || DEFAULT_NEW_MASTER_TASK_TITLE,
      createdAt: now,
      updatedAt: now
    }, masterTasks.value.length)

    masterTasks.value = [...masterTasks.value, normalized]
    if (options.select !== false) {
      selectedMasterTaskId.value = normalized.id
    }
    return normalized
  }

  const ensureMasterTaskForPhases = () => {
    if (!masterTimeline.value.length) {
      ensureSelectedMasterTask()
      return
    }

    if (!masterTasks.value.length) {
      const imported = createMasterTask(previewGoal.value || DEFAULT_IMPORTED_MASTER_TASK_TITLE, { select: false })
      masterTimeline.value = masterTimeline.value.map((task) => ({
        ...task,
        masterTaskId: imported.id
      }))
    }

    const validMasterTaskIds = new Set(masterTasks.value.map((task) => task.id))
    const fallbackMasterTaskId = masterTasks.value[0]?.id || ''

    masterTimeline.value = masterTimeline.value.map((task) => {
      const currentMasterTaskId = validMasterTaskIds.has(task.masterTaskId)
        ? task.masterTaskId
        : fallbackMasterTaskId
      return currentMasterTaskId === task.masterTaskId
        ? task
        : { ...task, masterTaskId: currentMasterTaskId }
    })

    normalizePhaseOrders()
    ensureSelectedMasterTask()
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

    masterTasks.value = safeParseArray(window.localStorage.getItem(scopedKey('masterTasks', username, dateKey)))
      .map((item, index) => normalizeMasterTask(item, index))

    selectedMasterTaskId.value = String(window.localStorage.getItem(scopedKey('selectedMasterTaskId', username, dateKey)) || '')

    previewGoal.value = window.localStorage.getItem(scopedKey('sequenceGoal', username, dateKey)) || ''

    const meta = safeParseObject(window.localStorage.getItem(scopedKey('sequenceMeta', username, dateKey)), {})
    decomposeStyle.value = normalizeStyle(meta.decomposeStyle)

    preflightDraft.value = normalizeDraftPriorities(preflightDraft.value)
    rehydrateOrder()
    ensureMasterTaskForPhases()
    activeTaskId.value = masterTimeline.value.find((task) => task.status === 'deployed')?.id || ''
    persistSelectedMasterTaskId(username, dateKey)
  }

  let draftPersistTimer = null
  let timelinePersistTimer = null
  let orderPersistTimer = null
  let masterTaskPersistTimer = null

  watch(preflightDraft, (nextValue) => {
    if (!hydratedUsername.value) return
    if (draftPersistTimer) clearTimeout(draftPersistTimer)
    draftPersistTimer = setTimeout(() => persistArray('sequenceDraft', nextValue, hydratedUsername.value, hydratedDate.value), 300)
  }, { deep: true })

  watch(masterTimeline, (nextValue) => {
    if (!hydratedUsername.value) return
    if (timelinePersistTimer) clearTimeout(timelinePersistTimer)
    timelinePersistTimer = setTimeout(() => persistArray('masterTimeline', nextValue, hydratedUsername.value, hydratedDate.value), 300)
  }, { deep: true })

  watch(timelineOrder, (nextValue) => {
    if (!hydratedUsername.value) return
    if (orderPersistTimer) clearTimeout(orderPersistTimer)
    orderPersistTimer = setTimeout(() => persistArray('timelineOrder', nextValue, hydratedUsername.value, hydratedDate.value), 300)
  }, { deep: true })

  watch(masterTasks, (nextValue) => {
    if (!hydratedUsername.value) return
    if (masterTaskPersistTimer) clearTimeout(masterTaskPersistTimer)
    masterTaskPersistTimer = setTimeout(() => persistArray('masterTasks', nextValue, hydratedUsername.value, hydratedDate.value), 300)
  }, { deep: true })

  watch(selectedMasterTaskId, () => {
    if (!hydratedUsername.value) return
    persistSelectedMasterTaskId(hydratedUsername.value, hydratedDate.value)
  })

  watch([previewGoal, decomposeStyle], () => {
    if (!hydratedUsername.value) return
    persistMeta(hydratedUsername.value, hydratedDate.value)
  })

  const addMasterTask = (title = '') => {
    return createMasterTask(title, { select: true })
  }

  const updateMasterTask = (id, patch = {}) => {
    const targetId = String(id || '')
    if (!targetId) return
    const nextTitle = String(patch.title || '').trim()
    masterTasks.value = masterTasks.value.map((task) => {
      if (task.id !== targetId) return task
      return {
        ...task,
        title: nextTitle || task.title,
        updatedAt: new Date().toISOString()
      }
    })
  }

  const removeMasterTask = (id) => {
    const targetId = String(id || '')
    if (!targetId) return

    const removedPhaseIds = new Set(
      masterTimeline.value
        .filter((task) => task.masterTaskId === targetId)
        .map((task) => task.id)
    )

    masterTimeline.value = masterTimeline.value.filter((task) => task.masterTaskId !== targetId)
    timelineOrder.value = timelineOrder.value.filter((taskId) => !removedPhaseIds.has(taskId))

    if (removedPhaseIds.has(activeTaskId.value)) {
      activeTaskId.value = ''
    }

    masterTasks.value = masterTasks.value.filter((task) => task.id !== targetId)

    if (!masterTasks.value.length && masterTimeline.value.length) {
      const imported = createMasterTask(DEFAULT_IMPORTED_MASTER_TASK_TITLE, { select: false })
      masterTimeline.value = masterTimeline.value.map((task) => ({ ...task, masterTaskId: imported.id }))
    }

    normalizePhaseOrders()
    ensureSelectedMasterTask()
  }

  const selectMasterTask = (id) => {
    const targetId = String(id || '')
    if (!targetId) return
    if (!masterTasks.value.some((task) => task.id === targetId)) return
    selectedMasterTaskId.value = targetId
  }

  const addPhaseToMaster = (masterTaskId, phase = {}) => {
    let targetMasterTaskId = String(masterTaskId || selectedMasterTaskId.value || '')

    if (!targetMasterTaskId || !masterTasks.value.some((task) => task.id === targetMasterTaskId)) {
      const createdMasterTask = createMasterTask(DEFAULT_NEW_MASTER_TASK_TITLE, { select: true })
      targetMasterTaskId = createdMasterTask.id
    }

    const currentPhases = listPhasesByMaster(targetMasterTaskId)
    const title = String(phase.title || phase.task || '').trim() || `阶段 ${currentPhases.length + 1}`
    const createdAt = new Date().toISOString()

    const nextPhase = normalizeTimelineTask({
      ...phase,
      id: generateId('task'),
      title,
      task: title,
      masterTaskId: targetMasterTaskId,
      status: 'pending',
      createdAt,
      phaseOrder: currentPhases.length + 1,
      source: phase.source || 'manual',
      deployedAt: '',
      completedAt: ''
    }, currentPhases.length, targetMasterTaskId)

    masterTimeline.value = [...masterTimeline.value, nextPhase]
    timelineOrder.value = [...timelineOrder.value, nextPhase.id]
    touchMasterTask(targetMasterTaskId)

    return nextPhase
  }

  const updatePhase = (phaseId, patch = {}) => {
    const targetId = String(phaseId || '')
    if (!targetId) return

    let previousMasterTaskId = ''
    let nextMasterTaskId = ''

    masterTimeline.value = masterTimeline.value.map((task, index) => {
      if (task.id !== targetId) return task
      previousMasterTaskId = task.masterTaskId

      const requestedMasterTaskId = String(patch.masterTaskId || task.masterTaskId || '')
      const validMasterTaskId = masterTasks.value.some((masterTask) => masterTask.id === requestedMasterTaskId)
        ? requestedMasterTaskId
        : task.masterTaskId

      const requestedTitle = Object.prototype.hasOwnProperty.call(patch, 'title')
        ? String(patch.title || '').trim()
        : task.title

      const merged = {
        ...task,
        ...patch,
        title: requestedTitle || task.title,
        task: requestedTitle || task.task,
        masterTaskId: validMasterTaskId
      }

      nextMasterTaskId = merged.masterTaskId
      return normalizeTimelineTask(merged, index, merged.masterTaskId)
    })

    normalizePhaseOrders([previousMasterTaskId, nextMasterTaskId])
    touchMasterTask(previousMasterTaskId)
    if (nextMasterTaskId !== previousMasterTaskId) {
      touchMasterTask(nextMasterTaskId)
    }
  }

  const removePhase = (phaseId) => {
    const targetId = String(phaseId || '')
    if (!targetId) return

    const targetPhase = masterTimeline.value.find((task) => task.id === targetId)
    if (!targetPhase) return

    masterTimeline.value = masterTimeline.value.filter((task) => task.id !== targetId)
    timelineOrder.value = timelineOrder.value.filter((id) => id !== targetId)

    if (activeTaskId.value === targetId) {
      activeTaskId.value = ''
    }

    normalizePhaseOrders(targetPhase.masterTaskId)
    touchMasterTask(targetPhase.masterTaskId)
  }

  const movePhase = (phaseId, direction) => {
    const targetId = String(phaseId || '')
    if (!targetId) return

    const current = masterTimeline.value.find((task) => task.id === targetId)
    if (!current) return

    const phases = listPhasesByMaster(current.masterTaskId)
    const index = phases.findIndex((phase) => phase.id === targetId)
    if (index < 0) return

    const nextIndex = direction === 'up' ? index - 1 : index + 1
    if (nextIndex < 0 || nextIndex >= phases.length) return

    const swapTarget = phases[nextIndex]
    reorderTimeline(targetId, swapTarget.id)
    normalizePhaseOrders(current.masterTaskId)
    touchMasterTask(current.masterTaskId)
  }

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
      generationError.value = 'Please enter a goal to decompose.'
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
        generationError.value = 'No executable steps were generated. Please refine the goal and try again.'
      }
      return applied
    } catch (error) {
      if (error instanceof StalePlanningRequestError || error?.name === 'StalePlanningRequestError') {
        return preflightDraft.value
      }
      console.error('Failed to generate sequence draft', error)
      generationError.value = 'AI decomposition failed. Please try again later.'
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

    if (!masterTasks.value.length) {
      createMasterTask(previewGoal.value || DEFAULT_NEW_MASTER_TASK_TITLE, { select: true })
    }

    ensureSelectedMasterTask()
    const targetMasterTaskId = selectedMasterTaskId.value || masterTasks.value[0]?.id || ''
    const currentCount = listPhasesByMaster(targetMasterTaskId).length

    const incoming = preflightDraft.value
      .map((item, index) => normalizeDraftStepToTimelineItem(
        item,
        createdAt,
        targetMasterTaskId,
        currentCount + index + 1
      ))
      .filter((item) => item.task)

    if (!incoming.length) return []

    masterTimeline.value = [...masterTimeline.value, ...incoming]
    timelineOrder.value = [...timelineOrder.value, ...incoming.map((item) => item.id)]
    preflightDraft.value = []
    touchMasterTask(targetMasterTaskId)
    normalizePhaseOrders(targetMasterTaskId)

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
    normalizePhaseOrders()
  }

  const deployTask = (taskId) => {
    const targetId = String(taskId || '')
    if (!targetId) return
    const timestamp = new Date().toISOString()
    let targetMasterTaskId = ''

    masterTimeline.value = masterTimeline.value.map((task) => {
      if (task.id === targetId) {
        targetMasterTaskId = task.masterTaskId
        return { ...task, status: 'deployed', deployedAt: timestamp, completedAt: '' }
      }
      if (task.status === 'deployed') {
        return { ...task, status: 'pending', deployedAt: '' }
      }
      return task
    })

    activeTaskId.value = targetId
    if (targetMasterTaskId) {
      selectedMasterTaskId.value = targetMasterTaskId
      touchMasterTask(targetMasterTaskId)
    }
  }

  const completeTask = (taskId) => {
    const targetId = String(taskId || '')
    if (!targetId) return
    const timestamp = new Date().toISOString()
    let targetMasterTaskId = ''

    masterTimeline.value = masterTimeline.value.map((task) => {
      if (task.id !== targetId) return task
      targetMasterTaskId = task.masterTaskId
      return { ...task, status: 'completed', completedAt: timestamp }
    })

    if (activeTaskId.value === targetId) activeTaskId.value = ''
    if (targetMasterTaskId) touchMasterTask(targetMasterTaskId)
  }

  const returnTaskToPending = (taskId) => {
    const targetId = String(taskId || '')
    if (!targetId) return
    let targetMasterTaskId = ''

    masterTimeline.value = masterTimeline.value.map((task) => {
      if (task.id !== targetId) return task
      targetMasterTaskId = task.masterTaskId
      return { ...task, status: 'pending', deployedAt: '' }
    })

    if (activeTaskId.value === targetId) activeTaskId.value = ''
    if (targetMasterTaskId) touchMasterTask(targetMasterTaskId)
  }

  const clearTodayTimeline = () => {
    preflightDraft.value = []
    masterTimeline.value = []
    timelineOrder.value = []
    masterTasks.value = []
    selectedMasterTaskId.value = ''
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
    masterTasks,
    selectedMasterTaskId,
    selectedMasterTask,
    masterTaskSummaries,
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
    addMasterTask,
    updateMasterTask,
    removeMasterTask,
    selectMasterTask,
    addPhaseToMaster,
    listPhasesByMaster,
    updatePhase,
    removePhase,
    movePhase,
    clearTodayTimeline
  }
})

