/* @vitest-environment jsdom */
import { describe, expect, it, vi } from 'vitest'
import {
  extractJsonText,
  markRecommendedFirst,
  sanitizeDraftSteps,
  StalePlanningRequestError,
  useAIPlanning,
  type GoalDecomposeInput
} from './useAIPlanning'

vi.mock('../api', () => ({
  default: {
    post: vi.fn()
  }
}))

const baseInput: GoalDecomposeInput = {
  goal: '复习高数',
  style: 'balanced'
}

describe('useAIPlanning', () => {
  it('extractJsonText 支持 fenced 和前后解释文本', () => {
    const fenced = '```json\n[{"title":"任务A","estimatedPomodoros":2}]\n```'
    const mixed = '下面是结果：\n[{"title":"任务B","estimatedPomodoros":1}]\n请执行。'
    expect(extractJsonText(fenced)).toContain('"任务A"')
    expect(extractJsonText(mixed)).toContain('"任务B"')
  })

  it('sanitizeDraftSteps 会修复标题并限制番茄数', () => {
    const steps = sanitizeDraftSteps([
      {
        title: '复习高数',
        estimatedPomodoros: 5,
        reason: '',
        doneDefinition: ''
      }
    ], baseInput, 'llm')

    expect(steps.length).toBeGreaterThan(1)
    steps.forEach((step) => {
      expect(step.estimatedPomodoros).toBeGreaterThanOrEqual(1)
      expect(step.estimatedPomodoros).toBeLessThanOrEqual(3)
      expect(step.title.length).toBeGreaterThan(2)
    })
  })

  it('markRecommendedFirst 仅标记最终首项', () => {
    const marked = markRecommendedFirst([
      {
        id: '1', title: 'A', estimatedPomodoros: 1, priority: 1, difficulty: 'low', actionable: true
      },
      {
        id: '2', title: 'B', estimatedPomodoros: 1, priority: 2, difficulty: 'low', actionable: true
      }
    ])
    expect(marked[0].isRecommendedFirst).toBe(true)
    expect(marked[1].isRecommendedFirst).toBe(false)
  })

  it('LLM 无效结果会 fallback 到规则流并打 source', async () => {
    const { generateDraftPlan } = useAIPlanning({
      requestLLMPlan: async () => '[]',
      fallbackRuleBasedDecompose: () => ([
        {
          id: 'fallback-1',
          title: '高数：重做第二章错题 1-8 题',
          estimatedPomodoros: 2,
          priority: 1,
          difficulty: 'medium',
          actionable: true,
          reason: 'fallback',
          doneDefinition: '完成题目并记录错因',
          source: 'fallback_rule'
        }
      ])
    })

    const result = await generateDraftPlan(baseInput)
    expect(result.length).toBeGreaterThan(0)
    expect(result[0].source).toBe('fallback_rule')
    expect(result[0].isRecommendedFirst).toBe(true)
  })

  it('请求代次保护：旧响应必须丢弃', async () => {
    let callCount = 0
    let resolveFirst: (value: unknown) => void = () => {}
    let resolveSecond: (value: unknown) => void = () => {}

    const firstPromise = new Promise<unknown>((resolve) => { resolveFirst = resolve })
    const secondPromise = new Promise<unknown>((resolve) => { resolveSecond = resolve })

    const { generateDraftPlan } = useAIPlanning({
      requestLLMPlan: async () => {
        callCount += 1
        return callCount === 1 ? firstPromise : secondPromise
      }
    })

    const pendingA = generateDraftPlan({ goal: 'A 目标', style: 'balanced' })
    const pendingB = generateDraftPlan({ goal: 'B 目标', style: 'balanced' })

    resolveSecond('[{"title":"高数：重做错题","estimatedPomodoros":2,"doneDefinition":"完成","reason":"先做高收益"}]')
    const latest = await pendingB
    expect(latest[0].title).toContain('高数')

    resolveFirst('[{"title":"旧结果","estimatedPomodoros":1,"doneDefinition":"完成","reason":"旧"}]')
    await expect(pendingA).rejects.toBeInstanceOf(StalePlanningRequestError)
  })
})

