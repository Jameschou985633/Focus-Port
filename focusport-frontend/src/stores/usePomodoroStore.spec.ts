/* @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { usePomodoroStore } from './usePomodoroStore'

const commitSessionToTask = vi.fn()
const getTaskById = vi.fn((taskId: string) => ({ id: taskId, title: `Task ${taskId}` }))

vi.mock('./useTaskStore', () => ({
  useTaskStore: () => ({
    commitSessionToTask,
    getTaskById
  })
}))

const SNAPSHOT_KEY = 'focusport.p0.pomodoro.snapshot.v1'
const LEADER_ID_KEY = 'focusport.p0.pomodoro.leaderId.v1'
const LAST_HEARTBEAT_KEY = 'focusport.p0.pomodoro.lastHeartbeat.v1'

describe('usePomodoroStore P1 hotfix', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-13T10:00:00.000Z'))
    localStorage.clear()
    commitSessionToTask.mockClear()
    getTaskById.mockClear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  const makeStore = () => {
    setActivePinia(createPinia())
    return usePomodoroStore()
  }

  it('focus 到期后只推进一次并进入 break running', () => {
    const store = makeStore()
    expect(store.startFocus('task-1')).toBe(true)

    vi.advanceTimersByTime(25 * 60 * 1000)
    store.tickNow()

    expect(store.mode).toBe('break')
    expect(store.status).toBe('running')
    expect(commitSessionToTask).toHaveBeenCalledTimes(1)
    expect(store.lastSettledEndAt).not.toBeNull()

    store.tickNow()
    expect(commitSessionToTask).toHaveBeenCalledTimes(1)
  })

  it('break 运行会递减并在到期后回 focus idle，且 break 阶段不提交 session', () => {
    const store = makeStore()
    store.startFocus('task-2')
    vi.advanceTimersByTime(25 * 60 * 1000)
    store.tickNow()
    expect(commitSessionToTask).toHaveBeenCalledTimes(1)

    const before = store.remainingSeconds
    vi.advanceTimersByTime(2_000)
    store.tickNow()
    expect(store.remainingSeconds).toBeLessThan(before)

    vi.advanceTimersByTime(5 * 60 * 1000)
    store.tickNow()
    expect(store.mode).toBe('focus')
    expect(store.status).toBe('idle')
    expect(commitSessionToTask).toHaveBeenCalledTimes(1)
  })

  it('follower tickNow 只刷新显示，不执行 settle/commit', () => {
    const now = Date.now()
    localStorage.setItem(
      SNAPSHOT_KEY,
      JSON.stringify({
        mode: 'focus',
        status: 'running',
        activeTaskId: 'task-follower',
        endAt: now - 1000,
        nowTs: now,
        sessionStartedAt: now - 10000,
        runningSegmentStartedAt: now - 10000,
        pausedRemainingSeconds: null,
        accumulatedFocusSeconds: 10,
        lastSettledEndAt: null
      })
    )
    localStorage.setItem(LEADER_ID_KEY, 'other-instance')
    localStorage.setItem(LAST_HEARTBEAT_KEY, String(now))

    const store = makeStore()
    expect(store.isLeader).toBe(false)

    store.tickNow()
    expect(store.mode).toBe('focus')
    expect(store.status).toBe('running')
    expect(commitSessionToTask).not.toHaveBeenCalled()
  })

  it('leader 失效后 follower 按先同步后接管流程接管', () => {
    const now = Date.now()
    localStorage.setItem(
      SNAPSHOT_KEY,
      JSON.stringify({
        mode: 'focus',
        status: 'running',
        activeTaskId: 'task-running',
        endAt: now + 60_000,
        nowTs: now,
        sessionStartedAt: now - 30_000,
        runningSegmentStartedAt: now - 30_000,
        pausedRemainingSeconds: null,
        accumulatedFocusSeconds: 30,
        lastSettledEndAt: null
      })
    )
    localStorage.setItem(LEADER_ID_KEY, 'other-instance')
    localStorage.setItem(LAST_HEARTBEAT_KEY, String(now))

    const store = makeStore()
    expect(store.isLeader).toBe(false)
    expect(store.activeTaskId).toBe('task-running')

    localStorage.setItem(LAST_HEARTBEAT_KEY, String(now - 3001))
    vi.advanceTimersByTime(1000)

    expect(store.isLeader).toBe(true)
    expect(store.canControlTimer).toBe(true)
    expect(store.status).toBe('running')
    expect(store.activeTaskId).toBe('task-running')
  })

  it('非 leader 的 start/pause/resume/interrupt 都是 no-op 返回 false', () => {
    const now = Date.now()
    localStorage.setItem(LEADER_ID_KEY, 'other-instance')
    localStorage.setItem(LAST_HEARTBEAT_KEY, String(now))
    localStorage.setItem(
      SNAPSHOT_KEY,
      JSON.stringify({
        mode: 'focus',
        status: 'idle',
        activeTaskId: null,
        endAt: null,
        nowTs: now,
        sessionStartedAt: null,
        runningSegmentStartedAt: null,
        pausedRemainingSeconds: null,
        accumulatedFocusSeconds: 0,
        lastSettledEndAt: null
      })
    )

    const store = makeStore()
    expect(store.isLeader).toBe(false)
    expect(store.startFocus('task-noop')).toBe(false)
    expect(store.pauseFocus()).toBe(false)
    expect(store.resumeFocus()).toBe(false)
    expect(store.interruptFocus()).toBe(false)
    expect(commitSessionToTask).not.toHaveBeenCalled()
  })
})
