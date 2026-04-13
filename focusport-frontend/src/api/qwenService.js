import api from './index'

const QWEN_ENDPOINT = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
const DEFAULT_MODEL = 'qwen-plus'
const BLANK_LOG_FEEDBACK = '警告：未检测到有效算力日志，判定为系统休眠，收益减半。'
const FALLBACK_FEEDBACK = '量子评估通道波动，本次按基础收益结算。'
const SYSTEM_PROMPT = '你现在是极点星港的 AI 副官，兼具清华毒舌学长的人设。你需要根据指挥官（用户）提交的【学习日志】、【任务难度】和【专注时长】进行质量评估。你必须且只能输出合法的 JSON 格式，绝不能包含任何 Markdown 标记或多余的文字。'
const SEQUENCE_PLAN_SYSTEM_PROMPT = '你现在是极点星港的舰载参谋端。请把用户给出的目标拆解成简洁、可执行、适合待办清单的步序。你必须且只能输出合法 JSON，禁止 Markdown、禁止解释、禁止额外文本。输出格式固定为：{"plan":[{"id":1,"task":"任务文本","minutes":25,"priority":1}]}'

const clampMultiplier = (value, fallback = 1.0) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return fallback
  return Math.min(1.5, Math.max(0.5, numeric))
}

export const stripMarkdownCodeFence = (rawText = '') => {
  const trimmed = String(rawText || '').trim()
  if (!trimmed) return ''
  const withoutOpeningFence = trimmed.replace(/^\s*```(?:json)?\s*/i, '')
  return withoutOpeningFence.replace(/\s*```\s*$/i, '').trim()
}

export const extractJsonObjectText = (rawText = '') => {
  const normalized = stripMarkdownCodeFence(rawText)
  if (!normalized) return ''
  const jsonMatch = normalized.match(/\{[\s\S]*\}/)
  return jsonMatch ? jsonMatch[0] : normalized
}

export const parseQwenEvaluationResponse = (rawText = '', fallback = {}) => {
  const fallbackMultiplier = clampMultiplier(fallback.qualityMultiplier ?? 1.0, 1.0)
  const fallbackFeedback = String(fallback.feedback || FALLBACK_FEEDBACK)
  const candidate = extractJsonObjectText(rawText)

  try {
    const parsed = JSON.parse(candidate)
    return {
      qualityMultiplier: clampMultiplier(parsed.qualityMultiplier, fallbackMultiplier),
      feedback: String(parsed.feedback || fallbackFeedback).trim() || fallbackFeedback,
      rawContent: rawText
    }
  } catch (error) {
    return {
      qualityMultiplier: fallbackMultiplier,
      feedback: fallbackFeedback,
      rawContent: rawText,
      parseError: error
    }
  }
}

const clampTaskMinutes = (value) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return 25
  return Math.min(180, Math.max(5, Math.round(numeric)))
}

const normalizePlanTasks = (plan = []) => (
  Array.isArray(plan)
    ? plan
      .map((item, index) => ({
        id: item?.id || index + 1,
        task: String(item?.task || '').trim(),
        minutes: clampTaskMinutes(item?.minutes),
        priority: Number.isFinite(Number(item?.priority)) ? Math.max(1, Math.round(Number(item.priority))) : index + 1
      }))
      .filter((item) => item.task)
    : []
)

export const parseSequencePlanResponse = (rawText = '') => {
  const candidate = extractJsonObjectText(rawText)
  try {
    const parsed = JSON.parse(candidate)
    return {
      plan: normalizePlanTasks(parsed?.plan || []),
      rawContent: rawText
    }
  } catch (error) {
    return {
      plan: [],
      rawContent: rawText,
      parseError: error
    }
  }
}

const buildMessages = ({ sessionLog, taskDifficulty, durationMinutes, subject }) => ([
  { role: 'system', content: SYSTEM_PROMPT },
  {
    role: 'user',
    content: [
      `学习日志：${sessionLog || '（空）'}`,
      `任务难度：${taskDifficulty || 'L1'}`,
      `专注时长：${Number(durationMinutes || 0)} 分钟`,
      `任务主题：${subject || '专注任务'}`
    ].join('\n')
  }
])

const evaluateViaProxy = async ({ sessionLog, taskDifficulty, durationMinutes, subject, model }) => {
  const response = await api.post('/api/ai/evaluate-study-log', {
    session_log: sessionLog,
    task_difficulty: taskDifficulty,
    duration_minutes: durationMinutes,
    subject,
    model
  })
  return response.data || {}
}

const evaluateViaDirectFetch = async ({ sessionLog, taskDifficulty, durationMinutes, subject, model }) => {
  const apiKey = import.meta.env.VITE_QWEN_API_KEY
  if (!apiKey) {
    throw new Error('Missing VITE_QWEN_API_KEY for direct Qwen testing.')
  }

  const response = await fetch(QWEN_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`
    },
    body: JSON.stringify({
      model: model || DEFAULT_MODEL,
      temperature: 0.2,
      messages: buildMessages({ sessionLog, taskDifficulty, durationMinutes, subject })
    })
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Qwen direct request failed with status ${response.status}`)
  }

  const payload = await response.json()
  const rawContent = payload?.choices?.[0]?.message?.content || ''
  const parsed = parseQwenEvaluationResponse(rawContent)
  return {
    success: true,
    qualityMultiplier: parsed.qualityMultiplier,
    feedback: parsed.feedback,
    rawContent,
    model: model || DEFAULT_MODEL,
    source: parsed.parseError ? 'fallback' : 'qwen'
  }
}

const requestQwenChatCompletion = async ({ messages, model = DEFAULT_MODEL }) => {
  const apiKey = import.meta.env.VITE_QWEN_API_KEY
  if (!apiKey) {
    throw new Error('Missing VITE_QWEN_API_KEY for direct Qwen testing.')
  }

  const response = await fetch(QWEN_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`
    },
    body: JSON.stringify({
      model,
      temperature: 0.2,
      messages
    })
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Qwen request failed with status ${response.status}`)
  }

  const payload = await response.json()
  return payload?.choices?.[0]?.message?.content || ''
}

const localSequenceFallback = (goal = '') => {
  const normalizedGoal = String(goal || '').trim()
  const slices = normalizedGoal
    .split(/[，。,；;、\n]+/)
    .map((part) => part.trim())
    .filter(Boolean)

  const seedTasks = slices.length ? slices : [
    `明确目标边界：${normalizedGoal}`,
    `收集完成 ${normalizedGoal} 所需资料`,
    `执行核心任务并完成一次复盘`
  ]

  return {
    plan: normalizePlanTasks(
      seedTasks.slice(0, 5).map((task, index) => ({
        id: index + 1,
        task,
        minutes: index === 0 ? 15 : 25,
        priority: index + 1
      }))
    ),
    source: 'fallback'
  }
}

export const evaluateStudyLog = async ({
  sessionLog = '',
  taskDifficulty = 'L1',
  durationMinutes = 25,
  subject = '专注任务',
  mode = 'proxy',
  model = DEFAULT_MODEL
} = {}) => {
  const normalizedLog = String(sessionLog || '').trim()

  if (!normalizedLog) {
    return {
      success: true,
      qualityMultiplier: 0.5,
      feedback: BLANK_LOG_FEEDBACK,
      source: 'blank_shortcut',
      model,
      rawContent: ''
    }
  }

  const shouldUseDirect = mode === 'direct' && import.meta.env.DEV && import.meta.env.VITE_QWEN_API_KEY

  if (shouldUseDirect) {
    try {
      return await evaluateViaDirectFetch({
        sessionLog: normalizedLog,
        taskDifficulty,
        durationMinutes,
        subject,
        model
      })
    } catch (error) {
      return {
        success: false,
        qualityMultiplier: 1.0,
        feedback: FALLBACK_FEEDBACK,
        source: 'fallback',
        model,
        rawContent: '',
        error
      }
    }
  }

  try {
    return await evaluateViaProxy({
      sessionLog: normalizedLog,
      taskDifficulty,
      durationMinutes,
      subject,
      model
    })
  } catch (error) {
    return {
      success: false,
      qualityMultiplier: 1.0,
      feedback: FALLBACK_FEEDBACK,
      source: 'fallback',
      model,
      rawContent: '',
      error
    }
  }
}

export const previewSequencePlan = async ({
  goal = '',
  mode = 'direct',
  model = DEFAULT_MODEL
} = {}) => {
  const normalizedGoal = String(goal || '').trim()
  if (!normalizedGoal) {
    return { plan: [], source: 'empty', rawContent: '' }
  }

  const canUseDirect = import.meta.env.VITE_QWEN_API_KEY && (mode === 'direct' || import.meta.env.DEV)
  if (!canUseDirect) {
    return localSequenceFallback(normalizedGoal)
  }

  try {
    const rawContent = await requestQwenChatCompletion({
      model,
      messages: [
        { role: 'system', content: SEQUENCE_PLAN_SYSTEM_PROMPT },
        {
          role: 'user',
          content: `目标：${normalizedGoal}\n请直接输出 JSON 待办计划，每个任务应简洁并带建议专注时长 minutes。`
        }
      ]
    })
    const parsed = parseSequencePlanResponse(rawContent)
    if (!parsed.plan.length) {
      return {
        ...localSequenceFallback(normalizedGoal),
        rawContent,
        parseError: parsed.parseError
      }
    }
    return {
      plan: parsed.plan,
      source: 'qwen',
      rawContent
    }
  } catch (error) {
    return {
      ...localSequenceFallback(normalizedGoal),
      error
    }
  }
}

export const qwenService = {
  evaluateStudyLog,
  parseQwenEvaluationResponse,
  parseSequencePlanResponse,
  stripMarkdownCodeFence,
  extractJsonObjectText,
  previewSequencePlan
}

export default qwenService
