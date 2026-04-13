import api from '../api'

export type DecomposeStyle = 'conservative' | 'balanced' | 'sprint'

export type GoalDecomposeInput = {
  goal: string
  style: DecomposeStyle
  availableMinutes?: number
  weakPoints?: string
}

export type AITaskStep = {
  id: string
  title: string
  description?: string
  doneDefinition?: string
  estimatedPomodoros: number
  priority: number
  difficulty: 'low' | 'medium' | 'high'
  category?: string
  reason?: string
  actionable: boolean
  isRecommendedFirst?: boolean
  source?: 'llm' | 'fallback_rule'
}

type LLMRoute = 'proxy' | 'direct'

type PlanningPrompt = {
  systemPrompt: string
  userPrompt: string
}

type PartialStep = Partial<AITaskStep> & {
  task?: string
  minutes?: number
}

type PlanningDeps = {
  requestLLMPlan: (input: GoalDecomposeInput, prompt: PlanningPrompt) => Promise<unknown>
  fallbackRuleBasedDecompose: (input: GoalDecomposeInput) => AITaskStep[]
}

const DEFAULT_MODEL = import.meta.env.VITE_LLM_MODEL || 'qwen-plus'
const DEFAULT_BASE_URL = import.meta.env.VITE_LLM_API_BASE_URL || 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
const DEFAULT_TIMEOUT_MS = Number(import.meta.env.VITE_LLM_TIMEOUT_MS || 10000)
const PROXY_ENDPOINT = '/api/plans/ai/chat'
const ABSTRACT_PATTERNS = ['复习', '学习', '处理', '巩固', '提升', '整理']

export class StalePlanningRequestError extends Error {
  constructor() {
    super('Stale planning request')
    this.name = 'StalePlanningRequestError'
  }
}

const makeId = (prefix = 'ai-step'): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}-${crypto.randomUUID()}`
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

const clampPomodoros = (value: unknown): number => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return 1
  return Math.max(1, Math.min(3, Math.round(numeric)))
}

const normalizePriority = (steps: AITaskStep[]): AITaskStep[] => {
  return steps.map((step, index) => ({ ...step, priority: index + 1 }))
}

const withTimeout = async <T>(promise: Promise<T>, timeoutMs = DEFAULT_TIMEOUT_MS, message = 'Timeout'): Promise<T> => {
  return new Promise<T>((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(message)), timeoutMs)
    promise
      .then((value) => resolve(value))
      .catch((error) => reject(error))
      .finally(() => clearTimeout(timer))
  })
}

const stripCodeFence = (raw: string): string => {
  const trimmed = raw.trim()
  if (!trimmed) return ''
  const noStart = trimmed.replace(/^\s*```(?:json)?\s*/i, '')
  return noStart.replace(/\s*```\s*$/i, '').trim()
}

const extractBalancedJson = (raw: string, openChar: string, closeChar: string): string => {
  const start = raw.indexOf(openChar)
  if (start < 0) return ''
  let depth = 0
  let inString = false
  let escaped = false

  for (let index = start; index < raw.length; index += 1) {
    const char = raw[index]
    if (escaped) {
      escaped = false
      continue
    }
    if (char === '\\') {
      escaped = true
      continue
    }
    if (char === '"') {
      inString = !inString
      continue
    }
    if (inString) continue
    if (char === openChar) depth += 1
    if (char === closeChar) depth -= 1
    if (depth === 0) return raw.slice(start, index + 1)
  }

  return ''
}

const inferScenario = (goal: string): 'math' | 'english' | 'politics' | 'writing' | 'video' | 'review' | 'general' => {
  if (/高数|数学|刷题|错题|题/.test(goal)) return 'math'
  if (/英语|作文|阅读|单词/.test(goal)) return 'english'
  if (/政治|背诵|关键词/.test(goal)) return 'politics'
  if (/写作|提纲|初稿/.test(goal)) return 'writing'
  if (/网课|视频|课程/.test(goal)) return 'video'
  if (/复习|复盘|章节/.test(goal)) return 'review'
  return 'general'
}

export const rewriteToActionableTitle = (raw: string, context = ''): string => {
  const normalized = String(raw || '').trim()
  if (!normalized) return '执行一个可量化学习动作'

  const isAbstract = ABSTRACT_PATTERNS.some((pattern) => normalized.includes(pattern))
  if (!isAbstract) return normalized

  const source = `${normalized} ${context}`
  if (/高数|数学/.test(source)) return '高数：重做本章典型题并标注错因'
  if (/英语/.test(source)) return '英语：背诵作文模板并默写关键句'
  if (/政治/.test(source)) return '政治：背诵关键词并口述一遍'
  if (/网课|视频/.test(source)) return '网课：看完指定片段并整理笔记'
  return `${normalized}：拆成可执行动作并完成一次复盘`
}

const buildReasonByStyle = (style: DecomposeStyle): string => {
  if (style === 'conservative') return '优先保证可完成性，保留缓冲。'
  if (style === 'sprint') return '冲刺模式优先高收益步骤。'
  return '平衡推进任务质量与节奏。'
}

const inferDifficulty = (estimatedPomodoros: number): 'low' | 'medium' | 'high' => {
  if (estimatedPomodoros <= 1) return 'low'
  if (estimatedPomodoros >= 3) return 'high'
  return 'medium'
}

const toActionStep = (partial: PartialStep, input: GoalDecomposeInput, fallbackTitle = ''): AITaskStep => {
  const titleSeed = String(partial.title || partial.task || fallbackTitle || input.goal).trim()
  const title = rewriteToActionableTitle(titleSeed, input.weakPoints || '')
  const estimated = partial.estimatedPomodoros ?? (partial.minutes ? Math.max(1, Math.round(Number(partial.minutes) / 25)) : 1)
  const normalizedEstimated = Math.max(1, Math.round(Number(estimated) || 1))
  return {
    id: partial.id || makeId(),
    title,
    description: String(partial.description || '').trim(),
    doneDefinition: String(partial.doneDefinition || '完成该步骤并记录关键产出。').trim(),
    estimatedPomodoros: normalizedEstimated,
    priority: Math.max(1, Math.round(Number(partial.priority || 1))),
    difficulty: ['low', 'medium', 'high'].includes(String(partial.difficulty)) ? (partial.difficulty as 'low' | 'medium' | 'high') : inferDifficulty(normalizedEstimated),
    category: String(partial.category || inferScenario(input.goal)),
    reason: String(partial.reason || buildReasonByStyle(input.style)).trim(),
    actionable: true,
    source: partial.source || 'llm'
  }
}

const splitLargeStep = (step: AITaskStep): AITaskStep[] => {
  if (step.estimatedPomodoros <= 3) return [step]
  const total = Math.max(1, Math.ceil(step.estimatedPomodoros))

  if (step.category === 'problem-solving' || /题|错题|刷题/.test(step.title)) {
    return [
      { ...step, id: makeId(), title: `${step.title} - 基础题热身`, estimatedPomodoros: 2, difficulty: 'medium' },
      { ...step, id: makeId(), title: `${step.title} - 核心题突破`, estimatedPomodoros: 3, difficulty: 'high' },
      { ...step, id: makeId(), title: `${step.title} - 错因复盘`, estimatedPomodoros: 1, difficulty: 'medium' }
    ]
  }

  if (step.category === 'writing' || /作文|写作/.test(step.title)) {
    return [
      { ...step, id: makeId(), title: `${step.title} - 列提纲`, estimatedPomodoros: 1, difficulty: 'low' },
      { ...step, id: makeId(), title: `${step.title} - 写初稿`, estimatedPomodoros: 2, difficulty: 'medium' },
      { ...step, id: makeId(), title: `${step.title} - 修改定稿`, estimatedPomodoros: 1, difficulty: 'medium' }
    ]
  }

  if (step.category === 'review' || /复习|复盘|章节/.test(step.title)) {
    return [
      { ...step, id: makeId(), title: `${step.title} - 回顾要点`, estimatedPomodoros: 1, difficulty: 'low' },
      { ...step, id: makeId(), title: `${step.title} - 练习验证`, estimatedPomodoros: 2, difficulty: 'medium' },
      { ...step, id: makeId(), title: `${step.title} - 总结归档`, estimatedPomodoros: 1, difficulty: 'low' }
    ]
  }

  const chunks = Math.ceil(total / 3)
  return Array.from({ length: chunks }, (_, index) => {
    const isLast = index === chunks - 1
    const remain = total - index * 3
    return {
      ...step,
      id: makeId(),
      title: `${step.title} - 子任务 ${index + 1}`,
      estimatedPomodoros: isLast ? Math.max(1, remain) : 3,
      difficulty: isLast ? inferDifficulty(Math.max(1, remain)) : 'high'
    }
  })
}

const applyStyle = (steps: AITaskStep[], input: GoalDecomposeInput): AITaskStep[] => {
  const availablePomodoros = input.availableMinutes ? Math.max(1, Math.floor(input.availableMinutes / 25)) : undefined
  const budgetByStyle: Record<DecomposeStyle, number> = {
    conservative: availablePomodoros ? Math.max(1, Math.floor(availablePomodoros * 0.75)) : 5,
    balanced: availablePomodoros ? Math.max(1, Math.floor(availablePomodoros * 0.88)) : 7,
    sprint: availablePomodoros ? Math.max(1, Math.floor(availablePomodoros * 1.0)) : 9
  }
  const budget = budgetByStyle[input.style]

  if (input.style === 'conservative') {
    return steps.slice(0, 3).map((step) => ({ ...step, estimatedPomodoros: Math.min(2, step.estimatedPomodoros) }))
  }

  if (input.style === 'sprint') {
    const expanded: AITaskStep[] = []
    steps.forEach((step) => {
      if (step.estimatedPomodoros <= 1) {
        expanded.push(step)
        return
      }
      const blocks = Math.min(3, step.estimatedPomodoros)
      for (let index = 0; index < blocks; index += 1) {
        expanded.push({
          ...step,
          id: makeId(),
          title: `${step.title} - 冲刺段 ${index + 1}`,
          estimatedPomodoros: 1,
          difficulty: 'high',
          doneDefinition: step.doneDefinition || '完成该冲刺段并记录结果。'
        })
      }
    })
    return expanded
  }

  const total = steps.reduce((sum, step) => sum + step.estimatedPomodoros, 0)
  if (total <= budget) return steps

  const trimmed: AITaskStep[] = []
  let consumed = 0
  for (const step of steps) {
    if (consumed >= budget) break
    const remain = budget - consumed
    const assigned = Math.min(remain, step.estimatedPomodoros)
    trimmed.push({ ...step, estimatedPomodoros: Math.max(1, assigned), difficulty: inferDifficulty(Math.max(1, assigned)) })
    consumed += assigned
  }
  return trimmed
}

const createFallbackSeeds = (input: GoalDecomposeInput): AITaskStep[] => {
  const scenario = inferScenario(input.goal)
  const actionableGoal = rewriteToActionableTitle(input.goal, input.weakPoints || '')
  if (scenario === 'math') {
    return [
      toActionStep({
        title: '高数：重做第二章错题 1-8 题',
        estimatedPomodoros: 2,
        category: 'problem-solving',
        doneDefinition: '完成 1-8 题重做并标注仍不会的题。',
        reason: '先修复高频错题，再做新题更稳。',
        source: 'fallback_rule'
      }, input),
      toActionStep({
        title: '高数：整理错因并写 5 条避坑策略',
        estimatedPomodoros: 1,
        category: 'review',
        doneDefinition: '输出 5 条错因-修正策略。',
        reason: '复盘让练习结果沉淀为可复用方法。',
        source: 'fallback_rule'
      }, input)
    ]
  }

  return [
    toActionStep({
      title: actionableGoal,
      estimatedPomodoros: 2,
      doneDefinition: '完成可检查的输出并记录卡点。',
      reason: buildReasonByStyle(input.style),
      category: inferScenario(input.goal),
      source: 'fallback_rule'
    }, input),
    toActionStep({
      title: `${actionableGoal} - 复盘并整理下一步`,
      estimatedPomodoros: 1,
      doneDefinition: '输出复盘记录并列出下一步动作。',
      reason: '复盘可降低下一轮启动摩擦。',
      category: 'review',
      source: 'fallback_rule'
    }, input)
  ]
}

export const fallbackRuleBasedDecompose = (input: GoalDecomposeInput): AITaskStep[] => {
  const seeds = createFallbackSeeds(input)
  const styled = applyStyle(seeds, input)
  const expanded = styled.flatMap((step) => splitLargeStep(step))
  const bounded = expanded.map((step) => ({
    ...step,
    estimatedPomodoros: clampPomodoros(step.estimatedPomodoros),
    difficulty: inferDifficulty(clampPomodoros(step.estimatedPomodoros)),
    actionable: true,
    source: 'fallback_rule' as const
  }))
  return normalizePriority(bounded)
}

export const buildPlanningPrompt = (input: GoalDecomposeInput): PlanningPrompt => {
  const styleGuide: Record<DecomposeStyle, string> = {
    conservative: '步骤更少、更稳妥，保留缓冲，优先保证完成。',
    balanced: '步骤数量与粒度适中，平衡质量和节奏。',
    sprint: '步骤更多、节奏更紧，优先冲刺高收益任务。'
  }

  return {
    systemPrompt: [
      '你是学生任务拆解器，只输出严格 JSON 数组。',
      '禁止输出 markdown、解释文本或前后缀。',
      '每条步骤都必须可直接开始，不能是抽象目标。',
      '每条必须包含 title、estimatedPomodoros、doneDefinition、reason。',
      'estimatedPomodoros 必须是整数，默认 1~3。',
      '任务过大请拆分。',
      '输出语言与用户输入一致（默认中文）。'
    ].join('\n'),
    userPrompt: [
      `目标: ${input.goal}`,
      `风格: ${input.style}（${styleGuide[input.style]}）`,
      `可用时长(分钟): ${input.availableMinutes ?? '未提供'}`,
      `薄弱点: ${input.weakPoints || '未提供'}`,
      '请返回 JSON 数组，元素示例：',
      '{"title":"高数：重做第二章错题 1-8 题","estimatedPomodoros":2,"doneDefinition":"完成错题重做并标记仍不会的题","reason":"这是高优先级基础步骤"}'
    ].join('\n')
  }
}

const extractModelText = (raw: unknown): string => {
  if (typeof raw === 'string') return raw
  if (!raw || typeof raw !== 'object') return ''

  const anyRaw = raw as any
  if (typeof anyRaw?.choices?.[0]?.message?.content === 'string') return anyRaw.choices[0].message.content
  if (typeof anyRaw?.data?.choices?.[0]?.message?.content === 'string') return anyRaw.data.choices[0].message.content
  if (typeof anyRaw?.content === 'string') return anyRaw.content
  if (typeof anyRaw?.text === 'string') return anyRaw.text
  if (typeof anyRaw?.output_text === 'string') return anyRaw.output_text
  if (typeof anyRaw?.result === 'string') return anyRaw.result
  if (Array.isArray(anyRaw?.plan)) return JSON.stringify(anyRaw.plan)
  if (Array.isArray(anyRaw?.steps)) return JSON.stringify(anyRaw.steps)
  if (Array.isArray(anyRaw?.data?.plan)) return JSON.stringify(anyRaw.data.plan)
  if (Array.isArray(anyRaw?.data?.steps)) return JSON.stringify(anyRaw.data.steps)
  return JSON.stringify(raw)
}

export const extractJsonText = (raw: unknown): string => {
  const text = stripCodeFence(extractModelText(raw))
  if (!text) return ''
  if (text.startsWith('[')) {
    return extractBalancedJson(text, '[', ']') || text
  }
  const arrayText = extractBalancedJson(text, '[', ']')
  if (arrayText) return arrayText
  const objectText = extractBalancedJson(text, '{', '}')
  return objectText || text
}

export const parseDraftSteps = (jsonText: string): unknown => {
  if (!jsonText) return []
  const parsed = JSON.parse(jsonText)
  if (Array.isArray(parsed)) return parsed
  if (parsed && typeof parsed === 'object') {
    const anyParsed = parsed as any
    if (Array.isArray(anyParsed.plan)) return anyParsed.plan
    if (Array.isArray(anyParsed.steps)) return anyParsed.steps
    if (Array.isArray(anyParsed.data?.plan)) return anyParsed.data.plan
    if (Array.isArray(anyParsed.data?.steps)) return anyParsed.data.steps
  }
  return []
}

export const validateDraftSteps = (data: unknown): PartialStep[] => {
  if (!Array.isArray(data)) return []
  return data
    .map((item) => {
      if (!item || typeof item !== 'object') return null
      const source = item as any
      const title = String(source.title || source.task || '').trim()
      const estimated = source.estimatedPomodoros ?? (Number.isFinite(Number(source.minutes)) ? Math.max(1, Math.round(Number(source.minutes) / 25)) : undefined)
      return {
        id: source.id ? String(source.id) : undefined,
        title,
        description: source.description ? String(source.description) : undefined,
        doneDefinition: source.doneDefinition ? String(source.doneDefinition) : undefined,
        estimatedPomodoros: estimated,
        priority: source.priority,
        difficulty: source.difficulty,
        category: source.category ? String(source.category) : undefined,
        reason: source.reason ? String(source.reason) : undefined,
        actionable: source.actionable,
        source: source.source
      } satisfies PartialStep
    })
    .filter(Boolean) as PartialStep[]
}

export const sanitizeDraftSteps = (
  rawSteps: PartialStep[],
  input: GoalDecomposeInput,
  source: 'llm' | 'fallback_rule' = 'llm'
): AITaskStep[] => {
  const normalized = rawSteps
    .map((item, index) => toActionStep({
      ...item,
      priority: item.priority ?? index + 1,
      source
    }, input, input.goal))
    .filter((item) => item.title && item.estimatedPomodoros > 0)

  const expanded = normalized.flatMap((step) => splitLargeStep(step))
  const bounded = expanded.map((step) => {
    const estimated = clampPomodoros(step.estimatedPomodoros)
    return {
      ...step,
      estimatedPomodoros: estimated,
      difficulty: inferDifficulty(estimated),
      doneDefinition: step.doneDefinition || '完成该步骤并记录关键产出。',
      reason: step.reason || buildReasonByStyle(input.style),
      actionable: true,
      source
    }
  })

  return normalizePriority(bounded)
}

export const markRecommendedFirst = (steps: AITaskStep[]): AITaskStep[] => {
  return steps.map((step, index) => ({
    ...step,
    isRecommendedFirst: index === 0
  }))
}

const requestViaProxy = async (input: GoalDecomposeInput, prompt: PlanningPrompt): Promise<unknown> => {
  const response = await withTimeout(
    api.post(PROXY_ENDPOINT, {
      goal: input.goal,
      style: input.style,
      available_minutes: input.availableMinutes,
      weak_points: input.weakPoints,
      system_prompt: prompt.systemPrompt,
      user_prompt: prompt.userPrompt
    }, { timeout: DEFAULT_TIMEOUT_MS }),
    DEFAULT_TIMEOUT_MS,
    'Proxy planning timeout'
  )
  return response?.data
}

const requestViaDirect = async (input: GoalDecomposeInput, prompt: PlanningPrompt): Promise<unknown> => {
  const apiKey = import.meta.env.VITE_LLM_API_KEY || import.meta.env.VITE_QWEN_API_KEY
  if (!apiKey) {
    throw new Error('Missing direct LLM API key')
  }

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS)
  try {
    const response = await fetch(DEFAULT_BASE_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`
      },
      signal: controller.signal,
      body: JSON.stringify({
        model: DEFAULT_MODEL,
        temperature: 0.2,
        messages: [
          { role: 'system', content: prompt.systemPrompt },
          { role: 'user', content: prompt.userPrompt }
        ],
        metadata: {
          goal: input.goal,
          style: input.style
        }
      })
    })
    if (!response.ok) {
      const detail = await response.text()
      throw new Error(detail || `Direct planning request failed: ${response.status}`)
    }
    return response.json()
  } finally {
    clearTimeout(timer)
  }
}

export const requestLLMPlan = async (input: GoalDecomposeInput, prompt: PlanningPrompt): Promise<unknown> => {
  if (import.meta.env.MODE === 'test' && import.meta.env.VITE_FORCE_LLM_IN_TEST !== 'true') {
    throw new Error('LLM disabled in test mode')
  }

  const routePreference = (import.meta.env.VITE_LLM_ROUTE_MODE || 'proxy') as LLMRoute
  const routes: LLMRoute[] = routePreference === 'direct' ? ['direct', 'proxy'] : ['proxy', 'direct']

  let lastError: unknown = null
  for (const route of routes) {
    try {
      if (route === 'proxy') return await requestViaProxy(input, prompt)
      return await requestViaDirect(input, prompt)
    } catch (error) {
      lastError = error
    }
  }
  throw lastError || new Error('LLM planning failed')
}

export const useAIPlanning = (deps: Partial<PlanningDeps> = {}) => {
  let activeRequestId = 0
  const request = deps.requestLLMPlan || requestLLMPlan
  const fallback = deps.fallbackRuleBasedDecompose || fallbackRuleBasedDecompose

  const generateDraftPlan = async (input: GoalDecomposeInput): Promise<AITaskStep[]> => {
    const requestId = ++activeRequestId
    const normalizedInput: GoalDecomposeInput = {
      goal: String(input.goal || '').trim(),
      style: input.style || 'balanced',
      availableMinutes: input.availableMinutes,
      weakPoints: String(input.weakPoints || '').trim() || undefined
    }

    if (!normalizedInput.goal) return []

    const ensureFresh = (): void => {
      if (requestId !== activeRequestId) {
        throw new StalePlanningRequestError()
      }
    }

    try {
      const prompt = buildPlanningPrompt(normalizedInput)
      const raw = await request(normalizedInput, prompt)
      ensureFresh()

      const jsonText = extractJsonText(raw)
      const parsed = parseDraftSteps(jsonText)
      const validated = validateDraftSteps(parsed)
      const sanitized = sanitizeDraftSteps(validated, normalizedInput, 'llm')
      if (sanitized.length < 1) {
        throw new Error('No valid steps after sanitize')
      }

      ensureFresh()
      return markRecommendedFirst(sanitized)
    } catch (error) {
      if (error instanceof StalePlanningRequestError) {
        throw error
      }
      const fallbackSteps = fallback(normalizedInput)
      if (fallbackSteps.length < 1) return []
      ensureFresh()
      return markRecommendedFirst(
        sanitizeDraftSteps(fallbackSteps, normalizedInput, 'fallback_rule')
      )
    }
  }

  return {
    generateDraftPlan
  }
}

