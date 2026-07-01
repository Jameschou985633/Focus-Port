/* @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useTaskStore } from './useTaskStore'

describe('useTaskStore P1 hotfix', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-13T12:00:00.000Z'))
    localStorage.clear()
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  const settleAnalysis = async () => {
    vi.advanceTimersByTime(2000)
    await Promise.resolve()
    await Promise.resolve()
  }

  const completeAndAnalyze = async (note: string, totalFocusSeconds = 1500, actualPomodoros = 1) => {
    const store = useTaskStore()
    const task = store.addTask('Analyze target')
    expect(task).toBeTruthy()
    task!.totalFocusSeconds = totalFocusSeconds
    task!.actualPomodoros = actualPomodoros
    store.completeTask(task!.id, note)
    const completedAt = store.getTaskById(task!.id)?.completedAt ?? Date.now()
    const pending = store.triggerAIAnalysis(task!.id, {
      note,
      completedAt,
      totalFocusSeconds,
      actualPomodoros
    })
    await settleAnalysis()
    const result = await pending
    return { store, task: task!, result, completedAt }
  }

  it('distractionDetected / incompleteDetected 分离识别与 completionStatus 推导正确', async () => {
    const partial = await completeAndAnalyze('今天没做完，只做一半')
    expect(partial.result.distractionDetected).toBe(false)
    expect(partial.result.completionStatus).toBe('partial')

    const failedWithDistraction = await completeAndAnalyze('我刷手机一直切窗口，几乎没做')
    expect(failedWithDistraction.result.distractionDetected).toBe(true)
    expect(failedWithDistraction.result.completionStatus).toBe('failed')
  })

  it('honestyBonus 仅在命中负面词且 note 足够长时触发（通过 multiplier 可观测）', async () => {
    const shortNote = await completeAndAnalyze('分心')
    const longNote = await completeAndAnalyze('我今天分心并且刷手机，后面及时拉回')
    expect(shortNote.result.multiplier).toBeLessThan(1)
    expect(longNote.result.multiplier).toBeGreaterThan(shortNote.result.multiplier)
  })

  it('奖励计算稳定，不依赖 AI 文案文本变化', async () => {
    const left = await completeAndAnalyze('正常推进任务')
    const right = await completeAndAnalyze('正常推进任务，补充了细节')
    expect(left.result.computePowerGained).toBe(right.result.computePowerGained)
    expect(left.result.expGained).toBe(right.result.expGained)
  })

  it('triggerAIAnalysis 对同一 reward key 幂等，不重复加钱包', async () => {
    const store = useTaskStore()
    const task = store.addTask('Idempotent target')!
    task.totalFocusSeconds = 1500
    task.actualPomodoros = 1
    store.completeTask(task.id, '完成')
    const completedAt = store.getTaskById(task.id)!.completedAt!

    const firstPromise = store.triggerAIAnalysis(task.id, {
      note: '完成',
      completedAt,
      totalFocusSeconds: 1500,
      actualPomodoros: 1
    })
    await settleAnalysis()
    const first = await firstPromise
    const walletAfterFirst = { ...store.wallet }

    const second = await store.triggerAIAnalysis(task.id, {
      note: '重复点击',
      completedAt,
      totalFocusSeconds: 1500,
      actualPomodoros: 1
    })

    expect(second.computePowerGained).toBe(first.computePowerGained)
    expect(second.expGained).toBe(first.expGained)
    expect(store.wallet.computePower).toBe(walletAfterFirst.computePower)
    expect(store.wallet.energy).toBe(walletAfterFirst.energy)
    expect(store.taskRewardLogs.filter((log) => log.taskId === task.id)).toHaveLength(1)
  })

  it('convertCUToEnergy 批量兑换正确', () => {
    const store = useTaskStore()
    store.wallet.computePower = 250
    store.wallet.energy = 3
    const result = store.convertCUToEnergy()
    expect(result).toEqual({
      converted: 2,
      consumedCU: 200,
      remainingCU: 50,
      energy: 5
    })
  })

  it('getDaySummary 能正确聚合 completedCount / focus / pomodoro / CU / EXP', async () => {
    const store = useTaskStore()
    const activeDay = '2026-04-13'
    const now = Date.now()

    const completedTask = store.addTask('Completed task')!
    store.commitSessionToTask({
      taskId: completedTask.id,
      startedAt: now - 1_500_000,
      endedAt: now - 1_000,
      focusSeconds: 1500,
      isFullPomodoro: true,
      source: 'focus-finished'
    })
    store.completeTask(completedTask.id, '完成')
    const completedAt = store.getTaskById(completedTask.id)!.completedAt!
    const rewardPromise = store.triggerAIAnalysis(completedTask.id, {
      note: '完成',
      completedAt,
      totalFocusSeconds: completedTask.totalFocusSeconds,
      actualPomodoros: completedTask.actualPomodoros
    })
    await settleAnalysis()
    await rewardPromise

    const pendingTask = store.addTask('Carry over task')!
    pendingTask.isCarriedOver = true
    pendingTask.carryOverCount = 2

    const summary = store.getDaySummary(activeDay)
    expect(summary.completedCount).toBe(1)
    expect(summary.totalFocusSeconds).toBe(1500)
    expect(summary.totalPomodoros).toBe(1)
    expect(summary.totalComputePowerGained).toBeGreaterThan(0)
    expect(summary.totalExpGained).toBeGreaterThan(0)
    expect(summary.pendingTasks.some((task) => task.id === pendingTask.id)).toBe(true)
  })

  it('importPlannedTasks 仅导入草稿任务，不覆盖原任务', () => {
    const store = useTaskStore()
    const existing = store.addTask('Existing')!
    const created = store.importPlannedTasks([
      { title: 'Draft A', priority: 2 },
      { title: 'Draft B', priority: 1 },
      { title: '   ' }
    ])
    expect(created).toHaveLength(2)
    expect(store.tasks.some((task) => task.id === existing.id)).toBe(true)
    expect(store.tasks.filter((task) => task.title.startsWith('Draft'))).toHaveLength(2)
  })
})
