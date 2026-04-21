<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { focusApi, taskApi } from '../api'
import { useUserStore } from '../stores/user'
import { useFocusHubStore } from '../stores/focusHub'
import { useDimensionStore } from '../stores/dimension'
import { useMailStore } from '../stores/mail'
import { useGoalDecomposer } from '../composables/useGoalDecomposer'
import TaskDecomposeSheet from './focus-hub/TaskDecomposeSheet.vue'

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
const taskError = ref('')
const initError = ref('')

const todoTasks = ref([])
const selectedTodoTaskId = ref('')
const activeFocusTodoId = ref('')
const selectedDateKey = ref('')
const monthCursor = ref(new Date())
const taskModalOpen = ref(false)
const decomposeSheetOpen = ref(false)
const decomposeDraftItems = ref([])
const decomposeIsGenerating = ref(false)
const decomposeError = ref('')

const userAvatar = ref('')
const userNickname = ref('')

const taskForm = ref({
  content: '',
  scheduledDate: '',
  scheduledTime: '10:00',
  category: 'FocusPort',
  accent: '#4880FF'
})

const accentOptions = ['#4880FF', '#7551E9', '#E951BF', '#FF9E58', '#00B69B']
const dateKeyPattern = /^\d{4}-\d{2}-\d{2}$/
const weekdayLabels = ['MON', 'TUE', 'WED', 'THE', 'FRI', 'SAT', 'SUN']

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

const displayName = computed(() => {
  const nickname = String(userNickname.value || '').trim()
  return nickname || username.value
})

const avatarToken = computed(() => {
  const raw = String(userAvatar.value || '').trim()
  if (raw) return raw
  return (username.value?.[0] || 'F').toUpperCase()
})

const avatarIsImage = computed(() => {
  const value = avatarToken.value
  return value.startsWith('http://') || value.startsWith('https://') || value.startsWith('data:image')
})

const formattedRemaining = computed(() => {
  const total = Math.max(0, Number(focusHubStore.pomodoro.remainingSeconds) || 0)
  const mm = String(Math.floor(total / 60)).padStart(2, '0')
  const ss = String(total % 60).padStart(2, '0')
  return `${mm}:${ss}`
})

const safeTotalSeconds = computed(() => Math.max(60, Number(focusHubStore.pomodoro.focusMinutes || selectedDuration.value || 25) * 60))
const safeRemainingSeconds = computed(() => Math.max(0, Number(focusHubStore.pomodoro.remainingSeconds || 0)))
const progressPercent = computed(() => {
  const elapsed = 1 - Math.min(1, safeRemainingSeconds.value / safeTotalSeconds.value)
  return Math.round(elapsed * 100)
})

const ringRadius = 34
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

const selectedTodoTask = computed(() => (
  todoTasks.value.find((task) => String(task.id) === String(selectedTodoTaskId.value)) || null
))

const selectedTaskIsDone = computed(() => Boolean(selectedTodoTask.value?.isCompleted || selectedTodoTask.value?.status === 'done'))

const visibleTasks = computed(() => (
  todoTasks.value.filter((task) => task.scheduledDate === selectedDateKey.value)
))

const tasksByDate = computed(() => {
  const map = new Map()
  todoTasks.value.forEach((task) => {
    if (!map.has(task.scheduledDate)) map.set(task.scheduledDate, [])
    map.get(task.scheduledDate).push(task)
  })
  return map
})

const monthTitle = computed(() => (
  new Intl.DateTimeFormat('zh-CN', { month: 'long' }).format(monthCursor.value)
))

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

const focusActionDisabled = computed(() => (
  !focusHubStore.pomodoro.isRunning &&
  (isStartingFocus.value || isTaskLoading.value || !selectedTodoTask.value || selectedTaskIsDone.value)
))

const focusActionLabel = computed(() => {
  if (isStartingFocus.value) return '启动中'
  if (focusHubStore.pomodoro.isRunning) return '暂停专注'
  return '开始专注'
})

const focusSubject = computed(() => selectedTodoTask.value?.title || 'Focus Session')
const focusGoalTitle = computed(() => selectedTodoTask.value?.category || 'Today Focus')
const focusActionTitle = computed(() => selectedTodoTask.value?.title || '请选择一个待办任务')
const showFocusGoal = computed(() => Boolean(focusGoalTitle.value && focusGoalTitle.value !== focusActionTitle.value))
const durationProgress = computed(() => {
  const maxIndex = Math.max(1, durationOptions.length - 1)
  return `${(selectedDurationIndex.value / maxIndex) * 100}%`
})

const selectFallbackTask = () => {
  const currentExists = todoTasks.value.some((task) => String(task.id) === String(selectedTodoTaskId.value))
  if (currentExists) return
  const sameDay = visibleTasks.value.find((task) => !task.isCompleted) || visibleTasks.value[0]
  const fallback = sameDay || todoTasks.value.find((task) => !task.isCompleted) || todoTasks.value[0]
  selectedTodoTaskId.value = fallback ? String(fallback.id) : ''
}

const goProfile = () => router.push('/more')
const goMail = () => router.push('/mail')
const goHome = () => router.push('/')
const goDashboard = () => router.push('/dashboard')
const goShop = () => router.push('/shop')
const goVault = () => router.push('/vault')
const goStats = () => router.push('/stats')
const goFriends = () => router.push('/friends')
const goPlayground = () => router.push('/playground')

const enter2DCity = () => {
  dimensionStore.setDimension('GAIA')
  router.push({ path: '/island', query: { dimension: 'GAIA' } })
}

const logout = () => {
  userStore.logout()
  router.push('/login')
}

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
    todoTasks.value = (response.data?.tasks || [])
      .map(normalizeTask)
      .filter((task) => task.id && task.title)
    selectFallbackTask()
  } catch (error) {
    console.error('Failed to load todo tasks', error)
    taskError.value = '任务同步失败，请稍后重试。'
  } finally {
    isTaskLoading.value = false
  }
}

const openTaskModal = () => {
  taskForm.value = {
    content: '',
    scheduledDate: selectedDateKey.value || todayDateKey(),
    scheduledTime: '10:00',
    category: 'FocusPort',
    accent: '#4880FF'
  }
  taskError.value = ''
  taskModalOpen.value = true
}

const closeTaskModal = () => {
  taskModalOpen.value = false
}

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
    const created = normalizeTask(response.data?.task || {
      id: response.data?.task_id,
      content,
      scheduled_date: scheduledDate,
      scheduled_time: taskForm.value.scheduledTime,
      category: taskForm.value.category,
      accent: taskForm.value.accent
    })
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
  const closestIndex = durationOptions.reduce((bestIndex, option, index) => {
    const bestDistance = Math.abs(option - Number(minutes))
    const currentDistance = Math.abs(durationOptions[bestIndex] - Number(minutes))
    return bestDistance < currentDistance ? index : bestIndex
  }, 0)
  selectedDurationIndex.value = closestIndex
  selectedDuration.value = durationOptions[closestIndex]
}

const handleDurationDrag = (event) => {
  handleDurationSelect(durationOptions[Number(event.target.value)] || selectedDuration.value)
}

const handleStartFocus = async () => {
  if (focusActionDisabled.value) return
  isStartingFocus.value = true
  try {
    if (focusHubStore.pomodoro.pendingSettlement) {
      focusHubStore.skipSettlement()
    }
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
}

const handleCompleteFocusQuick = async () => {
  const targetTaskId = activeFocusTodoId.value || selectedTodoTaskId.value
  focusHubStore.pausePomodoro()

  try {
    await focusApi.complete(
      username.value,
      focusHubStore.pomodoro.focusMinutes,
      focusSubject.value,
      '',
      focusHubStore.pomodoro.taskDifficulty
    )
    await markTaskDone(targetTaskId)
  } catch (error) {
    console.error('quick focus completion failed', error)
    try {
      await markTaskDone(targetTaskId)
    } catch (taskErrorValue) {
      console.error('failed to mark todo task complete', taskErrorValue)
    }
  }

  activeFocusTodoId.value = ''
  focusHubStore.resetPomodoro()
}

const statusLabel = (task) => {
  if (task.isCompleted || task.status === 'done') return 'Done'
  if (String(task.id) === String(selectedTodoTaskId.value) && focusHubStore.pomodoro.isRunning) return 'In Progress'
  return task.status === 'in_progress' ? 'In Progress' : 'To-do'
}

const statusClass = (task) => {
  const status = statusLabel(task)
  if (status === 'Done') return 'done'
  if (status === 'In Progress') return 'progress'
  return 'todo'
}

const handleAIDecompose = async () => {
  const task = selectedTodoTask.value
  if (!task) return
  decomposeSheetOpen.value = true
  decomposeError.value = ''
  decomposeDraftItems.value = []
  decomposeIsGenerating.value = true
  try {
    const steps = await decomposeGoal({
      goal: task.title || task.content || '',
      style: 'balanced',
      availableMinutes: selectedDuration.value
    })
    decomposeDraftItems.value = steps.map((s, i) => ({
      id: s.id || `step-${i}`,
      title: s.title,
      estimatedPomodoros: s.estimatedPomodoros || 1,
      description: s.description || ''
    }))
  } catch (err) {
    decomposeError.value = String(err?.message || err || 'AI 拆解失败')
  } finally {
    decomposeIsGenerating.value = false
  }
}

const handleDecomposeConfirm = () => {
  decomposeSheetOpen.value = false
  decomposeDraftItems.value = []
}

onMounted(async () => {
  try {
    focusHubStore.hydrate(userStore.username)
    dimensionStore.rehydrate()
    handleDurationSelect(Number(focusHubStore.pomodoro.focusMinutes) || 25)
    selectedDateKey.value = todayDateKey()
    taskForm.value.scheduledDate = selectedDateKey.value
    await Promise.all([loadAvatarProfile(), loadTodoTasks()])
  } catch (error) {
    console.error('FocusHub init failed:', error)
    initError.value = error instanceof Error ? error.message : 'Unknown initialization error'
  } finally {
    isActionHydrating.value = false
  }
})

watch(selectedDuration, (minutes) => {
  focusHubStore.setFocusMinutes(minutes)
})

watch(() => userStore.username, async () => {
  await Promise.all([loadAvatarProfile(), loadTodoTasks()])
})

watch(taskModalOpen, (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
})

watch(selectedDateKey, () => {
  selectFallbackTask()
})

onUnmounted(() => {
  document.body.style.overflow = ''
})
</script>

<template>
  <div class="focus-home-shell" :class="{ 'is-focus-mode': isFocusMode }">
    <div
      v-if="initError"
      class="focus-init-error"
    >
      <div class="focus-init-error-card">
        <p>FocusHub Init Error</p>
        <h2>Home failed to initialize</h2>
        <span>{{ initError }}</span>
        <div>
          <button type="button" @click="goProfile">个人中心</button>
          <button type="button" @click="$router.go(0)">重新加载</button>
        </div>
      </div>
    </div>

    <template v-if="isFocusMode">
      <header class="focus-mode-header">
        <div class="focus-mode-status">
          <span />
          <b>Mission Active</b>
        </div>
        <div class="focus-mode-actions">
          <button type="button" @click="goProfile">个人中心</button>
          <button type="button" @click="enter2DCity">进入城市</button>
        </div>
      </header>

      <main class="focus-mode-main">
        <section class="focus-mode-panel">
          <div v-if="showFocusGoal" class="focus-mode-goal">
            <p>{{ focusGoalTitle }}</p>
            <h2>{{ focusActionTitle }}</h2>
          </div>

          <p class="focus-mode-time">
            {{ formattedRemaining.slice(0, 2) }}<span>:</span>{{ formattedRemaining.slice(3, 5) }}
          </p>

          <article class="focus-mode-task">
            <p>Now Focusing</p>
            <h3>{{ focusActionTitle }}</h3>
          </article>

          <div class="focus-mode-controls">
            <button type="button" class="danger" title="Abort focus" @click="handleAbortFocus">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 18 18 6M6 6l12 12" stroke-linecap="round" /></svg>
            </button>
            <button type="button" class="primary" :title="focusHubStore.pomodoro.isRunning ? 'Pause' : 'Resume'" @click="handleToggleFocus">
              <svg v-if="focusHubStore.pomodoro.isRunning" viewBox="0 0 24 24" fill="currentColor"><path d="M7 5h3v14H7zm7 0h3v14h-3z" /></svg>
              <svg v-else viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>
            </button>
            <button type="button" class="success" title="Complete focus" @click="handleCompleteFocusQuick">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m5 13 4 4L19 7" stroke-linecap="round" stroke-linejoin="round" /></svg>
            </button>
          </div>
        </section>
      </main>
    </template>

    <template v-else>
      <aside class="figma-side-rail" aria-label="Focus navigation">
        <button type="button" class="rail-brand" title="FocusPort Home" data-label="FocusPort" @click="goHome">
          <span>F</span>
        </button>

        <nav class="rail-nav">
          <button type="button" title="Dashboard" data-label="Dashboard" @click="goDashboard"><svg viewBox="0 0 24 24"><path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" /></svg></button>
          <button type="button" title="City" data-label="2D City" @click="enter2DCity"><svg viewBox="0 0 24 24"><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3z" /></svg></button>
          <button type="button" title="Shop" data-label="Shop" @click="goShop"><svg viewBox="0 0 24 24"><path d="M5 9h14l-1 11H6L5 9zm3 0a4 4 0 0 1 8 0" /></svg></button>
          <button type="button" title="Mail" data-label="Mail" @click="goMail"><svg viewBox="0 0 24 24"><path d="M4 6h16v12H4z" /><path d="m4 8 8 6 8-6" /></svg><span v-if="mailUnread > 0" class="rail-badge">{{ mailUnread > 9 ? '9+' : mailUnread }}</span></button>
          <span class="rail-divider" aria-hidden="true" />
          <button type="button" class="active" title="Focus Home" data-label="Focus Home"><svg viewBox="0 0 24 24"><path d="M6 7h12M6 12h12M6 17h8" /></svg></button>
          <button type="button" title="Calendar" data-label="Calendar"><svg viewBox="0 0 24 24"><path d="M5 5h14v15H5zM8 3v4M16 3v4M5 10h14" /></svg></button>
          <span class="rail-divider" aria-hidden="true" />
          <button type="button" title="Vault" data-label="Vault" @click="goVault"><svg viewBox="0 0 24 24"><path d="M7 4h10v16H7zM9 8h6M9 12h6" /></svg></button>
          <button type="button" title="Friends" data-label="Friends" @click="goFriends"><svg viewBox="0 0 24 24"><path d="M8 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm8 0a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM3 20c.7-3 2.5-5 5-5s4.3 2 5 5m-1.5 0c.6-2.1 2.1-3.5 4.5-3.5 2.2 0 3.8 1.4 4.5 3.5" /></svg></button>
          <button type="button" title="Stats" data-label="Stats" @click="goStats"><svg viewBox="0 0 24 24"><path d="M5 19V5m0 14h14M9 16v-5M13 16V8M17 16v-8" /></svg></button>
          <button type="button" title="Profile" data-label="Profile" @click="goProfile"><svg viewBox="0 0 24 24"><path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-7 8c1-4 3.4-6 7-6s6 2 7 6" /></svg></button>
          <button type="button" title="Playground" data-label="Playground" @click="goPlayground"><svg viewBox="0 0 24 24"><path d="M7 8h10l3 7-2 2-3-3H9l-3 3-2-2 3-7zM9 11h.01M12 11h.01M15 11h.01" /></svg></button>
        </nav>

        <button type="button" class="rail-logout" title="Logout" data-label="Logout" @click="logout">
          <svg viewBox="0 0 24 24"><path d="M12 3v9m6.4-5A8 8 0 1 1 5.6 7" /></svg>
        </button>
      </aside>

      <header class="figma-top-bar">
        <div />
        <div class="top-profile-cluster">
          <button type="button" class="mail-button" aria-label="Open mail" @click="goMail">
            <svg viewBox="0 0 24 24"><path d="M4 6h16v12H4z" /><path d="m4 8 8 6 8-6" /></svg>
            <span v-if="mailUnread > 0">{{ mailUnread > 99 ? '99+' : mailUnread }}</span>
          </button>

          <button type="button" class="profile-button" @click="goProfile">
            <span class="profile-avatar">
              <img v-if="avatarIsImage" :src="avatarToken" alt="avatar">
              <b v-else>{{ avatarToken }}</b>
            </span>
            <span class="profile-copy">
              <strong>{{ displayName }}</strong>
              <small>Admin</small>
            </span>
            <svg viewBox="0 0 24 24"><path d="m7 10 5 5 5-5" /></svg>
          </button>
        </div>
      </header>

      <main class="figma-home-main">
        <section class="figma-left-column">
          <article class="pomodoro-card">
            <div class="timer-row">
              <strong>{{ formattedRemaining.replace(':', ' : ') }}</strong>
              <button type="button" class="ai-decompose-btn" title="AI 任务拆解" @click="handleAIDecompose">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l2 7h7l-5.5 4 2 7L12 16l-5.5 4 2-7L3 9h7z"/></svg>
                <span>AI拆解</span>
              </button>
            </div>

            <button
              type="button"
              class="start-focus-btn"
              :disabled="focusActionDisabled"
              :title="selectedTaskIsDone ? '已完成任务不能再启动番茄钟' : focusActionLabel"
              @click="handleToggleFocus"
            >
              {{ focusActionLabel }}
            </button>

            <div
              class="duration-slider"
              :class="{ locked: focusHubStore.pomodoro.isRunning || isStartingFocus }"
              :style="{ '--duration-progress': durationProgress }"
            >
              <input
                v-model.number="selectedDurationIndex"
                type="range"
                min="0"
                :max="durationOptions.length - 1"
                step="1"
                :disabled="focusHubStore.pomodoro.isRunning || isStartingFocus"
                aria-label="Pomodoro duration"
                @input="handleDurationDrag"
                @change="handleDurationDrag"
              >
              <div class="duration-ticks" aria-hidden="true">
                <button
                  v-for="(m, index) in durationOptions"
                  :key="m"
                  type="button"
                  :class="{ active: selectedDurationIndex === index }"
                  :disabled="focusHubStore.pomodoro.isRunning || isStartingFocus"
                  @click="handleDurationSelect(m)"
                >
                  <span />
                  <b>{{ m }}</b>
                </button>
              </div>
            </div>
          </article>

          <article class="task-list-panel">
            <div class="task-list-scroll">
              <button
                v-for="task in visibleTasks"
                :key="task.id"
                type="button"
                class="todo-card"
                :class="{ selected: String(task.id) === String(selectedTodoTaskId), completed: task.isCompleted }"
                @click="selectTask(task)"
              >
                <span class="todo-category">{{ task.category }}</span>
                <strong>{{ task.title }}</strong>
                <span class="todo-time">
                  <svg viewBox="0 0 24 24"><path d="M12 7v5l3 2" /><circle cx="12" cy="12" r="8" /></svg>
                  {{ task.scheduledTime || 'Today' }}
                </span>
                <span class="todo-status" :class="statusClass(task)">{{ statusLabel(task) }}</span>
                <span class="todo-icon" :style="{ backgroundColor: `${task.accent}18`, color: task.accent }">
                  <svg viewBox="0 0 24 24"><path d="M8 6h8v12H8zM10 4h4v4h-4z" /></svg>
                </span>
              </button>

              <div v-if="!visibleTasks.length" class="empty-task-state">
                <strong>暂无任务</strong>
                <span>{{ selectedDateKey }} 没有待办。</span>
              </div>
            </div>

            <p v-if="taskError" class="task-error">{{ taskError }}</p>

            <button type="button" class="add-task-bottom" @click="openTaskModal">添加任务</button>
          </article>
        </section>

        <section class="calendar-card">
          <header class="calendar-toolbar">
            <button type="button" class="today-button" @click="selectToday">Today</button>

            <div class="month-switcher">
              <button type="button" @click="shiftMonth(-1)">‹</button>
              <strong>{{ monthTitle }}</strong>
              <button type="button" @click="shiftMonth(1)">›</button>
            </div>

            <button type="button" class="new-event-btn" @click="openTaskModal">+ Add New Event</button>
          </header>

          <div class="calendar-weekdays">
            <span v-for="label in weekdayLabels" :key="label">{{ label }}</span>
          </div>

          <div class="calendar-grid">
            <button
              v-for="cell in calendarCells"
              :key="cell.dateKey"
              type="button"
              class="calendar-cell"
              :class="{ muted: !cell.inMonth, today: cell.isToday, selected: cell.isSelected }"
              @click="selectDate(cell.dateKey)"
            >
              <span class="day-number">{{ cell.day }}</span>
              <span
                v-for="task in cell.tasks.slice(0, 2)"
                :key="task.id"
                class="calendar-event"
                :class="{ done: task.isCompleted }"
                :style="{ '--event-color': task.accent }"
              >
                {{ task.title }}
              </span>
              <span v-if="cell.tasks.length > 2" class="calendar-more">+{{ cell.tasks.length - 2 }}</span>
            </button>
          </div>
        </section>
      </main>

      <div v-if="taskModalOpen" class="task-modal-overlay" @click.self="closeTaskModal">
        <form class="task-modal" @submit.prevent="createTodoTask">
          <header>
            <p>New Event</p>
            <button type="button" @click="closeTaskModal">×</button>
          </header>

          <label>
            <span>任务</span>
            <input v-model="taskForm.content" type="text" maxlength="80" placeholder="输入任务内容">
          </label>

          <div class="task-modal-grid">
            <label>
              <span>日期</span>
              <input v-model="taskForm.scheduledDate" type="date" pattern="\d{4}-\d{2}-\d{2}">
            </label>
            <label>
              <span>时间</span>
              <input v-model="taskForm.scheduledTime" type="time">
            </label>
          </div>

          <label>
            <span>分类</span>
            <input v-model="taskForm.category" type="text" maxlength="28" placeholder="FocusPort">
          </label>

          <div class="accent-row">
            <button
              v-for="accent in accentOptions"
              :key="accent"
              type="button"
              :class="{ active: taskForm.accent === accent }"
              :style="{ backgroundColor: accent }"
              @click="taskForm.accent = accent"
            />
          </div>

          <p v-if="taskError" class="task-error">{{ taskError }}</p>

          <footer>
            <button type="button" class="ghost" @click="closeTaskModal">取消</button>
            <button type="submit" :disabled="isTaskSubmitting">{{ isTaskSubmitting ? '创建中' : '创建任务' }}</button>
          </footer>
        </form>
      </div>
    </template>
  </div>

  <TaskDecomposeSheet
    :open="decomposeSheetOpen"
    :goal="selectedTodoTask?.title || ''"
    :target-task-title="selectedTodoTask?.title || '未选择任务'"
    :draft-items="decomposeDraftItems"
    :is-generating="decomposeIsGenerating"
    :generation-error="decomposeError"
    @close="decomposeSheetOpen = false"
    @refresh-ai="handleAIDecompose"
    @confirm="handleDecomposeConfirm"
    @remove-step="(id) => decomposeDraftItems = decomposeDraftItems.filter(s => s.id !== id)"
    @update-step-title="({ id, value }) => decomposeDraftItems = decomposeDraftItems.map(s => s.id === id ? { ...s, title: value } : s)"
    @update-step-pomodoros="({ id, value }) => decomposeDraftItems = decomposeDraftItems.map(s => s.id === id ? { ...s, estimatedPomodoros: Number(value) || 1 } : s)"
  />
</template>

<style scoped>
.focus-home-shell {
  min-height: 100vh;
  width: 100%;
  overflow: hidden;
  background: #1b2432;
  color: #f5f7fb;
  font-family: "Nunito Sans", "Noto Sans SC", "Microsoft YaHei", sans-serif;
}

.figma-side-rail {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: 40;
  width: 86px;
  background:
    radial-gradient(circle at 50% 0%, rgba(72, 128, 255, 0.2), transparent 34%),
    linear-gradient(180deg, #2c3749 0%, #222b3a 48%, #1d2633 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  border-right: 1px solid rgba(90, 107, 132, 0.38);
  box-shadow: 18px 0 38px rgba(0, 0, 0, 0.16);
}

.rail-brand,
.rail-logout,
.figma-side-rail .rail-nav button {
  width: 48px;
  height: 48px;
  border: 0;
  background: transparent;
  color: rgba(223, 230, 241, 0.7);
  display: grid;
  place-items: center;
  cursor: pointer;
  position: relative;
  border-radius: 16px;
  transition:
    color 0.2s ease,
    background 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.rail-brand {
  margin-top: 18px;
  margin-bottom: 20px;
  color: #fff;
  background: linear-gradient(135deg, #4880ff 0%, #7ca4ff 100%);
  box-shadow: 0 14px 28px rgba(72, 128, 255, 0.28);
}

.rail-brand span {
  width: 30px;
  height: 30px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 18px;
  font-weight: 900;
  letter-spacing: -0.04em;
}

.rail-brand:hover {
  transform: translateY(-1px) scale(1.03);
  box-shadow: 0 18px 34px rgba(72, 128, 255, 0.36);
}

.figma-side-rail .rail-nav {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 0 0 14px;
}

.figma-side-rail svg {
  width: 21px;
  height: 21px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.figma-side-rail button:hover,
.figma-side-rail button.active {
  color: #fff;
  background: rgba(72, 128, 255, 0.16);
  box-shadow: inset 0 0 0 1px rgba(72, 128, 255, 0.24);
  transform: translateX(2px);
}

.figma-side-rail button.active {
  background: linear-gradient(135deg, rgba(72, 128, 255, 0.98), rgba(72, 128, 255, 0.7));
  box-shadow: 0 16px 30px rgba(72, 128, 255, 0.25);
}

.figma-side-rail button.active::before {
  content: "";
  position: absolute;
  left: -19px;
  width: 4px;
  height: 34px;
  border-radius: 0 2px 2px 0;
  background: #4880ff;
  box-shadow: 0 0 18px rgba(72, 128, 255, 0.9);
}

.figma-side-rail button[data-label]::after {
  content: attr(data-label);
  position: absolute;
  left: 62px;
  top: 50%;
  transform: translate(-8px, -50%);
  opacity: 0;
  pointer-events: none;
  white-space: nowrap;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.96);
  border: 1px solid rgba(148, 163, 184, 0.22);
  color: #f8fafc;
  box-shadow: 0 16px 30px rgba(0, 0, 0, 0.24);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.01em;
  padding: 8px 11px;
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.figma-side-rail button[data-label]:hover::after {
  opacity: 1;
  transform: translate(0, -50%);
}

.rail-divider {
  width: 30px;
  height: 1px;
  margin: 6px 0;
  background: linear-gradient(90deg, transparent, rgba(211, 220, 235, 0.24), transparent);
}

.rail-badge {
  position: absolute;
  top: 7px;
  right: 6px;
  min-width: 17px;
  height: 17px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  padding: 0 4px;
  background: #ff5f6d;
  color: #fff;
  border: 2px solid #273142;
  font-size: 9px;
  font-weight: 900;
  line-height: 1;
}

.rail-logout {
  margin-top: auto;
  margin-bottom: 22px;
  color: rgba(255, 255, 255, 0.58);
}

.rail-logout:hover {
  color: #ff8c8c;
  background: rgba(255, 95, 109, 0.12);
  box-shadow: inset 0 0 0 1px rgba(255, 95, 109, 0.2);
}

.figma-top-bar {
  position: fixed;
  top: 0;
  left: 86px;
  right: 0;
  z-index: 30;
  height: 70px;
  background: #273142;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 42px;
}

.top-profile-cluster {
  display: flex;
  align-items: center;
  gap: 28px;
}

.mail-button,
.profile-button {
  border: 0;
  background: transparent;
  color: #fff;
  cursor: pointer;
}

.mail-button {
  position: relative;
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
}

.mail-button svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: #4880ff;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.mail-button span {
  position: absolute;
  top: 0;
  right: 1px;
  min-width: 16px;
  height: 16px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: #f93c65;
  color: white;
  font-size: 10px;
  font-weight: 800;
}

.profile-button {
  display: grid;
  grid-template-columns: 44px auto 18px;
  align-items: center;
  gap: 12px;
  text-align: left;
}

.profile-avatar {
  width: 44px;
  height: 44px;
  border-radius: 999px;
  overflow: hidden;
  display: grid;
  place-items: center;
  background: #354258;
  color: white;
  font-weight: 800;
}

.profile-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile-copy strong,
.profile-copy small {
  display: block;
}

.profile-copy strong {
  font-size: 14px;
  line-height: 18px;
}

.profile-copy small {
  margin-top: 2px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.78);
}

.profile-button > svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: rgba(255, 255, 255, 0.55);
  stroke-width: 2;
}

.figma-home-main {
  height: 100vh;
  padding: 92px 48px 28px 106px;
  display: flex;
  gap: 32px;
  box-sizing: border-box;
}

.figma-left-column {
  width: 324px;
  flex: 0 0 324px;
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.pomodoro-card {
  height: 204px;
  border-radius: 20px;
  background: #111827;
  padding: 28px 26px 22px;
  color: white;
  box-shadow: 0 22px 42px rgba(6, 11, 20, 0.24);
}

.timer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.timer-row > strong {
  font-size: 38px;
  font-weight: 500;
  letter-spacing: 0;
  line-height: 1;
}

.ai-decompose-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 76px;
  height: 76px;
  border: 1px solid rgba(72, 128, 255, 0.3);
  border-radius: 16px;
  background: rgba(72, 128, 255, 0.1);
  color: #4880ff;
  cursor: pointer;
  transition: background 0.2s;
}

.ai-decompose-btn:hover {
  background: rgba(72, 128, 255, 0.2);
}

.ai-decompose-btn svg {
  width: 24px;
  height: 24px;
}

.ai-decompose-btn span {
  font-size: 11px;
  font-weight: 600;
}

.start-focus-btn {
  display: block;
  width: 148px;
  height: 34px;
  margin: 14px auto 18px;
  border: 0;
  border-radius: 6px;
  color: white;
  font-size: 14px;
  font-weight: 800;
  background: linear-gradient(90deg, #4880ff, #5f33e1);
  cursor: pointer;
}

.start-focus-btn:disabled {
  cursor: not-allowed;
  opacity: 0.42;
}

.duration-slider {
  position: relative;
  height: 44px;
  padding-top: 6px;
}

.duration-slider::before {
  content: "";
  position: absolute;
  left: 10px;
  right: 10px;
  top: 16px;
  height: 8px;
  border-radius: 999px;
  background:
    linear-gradient(90deg, #4880ff 0 var(--duration-progress), rgba(255, 255, 255, 0.9) var(--duration-progress) 100%);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.18);
}

.duration-slider.locked {
  opacity: 0.62;
}

.duration-slider input {
  position: absolute;
  z-index: 3;
  left: 0;
  right: 0;
  top: 4px;
  width: 100%;
  height: 30px;
  opacity: 0;
  cursor: grab;
}

.duration-slider input:disabled {
  cursor: not-allowed;
}

.duration-slider input:active {
  cursor: grabbing;
}

.duration-ticks {
  position: relative;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.duration-ticks button {
  width: 34px;
  border: 0;
  background: transparent;
  color: rgba(255, 255, 255, 0.58);
  display: grid;
  justify-items: center;
  gap: 8px;
  padding: 0;
  cursor: pointer;
}

.duration-ticks button:disabled {
  cursor: not-allowed;
}

.duration-ticks span {
  width: 18px;
  height: 18px;
  border-radius: 999px;
  background: #eef4ff;
  box-shadow: 0 0 0 5px rgba(17, 24, 39, 0.92);
  transition: transform 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}

.duration-ticks button.active {
  color: #fff;
}

.duration-ticks button.active span {
  transform: scale(1.42);
  background: #7e8793;
  box-shadow:
    0 0 0 5px rgba(17, 24, 39, 0.94),
    0 10px 20px rgba(72, 128, 255, 0.26);
}

.duration-ticks b {
  font-size: 11px;
  font-weight: 900;
  line-height: 1;
}

.task-list-panel {
  min-height: 0;
  flex: 1;
  border-radius: 14px;
  border: 1px solid #313d4f;
  background: #273142;
  padding: 24px 16px 16px;
  display: flex;
  flex-direction: column;
}

.task-list-scroll {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  padding: 0 0 14px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.todo-card {
  position: relative;
  min-height: 94px;
  border: 1px solid transparent;
  border-radius: 15px;
  background: #fff;
  color: #202735;
  padding: 14px 48px 14px 18px;
  text-align: left;
  cursor: pointer;
  box-shadow: 0 4px 32px rgba(0, 0, 0, 0.04);
}

.todo-card.selected {
  border-color: #4880ff;
  box-shadow: 0 0 0 2px rgba(72, 128, 255, 0.18);
}

.todo-card.completed {
  opacity: 0.72;
}

.todo-category {
  display: block;
  max-width: 170px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  color: #6b7280;
  font-size: 11px;
  line-height: 14px;
}

.todo-card strong {
  display: block;
  margin-top: 3px;
  max-width: 180px;
  color: #151a24;
  font-size: 16px;
  line-height: 18px;
  font-weight: 800;
}

.todo-time {
  position: absolute;
  left: 18px;
  bottom: 13px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #8a55ff;
  font-size: 11px;
  font-weight: 700;
}

.todo-time svg,
.todo-icon svg {
  width: 13px;
  height: 13px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.todo-status {
  position: absolute;
  right: 10px;
  bottom: 12px;
  max-width: 76px;
  border-radius: 6px;
  padding: 2px 7px;
  font-size: 9px;
  font-weight: 800;
  line-height: 10px;
  text-align: center;
}

.todo-status.done {
  background: #eee8ff;
  color: #7b55ff;
}

.todo-status.progress {
  background: #ffece8;
  color: #f05f42;
}

.todo-status.todo {
  background: #e6f5ff;
  color: #2388d9;
}

.todo-icon {
  position: absolute;
  right: 16px;
  top: 14px;
  width: 22px;
  height: 24px;
  border-radius: 8px;
  display: grid;
  place-items: center;
}

.empty-task-state {
  margin-top: 20px;
  min-height: 120px;
  border: 1px dashed rgba(255, 255, 255, 0.16);
  border-radius: 14px;
  display: grid;
  place-items: center;
  text-align: center;
  color: rgba(255, 255, 255, 0.7);
}

.empty-task-state strong,
.empty-task-state span {
  display: block;
}

.empty-task-state strong {
  font-size: 16px;
}

.empty-task-state span {
  margin-top: 6px;
  font-size: 12px;
}

.task-error {
  color: #ff8fa3;
  font-size: 12px;
  margin: 0 0 10px;
}

.add-task-bottom {
  align-self: center;
  width: 126px;
  height: 38px;
  border: 0;
  border-radius: 12px;
  background: #3d4a5f;
  color: rgba(255, 255, 255, 0.92);
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
}

.calendar-card {
  flex: 1;
  min-width: 400px;
  min-height: 0;
  border-radius: 14px;
  border: 1px solid #313d4f;
  background: #273142;
  padding: 28px 24px 18px;
  display: flex;
  flex-direction: column;
}

.calendar-toolbar {
  height: 62px;
  display: grid;
  grid-template-columns: 180px 1fr 220px;
  align-items: start;
  gap: 20px;
}

.today-button,
.new-event-btn,
.month-switcher button {
  border: 0;
  color: white;
  cursor: pointer;
}

.today-button {
  justify-self: start;
  background: transparent;
  color: rgba(255, 255, 255, 0.78);
  font-size: 14px;
  font-weight: 700;
}

.month-switcher {
  justify-self: center;
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.month-switcher strong {
  min-width: 72px;
  text-align: center;
  font-size: 24px;
  line-height: 28px;
  font-weight: 900;
}

.month-switcher button {
  width: 22px;
  height: 28px;
  background: transparent;
  color: rgba(255, 255, 255, 0.74);
  font-size: 26px;
  line-height: 24px;
}

.new-event-btn {
  justify-self: end;
  width: 200px;
  height: 40px;
  border-radius: 8px;
  background: #4880ff;
  font-weight: 800;
  font-size: 14px;
}

.calendar-weekdays {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  height: 48px;
  border: 1px solid #313d4f;
  border-bottom: 0;
  border-radius: 12px 12px 0 0;
  overflow: hidden;
  background: #323d4e;
}

.calendar-weekdays span {
  display: grid;
  place-items: center;
  font-size: 14px;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.92);
}

.calendar-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  grid-template-rows: repeat(6, minmax(0, 1fr));
  border: 1px solid #313d4f;
  border-top: 0;
}

.calendar-cell {
  position: relative;
  min-width: 0;
  border: 0;
  border-right: 1px solid rgba(49, 61, 79, 0.7);
  border-bottom: 1px solid rgba(49, 61, 79, 0.7);
  background: transparent;
  color: white;
  cursor: pointer;
  overflow: hidden;
}

.calendar-cell:nth-child(7n) {
  border-right: 0;
}

.calendar-cell.muted {
  background:
    repeating-linear-gradient(153deg, rgba(72, 128, 255, 0.08) 0 1px, transparent 1px 9px),
    rgba(27, 36, 50, 0.35);
}

.calendar-cell.selected {
  box-shadow: inset 0 0 0 2px rgba(72, 128, 255, 0.65);
}

.calendar-cell.today .day-number {
  color: #4880ff;
}

.day-number {
  position: absolute;
  top: 14px;
  right: 20px;
  font-size: 16px;
  font-weight: 700;
}

.calendar-event {
  position: relative;
  display: block;
  width: calc(100% - 2px);
  height: 28px;
  margin-top: 48px;
  padding: 5px 8px 4px 18px;
  overflow: hidden;
  color: var(--event-color);
  background:
    linear-gradient(90deg, var(--event-color) 0 4px, transparent 4px),
    repeating-linear-gradient(0deg, color-mix(in srgb, var(--event-color) 22%, transparent) 0 1px, transparent 1px 4px),
    color-mix(in srgb, var(--event-color) 16%, transparent);
  font-size: 10px;
  font-weight: 900;
  line-height: 10px;
  text-overflow: ellipsis;
}

.calendar-event + .calendar-event {
  margin-top: 4px;
}

.calendar-event.done {
  opacity: 0.52;
}

.calendar-more {
  position: absolute;
  left: 10px;
  bottom: 8px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.62);
}

.task-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 120;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(10, 15, 24, 0.72);
  backdrop-filter: blur(10px);
}

.task-modal {
  width: min(460px, 100%);
  border: 1px solid #313d4f;
  border-radius: 14px;
  background: #273142;
  padding: 20px;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.35);
}

.task-modal header,
.task-modal footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.task-modal header p {
  margin: 0;
  font-size: 18px;
  font-weight: 900;
}

.task-modal header button {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 8px;
  background: #3d4a5f;
  color: white;
  font-size: 20px;
  cursor: pointer;
}

.task-modal label {
  display: grid;
  gap: 8px;
  margin-top: 16px;
}

.task-modal label span {
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  font-weight: 800;
}

.task-modal input {
  height: 42px;
  border: 1px solid #3d4a5f;
  border-radius: 8px;
  background: #1b2432;
  color: white;
  padding: 0 12px;
  outline: none;
}

.task-modal input:focus {
  border-color: #4880ff;
}

.task-modal-grid {
  display: grid;
  grid-template-columns: 1fr 140px;
  gap: 12px;
}

.accent-row {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}

.accent-row button {
  width: 26px;
  height: 26px;
  border: 2px solid transparent;
  border-radius: 999px;
  cursor: pointer;
}

.accent-row button.active {
  border-color: white;
}

.task-modal footer {
  margin-top: 20px;
  justify-content: flex-end;
}

.task-modal footer button {
  height: 38px;
  border: 0;
  border-radius: 8px;
  padding: 0 16px;
  background: #4880ff;
  color: white;
  font-weight: 900;
  cursor: pointer;
}

.task-modal footer button.ghost {
  background: #3d4a5f;
}

.task-modal footer button:disabled {
  opacity: 0.55;
  cursor: wait;
}

.focus-mode-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 20;
  height: 76px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 32px;
}

.focus-mode-status {
  display: flex;
  align-items: center;
  gap: 10px;
  color: rgba(147, 197, 253, 0.9);
  text-transform: uppercase;
  letter-spacing: 0;
  font-size: 12px;
}

.focus-mode-status span {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #4880ff;
  box-shadow: 0 0 18px rgba(72, 128, 255, 0.8);
}

.focus-mode-actions {
  display: flex;
  gap: 10px;
}

.focus-mode-actions button {
  height: 36px;
  border: 1px solid rgba(72, 128, 255, 0.34);
  border-radius: 8px;
  background: rgba(39, 49, 66, 0.65);
  color: white;
  padding: 0 14px;
  cursor: pointer;
}

.focus-mode-main {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 80px 24px;
  background:
    radial-gradient(circle at 50% 48%, rgba(72, 128, 255, 0.16), transparent 42%),
    #111827;
}

.focus-mode-panel {
  width: min(820px, 100%);
  text-align: center;
}

.focus-mode-goal p {
  margin: 0;
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  text-transform: uppercase;
  font-weight: 900;
}

.focus-mode-goal h2 {
  margin: 10px 0 0;
  color: white;
  font-size: 28px;
  font-weight: 700;
}

.focus-mode-time {
  margin: 28px 0 0;
  color: white;
  font-size: clamp(84px, 13vw, 144px);
  line-height: 1;
  font-weight: 300;
}

.focus-mode-time span {
  color: rgba(255, 255, 255, 0.28);
}

.focus-mode-task {
  width: min(640px, 100%);
  margin: 36px auto 0;
  border: 1px solid rgba(72, 128, 255, 0.28);
  border-radius: 14px;
  background: rgba(39, 49, 66, 0.68);
  padding: 22px;
}

.focus-mode-task p {
  margin: 0;
  color: #82a8ff;
  font-size: 11px;
  font-weight: 900;
  text-transform: uppercase;
}

.focus-mode-task h3 {
  margin: 10px 0 0;
  color: white;
  font-size: 22px;
  line-height: 1.35;
}

.focus-mode-controls {
  margin-top: 34px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 28px;
}

.focus-mode-controls button {
  border: 0;
  border-radius: 999px;
  display: grid;
  place-items: center;
  color: white;
  cursor: pointer;
}

.focus-mode-controls svg {
  width: 24px;
  height: 24px;
}

.focus-mode-controls .danger,
.focus-mode-controls .success {
  width: 46px;
  height: 46px;
  background: rgba(255, 255, 255, 0.08);
}

.focus-mode-controls .primary {
  width: 64px;
  height: 64px;
  background: rgba(72, 128, 255, 0.22);
  border: 1px solid rgba(72, 128, 255, 0.55);
  box-shadow: 0 0 28px rgba(72, 128, 255, 0.22);
}

.focus-init-error {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(10, 15, 24, 0.94);
}

.focus-init-error-card {
  width: min(560px, 100%);
  border: 1px solid rgba(255, 143, 163, 0.4);
  border-radius: 14px;
  background: #273142;
  padding: 24px;
}

.focus-init-error-card p,
.focus-init-error-card h2 {
  margin: 0;
}

.focus-init-error-card p {
  color: #ff8fa3;
  font-size: 12px;
  font-weight: 900;
  text-transform: uppercase;
}

.focus-init-error-card h2 {
  margin-top: 8px;
  font-size: 22px;
}

.focus-init-error-card span {
  display: block;
  margin-top: 12px;
  color: rgba(255, 255, 255, 0.72);
}

.focus-init-error-card div {
  display: flex;
  gap: 10px;
  margin-top: 18px;
}

.focus-init-error-card button {
  height: 38px;
  border: 0;
  border-radius: 8px;
  background: #4880ff;
  color: white;
  padding: 0 14px;
  cursor: pointer;
}

@media (max-width: 1120px) {
  .figma-home-main {
    padding-right: 24px;
    gap: 22px;
  }

  .calendar-toolbar {
    grid-template-columns: 90px 1fr 160px;
  }

  .new-event-btn {
    width: 160px;
  }
}

@media (max-width: 900px) {
  .figma-side-rail {
    width: 60px;
  }

  .figma-side-rail button.active::before {
    left: -4px;
  }

  .figma-top-bar {
    left: 60px;
    padding: 0 18px;
  }

  .profile-copy {
    display: none;
  }

  .profile-button {
    grid-template-columns: 44px 18px;
  }

  .figma-home-main {
    padding: 88px 16px 22px 76px;
    flex-direction: column;
    overflow-y: auto;
    height: auto;
    min-height: 100vh;
  }

  .figma-left-column {
    width: 100%;
    flex-basis: auto;
  }

  .task-list-panel {
    min-height: 360px;
  }

  .calendar-card {
    min-width: 0;
  }

  .calendar-toolbar {
    height: auto;
    grid-template-columns: 1fr;
    align-items: center;
  }

  .today-button,
  .new-event-btn,
  .month-switcher {
    justify-self: stretch;
  }

  .new-event-btn {
    width: 100%;
  }

  .calendar-grid {
    min-height: 620px;
    grid-template-rows: repeat(6, minmax(92px, 1fr));
  }
}

@media (max-width: 620px) {
  .figma-side-rail {
    display: none;
  }

  .figma-top-bar {
    left: 0;
  }

  .figma-home-main {
    padding-left: 14px;
    padding-right: 14px;
  }

  .timer-row > strong {
    font-size: 32px;
  }

  .calendar-weekdays span {
    font-size: 11px;
  }

  .day-number {
    top: 10px;
    right: 10px;
    font-size: 13px;
  }

  .calendar-event {
    padding-left: 8px;
    font-size: 9px;
  }

  .task-modal-grid {
    grid-template-columns: 1fr;
  }
}
</style>
