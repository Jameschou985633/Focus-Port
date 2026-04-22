<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { focusApi, growthApi, phoneApi, taskApi } from '../api'
import { useUserStore } from '../stores/user'
import { useFocusHubStore } from '../stores/focusHub'
import { useDimensionStore } from '../stores/dimension'
import { useMailStore } from '../stores/mail'
import { useGoalDecomposer } from '../composables/useGoalDecomposer'

const router = useRouter()
const userStore = useUserStore()
const focusHubStore = useFocusHubStore()
const dimensionStore = useDimensionStore()
const mailStore = useMailStore()
const { decomposeGoal } = useGoalDecomposer()

const durationOptions = [15, 25, 40, 60]
const selectedDuration = ref(25)
const selectedDurationIndex = ref(1)
const isActionHydrating = ref(true)
const isStartingFocus = ref(false)
const isTaskLoading = ref(false)
const isTaskSubmitting = ref(false)
const deletingTaskId = ref('')
const taskError = ref('')
const initError = ref('')

const todoTasks = ref([])
const selectedTodoTaskId = ref('')
const activeFocusTodoId = ref('')
const selectedDateKey = ref('')
const monthCursor = ref(new Date())
const taskModalOpen = ref(false)
const calendarModalOpen = ref(false)

const userAvatar = ref('')
const userNickname = ref('')

const stageRegistry = ref({})
const decomposeIntensity = ref('medium')
const decomposeState = ref('idle')
const decomposeError = ref('')

const auditModalOpen = ref(false)
const auditSelectedFile = ref(null)
const auditPreview = ref('')
const auditResult = ref(null)
const auditMinutes = ref(0)
const auditCategory = ref('学习')
const auditNotes = ref('')
const auditState = ref('idle')
const auditMessage = ref('')

const taskForm = ref({
  content: '',
  scheduledDate: '',
  scheduledTime: '10:00',
  category: 'FocusPort',
  accent: '#4880FF'
})

const accentOptions = ['#4880FF', '#7551E9', '#E951BF', '#FF9E58', '#00B69B']
const auditCategories = ['学习', '工作', '社交', '娱乐', '游戏', '其他']
const dateKeyPattern = /^\d{4}-\d{2}-\d{2}$/
const weekdayLabels = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
const STAGE_STORAGE_PREFIX = 'focusport.focushub.taskStages.v1'
const intensityStyleMap = { weak: 'conservative', medium: 'balanced', strong: 'sprint' }
const intensityLabels = { weak: '弱', medium: '中', strong: '强' }
const hardlinePhrases = [
  '锁定输入源，完成第一轮清障。',
  '压缩噪声窗口，推进核心算子。',
  '建立稳定链路，拒绝上下文漂移。',
  '执行高强度校验，清除薄弱节点。',
  '封装最终输出，准备跃迁验收。'
]

const toDateKey = (value = new Date()) => {
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const todayDateKey = () => toDateKey(new Date())
const normalizeDateKey = (value, fallback = todayDateKey()) => {
  const raw = String(value || '').trim()
  if (dateKeyPattern.test(raw)) return raw
  const prefix = raw.slice(0, 10)
  if (dateKeyPattern.test(prefix)) return prefix
  return fallback
}

const username = computed(() => userStore.username || 'guest')
const mailUnread = computed(() => Math.max(0, Number(mailStore.unreadCount || 0)))
const isFocusMode = computed(() => focusHubStore.pomodoro.isRunning)
const computeUnits = computed(() => Math.max(0, Number(userStore.growth?.coins || 0)))
const focusEnergy = computed(() => Math.max(0, Number(userStore.growth?.focus_energy || 0)))
const disciplineScore = computed(() => Math.max(0, Math.min(100, Number(userStore.growth?.discipline_score || 50))))

const displayName = computed(() => String(userNickname.value || '').trim() || username.value)
const avatarToken = computed(() => String(userAvatar.value || '').trim() || (username.value?.[0] || 'F').toUpperCase())
const avatarIsImage = computed(() => avatarToken.value.startsWith('http://') || avatarToken.value.startsWith('https://') || avatarToken.value.startsWith('data:image'))

const formattedRemaining = computed(() => {
  const total = Math.max(0, Number(focusHubStore.pomodoro.remainingSeconds) || 0)
  const mm = String(Math.floor(total / 60)).padStart(2, '0')
  const ss = String(total % 60).padStart(2, '0')
  return `${mm}:${ss}`
})

const safeTotalSeconds = computed(() => Math.max(60, Number(focusHubStore.pomodoro.focusMinutes || selectedDuration.value || 25) * 60))
const safeRemainingSeconds = computed(() => Math.max(0, Number(focusHubStore.pomodoro.remainingSeconds || 0)))
const progressPercent = computed(() => Math.round((1 - Math.min(1, safeRemainingSeconds.value / safeTotalSeconds.value)) * 100))
const ringRadius = 48
const ringCircumference = 2 * Math.PI * ringRadius
const ringOffset = computed(() => ringCircumference * (1 - Math.min(1, Math.max(0, safeRemainingSeconds.value / safeTotalSeconds.value))))

const normalizeTask = (task = {}) => {
  const isCompleted = Boolean(task.isCompleted ?? task.is_completed)
  const scheduledDate = normalizeDateKey(task.scheduledDate || task.scheduled_date || task.createdAt || task.created_at)
  const status = isCompleted ? 'done' : ['in_progress', 'todo'].includes(task.status) ? task.status : 'todo'
  return {
    id: Number(task.id),
    title: String(task.title || task.content || '').trim(),
    isCompleted,
    status,
    scheduledDate,
    scheduledTime: String(task.scheduledTime || task.scheduled_time || '').slice(0, 5),
    category: String(task.category || '').trim() || 'FocusPort',
    accent: /^#[0-9a-f]{6}$/i.test(String(task.accent || '')) ? task.accent : '#4880FF',
    createdAt: String(task.createdAt || task.created_at || '')
  }
}

const selectedTodoTask = computed(() => todoTasks.value.find((task) => String(task.id) === String(selectedTodoTaskId.value)) || null)
const selectedTaskIsDone = computed(() => Boolean(selectedTodoTask.value?.isCompleted || selectedTodoTask.value?.status === 'done'))
const visibleTasks = computed(() => todoTasks.value.filter((task) => task.scheduledDate === selectedDateKey.value))

const tasksByDate = computed(() => {
  const map = new Map()
  todoTasks.value.forEach((task) => {
    if (!map.has(task.scheduledDate)) map.set(task.scheduledDate, [])
    map.get(task.scheduledDate).push(task)
  })
  return map
})

const monthTitle = computed(() => new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: 'long' }).format(monthCursor.value))
const calendarCells = computed(() => {
  const y = monthCursor.value.getFullYear()
  const m = monthCursor.value.getMonth()
  const firstDay = new Date(y, m, 1)
  const mondayIndex = (firstDay.getDay() + 6) % 7
  const gridStart = new Date(y, m, 1 - mondayIndex)
  const today = todayDateKey()
  return Array.from({ length: 42 }, (_, index) => {
    const current = new Date(gridStart)
    current.setDate(gridStart.getDate() + index)
    const dateKey = toDateKey(current)
    return {
      dateKey,
      day: current.getDate(),
      inMonth: current.getMonth() === m,
      isToday: dateKey === today,
      isSelected: dateKey === selectedDateKey.value,
      tasks: tasksByDate.value.get(dateKey) || []
    }
  })
})

const calendarPreviewCells = computed(() => {
  const selectedIndex = calendarCells.value.findIndex((cell) => cell.dateKey === selectedDateKey.value)
  const start = selectedIndex >= 0 ? Math.max(0, selectedIndex - (selectedIndex % 7)) : 0
  return calendarCells.value.slice(start, start + 14)
})

const focusActionDisabled = computed(() => !focusHubStore.pomodoro.isRunning && (isStartingFocus.value || isTaskLoading.value || !selectedTodoTask.value || selectedTaskIsDone.value))
const focusActionLabel = computed(() => isStartingFocus.value ? '启动中' : focusHubStore.pomodoro.isRunning ? '暂停专注' : '开始专注')
const focusSubject = computed(() => selectedTodoTask.value?.title || 'Focus Session')
const focusGoalTitle = computed(() => selectedTodoTask.value?.category || 'Today Focus')
const focusActionTitle = computed(() => selectedTodoTask.value?.title || '请选择一个待办任务')
const showFocusGoal = computed(() => Boolean(focusGoalTitle.value && focusGoalTitle.value !== focusActionTitle.value))
const durationProgress = computed(() => `${(selectedDurationIndex.value / Math.max(1, durationOptions.length - 1)) * 100}%`)

const stageStorageKey = computed(() => `${STAGE_STORAGE_PREFIX}.${username.value}`)
const selectedStageEntry = computed(() => stageRegistry.value[String(selectedTodoTaskId.value)] || null)
const selectedStages = computed(() => selectedStageEntry.value?.stages || [])
const activeStage = computed(() => selectedStages.value.find((stage) => stage.status === 'in_progress') || selectedStages.value.find((stage) => stage.status !== 'done') || null)
const completedStageCount = computed(() => selectedStages.value.filter((stage) => stage.status === 'done').length)
const stageProgressPercent = computed(() => selectedStages.value.length ? Math.round((completedStageCount.value / selectedStages.value.length) * 100) : 0)
const loadTaskStages = () => {
  if (typeof window === 'undefined') return
  try {
    const raw = window.localStorage.getItem(stageStorageKey.value)
    const parsed = raw ? JSON.parse(raw) : {}
    stageRegistry.value = parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch {
    stageRegistry.value = {}
  }
}

const saveTaskStages = () => {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(stageStorageKey.value, JSON.stringify(stageRegistry.value))
}

const cleanupStageRegistry = () => {
  const activeIds = new Set(todoTasks.value.map((task) => String(task.id)))
  const next = {}
  let changed = false
  Object.entries(stageRegistry.value).forEach(([taskId, entry]) => {
    if (activeIds.has(String(taskId))) next[taskId] = entry
    else changed = true
  })
  if (changed) {
    stageRegistry.value = next
    saveTaskStages()
  }
}

const removeStagesForTask = (taskId) => {
  const key = String(taskId)
  if (!stageRegistry.value[key]) return
  const next = { ...stageRegistry.value }
  delete next[key]
  stageRegistry.value = next
  saveTaskStages()
}

const normalizeStageProgress = (taskId) => {
  const key = String(taskId)
  const entry = stageRegistry.value[key]
  if (!entry?.stages?.length) return
  const stages = entry.stages.map((stage) => ({ ...stage }))
  const unfinished = stages.findIndex((stage) => stage.status !== 'done')
  if (unfinished >= 0) {
    stages.forEach((stage, index) => {
      if (stage.status !== 'done') stage.status = index === unfinished ? 'in_progress' : 'locked'
    })
  }
  stageRegistry.value = { ...stageRegistry.value, [key]: { ...entry, stages, updatedAt: new Date().toISOString() } }
  saveTaskStages()
}

const markAllStagesDone = (taskId) => {
  const key = String(taskId)
  const entry = stageRegistry.value[key]
  if (!entry?.stages?.length) return
  stageRegistry.value = {
    ...stageRegistry.value,
    [key]: { ...entry, updatedAt: new Date().toISOString(), stages: entry.stages.map((stage) => ({ ...stage, status: 'done' })) }
  }
  saveTaskStages()
}

const completeStage = (stageId) => {
  const task = selectedTodoTask.value
  const entry = selectedStageEntry.value
  if (!task || !entry?.stages?.length) return
  const stages = entry.stages.map((stage) => ({ ...stage }))
  const index = stages.findIndex((stage) => stage.id === stageId)
  if (index < 0 || stages[index].status === 'done') return
  stages[index].status = 'done'
  const nextIndex = stages.findIndex((stage, idx) => idx > index && stage.status !== 'done')
  if (nextIndex >= 0) stages[nextIndex].status = 'in_progress'
  stageRegistry.value = { ...stageRegistry.value, [String(task.id)]: { ...entry, stages, updatedAt: new Date().toISOString() } }
  saveTaskStages()
}

const buildBattlePhrase = (step, index) => {
  const description = String(step.description || step.doneDefinition || '').trim()
  if (description) return description.length > 46 ? `${description.slice(0, 46)}...` : description
  return hardlinePhrases[index % hardlinePhrases.length]
}

const fallbackStagesForTask = (taskTitle) => ([
  `拆解 ${taskTitle} 的知识边界`,
  '建立首轮执行清单',
  '攻克核心难点节点',
  '完成验证与复盘'
])

const withTimeout = (promise, timeoutMs = 24000) => Promise.race([
  promise,
  new Promise((_, reject) => window.setTimeout(() => reject(new Error('AI 拆解超时，请重试。')), timeoutMs))
])

const selectFallbackTask = () => {
  const currentExists = todoTasks.value.some((task) => String(task.id) === String(selectedTodoTaskId.value))
  if (currentExists) return
  const sameDay = visibleTasks.value.find((task) => !task.isCompleted) || visibleTasks.value[0]
  const fallback = sameDay || todoTasks.value.find((task) => !task.isCompleted) || todoTasks.value[0]
  selectedTodoTaskId.value = fallback ? String(fallback.id) : ''
}

const goTo = (path) => router.push(path)
const goProfile = () => goTo('/more')
const goMail = () => goTo('/mail')
const goHome = () => goTo('/')
const goShop = () => goTo('/shop')
const goVault = () => goTo('/vault')
const goFriends = () => goTo('/friends')
const goPlayground = () => goTo('/playground')
const goLeaderboard = () => goTo('/leaderboard')
const goPK = () => goTo('/pk')
const goCollab = () => goTo('/collab')
const goSettings = () => goTo('/more')

const enter3DCity = () => {
  dimensionStore.setDimension('PHYSICAL')
  router.push({ path: '/island', query: { dimension: 'PHYSICAL' } })
}

const enter2DCity = () => {
  dimensionStore.setDimension('GAIA')
  router.push({ path: '/island', query: { dimension: 'GAIA' } })
}

const logout = () => {
  userStore.logout()
  router.push('/login')
}

const sidebarGroups = computed(() => [
  { id: 'core', icon: '📍', title: '核心中枢', subtitle: 'FocusHub Home', active: true, action: goHome, children: [] },
  {
    id: 'world', icon: '🌍', title: '星港世界', subtitle: 'World / Maps', children: [
      { id: 'world-3d', title: '物理视界', meta: '3D 实体基地', action: enter3DCity },
      { id: 'world-2d', title: '盖亚拓扑', meta: '2D 数据网格地图', action: enter2DCity }
    ]
  },
  {
    id: 'vault', icon: '🎒', title: '工程装配仓与商城', subtitle: 'Vault & Shop', children: [
      { id: 'vault-home', title: '工程装配仓', meta: '已获得建筑 / 装备', action: goVault },
      { id: 'shop-home', title: '星际商城', meta: '购买建筑 / 装备', action: goShop }
    ]
  },
  {
    id: 'fleet', icon: '🛰️', title: '舰队枢纽', subtitle: 'Social / Hub', children: [
      { id: 'fleet-mail', title: '星际信箱', meta: mailUnread.value ? `${mailUnread.value} 未读` : '通知站', action: goMail, badge: mailUnread.value },
      { id: 'fleet-friends', title: '好友竞技', meta: '好友 / PK', action: goFriends },
      { id: 'fleet-rank', title: '舰队排行', meta: 'Leaderboard', action: goLeaderboard },
      { id: 'fleet-collab', title: '联合星桥', meta: 'Social Timer', action: goCollab },
      { id: 'fleet-pk', title: '竞技场', meta: 'PK Challenge', action: goPK }
    ]
  },
  { id: 'play', icon: '🎮', title: '娱乐仓', subtitle: 'Recreation Bay', children: [{ id: 'playground', title: '娱乐大厅', meta: '小游戏 / 对战', action: goPlayground }] }
])

const loadAvatarProfile = async () => {
  const currentUser = String(userStore.username || '').trim()
  if (!currentUser || currentUser === 'guest') {
    userAvatar.value = ''
    userNickname.value = ''
    return
  }
  try {
    const response = await axios.get(`/api/user/${currentUser}/avatar`)
    const payload = response?.data || {}
    userAvatar.value = String(payload.avatar || userStore.avatar || '')
    userNickname.value = String(payload.nickname || '')
  } catch {
    userAvatar.value = String(userStore.avatar || '')
    userNickname.value = ''
  }
}

const loadTodoTasks = async () => {
  isTaskLoading.value = true
  taskError.value = ''
  try {
    const response = await taskApi.list(username.value)
    todoTasks.value = (response.data?.tasks || []).map(normalizeTask).filter((task) => task.id && task.title)
    cleanupStageRegistry()
    selectFallbackTask()
  } catch (error) {
    console.error('Failed to load todo tasks', error)
    taskError.value = '任务同步失败，请稍后重试。'
  } finally {
    isTaskLoading.value = false
  }
}

const openTaskModal = (dateKey = selectedDateKey.value) => {
  taskForm.value = { content: '', scheduledDate: normalizeDateKey(dateKey || todayDateKey()), scheduledTime: '10:00', category: 'FocusPort', accent: '#4880FF' }
  taskError.value = ''
  taskModalOpen.value = true
}

const closeTaskModal = () => { taskModalOpen.value = false }

const createTodoTask = async () => {
  const content = String(taskForm.value.content || '').trim()
  const scheduledDate = normalizeDateKey(taskForm.value.scheduledDate, selectedDateKey.value || todayDateKey())
  if (!content) {
    taskError.value = '请输入任务内容。'
    return
  }
  isTaskSubmitting.value = true
  taskError.value = ''
  try {
    const response = await taskApi.add(username.value, content, {
      scheduledDate,
      scheduledTime: taskForm.value.scheduledTime || '',
      status: 'todo',
      category: taskForm.value.category || '',
      accent: taskForm.value.accent || '#4880FF'
    })
    const created = normalizeTask(response.data?.task || { id: response.data?.task_id, content, scheduled_date: scheduledDate, scheduled_time: taskForm.value.scheduledTime, category: taskForm.value.category, accent: taskForm.value.accent })
    todoTasks.value = [created, ...todoTasks.value.filter((task) => task.id !== created.id)]
    selectedDateKey.value = created.scheduledDate
    selectedTodoTaskId.value = String(created.id)
    closeTaskModal()
  } catch (error) {
    console.error('Failed to create todo task', error)
    taskError.value = error.response?.data?.detail || '任务创建失败。'
  } finally {
    isTaskSubmitting.value = false
  }
}

const selectDate = (dateKey) => {
  selectedDateKey.value = normalizeDateKey(dateKey)
  selectedTodoTaskId.value = ''
  selectFallbackTask()
}

const selectToday = () => {
  selectDate(todayDateKey())
  monthCursor.value = new Date()
}

const shiftMonth = (delta) => {
  const next = new Date(monthCursor.value)
  next.setMonth(monthCursor.value.getMonth() + delta)
  monthCursor.value = new Date(next.getFullYear(), next.getMonth(), 1)
}

const selectTask = (task) => {
  selectedTodoTaskId.value = String(task.id)
  selectedDateKey.value = task.scheduledDate
}

const handleDurationSelect = (minutes) => {
  if (focusHubStore.pomodoro.isRunning || isStartingFocus.value) return
  const closestIndex = durationOptions.reduce((bestIndex, option, index) => Math.abs(option - Number(minutes)) < Math.abs(durationOptions[bestIndex] - Number(minutes)) ? index : bestIndex, 0)
  selectedDurationIndex.value = closestIndex
  selectedDuration.value = durationOptions[closestIndex]
}

const handleDurationDrag = (event) => { handleDurationSelect(durationOptions[Number(event.target.value)] || selectedDuration.value) }
const handleStartFocus = async () => {
  if (focusActionDisabled.value) return
  isStartingFocus.value = true
  try {
    if (focusHubStore.pomodoro.pendingSettlement) focusHubStore.skipSettlement()
    activeFocusTodoId.value = String(selectedTodoTaskId.value || '')
    focusHubStore.startPomodoro()
    await new Promise((resolve) => window.setTimeout(resolve, 240))
  } finally {
    isStartingFocus.value = false
  }
}

const handleToggleFocus = () => {
  if (focusHubStore.pomodoro.isRunning) {
    focusHubStore.pausePomodoro()
    return
  }
  handleStartFocus()
}

const handleAbortFocus = () => {
  focusHubStore.pausePomodoro()
  focusHubStore.resetPomodoro()
  activeFocusTodoId.value = ''
}

const markTaskDone = async (taskId) => {
  const target = todoTasks.value.find((task) => String(task.id) === String(taskId))
  if (!target || target.isCompleted) return
  const response = await taskApi.toggle(target.id, username.value)
  const updated = normalizeTask(response.data?.task || { ...target, is_completed: true, status: 'done' })
  todoTasks.value = todoTasks.value.map((task) => (task.id === updated.id ? updated : task))
  if (updated.isCompleted) markAllStagesDone(updated.id)
}

const toggleTaskCompletion = async (task, event) => {
  event?.stopPropagation?.()
  if (!task) return
  try {
    const response = await taskApi.toggle(task.id, username.value)
    const updated = normalizeTask(response.data?.task || { ...task, is_completed: !task.isCompleted, status: task.isCompleted ? 'todo' : 'done' })
    todoTasks.value = todoTasks.value.map((item) => (item.id === updated.id ? updated : item))
    if (updated.isCompleted) markAllStagesDone(updated.id)
    else normalizeStageProgress(updated.id)
  } catch (error) {
    console.error('failed to toggle task', error)
    taskError.value = error.response?.data?.detail || '任务状态更新失败。'
  }
}

const deleteTodoTask = async (task, event) => {
  event?.stopPropagation?.()
  if (!task || deletingTaskId.value) return
  deletingTaskId.value = String(task.id)
  taskError.value = ''
  try {
    await taskApi.delete(task.id, username.value)
    todoTasks.value = todoTasks.value.filter((item) => item.id !== task.id)
    removeStagesForTask(task.id)
    if (String(selectedTodoTaskId.value) === String(task.id)) selectedTodoTaskId.value = ''
    selectFallbackTask()
  } catch (error) {
    console.error('failed to delete task', error)
    taskError.value = error.response?.data?.detail || '任务删除失败。'
  } finally {
    deletingTaskId.value = ''
  }
}
const handleCompleteFocusQuick = async () => {
  const targetTaskId = activeFocusTodoId.value || selectedTodoTaskId.value
  focusHubStore.pausePomodoro()
  try {
    await focusApi.complete(username.value, focusHubStore.pomodoro.focusMinutes, focusSubject.value, '', focusHubStore.pomodoro.taskDifficulty)
    await markTaskDone(targetTaskId)
  } catch (error) {
    console.error('quick focus completion failed', error)
    try { await markTaskDone(targetTaskId) } catch (taskErrorValue) { console.error('failed to mark todo task complete', taskErrorValue) }
  }
  activeFocusTodoId.value = ''
  focusHubStore.resetPomodoro()
}

const statusLabel = (task) => {
  if (task.isCompleted || task.status === 'done') return 'Done'
  if (String(task.id) === String(selectedTodoTaskId.value) && focusHubStore.pomodoro.isRunning) return 'In Progress'
  return task.status === 'in_progress' ? 'In Progress' : 'To-do'
}
const statusClass = (task) => statusLabel(task) === 'Done' ? 'done' : statusLabel(task) === 'In Progress' ? 'progress' : 'todo'

const handleAIDecompose = async () => {
  const task = selectedTodoTask.value
  if (!task || decomposeState.value === 'loading') return
  decomposeState.value = 'loading'
  decomposeError.value = ''
  try {
    const steps = await withTimeout(decomposeGoal({ goal: task.title || '', style: intensityStyleMap[decomposeIntensity.value] || 'balanced', availableMinutes: selectedDuration.value }))
    const sourceSteps = Array.isArray(steps) && steps.length ? steps : fallbackStagesForTask(task.title).map((title) => ({ title, estimatedPomodoros: 1 }))
    const stages = sourceSteps.slice(0, 7).map((step, index) => ({
      id: String(step.id || `stage-${Date.now()}-${index}`),
      node: `Node ${String(index + 1).padStart(2, '0')}`,
      title: String(step.title || step.task || `战术节点 ${index + 1}`).trim(),
      status: index === 0 ? 'in_progress' : 'locked',
      battlePhrase: buildBattlePhrase(step, index),
      estimatedPomodoros: Math.max(1, Math.min(3, Number(step.estimatedPomodoros || 1)))
    }))
    stageRegistry.value = { ...stageRegistry.value, [String(task.id)]: { taskId: String(task.id), updatedAt: new Date().toISOString(), intensity: decomposeIntensity.value, stages } }
    saveTaskStages()
    decomposeState.value = 'ready'
  } catch (err) {
    decomposeError.value = String(err?.message || err || 'AI 拆解失败，请重试。')
    decomposeState.value = 'error'
  }
}

const stageStatusLabel = (stage) => stage.status === 'done' ? '✅ 已完成' : stage.status === 'in_progress' ? '⚡ 进行中' : '🔒 待激活'

const openAuditModal = () => {
  auditModalOpen.value = true
  auditMessage.value = ''
}
const closeAuditModal = () => { auditModalOpen.value = false }
const resetAuditFlow = () => {
  auditSelectedFile.value = null
  auditPreview.value = ''
  auditResult.value = null
  auditMinutes.value = 0
  auditCategory.value = '学习'
  auditNotes.value = ''
  auditState.value = 'idle'
  auditMessage.value = ''
}

const handleAuditFileSelect = (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  auditSelectedFile.value = file
  auditResult.value = null
  auditState.value = 'idle'
  auditMessage.value = ''
  const reader = new FileReader()
  reader.onload = (loadEvent) => { auditPreview.value = String(loadEvent.target?.result || '') }
  reader.readAsDataURL(file)
}

const analyzeAuditScreenshot = async () => {
  if (!auditSelectedFile.value || auditState.value === 'analyzing') return
  auditState.value = 'analyzing'
  auditMessage.value = ''
  try {
    const response = await phoneApi.analyzeScreenshot(auditSelectedFile.value, username.value)
    const result = response.data || {}
    auditResult.value = result
    auditMinutes.value = Math.max(0, Number(result.total_minutes || 0))
    auditCategory.value = String(result.top_category || auditCategory.value || '学习')
    auditState.value = 'audit'
  } catch (error) {
    console.error('phone screenshot analysis failed', error)
    auditState.value = 'audit'
    auditMessage.value = error.response?.data?.detail || 'AI 扫描未完成，请手动校正分钟数。'
  }
}

const submitAuditReport = async () => {
  const minutes = Math.max(0, Number(auditMinutes.value || 0))
  if (!minutes) {
    auditMessage.value = '请输入有效的手机使用分钟数。'
    return
  }
  auditState.value = 'submitting'
  auditMessage.value = ''
  try {
    await phoneApi.report(username.value, minutes, auditCategory.value, auditNotes.value)
    await growthApi.updateDiscipline(username.value, minutes)
    await userStore.loadGrowth()
    auditMessage.value = 'Audit confirmed. 自律指数已刷新。'
    auditState.value = 'done'
    window.setTimeout(() => {
      closeAuditModal()
      resetAuditFlow()
    }, 900)
  } catch (error) {
    console.error('phone audit submit failed', error)
    auditState.value = 'audit'
    auditMessage.value = error.response?.data?.detail || 'Audit 提交失败，请稍后重试。'
  }
}

const anyModalOpen = computed(() => taskModalOpen.value || calendarModalOpen.value || auditModalOpen.value)

onMounted(async () => {
  try {
    focusHubStore.hydrate(userStore.username)
    dimensionStore.rehydrate()
    handleDurationSelect(Number(focusHubStore.pomodoro.focusMinutes) || 25)
    selectedDateKey.value = todayDateKey()
    taskForm.value.scheduledDate = selectedDateKey.value
    loadTaskStages()
    await Promise.all([loadAvatarProfile(), loadTodoTasks(), userStore.loadGrowth()])
  } catch (error) {
    console.error('FocusHub init failed:', error)
    initError.value = error instanceof Error ? error.message : 'Unknown initialization error'
  } finally {
    isActionHydrating.value = false
  }
})

watch(selectedDuration, (minutes) => { focusHubStore.setFocusMinutes(minutes) })
watch(() => userStore.username, async () => {
  loadTaskStages()
  await Promise.all([loadAvatarProfile(), loadTodoTasks(), userStore.loadGrowth()])
})
watch(anyModalOpen, (open) => { document.body.style.overflow = open ? 'hidden' : '' })
watch(selectedDateKey, () => { selectFallbackTask() })
watch(auditModalOpen, (open) => { if (!open) resetAuditFlow() })
onUnmounted(() => { document.body.style.overflow = '' })
</script>

<template>
  <div class="focus-home-shell" :class="{ 'is-focus-mode': isFocusMode }">
    <div v-if="initError" class="focus-init-error">
      <div class="focus-init-error-card">
        <p>FocusHub Init Error</p>
        <h2>Home failed to initialize</h2>
        <span>{{ initError }}</span>
        <div><button type="button" @click="loadTodoTasks">Retry tasks</button><button type="button" @click="goHome">Go home</button></div>
      </div>
    </div>

    <section v-if="isFocusMode" class="focus-mode-shell">
      <header class="focus-mode-header"><div class="focus-mode-status"><span /> Focus mode</div><div class="focus-mode-actions"><button type="button" @click="handleAbortFocus">退出专注</button></div></header>
      <main class="focus-mode-main">
        <section class="focus-mode-panel">
          <div class="focus-mode-goal"><p v-if="showFocusGoal">{{ focusGoalTitle }}</p><h2>{{ focusActionTitle }}</h2></div>
          <p class="focus-mode-time">{{ formattedRemaining.slice(0, 2) }}<span>:</span>{{ formattedRemaining.slice(3, 5) }}</p>
          <article class="focus-mode-task"><p>Now Focusing</p><h3>{{ focusActionTitle }}</h3></article>
          <div class="focus-mode-controls">
            <button type="button" class="danger" title="Abort focus" @click="handleAbortFocus"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 18 18 6M6 6l12 12" stroke-linecap="round" /></svg></button>
            <button type="button" class="primary" :title="focusHubStore.pomodoro.isRunning ? 'Pause' : 'Resume'" @click="handleToggleFocus"><svg v-if="focusHubStore.pomodoro.isRunning" viewBox="0 0 24 24" fill="currentColor"><path d="M7 5h3v14H7zm7 0h3v14h-3z" /></svg><svg v-else viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z" /></svg></button>
            <button type="button" class="success" title="Complete focus" @click="handleCompleteFocusQuick"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m5 13 4 4L19 7" stroke-linecap="round" stroke-linejoin="round" /></svg></button>
          </div>
        </section>
      </main>
    </section>

    <template v-else>
      <aside class="vision-sidebar">
        <button type="button" class="vision-logo" @click="goHome"><span>FP</span><strong>FOCUSPORT</strong><small>VISION UI</small></button>
        <nav class="vision-menu" aria-label="FocusHub navigation">
          <section v-for="group in sidebarGroups" :key="group.id" class="menu-group" :class="{ active: group.active }">
            <button type="button" class="menu-main" @click="group.action?.()"><span class="menu-emoji">{{ group.icon }}</span><span><strong>{{ group.title }}</strong><small>{{ group.subtitle }}</small></span></button>
            <div v-if="group.children.length" class="menu-children">
              <button v-for="entry in group.children" :key="entry.id" type="button" @click="entry.action"><span><strong>{{ entry.title }}</strong><small>{{ entry.meta }}</small></span><b v-if="entry.badge" class="menu-badge">{{ entry.badge > 99 ? '99+' : entry.badge }}</b></button>
            </div>
          </section>
        </nav>
        <div class="sidebar-footer"><button type="button" @click="goSettings">设置 / 个人中心</button><button type="button" class="logout-link" @click="logout">退出登录</button></div>
      </aside>
      <main class="vision-main">
        <header class="vision-topbar">
          <div class="mission-copy"><p>CORE COMMAND CENTER</p><h1>FocusHub Home</h1><span>降噪，拆解，跃迁。今天的执行链路已经展开。</span></div>
          <div class="topbar-cluster">
            <article class="metric-card"><span>算力 CU</span><strong>{{ computeUnits.toLocaleString() }}</strong><small>专注收益储备</small></article>
            <article class="metric-card energy"><span>专注能量</span><strong>{{ focusEnergy }}</strong><small>Focus Energy</small></article>
            <button type="button" class="metric-card discipline" @click="openAuditModal"><span>自律指数</span><strong>{{ disciplineScore.toFixed(1) }}</strong><small>上传手机截图提升校准</small></button>
            <button type="button" class="mail-chip" @click="goMail"><svg viewBox="0 0 24 24"><path d="M4 6h16v12H4z" /><path d="m4 8 8 6 8-6" /></svg><b v-if="mailUnread">{{ mailUnread > 99 ? '99+' : mailUnread }}</b></button>
            <button type="button" class="avatar-chip" @click="goProfile"><span><img v-if="avatarIsImage" :src="avatarToken" alt="avatar"><b v-else>{{ avatarToken }}</b></span><strong>{{ displayName }}</strong></button>
          </div>
        </header>

        <section class="vision-dashboard-grid">
          <article class="welcome-card glass-card"><p>Welcome back!</p><h2>{{ displayName }}</h2><span>当前任务：{{ focusActionTitle }}</span><div class="welcome-progress"><small>今日执行链路</small><strong>{{ visibleTasks.filter(task => task.isCompleted).length }} / {{ visibleTasks.length || 0 }}</strong></div></article>

          <article class="pomodoro-card glass-card">
            <div class="card-heading"><span>番茄钟</span><strong>{{ selectedDuration }} min</strong></div>
            <div class="timer-layout">
              <div class="timer-ring-xl"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" :r="ringRadius" /><circle cx="60" cy="60" :r="ringRadius" :stroke-dasharray="ringCircumference" :stroke-dashoffset="ringOffset" /></svg><span>{{ progressPercent }}%</span></div>
              <div class="timer-copy"><strong>{{ formattedRemaining }}</strong><small>{{ selectedTaskIsDone ? '已完成任务不可再次启动' : focusActionTitle }}</small><button type="button" :disabled="focusActionDisabled" :title="selectedTaskIsDone ? '已完成任务不能再启动番茄钟' : focusActionLabel" @click="handleToggleFocus">{{ focusActionLabel }}</button></div>
            </div>
            <div class="duration-slider" :class="{ locked: focusHubStore.pomodoro.isRunning || isStartingFocus }" :style="{ '--duration-progress': durationProgress }">
              <input v-model.number="selectedDurationIndex" type="range" min="0" :max="durationOptions.length - 1" step="1" :disabled="focusHubStore.pomodoro.isRunning || isStartingFocus" aria-label="Pomodoro duration" @input="handleDurationDrag" @change="handleDurationDrag">
              <div class="duration-ticks" aria-hidden="true"><button v-for="(m, index) in durationOptions" :key="m" type="button" :class="{ active: selectedDurationIndex === index }" :disabled="focusHubStore.pomodoro.isRunning || isStartingFocus" @click="handleDurationSelect(m)"><span /><b>{{ m }}</b></button></div>
            </div>
          </article>

          <button type="button" class="calendar-mini glass-card" @click="calendarModalOpen = true">
            <header><span>日历缩略图</span><strong>{{ monthTitle }}</strong></header>
            <div class="mini-calendar-grid"><i v-for="cell in calendarPreviewCells" :key="cell.dateKey" :class="{ today: cell.isToday, selected: cell.isSelected, muted: !cell.inMonth, busy: cell.tasks.length }">{{ cell.day }}</i></div>
            <small>{{ selectedDateKey }} · {{ visibleTasks.length }} 个日程</small>
          </button>
        </section>

        <section class="workbench-grid">
          <article class="todo-panel glass-card">
            <header class="panel-heading"><div><p>TO-DO LIST</p><h2>任务队列</h2></div><button type="button" @click="openTaskModal()">+ 添加任务</button></header>
            <div class="date-strip"><button type="button" @click="selectToday">Today</button><button type="button" @click="calendarModalOpen = true">{{ selectedDateKey }}</button></div>
            <div class="task-list-scroll">
              <button v-for="task in visibleTasks" :key="task.id" type="button" class="todo-card" :class="{ selected: String(task.id) === String(selectedTodoTaskId), completed: task.isCompleted }" @click="selectTask(task)">
                <span class="task-accent" :style="{ background: task.accent }" />
                <span class="todo-body"><small>{{ task.category }} · {{ task.scheduledTime || 'Today' }}</small><strong>{{ task.title }}</strong><em :class="statusClass(task)">{{ statusLabel(task) }}</em></span>
                <span class="todo-actions"><i role="button" tabindex="0" @click="toggleTaskCompletion(task, $event)">{{ task.isCompleted ? '↺' : '✓' }}</i><i role="button" tabindex="0" @click="deleteTodoTask(task, $event)">{{ deletingTaskId === String(task.id) ? '...' : '×' }}</i></span>
              </button>
              <div v-if="isTaskLoading" class="empty-task-state">任务同步中...</div>
              <div v-else-if="!visibleTasks.length" class="empty-task-state"><strong>暂无任务</strong><span>{{ selectedDateKey }} 还没有待办，添加一个战术节点吧。</span></div>
            </div>
            <p v-if="taskError" class="task-error">{{ taskError }}</p>
          </article>

          <article class="stages-panel glass-card">
            <header class="panel-heading"><div><p>AI TASK DECOMPOSE</p><h2>阶段序列</h2></div><div class="intensity-control" aria-label="AI 拆解强度"><button v-for="value in ['weak', 'medium', 'strong']" :key="value" type="button" :class="{ active: decomposeIntensity === value }" @click="decomposeIntensity = value">{{ intensityLabels[value] }}</button></div></header>
            <div class="selected-task-banner"><span>{{ selectedTodoTask?.category || 'No Task' }}</span><strong>{{ selectedTodoTask?.title || '请选择一个 To-do 任务' }}</strong><small v-if="selectedStages.length">{{ completedStageCount }}/{{ selectedStages.length }} nodes · {{ stageProgressPercent }}%</small><small v-else>点击 AI 帮助拆解任务，生成战术节点。</small></div>
            <div class="stage-actions"><button type="button" :disabled="!selectedTodoTask || decomposeState === 'loading'" @click="handleAIDecompose">{{ decomposeState === 'loading' ? '战术节点扫描中' : selectedStages.length ? '重新 AI 拆解' : 'AI 帮助拆解任务' }}</button><span v-if="activeStage">当前：{{ activeStage.node }}</span></div>
            <div v-if="decomposeState === 'loading'" class="scan-loader"><div v-for="index in 5" :key="index" class="scan-line"><span /> <b /></div><p>Starport OS 正在扫描任务结构...</p></div>
            <div v-else-if="decomposeState === 'error'" class="stage-error"><strong>AI 拆解失败</strong><span>{{ decomposeError }}</span><button type="button" @click="handleAIDecompose">重试拆解</button></div>
            <div v-else-if="selectedStages.length" class="stage-table">
              <div class="stage-row header"><span>Node</span><span>战术节点名称</span><span>状态</span><span>建议配词</span></div>
              <button v-for="stage in selectedStages" :key="stage.id" type="button" class="stage-row" :class="stage.status" :disabled="stage.status === 'locked'" @click="completeStage(stage.id)"><span>{{ stage.node }}</span><strong>{{ stage.title }}</strong><em>{{ stageStatusLabel(stage) }}</em><small>{{ stage.battlePhrase }}</small></button>
            </div>
            <div v-else class="stage-empty"><strong>示例：学习高数</strong><span>Node 01 · 矩阵运算与线性方程组 · ✅ 已完成</span><span>Node 02 · 向量空间与基变换 · ⚡ 进行中</span><span>Node 03 · 行列式与逆矩阵 · 🔒 待激活</span></div>
          </article>
        </section>
      </main>
      <div v-if="taskModalOpen" class="glass-modal-overlay" @click.self="closeTaskModal">
        <form class="glass-modal task-modal" @submit.prevent="createTodoTask">
          <header><div><p>TACTICAL NODE</p><h3>新建任务</h3></div><button type="button" aria-label="关闭弹窗" @click="closeTaskModal">×</button></header>
          <label><span>任务</span><input v-model="taskForm.content" type="text" maxlength="80" placeholder="例如：学习高数"></label>
          <div class="modal-grid"><label><span>日期</span><input v-model="taskForm.scheduledDate" type="date" pattern="\d{4}-\d{2}-\d{2}"></label><label><span>时间</span><input v-model="taskForm.scheduledTime" type="time"></label></div>
          <label><span>分类</span><input v-model="taskForm.category" type="text" maxlength="28" placeholder="FocusPort"></label>
          <div class="accent-row" aria-label="任务颜色"><button v-for="accent in accentOptions" :key="accent" type="button" :aria-label="`选择颜色 ${accent}`" :class="{ active: taskForm.accent === accent }" :style="{ backgroundColor: accent }" @click="taskForm.accent = accent" /></div>
          <p v-if="taskError" class="task-error">{{ taskError }}</p>
          <footer><button type="button" class="ghost" @click="closeTaskModal">取消</button><button type="submit" :disabled="isTaskSubmitting">{{ isTaskSubmitting ? '创建中' : '创建任务' }}</button></footer>
        </form>
      </div>

      <div v-if="calendarModalOpen" class="glass-modal-overlay" @click.self="calendarModalOpen = false">
        <section class="glass-modal calendar-modal">
          <header><div><p>CALENDAR MATRIX</p><h3>{{ monthTitle }}</h3></div><button type="button" aria-label="关闭日历" @click="calendarModalOpen = false">×</button></header>
          <div class="calendar-toolbar"><button type="button" @click="selectToday">Today</button><div><button type="button" aria-label="Previous month" @click="shiftMonth(-1)">‹</button><button type="button" aria-label="Next month" @click="shiftMonth(1)">›</button></div><button type="button" @click="openTaskModal(selectedDateKey)">+ Add New Event</button></div>
          <div class="calendar-weekdays"><span v-for="label in weekdayLabels" :key="label">{{ label }}</span></div>
          <div class="calendar-grid">
            <button v-for="cell in calendarCells" :key="cell.dateKey" type="button" class="calendar-cell" :class="{ muted: !cell.inMonth, today: cell.isToday, selected: cell.isSelected }" @click="selectDate(cell.dateKey)">
              <span class="day-number">{{ cell.day }}</span>
              <span v-for="task in cell.tasks.slice(0, 2)" :key="task.id" class="calendar-event" :class="{ done: task.isCompleted }" :style="{ '--event-color': task.accent }">{{ task.title }}</span>
              <span v-if="cell.tasks.length > 2" class="calendar-more">+{{ cell.tasks.length - 2 }}</span>
            </button>
          </div>
        </section>
      </div>

      <div v-if="auditModalOpen" class="glass-modal-overlay" @click.self="closeAuditModal">
        <section class="glass-modal audit-modal">
          <header><div><p>DISCIPLINE AUDIT</p><h3>手机截图校准</h3></div><button type="button" aria-label="关闭 Audit" @click="closeAuditModal">×</button></header>
          <div class="audit-layout">
            <label class="audit-upload" :class="{ ready: auditPreview }"><input type="file" accept="image/*" @change="handleAuditFileSelect"><img v-if="auditPreview" :src="auditPreview" alt="手机截图预览"><span v-else><b>上传终端截图</b><small>支持 iOS / Android 屏幕使用时间截图</small></span></label>
            <div class="audit-panel">
              <p class="audit-copy">AI scan detected: <strong>{{ auditMinutes || 0 }} mins</strong>. Awaiting Commander validation.</p>
              <button type="button" class="audit-scan" :disabled="!auditSelectedFile || auditState === 'analyzing'" @click="analyzeAuditScreenshot">{{ auditState === 'analyzing' ? '扫描中...' : 'AI 扫描截图' }}</button>
              <div v-if="auditResult" class="audit-result"><span>主要分类：{{ auditResult.top_category || auditCategory }}</span><small>{{ auditResult.summary || '请校正后确认提交。' }}</small></div>
              <label><span>校正分钟数</span><input v-model.number="auditMinutes" type="number" min="0" max="1440" placeholder="分钟"></label>
              <label><span>分类</span><select v-model="auditCategory"><option v-for="item in auditCategories" :key="item" :value="item">{{ item }}</option></select></label>
              <label><span>备注</span><textarea v-model="auditNotes" rows="3" placeholder="可选，记录今天的干扰源" /></label>
            </div>
          </div>
          <p v-if="auditMessage" class="audit-message">{{ auditMessage }}</p>
          <footer><button type="button" class="ghost" @click="closeAuditModal">取消</button><button type="button" :disabled="auditState === 'submitting'" @click="submitAuditReport">{{ auditState === 'submitting' ? '提交中' : '确认 Audit' }}</button></footer>
        </section>
      </div>
    </template>
  </div>
</template>
<style scoped>
.focus-home-shell {
  --vision-bg: #060b26;
  --vision-panel: rgba(6, 11, 40, 0.82);
  --vision-line: rgba(226, 232, 240, 0.16);
  --vision-blue: #0075ff;
  --vision-blue-2: #4880ff;
  --vision-text: #ffffff;
  --vision-muted: #a0aec0;
  min-height: 100vh;
  width: 100%;
  overflow: hidden;
  color: var(--vision-text);
  background: radial-gradient(circle at 50% 28%, rgba(0,117,255,.86), transparent 33%), radial-gradient(circle at 82% 14%, rgba(24,206,255,.18), transparent 28%), linear-gradient(166deg, #0f123b 14%, #090d2e 56%, #020515 86%);
  font-family: "Plus Jakarta Sans", "Noto Sans SC", "Microsoft YaHei", sans-serif;
}
.focus-home-shell::before { content: ""; position: fixed; inset: -20%; pointer-events: none; background: linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.03) 1px, transparent 1px); background-size: 64px 64px; opacity: .22; mask-image: radial-gradient(circle at 54% 42%, #000 0, transparent 72%); }
button,input,select,textarea { font: inherit; }
button { cursor: pointer; }
button:disabled { cursor: not-allowed; }
.glass-card,.glass-modal,.vision-sidebar { border: 1px solid var(--vision-line); background: linear-gradient(145deg, rgba(6,11,40,.92), rgba(10,14,35,.54)); box-shadow: 0 24px 80px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.1); backdrop-filter: blur(34px); -webkit-backdrop-filter: blur(34px); }
.vision-sidebar { position: fixed; inset: 10px auto 10px 10px; z-index: 42; width: 264px; display: flex; flex-direction: column; overflow: hidden; border-radius: 20px; }
.vision-logo { display: grid; grid-template-columns: 42px 1fr; gap: 12px; align-items: center; margin: 18px 16px 14px; padding: 12px; color: white; border: 0; border-bottom: 1px solid rgba(255,255,255,.14); background: transparent; text-align: left; }
.vision-logo span { grid-row: span 2; display: grid; width: 42px; height: 42px; place-items: center; border-radius: 16px; background: linear-gradient(135deg, #0075ff, #845ef7); font-weight: 950; }
.vision-logo strong { font-size: 13px; letter-spacing: .22em; }
.vision-logo small { color: var(--vision-muted); font-size: 11px; letter-spacing: .14em; }
.vision-menu { flex: 1; overflow-y: auto; padding: 4px 12px 16px; }
.vision-menu::-webkit-scrollbar,.task-list-scroll::-webkit-scrollbar,.stage-table::-webkit-scrollbar { width: 4px; }
.vision-menu::-webkit-scrollbar-thumb,.task-list-scroll::-webkit-scrollbar-thumb,.stage-table::-webkit-scrollbar-thumb { border-radius: 99px; background: rgba(72,128,255,.5); }
.menu-group { margin-bottom: 10px; border-radius: 18px; padding: 6px; }
.menu-group.active { background: rgba(255,255,255,.055); }
.menu-main,.menu-children button,.sidebar-footer button { width: 100%; border: 0; color: white; background: transparent; text-align: left; }
.menu-main { display: grid; grid-template-columns: 34px 1fr; gap: 10px; align-items: center; min-height: 54px; padding: 8px 10px; border-radius: 15px; }
.menu-group.active .menu-main { background: rgba(0,117,255,.18); }
.menu-emoji { display: grid; width: 30px; height: 30px; place-items: center; border-radius: 12px; background: #1a1f37; font-size: 15px; }
.menu-main strong,.menu-main small,.menu-children strong,.menu-children small { display: block; }
.menu-main strong { font-size: 13px; line-height: 1.3; }
.menu-main small,.menu-children small { margin-top: 2px; color: var(--vision-muted); font-size: 10px; }
.menu-children { display: grid; gap: 4px; padding: 0 4px 4px 44px; }
.menu-children button { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 10px; min-height: 40px; padding: 8px 10px; border-radius: 12px; }
.menu-children button:hover,.sidebar-footer button:hover { background: rgba(255,255,255,.07); }
.menu-badge { min-width: 22px; border-radius: 999px; padding: 2px 7px; background: #f93c65; color: white; font-size: 10px; text-align: center; }
.sidebar-footer { display: grid; gap: 8px; padding: 14px 16px 18px; }
.sidebar-footer button { border-radius: 14px; padding: 12px; background: rgba(255,255,255,.055); font-size: 12px; font-weight: 800; }
.sidebar-footer .logout-link { color: #ffb4bf; }
.vision-main { position: relative; z-index: 1; min-height: 100vh; margin-left: 288px; padding: 26px 28px 34px; }
.vision-topbar { display: grid; grid-template-columns: minmax(260px,1fr) auto; gap: 24px; align-items: center; margin-bottom: 24px; }
.mission-copy p,.panel-heading p,.card-heading span,.metric-card span,.calendar-mini header span,.glass-modal header p { margin: 0; color: rgba(209,226,255,.64); font-size: 11px; font-weight: 900; letter-spacing: .18em; text-transform: uppercase; }
.mission-copy h1 { margin: 6px 0 5px; font-size: clamp(28px,3vw,42px); line-height: 1; letter-spacing: -.04em; }
.mission-copy span { color: var(--vision-muted); font-size: 14px; }
.topbar-cluster { display: flex; align-items: center; gap: 12px; min-width: 0; }
.metric-card,.mail-chip,.avatar-chip { border: 1px solid rgba(226,232,240,.14); background: rgba(6,11,40,.72); color: white; border-radius: 18px; box-shadow: 0 18px 46px rgba(0,0,0,.18); }
.metric-card { display: grid; min-width: 142px; gap: 4px; padding: 14px 16px; text-align: left; }
.metric-card strong { font-size: 22px; line-height: 1; }
.metric-card small { color: var(--vision-muted); font-size: 11px; }
.metric-card.discipline { background: linear-gradient(145deg, rgba(0,117,255,.28), rgba(6,11,40,.76)); }
.mail-chip { position: relative; display: grid; width: 46px; height: 46px; place-items: center; }
.mail-chip svg,.avatar-chip svg { width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.mail-chip b { position: absolute; top: -6px; right: -6px; display: grid; min-width: 20px; height: 20px; place-items: center; border-radius: 99px; background: #f93c65; font-size: 10px; }
.avatar-chip { display: flex; align-items: center; gap: 10px; min-height: 48px; padding: 5px 12px 5px 5px; }
.avatar-chip span { display: grid; width: 38px; height: 38px; place-items: center; overflow: hidden; border-radius: 14px; background: linear-gradient(135deg,#0075ff,#845ef7); }
.avatar-chip img { width: 100%; height: 100%; object-fit: cover; }
.avatar-chip strong { max-width: 120px; overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.vision-dashboard-grid { display: grid; grid-template-columns: minmax(240px,.8fr) minmax(360px,1fr) minmax(300px,.75fr); gap: 18px; margin-bottom: 18px; }
.glass-card { border-radius: 24px; }
.welcome-card { min-height: 248px; padding: 28px; background: radial-gradient(circle at 75% 10%, rgba(255,255,255,.22), transparent 32%), linear-gradient(135deg, rgba(132,94,247,.94), rgba(0,117,255,.82)); }
.welcome-card p,.welcome-card h2,.welcome-card span,.welcome-card small,.welcome-card strong { display: block; margin: 0; }
.welcome-card p { font-size: 28px; font-weight: 900; }
.welcome-card h2 { margin-top: 10px; font-size: 18px; }
.welcome-card > span { margin-top: 12px; color: rgba(255,255,255,.78); font-size: 13px; line-height: 1.7; }
.welcome-progress { margin-top: 42px; border-radius: 16px; padding: 14px 18px; background: rgba(6,11,40,.74); }
.welcome-progress small { color: rgba(255,255,255,.58); }
.welcome-progress strong { margin-top: 5px; font-size: 26px; }
.pomodoro-card { min-height: 248px; padding: 24px; }
.card-heading,.panel-heading,.calendar-mini header,.glass-modal header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.card-heading strong { color: #fff; font-size: 13px; }
.timer-layout { display: grid; grid-template-columns: 124px 1fr; gap: 24px; align-items: center; margin-top: 18px; }
.timer-ring-xl { position: relative; width: 124px; height: 124px; }
.timer-ring-xl svg { width: 124px; height: 124px; transform: rotate(-90deg); }
.timer-ring-xl circle { fill: none; stroke-width: 10; }
.timer-ring-xl circle:first-child { stroke: rgba(255,255,255,.1); }
.timer-ring-xl circle:last-child { stroke: #00d2a8; stroke-linecap: round; transition: stroke-dashoffset .3s ease; }
.timer-ring-xl span { position: absolute; inset: 0; display: grid; place-items: center; font-size: 25px; font-weight: 900; }
.timer-copy strong { display: block; font-size: clamp(34px,4vw,58px); line-height: 1; letter-spacing: -.04em; }
.timer-copy small { display: block; margin-top: 8px; min-height: 36px; color: var(--vision-muted); font-size: 13px; line-height: 1.45; }
.timer-copy button,.panel-heading button,.stage-actions button,.calendar-toolbar button,.glass-modal footer button,.audit-scan { border: 0; border-radius: 13px; background: var(--vision-blue); color: white; font-weight: 900; transition: transform .2s ease, opacity .2s ease, background .2s ease; }
.timer-copy button { margin-top: 12px; padding: 11px 18px; }
.timer-copy button:hover:not(:disabled),.panel-heading button:hover,.stage-actions button:hover:not(:disabled),.calendar-toolbar button:hover,.glass-modal footer button:hover:not(:disabled),.audit-scan:hover:not(:disabled) { transform: translateY(-1px); background: #1684ff; }
.timer-copy button:disabled,.stage-actions button:disabled,.audit-scan:disabled,.glass-modal footer button:disabled { opacity: .48; }
.duration-slider { position: relative; margin-top: 20px; }
.duration-slider input { width: 100%; accent-color: var(--vision-blue); }
.duration-ticks { display: grid; grid-template-columns: repeat(4,1fr); margin-top: 4px; }
.duration-ticks button { display: grid; justify-items: center; gap: 3px; border: 0; background: transparent; color: var(--vision-muted); font-size: 11px; }
.duration-ticks button span { width: 6px; height: 6px; border-radius: 99px; background: rgba(255,255,255,.24); }
.duration-ticks button.active { color: white; }
.duration-ticks button.active span { background: var(--vision-blue); }
.calendar-mini { min-height: 248px; padding: 22px; color: white; text-align: left; }
.calendar-mini header strong { font-size: 14px; }
.mini-calendar-grid { display: grid; grid-template-columns: repeat(7,1fr); gap: 6px; margin: 20px 0 14px; }
.mini-calendar-grid i { display: grid; min-height: 28px; place-items: center; border-radius: 10px; background: rgba(255,255,255,.06); color: rgba(255,255,255,.72); font-size: 12px; font-style: normal; }
.mini-calendar-grid i.muted { opacity: .38; }
.mini-calendar-grid i.busy { box-shadow: inset 0 -3px 0 var(--vision-blue); }
.mini-calendar-grid i.today,.mini-calendar-grid i.selected { background: var(--vision-blue); color: white; }
.calendar-mini small { color: var(--vision-muted); }
.workbench-grid { display: grid; grid-template-columns: minmax(320px,.82fr) minmax(520px,1.18fr); gap: 18px; min-height: calc(100vh - 390px); }
.todo-panel,.stages-panel { min-height: 450px; padding: 24px; overflow: hidden; }
.panel-heading h2 { margin: 5px 0 0; font-size: 24px; line-height: 1; }
.panel-heading button { padding: 10px 16px; }
.date-strip { display: flex; gap: 8px; margin: 20px 0 14px; }
.date-strip button { border: 1px solid rgba(255,255,255,.13); border-radius: 13px; padding: 8px 11px; background: rgba(255,255,255,.06); color: white; font-size: 12px; font-weight: 800; }
.task-list-scroll { display: grid; max-height: 54vh; gap: 10px; overflow-y: auto; padding-right: 4px; }
.todo-card { display: grid; grid-template-columns: 5px 1fr auto; gap: 12px; align-items: stretch; border: 1px solid rgba(255,255,255,.09); border-radius: 18px; padding: 12px; background: rgba(255,255,255,.055); color: white; text-align: left; transition: transform .18s ease, border-color .18s ease, background .18s ease; }
.todo-card:hover,.todo-card.selected { transform: translateY(-1px); border-color: rgba(72,128,255,.55); background: rgba(72,128,255,.12); }
.todo-card.completed { opacity: .62; }
.task-accent { min-height: 100%; border-radius: 99px; }
.todo-body small,.todo-body strong,.todo-body em { display: block; }
.todo-body small { color: var(--vision-muted); font-size: 11px; }
.todo-body strong { margin-top: 4px; font-size: 15px; }
.todo-body em { width: fit-content; margin-top: 7px; border-radius: 99px; padding: 3px 8px; font-size: 10px; font-style: normal; font-weight: 900; }
.todo-body em.done { background: rgba(0,214,143,.16); color: #62ffc8; }
.todo-body em.progress { background: rgba(255,191,71,.16); color: #ffda82; }
.todo-body em.todo { background: rgba(72,128,255,.16); color: #9dbaff; }
.todo-actions { display: grid; gap: 7px; }
.todo-actions i { display: grid; width: 28px; height: 28px; place-items: center; border-radius: 10px; background: rgba(255,255,255,.08); color: white; font-style: normal; font-weight: 900; }
.empty-task-state,.stage-empty,.stage-error,.scan-loader { border: 1px dashed rgba(255,255,255,.14); border-radius: 18px; padding: 20px; color: var(--vision-muted); background: rgba(255,255,255,.04); }
.empty-task-state strong,.stage-empty strong,.stage-error strong { display: block; color: white; margin-bottom: 7px; }
.task-error,.audit-message { color: #ffb4bf; font-size: 13px; }
.intensity-control { display: grid; grid-template-columns: repeat(3,1fr); min-width: 184px; border-radius: 999px; padding: 4px; background: rgba(255,255,255,.08); }
.intensity-control button { border: 0; border-radius: 999px; padding: 8px 14px; background: transparent; color: var(--vision-muted); font-weight: 900; }
.intensity-control button.active { background: rgba(255,255,255,.16); color: white; box-shadow: inset 0 1px 0 rgba(255,255,255,.24); }
.selected-task-banner { display: grid; gap: 5px; margin: 20px 0 14px; border-radius: 18px; padding: 16px; background: rgba(0,117,255,.12); }
.selected-task-banner span,.selected-task-banner small { color: var(--vision-muted); font-size: 12px; }
.selected-task-banner strong { font-size: 19px; }
.stage-actions { display: flex; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 14px; }
.stage-actions button { padding: 11px 15px; }
.stage-actions span { color: var(--vision-muted); font-size: 12px; }
.scan-loader { display: grid; gap: 10px; }
.scan-line { display: grid; grid-template-columns: 90px 1fr; gap: 12px; align-items: center; }
.scan-line span,.scan-line b { display: block; height: 12px; border-radius: 99px; background: linear-gradient(90deg, rgba(72,128,255,.22), rgba(255,255,255,.16), rgba(72,128,255,.22)); background-size: 220% 100%; animation: scanPulse 1.15s linear infinite; }
.scan-line b { height: 16px; }
.scan-loader p { margin: 8px 0 0; color: #9dbaff; font-size: 13px; }
.stage-table { display: grid; max-height: 44vh; overflow-y: auto; gap: 8px; padding-right: 4px; }
.stage-row { display: grid; grid-template-columns: 88px minmax(150px,1fr) 116px minmax(180px,.85fr); gap: 12px; align-items: center; border: 1px solid rgba(255,255,255,.1); border-radius: 15px; padding: 12px 14px; background: rgba(255,255,255,.05); color: white; text-align: left; }
.stage-row.header { position: sticky; top: 0; z-index: 1; color: var(--vision-muted); background: rgba(6,11,40,.94); font-size: 11px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; }
.stage-row.done { opacity: .68; }
.stage-row.in_progress { border-color: rgba(72,128,255,.58); box-shadow: 0 0 0 1px rgba(72,128,255,.14); }
.stage-row.locked { opacity: .52; }
.stage-row em,.stage-row small { font-style: normal; color: var(--vision-muted); font-size: 12px; }
.stage-empty { display: grid; gap: 8px; }
.glass-modal-overlay { position: fixed; inset: 0; z-index: 160; display: grid; place-items: center; overflow-y: auto; padding: 24px; background: rgba(2,6,23,.62); backdrop-filter: blur(12px); }
.glass-modal { width: min(760px,100%); max-height: min(86vh,900px); overflow-y: auto; border-radius: 28px; padding: 24px; }
.glass-modal header { margin-bottom: 20px; }
.glass-modal header h3 { margin: 4px 0 0; font-size: 25px; }
.glass-modal header > button { display: grid; width: 38px; height: 38px; place-items: center; border: 0; border-radius: 14px; background: rgba(255,255,255,.08); color: white; font-size: 24px; }
.glass-modal label { display: grid; gap: 8px; margin-bottom: 14px; }
.glass-modal label span { color: rgba(229,239,255,.74); font-size: 12px; font-weight: 900; letter-spacing: .08em; }
.glass-modal input,.glass-modal select,.glass-modal textarea { width: 100%; box-sizing: border-box; border: 1px solid rgba(255,255,255,.13); border-radius: 15px; outline: none; background: rgba(255,255,255,.08); color: white; padding: 12px 14px; }
.glass-modal select option { color: #0f172a; }
.modal-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.accent-row { display: flex; gap: 10px; margin: 10px 0 16px; }
.accent-row button { width: 30px; height: 30px; border: 3px solid transparent; border-radius: 999px; }
.accent-row button.active { border-color: white; }
.glass-modal footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; }
.glass-modal footer button { padding: 11px 16px; }
.glass-modal footer .ghost { background: rgba(255,255,255,.09); }
.calendar-modal { width: min(1120px,100%); }
.calendar-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.calendar-toolbar button { padding: 10px 13px; }
.calendar-toolbar div { display: flex; gap: 8px; }
.calendar-weekdays,.calendar-grid { display: grid; grid-template-columns: repeat(7,minmax(0,1fr)); }
.calendar-weekdays { gap: 8px; margin-bottom: 8px; }
.calendar-weekdays span { color: var(--vision-muted); font-size: 11px; font-weight: 900; text-align: center; }
.calendar-grid { gap: 8px; }
.calendar-cell { min-height: 112px; border: 1px solid rgba(255,255,255,.1); border-radius: 16px; padding: 10px; background: rgba(255,255,255,.055); color: white; text-align: left; }
.calendar-cell.muted { opacity: .44; }
.calendar-cell.today,.calendar-cell.selected { border-color: rgba(72,128,255,.72); background: rgba(72,128,255,.14); }
.day-number { display: block; margin-bottom: 8px; font-weight: 900; }
.calendar-event,.calendar-more { display: block; overflow: hidden; border-left: 3px solid var(--event-color,#4880ff); border-radius: 7px; margin-top: 5px; padding: 5px 6px; background: rgba(255,255,255,.08); color: rgba(255,255,255,.82); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.calendar-event.done { opacity: .52; text-decoration: line-through; }
.audit-modal { width: min(900px,100%); }
.audit-layout { display: grid; grid-template-columns: minmax(260px,.82fr) minmax(280px,1fr); gap: 18px; }
.audit-upload { min-height: 420px; border: 1px dashed rgba(255,255,255,.2); border-radius: 24px; overflow: hidden; margin: 0; background: rgba(255,255,255,.045); }
.audit-upload input { display: none; }
.audit-upload img { width: 100%; height: 100%; object-fit: cover; }
.audit-upload > span { display: grid; height: 100%; min-height: 420px; place-items: center; align-content: center; gap: 8px; padding: 26px; text-align: center; }
.audit-upload b { color: white; font-size: 20px; }
.audit-upload small { color: var(--vision-muted); }
.audit-panel { display: grid; align-content: start; gap: 12px; }
.audit-copy { margin: 0; border-radius: 18px; padding: 14px 16px; background: rgba(0,117,255,.12); color: var(--vision-muted); line-height: 1.6; }
.audit-copy strong { color: white; }
.audit-scan { padding: 12px 14px; }
.audit-result { display: grid; gap: 6px; border-radius: 16px; padding: 12px; background: rgba(255,255,255,.06); }
.audit-result span { color: white; font-weight: 800; }
.audit-result small { color: var(--vision-muted); }
.focus-init-error,.focus-mode-shell { position: relative; z-index: 2; }
.focus-init-error { min-height: 100vh; display: grid; place-items: center; padding: 24px; }
.focus-init-error-card { max-width: 520px; border-radius: 24px; padding: 26px; background: rgba(15,23,42,.92); box-shadow: 0 30px 80px rgba(0,0,0,.28); }
.focus-init-error-card p { color: #ffb4bf; font-weight: 900; }
.focus-init-error-card button { margin-right: 10px; border: 0; border-radius: 12px; padding: 10px 14px; background: var(--vision-blue); color: white; }
.focus-mode-shell { min-height: 100vh; background: radial-gradient(circle at 50% 34%, rgba(72,128,255,.18), transparent 34%), #020617; }
.focus-mode-header { position: fixed; top: 24px; left: 28px; right: 28px; z-index: 2; display: flex; justify-content: space-between; }
.focus-mode-status,.focus-mode-actions button { border: 1px solid rgba(255,255,255,.14); border-radius: 999px; padding: 11px 15px; background: rgba(15,23,42,.7); color: white; backdrop-filter: blur(16px); }
.focus-mode-status span { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; background: #34d399; box-shadow: 0 0 20px rgba(52,211,153,.8); }
.focus-mode-main { min-height: 100vh; display: grid; place-items: center; padding: 24px; }
.focus-mode-panel { width: min(860px,92vw); border: 1px solid rgba(255,255,255,.12); border-radius: 36px; padding: clamp(28px,5vw,58px); background: rgba(6,11,40,.72); text-align: center; box-shadow: 0 34px 100px rgba(0,0,0,.38); backdrop-filter: blur(34px); }
.focus-mode-goal p { margin: 0 0 8px; color: var(--vision-muted); text-transform: uppercase; letter-spacing: .18em; }
.focus-mode-goal h2 { margin: 0; font-size: clamp(28px,5vw,54px); }
.focus-mode-time { margin: 36px 0; font-size: clamp(76px,14vw,160px); font-weight: 950; line-height: .9; letter-spacing: -.08em; }
.focus-mode-time span { color: var(--vision-blue-2); }
.focus-mode-task { width: min(520px,100%); margin: 0 auto 28px; border-radius: 24px; padding: 18px; background: rgba(255,255,255,.06); }
.focus-mode-task p,.focus-mode-task h3 { margin: 0; }
.focus-mode-task p { color: var(--vision-muted); font-size: 12px; letter-spacing: .14em; text-transform: uppercase; }
.focus-mode-task h3 { margin-top: 8px; }
.focus-mode-controls { display: flex; justify-content: center; gap: 14px; }
.focus-mode-controls button { display: grid; width: 58px; height: 58px; place-items: center; border: 0; border-radius: 20px; color: white; }
.focus-mode-controls svg { width: 24px; height: 24px; }
.focus-mode-controls .danger { background: #ef4444; }
.focus-mode-controls .primary { background: var(--vision-blue); }
.focus-mode-controls .success { background: #10b981; }
@keyframes scanPulse { from { background-position: 220% 0; } to { background-position: -220% 0; } }
@media (max-width: 1280px) {
  .vision-topbar { grid-template-columns: 1fr; }
  .topbar-cluster { flex-wrap: wrap; }
  .vision-dashboard-grid,.workbench-grid { grid-template-columns: 1fr; }
}
@media (max-width: 900px) {
  .focus-home-shell { overflow-y: auto; }
  .vision-sidebar { position: relative; inset: auto; width: auto; margin: 10px; max-height: none; }
  .vision-menu { max-height: 360px; }
  .vision-main { margin-left: 0; padding: 18px 14px 32px; }
  .stage-row { grid-template-columns: 1fr; }
  .audit-layout,.modal-grid { grid-template-columns: 1fr; }
  .calendar-cell { min-height: 82px; padding: 7px; }
  .calendar-event { display: none; }
}
@media (max-width: 620px) {
  .topbar-cluster,.stage-actions,.calendar-toolbar { align-items: stretch; flex-direction: column; }
  .metric-card,.mail-chip,.avatar-chip { width: 100%; box-sizing: border-box; }
  .timer-layout { grid-template-columns: 1fr; justify-items: center; text-align: center; }
  .panel-heading,.calendar-mini header,.glass-modal header { align-items: stretch; flex-direction: column; }
  .glass-modal-overlay { padding: 12px; }
}
</style>
