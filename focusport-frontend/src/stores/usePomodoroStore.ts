import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { useTaskStore } from './useTaskStore'

const SNAPSHOT_KEY = 'focusport.p0.pomodoro.snapshot.v1'
const LEADER_ID_KEY = 'focusport.p0.pomodoro.leaderId.v1'
const LAST_HEARTBEAT_KEY = 'focusport.p0.pomodoro.lastHeartbeat.v1'

const FOCUS_DURATION_SECONDS = 25 * 60
const BREAK_DURATION_SECONDS = 5 * 60
const TICK_INTERVAL_MS = 1000
const HEARTBEAT_INTERVAL_MS = 1000
const LEADER_STALE_MS = 2500

const __P0_DEBUG__ = import.meta.env.DEV

export type PomodoroMode = 'focus' | 'break'
export type PomodoroStatus = 'idle' | 'running' | 'paused'

type Nullable<T> = T | null

type Snapshot = {
  mode: PomodoroMode
  status: PomodoroStatus
  activeTaskId: Nullable<string>
  endAt: Nullable<number>
  nowTs: number
  sessionStartedAt: Nullable<number>
  runningSegmentStartedAt: Nullable<number>
  pausedRemainingSeconds: Nullable<number>
  accumulatedFocusSeconds: number
  lastSettledEndAt: Nullable<number>
}

const now = (): number => Date.now()

const debugLog = (...args: unknown[]): void => {
  if (!__P0_DEBUG__) return
  console.info('[PomodoroStore:P1]', ...args)
}

const safeParse = (raw: string | null): unknown => {
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch (error) {
    console.warn('[usePomodoroStore] Failed to parse snapshot', error)
    return null
  }
}

const toInt = (value: unknown, fallback = 0): number => {
  const casted = Number(value)
  if (!Number.isFinite(casted)) return fallback
  return Math.floor(casted)
}

const clampNonNegative = (value: unknown, fallback = 0): number => {
  return Math.max(0, toInt(value, fallback))
}

const isMode = (value: unknown): value is PomodoroMode => value === 'focus' || value === 'break'
const isStatus = (value: unknown): value is PomodoroStatus => value === 'idle' || value === 'running' || value === 'paused'

const normalizeSnapshot = (raw: any): Snapshot | null => {
  if (!raw || typeof raw !== 'object') return null

  const mode: PomodoroMode = isMode(raw.mode) ? raw.mode : 'focus'
  let status: PomodoroStatus = isStatus(raw.status) ? raw.status : 'idle'
  if (mode === 'break' && status === 'paused') {
    status = 'idle'
  }

  const snapshot: Snapshot = {
    mode,
    status,
    activeTaskId: raw.activeTaskId ? String(raw.activeTaskId) : null,
    endAt: raw.endAt == null ? null : clampNonNegative(raw.endAt),
    nowTs: clampNonNegative(raw.nowTs, now()),
    sessionStartedAt: raw.sessionStartedAt == null ? null : clampNonNegative(raw.sessionStartedAt),
    runningSegmentStartedAt: raw.runningSegmentStartedAt == null ? null : clampNonNegative(raw.runningSegmentStartedAt),
    pausedRemainingSeconds: raw.pausedRemainingSeconds == null ? null : clampNonNegative(raw.pausedRemainingSeconds),
    accumulatedFocusSeconds: clampNonNegative(raw.accumulatedFocusSeconds),
    lastSettledEndAt: raw.lastSettledEndAt == null ? null : clampNonNegative(raw.lastSettledEndAt)
  }

  if (snapshot.status === 'running' && !snapshot.endAt) snapshot.status = 'idle'
  if (snapshot.status === 'paused' && snapshot.mode !== 'focus') snapshot.status = 'idle'
  return snapshot
}

const loadSnapshotFromStorage = (): Snapshot | null => {
  if (typeof window === 'undefined') return null
  return normalizeSnapshot(safeParse(window.localStorage.getItem(SNAPSHOT_KEY)))
}

const getRemainingSecondsByEndAt = (endAt: Nullable<number>, currentTs: number): number => {
  if (!endAt) return 0
  return Math.max(0, Math.ceil((endAt - currentTs) / 1000))
}

const makeInstanceId = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `p0-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export const usePomodoroStore = defineStore('pomodoroStore', () => {
  const taskStore = useTaskStore()

  const instanceId = makeInstanceId()

  const mode = ref<PomodoroMode>('focus')
  const status = ref<PomodoroStatus>('idle')
  const activeTaskId = ref<Nullable<string>>(null)
  const endAt = ref<Nullable<number>>(null)
  const nowTs = ref<number>(now())
  const sessionStartedAt = ref<Nullable<number>>(null)
  const runningSegmentStartedAt = ref<Nullable<number>>(null)
  const pausedRemainingSeconds = ref<Nullable<number>>(null)
  const accumulatedFocusSeconds = ref<number>(0)
  const lastSettledEndAt = ref<Nullable<number>>(null)

  const leaderId = ref<Nullable<string>>(null)
  const lastHeartbeat = ref<number>(0)

  let tickHandle: Nullable<number> = null
  let displayHandle: Nullable<number> = null
  let heartbeatHandle: Nullable<number> = null
  let followerMonitorHandle: Nullable<number> = null
  let storageListenerAttached = false

  const isLeader = computed(() => leaderId.value === instanceId)
  const canControlTimer = computed(() => isLeader.value)
  const remainingSeconds = computed(() => {
    if (status.value === 'running') {
      return getRemainingSecondsByEndAt(endAt.value, nowTs.value)
    }
    if (status.value === 'paused') {
      return Math.max(0, pausedRemainingSeconds.value || 0)
    }
    return mode.value === 'focus' ? FOCUS_DURATION_SECONDS : BREAK_DURATION_SECONDS
  })
  const isBreakMode = computed(() => mode.value === 'break')
  const canPauseFocus = computed(() => canControlTimer.value && mode.value === 'focus' && status.value === 'running')
  const activeTask = computed(() => activeTaskId.value ? taskStore.getTaskById(activeTaskId.value) : undefined)

  const applySnapshotFields = (snapshot: Snapshot): void => {
    mode.value = snapshot.mode
    status.value = snapshot.status
    activeTaskId.value = snapshot.activeTaskId
    endAt.value = snapshot.endAt
    nowTs.value = now()
    sessionStartedAt.value = snapshot.sessionStartedAt
    runningSegmentStartedAt.value = snapshot.runningSegmentStartedAt
    pausedRemainingSeconds.value = snapshot.pausedRemainingSeconds
    accumulatedFocusSeconds.value = snapshot.accumulatedFocusSeconds
    lastSettledEndAt.value = snapshot.lastSettledEndAt
  }

  const persistSnapshot = (): void => {
    if (typeof window === 'undefined') return
    if (!isLeader.value) return

    const snapshot: Snapshot = {
      mode: mode.value,
      status: status.value,
      activeTaskId: activeTaskId.value,
      endAt: endAt.value,
      nowTs: nowTs.value,
      sessionStartedAt: sessionStartedAt.value,
      runningSegmentStartedAt: runningSegmentStartedAt.value,
      pausedRemainingSeconds: pausedRemainingSeconds.value,
      accumulatedFocusSeconds: accumulatedFocusSeconds.value,
      lastSettledEndAt: lastSettledEndAt.value
    }
    window.localStorage.setItem(SNAPSHOT_KEY, JSON.stringify(snapshot))
  }

  const readLeaderMetaFromStorage = (): { leaderId: Nullable<string>; lastHeartbeat: number } => {
    if (typeof window === 'undefined') {
      return { leaderId: null, lastHeartbeat: 0 }
    }
    return {
      leaderId: window.localStorage.getItem(LEADER_ID_KEY) || null,
      lastHeartbeat: clampNonNegative(window.localStorage.getItem(LAST_HEARTBEAT_KEY), 0)
    }
  }

  const syncLeaderMetaFromStorage = (): void => {
    const meta = readLeaderMetaFromStorage()
    leaderId.value = meta.leaderId
    lastHeartbeat.value = meta.lastHeartbeat
  }

  const writeLeaderMeta = (timestamp = now()): void => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(LEADER_ID_KEY, instanceId)
    window.localStorage.setItem(LAST_HEARTBEAT_KEY, String(timestamp))
    leaderId.value = instanceId
    lastHeartbeat.value = timestamp
  }

  const isLeaderStale = (timestamp = now()): boolean => {
    if (!leaderId.value) return true
    if (lastHeartbeat.value <= 0) return true
    return timestamp - lastHeartbeat.value > LEADER_STALE_MS
  }

  const stopTicker = (): void => {
    if (tickHandle != null && typeof window !== 'undefined') {
      window.clearInterval(tickHandle)
      tickHandle = null
    }
  }

  const startTicker = (): void => {
    stopTicker()
    if (typeof window === 'undefined') return
    if (!isLeader.value || status.value !== 'running') return
    tickHandle = window.setInterval(() => {
      tickNow()
    }, TICK_INTERVAL_MS)
  }

  const stopDisplayTicker = (): void => {
    if (displayHandle != null && typeof window !== 'undefined') {
      window.clearInterval(displayHandle)
      displayHandle = null
    }
  }

  const startDisplayTicker = (): void => {
    stopDisplayTicker()
    if (typeof window === 'undefined') return
    if (isLeader.value || status.value !== 'running') return
    displayHandle = window.setInterval(() => {
      nowTs.value = now()
    }, TICK_INTERVAL_MS)
  }

  const stopHeartbeatLoop = (): void => {
    if (heartbeatHandle != null && typeof window !== 'undefined') {
      window.clearInterval(heartbeatHandle)
      heartbeatHandle = null
    }
  }

  const startHeartbeatLoop = (): void => {
    stopHeartbeatLoop()
    if (typeof window === 'undefined') return
    heartbeatHandle = window.setInterval(() => {
      if (!isLeader.value || status.value !== 'running') return
      const ts = now()
      writeLeaderMeta(ts)
      debugLog('leader heartbeat', { mode: mode.value, status: status.value, ts })
    }, HEARTBEAT_INTERVAL_MS)
  }

  const updateLoopOwnership = (): void => {
    if (isLeader.value) {
      stopDisplayTicker()
      if (status.value === 'running') {
        startTicker()
        startHeartbeatLoop()
      } else {
        stopTicker()
        stopHeartbeatLoop()
      }
      return
    }

    stopTicker()
    stopHeartbeatLoop()
    if (status.value === 'running') {
      startDisplayTicker()
    } else {
      stopDisplayTicker()
    }
  }

  const resetToFocusIdle = (atTs = now()): void => {
    mode.value = 'focus'
    status.value = 'idle'
    activeTaskId.value = null
    endAt.value = null
    nowTs.value = atTs
    sessionStartedAt.value = null
    runningSegmentStartedAt.value = null
    pausedRemainingSeconds.value = null
    accumulatedFocusSeconds.value = 0
    lastSettledEndAt.value = null
    updateLoopOwnership()
  }

  const getCurrentFocusSeconds = (atTs: number): number => {
    let total = accumulatedFocusSeconds.value
    if (mode.value === 'focus' && status.value === 'running' && runningSegmentStartedAt.value != null) {
      total += Math.max(0, Math.floor((atTs - runningSegmentStartedAt.value) / 1000))
    }
    return Math.max(0, Math.min(FOCUS_DURATION_SECONDS, total))
  }

  const accrueRunningFocusSeconds = (atTs: number): void => {
    if (mode.value !== 'focus') return
    if (status.value !== 'running') return
    if (runningSegmentStartedAt.value == null) return

    const elapsed = Math.max(0, Math.floor((atTs - runningSegmentStartedAt.value) / 1000))
    if (elapsed <= 0) return

    accumulatedFocusSeconds.value = Math.max(
      0,
      Math.min(FOCUS_DURATION_SECONDS, accumulatedFocusSeconds.value + elapsed)
    )
    runningSegmentStartedAt.value = runningSegmentStartedAt.value + elapsed * 1000
  }

  const settleExpiredBreak = (currentTs: number, settledEndAt: number): void => {
    lastSettledEndAt.value = settledEndAt
    debugLog('break finished', { settledEndAt, at: currentTs })
    resetToFocusIdle(currentTs)
  }

  const enterBreakRunning = (breakEndAt: number, currentTs: number, settledEndAt: number): void => {
    lastSettledEndAt.value = settledEndAt
    mode.value = 'break'
    status.value = 'running'
    activeTaskId.value = null
    nowTs.value = currentTs
    endAt.value = breakEndAt
    sessionStartedAt.value = null
    runningSegmentStartedAt.value = currentTs
    pausedRemainingSeconds.value = null
    accumulatedFocusSeconds.value = 0
    debugLog('break entered', { breakEndAt, at: currentTs })
    updateLoopOwnership()
  }

  const settleExpiredFocus = (focusEndedAt: number, currentTs: number, restoredFromSnapshot: boolean): void => {
    const taskId = activeTaskId.value
    const startedAt = sessionStartedAt.value ?? Math.max(0, focusEndedAt - FOCUS_DURATION_SECONDS * 1000)

    if (taskId) {
      taskStore.commitSessionToTask({
        taskId,
        startedAt,
        endedAt: focusEndedAt,
        focusSeconds: FOCUS_DURATION_SECONDS,
        isFullPomodoro: true,
        source: 'focus-finished',
        restoredFromSnapshot
      })
    }

    const breakEndAt = currentTs + BREAK_DURATION_SECONDS * 1000
    debugLog('focus settled', { taskId, focusEndedAt, breakEndAt, restoredFromSnapshot })
    enterBreakRunning(breakEndAt, currentTs, focusEndedAt)
  }

  const claimLeadership = (reason: string): boolean => {
    if (typeof window === 'undefined') return true

    const latestSnapshot = loadSnapshotFromStorage()
    if (latestSnapshot) applySnapshotFields(latestSnapshot)

    const ts = now()
    writeLeaderMeta(ts)

    const confirmedLeaderId = window.localStorage.getItem(LEADER_ID_KEY)
    const confirmedHeartbeat = clampNonNegative(window.localStorage.getItem(LAST_HEARTBEAT_KEY), ts)
    leaderId.value = confirmedLeaderId || null
    lastHeartbeat.value = confirmedHeartbeat

    const won = confirmedLeaderId === instanceId
    debugLog('claimLeadership', { reason, won, leaderId: leaderId.value })
    updateLoopOwnership()
    return won
  }

  const ensureLeaderForControl = (action: string): boolean => {
    if (isLeader.value) return true
    syncLeaderMetaFromStorage()
    if (isLeaderStale(now())) {
      return claimLeadership(`control:${action}`)
    }
    return false
  }

  const startFocus = (taskId: string): boolean => {
    if (!ensureLeaderForControl('startFocus')) return false

    const normalizedTaskId = String(taskId || '').trim()
    if (!normalizedTaskId) return false
    if (mode.value !== 'focus' || status.value !== 'idle') return false

    const currentTs = now()
    mode.value = 'focus'
    status.value = 'running'
    activeTaskId.value = normalizedTaskId
    nowTs.value = currentTs
    sessionStartedAt.value = currentTs
    runningSegmentStartedAt.value = currentTs
    pausedRemainingSeconds.value = null
    accumulatedFocusSeconds.value = 0
    endAt.value = currentTs + FOCUS_DURATION_SECONDS * 1000
    lastSettledEndAt.value = null

    writeLeaderMeta(currentTs)
    updateLoopOwnership()
    return true
  }

  const pauseFocus = (): boolean => {
    if (!ensureLeaderForControl('pauseFocus')) return false
    if (mode.value !== 'focus' || status.value !== 'running') return false

    const currentTs = now()
    accrueRunningFocusSeconds(currentTs)
    pausedRemainingSeconds.value = getRemainingSecondsByEndAt(endAt.value, currentTs)
    status.value = 'paused'
    endAt.value = null
    runningSegmentStartedAt.value = null
    nowTs.value = currentTs

    updateLoopOwnership()
    return true
  }

  const resumeFocus = (): boolean => {
    if (!ensureLeaderForControl('resumeFocus')) return false
    if (mode.value !== 'focus' || status.value !== 'paused') return false

    const remaining = Math.max(0, pausedRemainingSeconds.value || 0)
    if (remaining <= 0) {
      resetToFocusIdle(now())
      return false
    }

    const currentTs = now()
    status.value = 'running'
    nowTs.value = currentTs
    endAt.value = currentTs + remaining * 1000
    runningSegmentStartedAt.value = currentTs
    pausedRemainingSeconds.value = null
    lastSettledEndAt.value = null

    writeLeaderMeta(currentTs)
    updateLoopOwnership()
    return true
  }

  const interruptFocus = (): boolean => {
    if (!ensureLeaderForControl('interruptFocus')) return false
    if (mode.value !== 'focus') return false
    if (status.value !== 'running' && status.value !== 'paused') return false

    const taskId = activeTaskId.value
    const currentTs = now()
    const focusSeconds = getCurrentFocusSeconds(currentTs)
    const startedAt = sessionStartedAt.value ?? Math.max(0, currentTs - focusSeconds * 1000)

    if (taskId) {
      taskStore.commitSessionToTask({
        taskId,
        startedAt,
        endedAt: currentTs,
        focusSeconds,
        isFullPomodoro: false,
        source: 'focus-interrupted'
      })
    }

    resetToFocusIdle(currentTs)
    return true
  }

  const tickNow = (): void => {
    const currentTs = now()
    nowTs.value = currentTs

    // Follower strictly mirrors display time only.
    if (!isLeader.value) return

    if (status.value !== 'running') return
    if (!endAt.value) {
      resetToFocusIdle(currentTs)
      return
    }
    if (currentTs < endAt.value) return

    if (lastSettledEndAt.value === endAt.value) {
      return
    }

    const settledEndAt = endAt.value
    if (mode.value === 'focus') {
      settleExpiredFocus(settledEndAt, currentTs, false)
    } else {
      settleExpiredBreak(currentTs, settledEndAt)
    }
  }

  const hydrateFromSnapshot = (): void => {
    const snapshot = loadSnapshotFromStorage()
    if (!snapshot) {
      resetToFocusIdle(now())
      if (isLeader.value) persistSnapshot()
      return
    }

    applySnapshotFields(snapshot)
    const currentTs = now()
    nowTs.value = currentTs

    if (!isLeader.value) {
      updateLoopOwnership()
      return
    }

    if (status.value === 'running' && endAt.value && currentTs >= endAt.value) {
      tickNow()
      if (isLeader.value) persistSnapshot()
      return
    }

    if (status.value === 'paused' && mode.value !== 'focus') {
      resetToFocusIdle(currentTs)
    }

    updateLoopOwnership()
    if (isLeader.value) persistSnapshot()
  }

  const handleStorageEvent = (event: StorageEvent): void => {
    if (event.storageArea !== window.localStorage) return

    if (event.key === SNAPSHOT_KEY) {
      if (isLeader.value) return
      const snapshot = normalizeSnapshot(safeParse(event.newValue))
      if (!snapshot) return
      applySnapshotFields(snapshot)
      updateLoopOwnership()
      return
    }

    if (event.key === LEADER_ID_KEY || event.key === LAST_HEARTBEAT_KEY) {
      const wasLeader = isLeader.value
      syncLeaderMetaFromStorage()
      if (!isLeader.value) {
        const snapshot = loadSnapshotFromStorage()
        if (snapshot) applySnapshotFields(snapshot)
      }
      if (wasLeader !== isLeader.value) {
        debugLog('leader-changed', { wasLeader, isLeader: isLeader.value })
      }
      updateLoopOwnership()
    }
  }

  const startFollowerMonitor = (): void => {
    if (typeof window === 'undefined') return
    if (followerMonitorHandle != null) return

    followerMonitorHandle = window.setInterval(() => {
      if (isLeader.value) return

      syncLeaderMetaFromStorage()
      if (status.value !== 'running') return
      if (!isLeaderStale(now())) return

      const latestSnapshot = loadSnapshotFromStorage()
      if (latestSnapshot) {
        applySnapshotFields(latestSnapshot)
      }

      const won = claimLeadership('heartbeat-timeout')
      if (won) {
        debugLog('follower takeover', { instanceId, reason: 'heartbeat-timeout' })
        tickNow()
      }
    }, HEARTBEAT_INTERVAL_MS)
  }

  const bootstrapLeaderState = (): void => {
    syncLeaderMetaFromStorage()
    if (isLeaderStale(now())) {
      claimLeadership('bootstrap')
    } else {
      updateLoopOwnership()
    }
  }

  const attachStorageListener = (): void => {
    if (typeof window === 'undefined') return
    if (storageListenerAttached) return
    window.addEventListener('storage', handleStorageEvent)
    storageListenerAttached = true
  }

  watch(
    [
      mode,
      status,
      activeTaskId,
      endAt,
      nowTs,
      sessionStartedAt,
      runningSegmentStartedAt,
      pausedRemainingSeconds,
      accumulatedFocusSeconds,
      lastSettledEndAt
    ],
    () => {
      persistSnapshot()
    }
  )

  watch([status, isLeader], () => {
    updateLoopOwnership()
    if (isLeader.value) {
      persistSnapshot()
    }
  })

  if (typeof window !== 'undefined') {
    bootstrapLeaderState()
    hydrateFromSnapshot()
    attachStorageListener()
    startFollowerMonitor()
  }

  return {
    instanceId,
    mode,
    status,
    activeTaskId,
    endAt,
    nowTs,
    sessionStartedAt,
    runningSegmentStartedAt,
    pausedRemainingSeconds,
    accumulatedFocusSeconds,
    lastSettledEndAt,
    remainingSeconds,
    isBreakMode,
    canPauseFocus,
    activeTask,
    isLeader,
    canControlTimer,
    startFocus,
    pauseFocus,
    resumeFocus,
    interruptFocus,
    tickNow,
    hydrateFromSnapshot
  }
})
