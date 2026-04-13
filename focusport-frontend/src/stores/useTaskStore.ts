import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'

const STORAGE_KEY = 'focusport.p0.tasks.snapshot.v1'
const AI_DELAY_MS = 2000
const __P0_DEBUG__ = import.meta.env.DEV

type Nullable<T> = T | null

export type TaskStatus = 'todo' | 'done'
export type AnalysisState = 'idle' | 'loading' | 'done' | 'error'
export type SessionSource = 'focus-finished' | 'focus-interrupted'
export type CompletionStatus = 'full' | 'partial' | 'failed'

export type AIAnalysisPayload = {
  score: number
  focusLevel: 'S' | 'A' | 'B' | 'C' | 'D'
  expGained: number
  computePowerGained: number
  summary: string
  encouragement: string
  multiplier: number
  distractionDetected: boolean
  completionStatus: CompletionStatus
  behaviorTags: string[]
}

export type AnalysisResult = {
  score: number
  focusLevel: 'S' | 'A' | 'B' | 'C' | 'D'
  completionStatus: CompletionStatus
  behaviorTags: string[]
  distractionDetected: boolean
  incompleteDetected: boolean
  honestyBonus: boolean
  multiplier: number
  summary: string
  encouragement: string
}

export type RewardResult = {
  finalCU: number
  finalExp: number
  multiplier: number
  energyGained: number
}

export type Wallet = {
  computePower: number
  energy: number
}

export type Task = {
  id: string
  title: string
  status: TaskStatus
  totalFocusSeconds: number
  actualPomodoros: number
  isCarriedOver: boolean
  carryOverCount?: number
  priority?: number
  isHidden?: boolean
  isDeleted?: boolean
  createdAt: number
  updatedAt: number
  completedAt: Nullable<number>
}

export type SessionLog = {
  id: string
  taskId: string
  startedAt: number
  endedAt: number
  focusSeconds: number
  isFullPomodoro: boolean
  source: SessionSource
  restoredFromSnapshot: boolean
}

export type TaskCompletionLog = {
  id: string
  taskId: string
  completedAt: number
  note?: string
}

export type TaskRewardLog = {
  id: string
  taskId: string
  completedAt: number
  expGained: number
  computePowerGained: number
  energyGained?: number
  multiplier?: number
  focusLevel?: 'S' | 'A' | 'B' | 'C' | 'D'
  distractionDetected?: boolean
}

export type DaySummary = {
  dateKey: string
  completedCount: number
  totalFocusSeconds: number
  totalPomodoros: number
  totalComputePowerGained: number
  totalExpGained: number
  completedTasks: Task[]
  pendingTasks: Task[]
}

export type PlannedTaskDraft = {
  title: string
  estimatedPomodoros?: number
  priority?: number
  note?: string
}

export type CommitSessionInput = {
  taskId: string
  startedAt: number
  endedAt: number
  focusSeconds: number
  isFullPomodoro: boolean
  source: SessionSource
  restoredFromSnapshot?: boolean
}

type AIAnalysisInput = {
  note?: string
  completedAt: number
  totalFocusSeconds: number
  actualPomodoros: number
}

type Snapshot = {
  tasks: Task[]
  sessionLogs: SessionLog[]
  taskCompletionLogs: TaskCompletionLog[]
  taskRewardLogs: TaskRewardLog[]
  wallet: Wallet
  analysisStateByTaskId: Record<string, AnalysisState>
  analysisResultByTaskId: Record<string, AIAnalysisPayload>
  lastRolloverDateKey: Nullable<string>
  lastSeenDateKey: Nullable<string>
}

const DISTRACTION_KEYWORDS = ['手机', '刷手机', '分心', '走神', '发呆', '摸鱼', '拖延', '切窗口', '一直切窗口', '看视频']
const INCOMPLETE_KEYWORDS = ['没做完', '未完成', '只做一半', '还差很多', '没开始', '几乎没做', '基本没做']
const FAILED_KEYWORDS = ['没开始', '几乎没做', '基本没做']
const HONESTY_MIN_NOTE_LENGTH = 8

const pendingAnalysisByTaskId = new Map<string, Promise<AIAnalysisPayload>>()

const debugLog = (...args: unknown[]): void => {
  if (!__P0_DEBUG__) return
  console.info('[TaskStore:P1]', ...args)
}

const nowTs = (): number => Date.now()

const makeDateKey = (ts: number): string => {
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const generateId = (prefix: string): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}-${crypto.randomUUID()}`
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

const toNumber = (value: unknown, fallback = 0): number => {
  const casted = Number(value)
  if (!Number.isFinite(casted)) return fallback
  return casted
}

const clampInt = (value: unknown, min = 0): number => Math.max(min, Math.floor(toNumber(value, min)))
const clamp = (value: number, min: number, max: number): number => Math.min(max, Math.max(min, value))

const safeParse = (raw: string | null): unknown => {
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch (error) {
    console.warn('[useTaskStore] Failed to parse snapshot', error)
    return null
  }
}

const normalizeTask = (raw: any): Task | null => {
  const id = String(raw?.id || '').trim()
  const title = String(raw?.title || '').trim()
  if (!id || !title) return null

  const status: TaskStatus = raw?.status === 'done' ? 'done' : 'todo'
  const createdAt = clampInt(raw?.createdAt, nowTs())
  const updatedAt = clampInt(raw?.updatedAt, createdAt)
  const completedAt = status === 'done' ? clampInt(raw?.completedAt, updatedAt) : null

  return {
    id,
    title,
    status,
    totalFocusSeconds: clampInt(raw?.totalFocusSeconds, 0),
    actualPomodoros: clampInt(raw?.actualPomodoros, 0),
    isCarriedOver: Boolean(raw?.isCarriedOver),
    carryOverCount: clampInt(raw?.carryOverCount, 0),
    priority: clampInt(raw?.priority, 0),
    isHidden: Boolean(raw?.isHidden),
    isDeleted: Boolean(raw?.isDeleted),
    createdAt,
    updatedAt,
    completedAt
  }
}

const normalizeSessionLog = (raw: any): SessionLog | null => {
  const id = String(raw?.id || '').trim()
  const taskId = String(raw?.taskId || '').trim()
  if (!id || !taskId) return null
  const startedAt = clampInt(raw?.startedAt, 0)
  const endedAt = Math.max(startedAt, clampInt(raw?.endedAt, startedAt))
  return {
    id,
    taskId,
    startedAt,
    endedAt,
    focusSeconds: clampInt(raw?.focusSeconds, 0),
    isFullPomodoro: Boolean(raw?.isFullPomodoro),
    source: raw?.source === 'focus-interrupted' ? 'focus-interrupted' : 'focus-finished',
    restoredFromSnapshot: Boolean(raw?.restoredFromSnapshot)
  }
}

const normalizeCompletionLog = (raw: any): TaskCompletionLog | null => {
  const id = String(raw?.id || '').trim()
  const taskId = String(raw?.taskId || '').trim()
  if (!id || !taskId) return null
  const completedAt = clampInt(raw?.completedAt, 0)
  return { id, taskId, completedAt, note: raw?.note ? String(raw.note) : undefined }
}

const normalizeRewardLog = (raw: any): TaskRewardLog | null => {
  const id = String(raw?.id || '').trim()
  const taskId = String(raw?.taskId || '').trim()
  if (!id || !taskId) return null
  return {
    id,
    taskId,
    completedAt: clampInt(raw?.completedAt, 0),
    expGained: clampInt(raw?.expGained, 0),
    computePowerGained: clampInt(raw?.computePowerGained, 0),
    energyGained: clampInt(raw?.energyGained, 0),
    multiplier: toNumber(raw?.multiplier, 1),
    focusLevel: ['S', 'A', 'B', 'C', 'D'].includes(raw?.focusLevel) ? raw.focusLevel : 'B',
    distractionDetected: Boolean(raw?.distractionDetected)
  }
}

const normalizeWallet = (raw: any): Wallet => ({
  computePower: clampInt(raw?.computePower, 0),
  energy: clampInt(raw?.energy, 0)
})

const normalizeAnalysisState = (raw: unknown): AnalysisState => {
  if (raw === 'loading' || raw === 'done' || raw === 'error') return raw
  return 'idle'
}

const normalizeAnalysisStateByTaskId = (raw: any): Record<string, AnalysisState> => {
  if (!raw || typeof raw !== 'object') return {}
  return Object.fromEntries(
    Object.entries(raw)
      .filter(([taskId]) => Boolean(taskId))
      .map(([taskId, value]) => [taskId, normalizeAnalysisState(value)])
  )
}

const normalizeAIAnalysisPayload = (raw: any): AIAnalysisPayload | null => {
  if (!raw || typeof raw !== 'object') return null
  return {
    score: clampInt(raw?.score, 0),
    focusLevel: ['S', 'A', 'B', 'C', 'D'].includes(raw?.focusLevel) ? raw.focusLevel : 'B',
    expGained: clampInt(raw?.expGained, 0),
    computePowerGained: clampInt(raw?.computePowerGained, 0),
    summary: String(raw?.summary || ''),
    encouragement: String(raw?.encouragement || ''),
    multiplier: toNumber(raw?.multiplier, 1),
    distractionDetected: Boolean(raw?.distractionDetected),
    completionStatus: ['full', 'partial', 'failed'].includes(raw?.completionStatus) ? raw.completionStatus : 'full',
    behaviorTags: Array.isArray(raw?.behaviorTags) ? raw.behaviorTags.map((v: unknown) => String(v)) : []
  }
}

const normalizeAnalysisResultByTaskId = (raw: any): Record<string, AIAnalysisPayload> => {
  if (!raw || typeof raw !== 'object') return {}
  const result: Record<string, AIAnalysisPayload> = {}
  Object.entries(raw).forEach(([taskId, payload]) => {
    const normalized = normalizeAIAnalysisPayload(payload)
    if (taskId && normalized) result[taskId] = normalized
  })
  return result
}

const loadSnapshot = (): Snapshot => {
  const fallback: Snapshot = {
    tasks: [],
    sessionLogs: [],
    taskCompletionLogs: [],
    taskRewardLogs: [],
    wallet: { computePower: 0, energy: 0 },
    analysisStateByTaskId: {},
    analysisResultByTaskId: {},
    lastRolloverDateKey: null,
    lastSeenDateKey: null
  }
  if (typeof window === 'undefined') return fallback

  const raw = safeParse(window.localStorage.getItem(STORAGE_KEY)) as any
  if (!raw || typeof raw !== 'object') return fallback

  return {
    tasks: Array.isArray(raw.tasks) ? (raw.tasks.map(normalizeTask).filter(Boolean) as Task[]) : [],
    sessionLogs: Array.isArray(raw.sessionLogs) ? (raw.sessionLogs.map(normalizeSessionLog).filter(Boolean) as SessionLog[]) : [],
    taskCompletionLogs: Array.isArray(raw.taskCompletionLogs)
      ? (raw.taskCompletionLogs.map(normalizeCompletionLog).filter(Boolean) as TaskCompletionLog[])
      : [],
    taskRewardLogs: Array.isArray(raw.taskRewardLogs)
      ? (raw.taskRewardLogs.map(normalizeRewardLog).filter(Boolean) as TaskRewardLog[])
      : [],
    wallet: normalizeWallet(raw.wallet),
    analysisStateByTaskId: normalizeAnalysisStateByTaskId(raw.analysisStateByTaskId),
    analysisResultByTaskId: normalizeAnalysisResultByTaskId(raw.analysisResultByTaskId),
    lastRolloverDateKey: raw.lastRolloverDateKey ? String(raw.lastRolloverDateKey) : null,
    lastSeenDateKey: raw.lastSeenDateKey ? String(raw.lastSeenDateKey) : null
  }
}

const makeSessionLogId = (taskId: string, startedAt: number, endedAt: number, source: SessionSource): string =>
  `session:${taskId}:${startedAt}:${endedAt}:${source}`
const makeRewardLogId = (taskId: string, completedAt: number): string => `reward:${taskId}:${completedAt}`
const isTaskVisible = (task: Task): boolean => !task.isHidden && !task.isDeleted

const matchKeywords = (source: string, keywords: string[]): string[] => keywords.filter((keyword) => source.includes(keyword))

const evaluateAnalysis = (input: AIAnalysisInput): AnalysisResult => {
  const note = String(input.note || '').trim()
  const normalizedNote = note.toLowerCase()
  const distractionTags = matchKeywords(normalizedNote, DISTRACTION_KEYWORDS)
  const incompleteTags = matchKeywords(normalizedNote, INCOMPLETE_KEYWORDS)
  const failedTags = matchKeywords(normalizedNote, FAILED_KEYWORDS)

  const distractionDetected = distractionTags.length > 0
  const incompleteDetected = incompleteTags.length > 0
  const completionStatus: CompletionStatus = failedTags.length > 0 ? 'failed' : incompleteDetected ? 'partial' : 'full'
  const behaviorTags = [...new Set([...distractionTags, ...incompleteTags])]
  const honestyBonus = behaviorTags.length > 0 && note.replace(/\s/g, '').length >= HONESTY_MIN_NOTE_LENGTH

  const rawScore = 45
    + Math.round(input.totalFocusSeconds / 60)
    + Math.round(input.actualPomodoros * 6)
    - (distractionDetected ? 18 : 0)
    - (completionStatus === 'partial' ? 12 : 0)
    - (completionStatus === 'failed' ? 24 : 0)
  const score = clamp(rawScore, 5, 99)
  const focusLevel: AnalysisResult['focusLevel'] = score >= 90 ? 'S' : score >= 78 ? 'A' : score >= 62 ? 'B' : score >= 45 ? 'C' : 'D'

  const gradeMultiplierMap: Record<AnalysisResult['focusLevel'], number> = { S: 1.2, A: 1.2, B: 1.0, C: 0.7, D: 0.4 }
  const completionMultiplierMap: Record<CompletionStatus, number> = { full: 1.0, partial: 0.8, failed: 0.5 }
  const multiplier = Math.max(
    0,
    Number(
      (
        gradeMultiplierMap[focusLevel]
        * completionMultiplierMap[completionStatus]
        * (distractionDetected ? 0.5 : 1)
        * (honestyBonus ? 1.05 : 1)
      ).toFixed(2)
    )
  )

  const summary = distractionDetected
    ? '检测到分心行为，本轮收益已按规则下调。'
    : completionStatus === 'failed'
      ? '任务完成度较低，本轮以保底收益结算。'
      : completionStatus === 'partial'
        ? '任务部分完成，收益按完成度折算。'
        : '任务完成状态良好，收益按标准倍率结算。'

  const encouragement = honestyBonus
    ? '检测到诚实复盘，已给予微小修正加成。'
    : '保持复盘质量，下一轮可获得更稳定收益。'

  return {
    score,
    focusLevel,
    completionStatus,
    behaviorTags,
    distractionDetected,
    incompleteDetected,
    honestyBonus,
    multiplier,
    summary,
    encouragement
  }
}

const calculateReward = (analysis: AnalysisResult, totalFocusSeconds: number): RewardResult => {
  const safeSeconds = clampInt(totalFocusSeconds, 0)
  const baseCU = Math.floor(safeSeconds / 60)
  const baseExp = Math.max(1, Math.round(safeSeconds / 120))
  return {
    finalCU: Math.max(0, Math.round(baseCU * analysis.multiplier)),
    finalExp: Math.max(0, Math.round(baseExp * analysis.multiplier)),
    multiplier: analysis.multiplier,
    energyGained: 0
  }
}

export const useTaskStore = defineStore('taskStore', () => {
  const snapshot = loadSnapshot()

  const tasks = ref<Task[]>(snapshot.tasks)
  const sessionLogs = ref<SessionLog[]>(snapshot.sessionLogs)
  const taskCompletionLogs = ref<TaskCompletionLog[]>(snapshot.taskCompletionLogs)
  const taskRewardLogs = ref<TaskRewardLog[]>(snapshot.taskRewardLogs)
  const wallet = ref<Wallet>(snapshot.wallet)
  const analysisStateByTaskId = ref<Record<string, AnalysisState>>(snapshot.analysisStateByTaskId)
  const analysisResultByTaskId = ref<Record<string, AIAnalysisPayload>>(snapshot.analysisResultByTaskId)
  const lastRolloverDateKey = ref<Nullable<string>>(snapshot.lastRolloverDateKey)
  const lastSeenDateKey = ref<Nullable<string>>(snapshot.lastSeenDateKey)

  const persistSnapshot = (): void => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({
      tasks: tasks.value,
      sessionLogs: sessionLogs.value,
      taskCompletionLogs: taskCompletionLogs.value,
      taskRewardLogs: taskRewardLogs.value,
      wallet: wallet.value,
      analysisStateByTaskId: analysisStateByTaskId.value,
      analysisResultByTaskId: analysisResultByTaskId.value,
      lastRolloverDateKey: lastRolloverDateKey.value,
      lastSeenDateKey: lastSeenDateKey.value
    }))
  }

  const getTaskById = (taskId: string): Task | undefined => tasks.value.find((task) => task.id === taskId)
  const getLatestRewardLogByTaskId = (taskId: string): TaskRewardLog | undefined => {
    return taskRewardLogs.value
      .filter((log) => log.taskId === taskId)
      .sort((left, right) => right.completedAt - left.completedAt)[0]
  }

  const addTask = (title: string): Task | null => {
    const nextTitle = String(title || '').trim()
    if (!nextTitle) return null
    const timestamp = nowTs()
    const task: Task = {
      id: generateId('task'),
      title: nextTitle,
      status: 'todo',
      totalFocusSeconds: 0,
      actualPomodoros: 0,
      isCarriedOver: false,
      carryOverCount: 0,
      priority: 0,
      isHidden: false,
      isDeleted: false,
      createdAt: timestamp,
      updatedAt: timestamp,
      completedAt: null
    }
    tasks.value.push(task)
    debugLog('addTask', { taskId: task.id })
    return task
  }

  const importPlannedTasks = (drafts: PlannedTaskDraft[]): Task[] => {
    if (!Array.isArray(drafts) || drafts.length === 0) return []
    const created: Task[] = []
    drafts.forEach((draft) => {
      const title = String(draft?.title || '').trim()
      if (!title) return
      const timestamp = nowTs()
      const task: Task = {
        id: generateId('task'),
        title,
        status: 'todo',
        totalFocusSeconds: 0,
        actualPomodoros: 0,
        isCarriedOver: false,
        carryOverCount: 0,
        priority: clampInt(draft?.priority, 0),
        isHidden: false,
        isDeleted: false,
        createdAt: timestamp,
        updatedAt: timestamp,
        completedAt: null
      }
      tasks.value.push(task)
      created.push(task)
    })
    if (created.length > 0) {
      debugLog('importPlannedTasks', { count: created.length })
    }
    return created
  }

  const updateTaskTitle = (taskId: string, title: string): boolean => {
    const task = getTaskById(taskId)
    const nextTitle = String(title || '').trim()
    if (!task || !nextTitle) return false
    task.title = nextTitle
    task.updatedAt = nowTs()
    return true
  }

  const deleteTask = (taskId: string): boolean => {
    const before = tasks.value.length
    tasks.value = tasks.value.filter((task) => task.id !== taskId)
    delete analysisStateByTaskId.value[taskId]
    delete analysisResultByTaskId.value[taskId]
    return tasks.value.length !== before
  }

  const commitSessionToTask = (input: CommitSessionInput): boolean => {
    const task = getTaskById(input.taskId)
    if (!task) return false

    const startedAt = clampInt(input.startedAt, 0)
    const endedAt = Math.max(startedAt, clampInt(input.endedAt, startedAt))
    const source: SessionSource = input.source === 'focus-interrupted' ? 'focus-interrupted' : 'focus-finished'
    const logId = makeSessionLogId(task.id, startedAt, endedAt, source)
    if (sessionLogs.value.some((log) => log.id === logId)) return false

    const focusSeconds = clampInt(input.focusSeconds, 0)
    const isFullPomodoro = Boolean(input.isFullPomodoro)
    sessionLogs.value.push({
      id: logId,
      taskId: task.id,
      startedAt,
      endedAt,
      focusSeconds,
      isFullPomodoro,
      source,
      restoredFromSnapshot: Boolean(input.restoredFromSnapshot)
    })

    task.totalFocusSeconds += focusSeconds
    if (isFullPomodoro) task.actualPomodoros += 1
    task.updatedAt = nowTs()
    return true
  }

  const completeTask = (taskId: string, note?: string): boolean => {
    const task = getTaskById(taskId)
    if (!task) return false
    if (task.status === 'done') return false

    const completedAt = nowTs()
    task.status = 'done'
    task.completedAt = completedAt
    task.updatedAt = completedAt
    taskCompletionLogs.value.push({
      id: `complete:${taskId}:${completedAt}`,
      taskId,
      completedAt,
      note: String(note || '').trim() || undefined
    })
    return true
  }

  const findRewardByKey = (taskId: string, completedAt: number): TaskRewardLog | undefined => {
    const id = makeRewardLogId(taskId, completedAt)
    return taskRewardLogs.value.find((log) => log.id === id)
  }

  const makePayloadFromReward = (reward: TaskRewardLog, fallback: Partial<AIAnalysisPayload> = {}): AIAnalysisPayload => ({
    score: fallback.score ?? 60,
    focusLevel: fallback.focusLevel ?? reward.focusLevel ?? 'B',
    expGained: reward.expGained,
    computePowerGained: reward.computePowerGained,
    summary: fallback.summary ?? '已读取历史结算结果。',
    encouragement: fallback.encouragement ?? '保持节律，持续推进。',
    multiplier: fallback.multiplier ?? reward.multiplier ?? 1,
    distractionDetected: fallback.distractionDetected ?? Boolean(reward.distractionDetected),
    completionStatus: fallback.completionStatus ?? 'full',
    behaviorTags: fallback.behaviorTags ?? []
  })

  const appendRewardAndWalletAtomically = (
    taskId: string,
    completedAt: number,
    analysis: AnalysisResult,
    reward: RewardResult
  ): TaskRewardLog => {
    const existing = findRewardByKey(taskId, completedAt)
    if (existing) {
      debugLog('reward log dedup hit', { taskId, completedAt })
      return existing
    }

    wallet.value.computePower += reward.finalCU
    wallet.value.energy += reward.energyGained
    debugLog('wallet updated', {
      taskId,
      completedAt,
      computePower: wallet.value.computePower,
      energy: wallet.value.energy
    })

    const log: TaskRewardLog = {
      id: makeRewardLogId(taskId, completedAt),
      taskId,
      completedAt,
      expGained: reward.finalExp,
      computePowerGained: reward.finalCU,
      energyGained: reward.energyGained,
      multiplier: reward.multiplier,
      focusLevel: analysis.focusLevel,
      distractionDetected: analysis.distractionDetected
    }
    taskRewardLogs.value.push(log)
    return log
  }

  const triggerAIAnalysis = (taskId: string, payload: AIAnalysisInput): Promise<AIAnalysisPayload> => {
    const task = getTaskById(taskId)
    if (!task) return Promise.reject(new Error('Task not found'))

    const stableCompletedAt = clampInt(payload.completedAt, task.completedAt ?? nowTs())
    const existingReward = findRewardByKey(taskId, stableCompletedAt)
    if (existingReward) {
      debugLog('reward log dedup hit', { taskId, completedAt: stableCompletedAt, phase: 'before-analysis' })
      const cached = analysisResultByTaskId.value[taskId]
      const result = makePayloadFromReward(existingReward, cached || {})
      analysisStateByTaskId.value[taskId] = 'done'
      analysisResultByTaskId.value[taskId] = result
      return Promise.resolve(result)
    }

    const pendingKey = `${taskId}:${stableCompletedAt}`
    const existingPromise = pendingAnalysisByTaskId.get(pendingKey)
    if (existingPromise) return existingPromise

    analysisStateByTaskId.value[taskId] = 'loading'
    debugLog('analysis started', { taskId, completedAt: stableCompletedAt })

    const promise = new Promise<AIAnalysisPayload>((resolve) => {
      setTimeout(() => {
        const analysis = evaluateAnalysis({
          note: payload.note,
          completedAt: stableCompletedAt,
          totalFocusSeconds: payload.totalFocusSeconds,
          actualPomodoros: payload.actualPomodoros
        })
        const reward = calculateReward(analysis, payload.totalFocusSeconds)
        debugLog('reward calculated', {
          taskId,
          completedAt: stableCompletedAt,
          multiplier: reward.multiplier,
          finalCU: reward.finalCU,
          finalExp: reward.finalExp
        })
        const rewardLog = appendRewardAndWalletAtomically(taskId, stableCompletedAt, analysis, reward)

        resolve({
          score: analysis.score,
          focusLevel: analysis.focusLevel,
          expGained: rewardLog.expGained,
          computePowerGained: rewardLog.computePowerGained,
          summary: analysis.summary,
          encouragement: analysis.encouragement,
          multiplier: analysis.multiplier,
          distractionDetected: analysis.distractionDetected,
          completionStatus: analysis.completionStatus,
          behaviorTags: analysis.behaviorTags
        })
      }, AI_DELAY_MS)
    })
      .then((result) => {
        analysisStateByTaskId.value[taskId] = 'done'
        analysisResultByTaskId.value[taskId] = result
        pendingAnalysisByTaskId.delete(pendingKey)
        return result
      })
      .catch((error) => {
        analysisStateByTaskId.value[taskId] = 'error'
        pendingAnalysisByTaskId.delete(pendingKey)
        throw error
      })

    pendingAnalysisByTaskId.set(pendingKey, promise)
    return promise
  }

  const convertCUToEnergy = (): { converted: number; consumedCU: number; remainingCU: number; energy: number } => {
    const converted = Math.floor(wallet.value.computePower / 100)
    const consumedCU = converted * 100
    if (converted <= 0) {
      return {
        converted: 0,
        consumedCU: 0,
        remainingCU: wallet.value.computePower,
        energy: wallet.value.energy
      }
    }

    wallet.value.computePower -= consumedCU
    wallet.value.energy += converted
    debugLog('CU converted to energy', {
      converted,
      consumedCU,
      remainingCU: wallet.value.computePower,
      energy: wallet.value.energy
    })
    return {
      converted,
      consumedCU,
      remainingCU: wallet.value.computePower,
      energy: wallet.value.energy
    }
  }

  const rolloverPendingTasks = (currentTs = nowTs()): void => {
    const todayKey = makeDateKey(currentTs)

    if (!lastSeenDateKey.value) {
      lastSeenDateKey.value = todayKey
      lastRolloverDateKey.value = todayKey
      return
    }

    if (lastRolloverDateKey.value === todayKey) {
      lastSeenDateKey.value = todayKey
      return
    }

    if (lastSeenDateKey.value !== todayKey) {
      tasks.value.forEach((task) => {
        if (task.status !== 'todo' || !isTaskVisible(task)) return
        task.isCarriedOver = true
        task.carryOverCount = clampInt(task.carryOverCount, 0) + 1
        task.updatedAt = currentTs
      })
    }

    lastSeenDateKey.value = todayKey
    lastRolloverDateKey.value = todayKey
  }

  const getDailyStats = (dateKey?: string): { dateKey: string; completedCount: number; totalFocusSeconds: number } => {
    const targetDateKey = String(dateKey || '').trim() || makeDateKey(nowTs())
    const completedTaskIds = new Set<string>()
    taskCompletionLogs.value
      .filter((log) => makeDateKey(log.completedAt) === targetDateKey)
      .sort((a, b) => a.completedAt - b.completedAt)
      .forEach((log) => completedTaskIds.add(log.taskId))

    const totalFocusSeconds = sessionLogs.value.reduce((total, log) => {
      return total + (makeDateKey(log.endedAt) === targetDateKey ? log.focusSeconds : 0)
    }, 0)
    return { dateKey: targetDateKey, completedCount: completedTaskIds.size, totalFocusSeconds }
  }

  const getDaySummary = (dateKey?: string): DaySummary => {
    const targetDateKey = String(dateKey || '').trim() || makeDateKey(nowTs())
    const firstCompletionByTaskId = new Map<string, TaskCompletionLog>()
    taskCompletionLogs.value
      .filter((log) => makeDateKey(log.completedAt) === targetDateKey)
      .sort((a, b) => a.completedAt - b.completedAt)
      .forEach((log) => {
        if (!firstCompletionByTaskId.has(log.taskId)) firstCompletionByTaskId.set(log.taskId, log)
      })

    const completedTasks = [...firstCompletionByTaskId.keys()]
      .map((taskId) => getTaskById(taskId))
      .filter(Boolean) as Task[]
    const pendingTasks = tasks.value.filter((task) => task.status === 'todo' && isTaskVisible(task))

    const totalFocusSeconds = sessionLogs.value.reduce((total, log) => {
      return total + (makeDateKey(log.endedAt) === targetDateKey ? log.focusSeconds : 0)
    }, 0)
    const totalPomodoros = sessionLogs.value.reduce((total, log) => {
      if (makeDateKey(log.endedAt) !== targetDateKey) return total
      return total + (log.isFullPomodoro ? 1 : 0)
    }, 0)
    const totalComputePowerGained = taskRewardLogs.value.reduce((total, log) => {
      return total + (makeDateKey(log.completedAt) === targetDateKey ? log.computePowerGained : 0)
    }, 0)
    const totalExpGained = taskRewardLogs.value.reduce((total, log) => {
      return total + (makeDateKey(log.completedAt) === targetDateKey ? log.expGained : 0)
    }, 0)

    return {
      dateKey: targetDateKey,
      completedCount: completedTasks.length,
      totalFocusSeconds,
      totalPomodoros,
      totalComputePowerGained,
      totalExpGained,
      completedTasks,
      pendingTasks
    }
  }

  const getNextDaySeedTask = (): Task | undefined => {
    const pendingTasks = tasks.value.filter((task) => task.status === 'todo' && isTaskVisible(task))
    if (!pendingTasks.length) return undefined
    return [...pendingTasks].sort((left, right) => {
      const priorityDiff = clampInt(right.priority, 0) - clampInt(left.priority, 0)
      if (priorityDiff !== 0) return priorityDiff
      const carryDiff = clampInt(right.carryOverCount, 0) - clampInt(left.carryOverCount, 0)
      if (carryDiff !== 0) return carryDiff
      return left.createdAt - right.createdAt
    })[0]
  }

  const todayStats = computed(() => getDailyStats())
  const walletBalance = computed(() => ({ ...wallet.value }))
  const isTaskAnalyzing = (taskId: string): boolean => analysisStateByTaskId.value[taskId] === 'loading'

  watch(
    [
      tasks,
      sessionLogs,
      taskCompletionLogs,
      taskRewardLogs,
      wallet,
      analysisStateByTaskId,
      analysisResultByTaskId,
      lastRolloverDateKey,
      lastSeenDateKey
    ],
    persistSnapshot,
    { deep: true }
  )

  rolloverPendingTasks(nowTs())
  persistSnapshot()

  return {
    tasks,
    sessionLogs,
    taskCompletionLogs,
    taskRewardLogs,
    wallet,
    analysisStateByTaskId,
    analysisResultByTaskId,
    lastRolloverDateKey,
    lastSeenDateKey,
    todayStats,
    walletBalance,
    addTask,
    importPlannedTasks,
    updateTaskTitle,
    deleteTask,
    getTaskById,
    getLatestRewardLogByTaskId,
    isTaskAnalyzing,
    commitSessionToTask,
    completeTask,
    triggerAIAnalysis,
    convertCUToEnergy,
    rolloverPendingTasks,
    getDailyStats,
    getDaySummary,
    getNextDaySeedTask
  }
})
