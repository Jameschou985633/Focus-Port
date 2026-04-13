/* @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useMasterTimelineStore } from './masterTimeline'

describe('masterTimeline store P1.5', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    localStorage.clear()
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  const flushPreview = async () => {
    vi.advanceTimersByTime(500)
    await Promise.resolve()
  }

  it('applyAIDraftSteps 默认 replace，append 可追加', () => {
    const store = useMasterTimelineStore()
    store.applyAIDraftSteps([{ id: 'a', title: '任务 A', estimatedPomodoros: 1, priority: 1, difficulty: 'low', actionable: true }])
    expect(store.preflightDraft).toHaveLength(1)
    expect(store.preflightDraft[0].title).toBe('任务 A')

    store.applyAIDraftSteps([{ id: 'b', title: '任务 B', estimatedPomodoros: 1, priority: 9, difficulty: 'low', actionable: true }], 'append')
    expect(store.preflightDraft).toHaveLength(2)
    expect(store.preflightDraft[0].priority).toBe(1)
    expect(store.preflightDraft[1].priority).toBe(2)
  })

  it('草稿删除与排序后 priority 连续归一', () => {
    const store = useMasterTimelineStore()
    store.applyAIDraftSteps([
      { id: 'a', title: '任务 A', estimatedPomodoros: 1, priority: 5, difficulty: 'low', actionable: true },
      { id: 'b', title: '任务 B', estimatedPomodoros: 1, priority: 1, difficulty: 'low', actionable: true },
      { id: 'c', title: '任务 C', estimatedPomodoros: 1, priority: 3, difficulty: 'low', actionable: true }
    ])

    store.moveDraftItem('c', 'up')
    store.removeDraftItem('a')
    expect(store.preflightDraft.map((item) => item.priority)).toEqual([1, 2])
  })

  it('confirmDraftToTimeline 前做归一化映射，且只写 timeline', () => {
    const store = useMasterTimelineStore()
    store.applyAIDraftSteps([
      {
        id: 'a',
        title: '英语：默写模板句',
        estimatedPomodoros: 2,
        priority: 1,
        difficulty: 'medium',
        reason: '先建立表达框架',
        doneDefinition: '默写 5 句',
        actionable: true
      }
    ])

    const addedIds = store.confirmDraftToTimeline()
    expect(addedIds.length).toBe(1)
    expect(store.preflightDraft).toHaveLength(0)
    expect(store.masterTimeline).toHaveLength(1)
    expect(store.masterTimeline[0].task).toBe('英语：默写模板句')
    expect(store.masterTimeline[0].minutes).toBe(50)
    expect(store.masterTimeline[0].reason).toBe('先建立表达框架')
  })

  it('AI 拆解只生成草稿，不会自动写正式 timeline', async () => {
    const store = useMasterTimelineStore()
    const promise = store.requestAIPreview('复习高数', { style: 'balanced' })
    await flushPreview()
    await promise

    expect(store.preflightDraft.length).toBeGreaterThan(0)
    expect(store.masterTimeline).toHaveLength(0)
  })
})
