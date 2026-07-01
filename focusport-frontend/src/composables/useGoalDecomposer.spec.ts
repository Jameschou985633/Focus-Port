/* @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useGoalDecomposer } from './useGoalDecomposer'

describe('useGoalDecomposer', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  const flushDecompose = async <T>(promise: Promise<T>): Promise<T> => {
    vi.advanceTimersByTime(500)
    await Promise.resolve()
    return promise
  }

  it('抽象目标会被改写为可执行动作并生成完整字段', async () => {
    const { decomposeGoal } = useGoalDecomposer()
    const promise = decomposeGoal({ goal: '复习高数', style: 'balanced' })
    const steps = await flushDecompose(promise)

    expect(steps.length).toBeGreaterThan(0)
    steps.forEach((step) => {
      expect(step.actionable).toBe(true)
      expect(step.doneDefinition).toBeTruthy()
      expect(step.estimatedPomodoros).toBeGreaterThanOrEqual(1)
      expect(step.estimatedPomodoros).toBeLessThanOrEqual(3)
      expect(step.title.length).toBeGreaterThan(2)
    })
  })

  it('style 差异可见：sprint 步骤数 >= balanced >= conservative', async () => {
    const { decomposeGoal } = useGoalDecomposer()
    const baseInput = { goal: '完成英语作文复盘', availableMinutes: 200 }
    const conservative = await flushDecompose(decomposeGoal({ ...baseInput, style: 'conservative' }))
    const balanced = await flushDecompose(decomposeGoal({ ...baseInput, style: 'balanced' }))
    const sprint = await flushDecompose(decomposeGoal({ ...baseInput, style: 'sprint' }))

    expect(sprint.length).toBeGreaterThanOrEqual(balanced.length)
    expect(balanced.length).toBeGreaterThanOrEqual(conservative.length)
  })
})
