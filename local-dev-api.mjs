import http from 'node:http'
import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { extname } from 'node:path'
import { existsSync, readdirSync } from 'node:fs'

const HOST = process.env.HOST || '127.0.0.1'
const PORT = Number(process.env.PORT || 8010)
const STATE_FILE = new URL('./.dev-api-state.json', import.meta.url)
const STATIC_DIR = new URL('./static/', import.meta.url)
const ADMIN_UPLOAD_ALLOWED_SUFFIXES = new Set(['.pdf', '.doc', '.docx', '.mp3', '.wav', '.m4a', '.ogg'])
const DAILY_POMODORO_COMPUTE_REWARD = 200
const ARCADE_ROOM_CREATE_COST = 25
const ARCADE_WINNER_COMPUTE_REWARD = 10
const ADMIN_TEST_USERNAME = 'admin_test'
const ADMIN_TEST_PASSWORD = 'FocusPortAdmin888'
const ADMIN_TEST_COMPUTE = 999999999

const mockExams = [
  {
    exam_code: 'ENG-MOCK-01',
    title: '语言考核站 01',
    time_limit: 45,
    config_json: {
      sections: [
        {
          name: '词汇选择',
          instruction: '选择最合适的答案完成句子。',
          questions: [
            { id: 'q1', type: 'choice', question: 'She usually ___ to school by bus.', options: { A: 'go', B: 'goes', C: 'going', D: 'gone' } },
            { id: 'q2', type: 'choice', question: 'We have lived here ___ five years.', options: { A: 'for', B: 'since', C: 'from', D: 'in' } },
            { id: 'q3', type: 'choice', question: 'If it rains tomorrow, we ___ at home.', options: { A: 'stay', B: 'stayed', C: 'will stay', D: 'stays' } }
          ]
        },
        {
          name: '填空练习',
          instruction: '根据句意填入合适单词。',
          questions: [
            { id: 'q4', type: 'fill', question: 'Learning takes time and ____ .' },
            { id: 'q5', type: 'fill', question: 'Please turn off your phone and stay ____ during study time.' }
          ]
        }
      ]
    },
    answer_key_json: { q1: 'B', q2: 'A', q3: 'C', q4: 'practice', q5: 'focused' }
  },
  {
    exam_code: 'ENG-MOCK-02',
    title: '语言考核站 02',
    time_limit: 35,
    config_json: {
      sections: [
        {
          name: '基础阅读',
          instruction: '选择最合适的答案。',
          questions: [
            { id: 'q1', type: 'choice', question: 'Tom is taller than ___ in his class.', options: { A: 'any student', B: 'any other student', C: 'other student', D: 'the student' } },
            { id: 'q2', type: 'choice', question: 'My homework ___ before dinner yesterday.', options: { A: 'finished', B: 'was finished', C: 'is finished', D: 'finishes' } },
            { id: 'q3', type: 'fill', question: 'The best way to improve English is to keep ____ every day.' }
          ]
        }
      ]
    },
    answer_key_json: { q1: 'B', q2: 'B', q3: 'practicing' }
  }
]

const defaultGrowth = () => ({
  exp: 0,
  level: 1,
  coins: 1000,
  diamonds: 50,
  discipline_score: 50,
  focus_energy: 0,
  streak_days: 0,
  max_streak: 0,
  total_focus_minutes: 0,
  total_trees: 0,
  achievements_count: 0,
  daily_pomodoro_compute_reward_date: ''
})

const loadState = async () => {
  if (!existsSync(STATE_FILE)) {
    return { users: {}, growth: {}, todos: {}, focusSessions: {}, aiChats: {}, messages: {}, friends: [], arcadeRooms: {}, computeLedger: {}, inventory: {}, placed: {}, nextTaskId: 1, nextAiChatId: 1, nextMessageId: 1, nextFriendshipId: 1, nextInventoryId: 1, nextPlacedId: 1 }
  }
  try {
    const loaded = JSON.parse(await readFile(STATE_FILE, 'utf8'))
    return {
      users: loaded.users || {},
      growth: loaded.growth || {},
      todos: loaded.todos || {},
      focusSessions: loaded.focusSessions || {},
      aiChats: loaded.aiChats || {},
      messages: loaded.messages || {},
      friends: Array.isArray(loaded.friends) ? loaded.friends : [],
      arcadeRooms: loaded.arcadeRooms || {},
      computeLedger: loaded.computeLedger || {},
      inventory: loaded.inventory || {},
      placed: loaded.placed || {},
      nextTaskId: loaded.nextTaskId || 1,
      nextAiChatId: loaded.nextAiChatId || 1,
      nextMessageId: loaded.nextMessageId || 1,
      nextFriendshipId: loaded.nextFriendshipId || 1,
      nextInventoryId: loaded.nextInventoryId || 1,
      nextPlacedId: loaded.nextPlacedId || 1
    }
  } catch {
    return { users: {}, growth: {}, todos: {}, focusSessions: {}, aiChats: {}, messages: {}, friends: [], arcadeRooms: {}, computeLedger: {}, inventory: {}, placed: {}, nextTaskId: 1, nextAiChatId: 1, nextMessageId: 1, nextFriendshipId: 1, nextInventoryId: 1, nextPlacedId: 1 }
  }
}

let state = await loadState()
let writeQueue = Promise.resolve()
const arcadeWsConnections = new Map()

const saveState = async () => {
  await writeFile(STATE_FILE, JSON.stringify(state, null, 2), 'utf8')
}

const withStateWrite = async (handler) => {
  const run = writeQueue.then(async () => {
    const result = await handler()
    await saveState()
    return result
  })
  writeQueue = run.catch(() => {})
  return run
}

const send = (res, status, payload) => {
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS,HEAD',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
    'Access-Control-Max-Age': '86400'
  })
  res.end(JSON.stringify(payload))
}

const staticContentTypes = new Map([
  ['.pdf', 'application/pdf'],
  ['.doc', 'application/msword'],
  ['.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
  ['.mp3', 'audio/mpeg'],
  ['.wav', 'audio/wav'],
  ['.m4a', 'audio/mp4'],
  ['.ogg', 'audio/ogg']
])

const sendStaticFile = async (req, res, pathname) => {
  const rawName = decodeURIComponent(pathname.replace(/^\/static\//, ''))
  const filename = sanitizeAdminUploadFilename(rawName)
  const data = await readFile(new URL(filename, STATIC_DIR))
  res.writeHead(200, {
    'Content-Type': staticContentTypes.get(extname(filename).toLowerCase()) || 'application/octet-stream',
    'Cache-Control': 'no-store',
    'Access-Control-Allow-Origin': '*'
  })
  if (req.method === 'HEAD') return res.end()
  res.end(data)
}

const readBody = async (req) => {
  const chunks = []
  for await (const chunk of req) chunks.push(chunk)
  const raw = Buffer.concat(chunks).toString('utf8')
  if (!raw) return {}
  try {
    return JSON.parse(raw)
  } catch {
    return {}
  }
}

const ensureUser = (username, password = 'dev') => {
  const name = String(username || '').trim()
  if (!name) return null
  if (name === ADMIN_TEST_USERNAME) password = ADMIN_TEST_PASSWORD
  if (!state.users[name]) state.users[name] = { username: name, password }
  if (name === ADMIN_TEST_USERNAME) state.users[name].password = ADMIN_TEST_PASSWORD
  if (!state.growth[name]) state.growth[name] = defaultGrowth()
  if (name === ADMIN_TEST_USERNAME) {
    state.growth[name].coins = ADMIN_TEST_COMPUTE
    state.growth[name].diamonds = Math.max(Number(state.growth[name].diamonds || 0), 999999)
  }
  if (!state.todos[name]) state.todos[name] = []
  if (!state.focusSessions) state.focusSessions = {}
  if (!state.focusSessions[name]) state.focusSessions[name] = []
  if (!state.aiChats[name]) state.aiChats[name] = []
  if (!state.messages[name]) state.messages[name] = []
  if (!state.inventory[name]) state.inventory[name] = []
  if (!state.placed[name]) state.placed[name] = []
  if (!state.computeLedger) state.computeLedger = {}
  if (!state.computeLedger[name]) state.computeLedger[name] = []
  return state.users[name]
}

const recordComputeLedger = (username, amount, source = 'system', description = '') => {
  const user = String(username || '').trim()
  if (!user || !Number(amount)) return
  ensureUser(user)
  state.computeLedger[user].push({
    amount: Number(amount),
    transaction_type: Number(amount) >= 0 ? 'compute_gain' : 'compute_spend',
    source,
    description: description || (Number(amount) >= 0 ? `Compute gain from ${source}` : `Compute spend for ${source}`),
    created_at: new Date().toISOString()
  })
}

const gradeExam = (exam, answers = {}) => {
  const questions = (exam.config_json.sections || []).flatMap((section) => section.questions || [])
  const mistakes = []
  let correct = 0

  for (const question of questions) {
    const expected = String(exam.answer_key_json[question.id] || '').trim()
    const actual = String(answers[question.id] || '').trim()
    const matched = question.type === 'fill'
      ? actual.toLowerCase() === expected.toLowerCase()
      : actual === expected
    if (matched) {
      correct += 1
    } else {
      mistakes.push({
        question: question.question,
        user: actual || '未作答',
        correct: expected,
        analysis: '回看题干关键词，再对照标准答案复盘一次。'
      })
    }
  }

  const total = Math.max(questions.length, 1)
  return {
    objective_score: Math.round((correct / total) * 1000) / 10,
    total_questions: questions.length,
    mistakes
  }
}

ensureUser(ADMIN_TEST_USERNAME, ADMIN_TEST_PASSWORD)
await saveState()

const normalizeFriendship = (entry, username) => {
  const other = entry.user_username === username ? entry.friend_username : entry.user_username
  const requestDirection = entry.user_username === username ? 'outgoing' : 'incoming'
  return {
    id: entry.id,
    user_username: entry.user_username,
    friend_username: other,
    requester_username: entry.user_username,
    recipient_username: entry.friend_username,
    request_direction: requestDirection,
    status: entry.status,
    created_at: entry.created_at
  }
}

const sanitizeAdminUploadFilename = (filename = '') => {
  const baseName = String(filename || '').replace(/\\/g, '/').split('/').pop().trim()
  const dotIndex = baseName.lastIndexOf('.')
  const ext = dotIndex >= 0 ? baseName.slice(dotIndex).toLowerCase() : ''
  if (!ADMIN_UPLOAD_ALLOWED_SUFFIXES.has(ext)) {
    const error = new Error('仅支持 PDF / Word / 音频文件')
    error.status = 400
    throw error
  }
  const rawStem = dotIndex >= 0 ? baseName.slice(0, dotIndex) : baseName
  const safeStem = rawStem.replace(/[^\p{L}\p{N}_.-]+/gu, '_').replace(/^[._]+|[._]+$/g, '') || `resource_${Date.now()}`
  return `${safeStem}${ext}`
}

const readMultipartFile = async (req) => {
  const contentType = String(req.headers['content-type'] || '')
  const boundaryMatch = contentType.match(/boundary=(?:"([^"]+)"|([^;]+))/i)
  if (!boundaryMatch) {
    const error = new Error('上传请求格式不正确')
    error.status = 400
    throw error
  }

  const boundary = Buffer.from(`--${boundaryMatch[1] || boundaryMatch[2]}`)
  const chunks = []
  for await (const chunk of req) chunks.push(chunk)
  const body = Buffer.concat(chunks)
  let cursor = 0

  while (cursor < body.length) {
    const boundaryIndex = body.indexOf(boundary, cursor)
    if (boundaryIndex < 0) break
    const nextBoundaryIndex = body.indexOf(boundary, boundaryIndex + boundary.length)
    if (nextBoundaryIndex < 0) break

    const partStart = boundaryIndex + boundary.length + 2
    const headerEnd = body.indexOf(Buffer.from('\r\n\r\n'), partStart)
    if (headerEnd < 0 || headerEnd > nextBoundaryIndex) {
      cursor = nextBoundaryIndex
      continue
    }

    const headers = body.subarray(partStart, headerEnd).toString('utf8')
    const disposition = headers.match(/content-disposition:[^\r\n]*/i)?.[0] || ''
    const name = disposition.match(/name="([^"]+)"/i)?.[1] || ''
    const filename = disposition.match(/filename="([^"]*)"/i)?.[1] || ''
    if (name === 'file' && filename) {
      const dataStart = headerEnd + 4
      const dataEnd = Math.max(dataStart, nextBoundaryIndex - 2)
      return { filename, data: body.subarray(dataStart, dataEnd) }
    }
    cursor = nextBoundaryIndex
  }

  const error = new Error('没有收到上传文件')
  error.status = 400
  throw error
}

const friendshipsFor = (username) => state.friends
  .filter((entry) => entry.user_username === username || entry.friend_username === username)
  .map((entry) => normalizeFriendship(entry, username))
  .sort((left, right) => Number(right.id || 0) - Number(left.id || 0))

const findFriendship = (left, right) => state.friends.find((entry) => (
  (entry.user_username === left && entry.friend_username === right) ||
  (entry.user_username === right && entry.friend_username === left)
))

const normalizeMessage = (message = {}) => ({
  id: message.id,
  sender: message.sender || '',
  receiver: message.receiver || '',
  title: message.title || '',
  content: message.content || '',
  category: message.category || 'friend',
  is_read: Boolean(message.is_read),
  created_at: message.created_at || new Date().toISOString()
})

const messagesFor = (username, category = '') => {
  ensureUser(username)
  return state.messages[username]
    .filter((message) => !category || message.category === category)
    .map(normalizeMessage)
    .sort((left, right) => Number(right.id || 0) - Number(left.id || 0))
}

const COMMERCIAL_ASSET_ROOT = new URL('./focusport-frontend/public/city-assets/commercial/', import.meta.url)
const COMMERCIAL_MODEL_ROOT = new URL('./Models/GLB format/', COMMERCIAL_ASSET_ROOT)
const COMMERCIAL_PREVIEW_BASE = '/city-assets/commercial/Previews'
const COMMERCIAL_MODEL_BASE = '/city-assets/commercial/Models/GLB format'

const isCommercialBuildingModel = (fileName = '') => (
  fileName.endsWith('.glb') &&
  (
    fileName.startsWith('building-') ||
    fileName.startsWith('low-detail-building-')
  )
)

const titleCaseAssetName = (stem = '') => stem
  .split('-')
  .filter(Boolean)
  .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
  .join(' ')

const commercialNameCn = (stem = '') => {
  const suffix = stem.split('-').pop()?.toUpperCase() || ''
  if (stem.startsWith('building-skyscraper-')) return `商业高楼 ${suffix}`
  if (stem.startsWith('low-detail-building-wide-')) return `低模宽体商业建筑 ${suffix}`
  if (stem.startsWith('low-detail-building-')) return `低模商业建筑 ${suffix}`
  return `商业建筑 ${suffix}`
}

const commercialRarity = (stem = '') => {
  if (stem.startsWith('building-skyscraper-')) return 'rare'
  if (stem.includes('wide')) return 'rare'
  return 'common'
}

const commercialPrice = (stem = '') => {
  if (stem.startsWith('building-skyscraper-')) return 450
  if (stem.includes('wide')) return 260
  if (stem.startsWith('low-detail-building-')) return 180
  return 290
}

const buildCommercialCatalog = () => {
  if (!existsSync(COMMERCIAL_MODEL_ROOT)) return []
  return readdirSync(COMMERCIAL_MODEL_ROOT)
    .filter(isCommercialBuildingModel)
    .sort((left, right) => left.localeCompare(right, undefined, { numeric: true }))
    .map((fileName, index) => {
      const stem = fileName.replace(/\.glb$/i, '')
      return {
        id: 31000 + index,
        item_code: `commercial_${stem.replace(/-/g, '_')}`,
        name: titleCaseAssetName(stem),
        name_cn: commercialNameCn(stem),
        category: 'structures',
        subcategory: 'commercial',
        tags: '3d,commercial,building',
        model_path: `${COMMERCIAL_MODEL_BASE}/${fileName}`,
        preview_path: `${COMMERCIAL_PREVIEW_BASE}/${stem}.png`,
        icon: '🏢',
        price_sunshine: 0,
        price_coins: commercialPrice(stem),
        rarity: commercialRarity(stem),
        description: `${commercialNameCn(stem)}，可部署到 3D 物理视界实体基地。`,
        is_available: 1,
        sort_order: 3000 + index,
        dimension: '3D',
        grid_width: 1,
        grid_height: 1
      }
    })
}

const physicalCatalog = buildCommercialCatalog()
const catalogById = new Map(physicalCatalog.map((item) => [Number(item.id), item]))
const physicalShopCatalog = physicalCatalog

const normalizeDimension = (value) => String(value || '3D').toUpperCase() === '2D' ? '2D' : '3D'
const placementTypeForCategory = (category) => ['plants', 'trees', 'greenery'].includes(category) ? 'greenery' : 'building'
const gradeForRarity = (rarity) => ({ common: 'C', rare: 'B', epic: 'A', legendary: 'S' }[String(rarity || '').toLowerCase()] || 'C')

const inventoryFor = (username) => {
  ensureUser(username)
  return state.inventory[username]
}

const placedFor = (username) => {
  ensureUser(username)
  return state.placed[username]
}

const slotCapacityFor = (username, placementType) => {
  const total = placementType === 'greenery' ? 20 : 30
  const used = placedFor(username).filter((placed) => {
    const item = catalogById.get(Number(placed.item_id))
    return item && placementTypeForCategory(item.category) === placementType
  }).length
  return Math.max(total - used, 0)
}

const enrichShopItem = (item, username = '') => {
  const inventory = username ? inventoryFor(username) : []
  const placed = username ? placedFor(username) : []
  const ownedCount = inventory.filter((unit) => Number(unit.item_id) === Number(item.id)).length
  const availableCount = inventory.filter((unit) => Number(unit.item_id) === Number(item.id) && unit.status === 'owned').length
  const placedCount = placed.filter((unit) => Number(unit.item_id) === Number(item.id)).length
  const placementType = placementTypeForCategory(item.category)
  return {
    ...item,
    placement_type: placementType,
    grade: item.grade || gradeForRarity(item.rarity),
    owned_count: ownedCount,
    available_to_place_count: availableCount,
    placed_count: placedCount,
    slot_capacity_remaining: username ? slotCapacityFor(username, placementType) : 0
  }
}

const placedPayload = (placed, username) => {
  const item = catalogById.get(Number(placed.item_id)) || {}
  return {
    ...enrichShopItem(item, username),
    id: placed.id,
    username,
    item_id: placed.item_id,
    inventory_id: placed.inventory_id,
    position_x: placed.position_x,
    position_y: placed.position_y,
    position_z: placed.position_z,
    rotation_y: placed.rotation_y,
    scale: placed.scale,
    map_id: placed.map_id,
    slot_id: placed.slot_id,
    dimension: placed.dimension,
    grid_x: placed.grid_x,
    grid_y: placed.grid_y
  }
}

const normalizeTask = (task) => ({
  id: task.id,
  content: task.content,
  title: task.content,
  is_completed: Boolean(task.is_completed),
  isCompleted: Boolean(task.is_completed),
  status: task.status || (task.is_completed ? 'done' : 'todo'),
  scheduled_date: task.scheduled_date || '',
  scheduledDate: task.scheduled_date || '',
  scheduled_time: task.scheduled_time || '',
  scheduledTime: task.scheduled_time || '',
  category: task.category || 'FocusPort',
  accent: task.accent || '#4880FF',
  created_at: task.created_at,
  createdAt: task.created_at,
  completed_at: task.completed_at || '',
  completedAt: task.completed_at || ''
})

const periodDayCount = (period = 'week') => ({
  day: 1,
  daily: 1,
  week: 7,
  weekly: 7,
  month: 30,
  monthly: 30,
  year: 365
}[String(period || 'week')] || 7)

const toDateKey = (value = new Date()) => {
  const date = value instanceof Date ? value : new Date(value)
  const safeDate = Number.isNaN(date.getTime()) ? new Date() : date
  const year = safeDate.getFullYear()
  const month = String(safeDate.getMonth() + 1).padStart(2, '0')
  const day = String(safeDate.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const startOfLocalDay = (value = new Date()) => {
  const date = value instanceof Date ? new Date(value) : new Date(value)
  if (Number.isNaN(date.getTime())) return new Date()
  date.setHours(0, 0, 0, 0)
  return date
}

const dailyStatsFor = (username, days) => {
  ensureUser(username)
  const end = startOfLocalDay()
  const start = new Date(end)
  start.setDate(start.getDate() - Math.max(days - 1, 0))

  const minutesByDate = new Map()
  for (const session of state.focusSessions[username] || []) {
    if (session.status && session.status !== 'completed') continue
    const createdAt = new Date(session.created_at || session.createdAt || Date.now())
    if (Number.isNaN(createdAt.getTime()) || createdAt < start || createdAt > new Date()) continue
    const key = toDateKey(createdAt)
    minutesByDate.set(key, (minutesByDate.get(key) || 0) + Math.max(0, Number(session.duration_minutes || session.duration || 0)))
  }

  return Array.from({ length: days }, (_, index) => {
    const date = new Date(start)
    date.setDate(start.getDate() + index)
    const key = toDateKey(date)
    return { stat_date: key, focus_minutes: Math.round(minutesByDate.get(key) || 0) }
  })
}

const taskCompletedWithinDays = (task, days) => {
  if (!task?.is_completed) return false
  const completedAt = startOfLocalDay(task.completed_at || task.created_at || new Date())
  const start = startOfLocalDay()
  start.setDate(start.getDate() - Math.max(days - 1, 0))
  return completedAt >= start
}

const normalizeAiChat = (message = {}) => ({
  role: message.role || 'assistant',
  content: message.content || '',
  created_at: message.created_at || new Date().toISOString()
})

const aiHistoryFor = (username, conversationId = '') => {
  ensureUser(username)
  return state.aiChats[username]
    .filter((message) => !conversationId || message.conversation_id === conversationId)
    .map(normalizeAiChat)
}

const includesAny = (text = '', keywords = []) => keywords.some((keyword) => text.includes(keyword))

const cleanAiText = (value = '') => (
  String(value || '')
    .replace(/\s+/g, ' ')
    .trim()
)

const topPendingTasksForAi = (username, limit = 5) => (
  (state.todos[username] || [])
    .filter((task) => !task.is_completed)
    .slice()
    .sort((a, b) => Number(b.id || 0) - Number(a.id || 0))
    .slice(0, limit)
    .map((task, index) => `${index + 1}. ${cleanAiText(task.content) || '未命名任务'}`)
)

const recentCompletedCountForAi = (username, days = 7) => (
  (state.todos[username] || []).filter((task) => taskCompletedWithinDays(task, days)).length
)

const weeklyFocusMinutesForAi = (username) => (
  dailyStatsFor(username, 7)
    .reduce((total, day) => total + Math.max(0, Number(day.focus_minutes || 0)), 0)
)

const recentChatContextForAi = (username) => (
  aiHistoryFor(username)
    .slice(-6)
    .map((item) => `${item.role === 'user' ? '用户' : 'AI'}: ${cleanAiText(item.content).slice(0, 80)}`)
    .join('\n')
)

const buildAiProfile = (username) => {
  ensureUser(username)
  const growth = state.growth[username] || defaultGrowth()
  const pendingTasks = topPendingTasksForAi(username)
  const completedThisWeek = recentCompletedCountForAi(username, 7)
  const weeklyFocusMinutes = weeklyFocusMinutesForAi(username)
  const focusSessions = state.focusSessions[username] || []
  const recentLedger = [...(state.computeLedger?.[username] || [])].slice(-3).reverse()

  return {
    growth,
    pendingTasks,
    pendingCount: (state.todos[username] || []).filter((task) => !task.is_completed).length,
    completedThisWeek,
    weeklyFocusMinutes,
    totalFocusMinutes: Number(growth.total_focus_minutes || 0),
    coins: Number(growth.coins || 0),
    diamonds: Number(growth.diamonds || 0),
    recentLedger,
    sessionCount: focusSessions.length,
    recentChat: recentChatContextForAi(username)
  }
}

const aiSnapshotLine = (profile) => {
  const hours = Math.round((profile.weeklyFocusMinutes / 60) * 10) / 10
  return `我先看了一眼你的状态：本周专注约 ${hours} 小时，已完成 ${profile.completedThisWeek} 个任务，当前还有 ${profile.pendingCount} 个待办，算力余额 ${profile.coins} CU。`
}

const taskBlock = (profile) => (
  profile.pendingTasks.length
    ? profile.pendingTasks.join('\n')
    : '目前没有待办。先新建 1 个最重要任务，再开始专注会更稳。'
)

const planReply = (profile, message) => {
  const wantsLongSession = includesAny(message, ['90', '一个半小时', '今晚', '晚上'])
  const blocks = wantsLongSession
    ? [
        '0-10 分钟：整理桌面，只保留一个任务和必要资料。',
        '10-35 分钟：做最难的一小块，目标是产出草稿或解出第一组题。',
        '35-40 分钟：休息，离开屏幕，别刷短视频。',
        '40-65 分钟：继续推进同一任务，把结果写进笔记。',
        '65-75 分钟：处理一个轻量任务或错题整理。',
        '75-90 分钟：复盘三句话：完成了什么、卡在哪里、下一步做什么。'
      ]
    : [
        '第 1 轮 25 分钟：只做最重要任务，不切换窗口。',
        '休息 5 分钟：喝水、站起来，不打开娱乐软件。',
        '第 2 轮 25 分钟：把刚才的成果整理成可提交/可复盘的版本。',
        '最后 5 分钟：记录结果，并决定下一次从哪里继续。'
      ]

  return [
    aiSnapshotLine(profile),
    '',
    '我建议这样安排：',
    ...blocks.map((item, index) => `${index + 1}. ${item}`),
    '',
    '优先处理这些待办：',
    taskBlock(profile),
    '',
    '执行标准：开始前把目标写成一句话，结束时必须留下一个看得见的产出。'
  ].join('\n')
}

const focusReply = (profile) => ([
  aiSnapshotLine(profile),
  '',
  '你现在需要的不是更强意志力，而是把入口变窄。下一轮这样做：',
  '1. 手机放到够不到的位置，通知全关。',
  '2. 桌面只留一个网页或一个文档。',
  '3. 任务缩小到 15 分钟内能开始的动作，比如“完成第 1 题”或“写完报告第一段”。',
  '4. 开始后前 5 分钟只要求进入状态，不追求效率。',
  '',
  `如果你现在卡住，就从这个任务开始：\n${profile.pendingTasks[0] || '新建一个最小任务，然后立刻开 15 分钟。'}`
]).join('\n')

const weaknessReply = (profile) => ([
  aiSnapshotLine(profile),
  '',
  '从当前数据看，我会先按三个方向排查薄弱点：',
  `1. 执行稳定性：本周完成 ${profile.completedThisWeek} 个任务，如果目标很多但完成少，先减少同时推进的任务数。`,
  `2. 专注持续性：累计专注 ${profile.totalFocusMinutes} 分钟，可以继续用 25 分钟一轮积累稳定性。`,
  '3. 复盘质量：每次结束后写下“错因/卡点/下一步”，比只记录时长更能提分。',
  '',
  '今天的改法：选一个最容易丢分或最拖延的点，做 25 分钟专项训练，然后把错题原因归成“不会、粗心、时间不够、知识点混淆”四类。'
]).join('\n')

const examReply = (profile, message) => {
  const english = includesAny(message, ['英语', '阅读', '听力', '写作', '词汇'])
  return [
    aiSnapshotLine(profile),
    '',
    english
      ? '英语复习建议按“词汇-阅读-错题复盘”走，不要只刷题。'
      : '考试复习建议按“知识点补洞-限时训练-错题复盘”走。',
    '1. 先做一组限时题，别边查边做。',
    '2. 做完立刻标出错因：知识点、审题、速度、表达。',
    '3. 把错题改写成 3 条可复习的问题。',
    '4. 明天只复查这些问题，而不是重新翻一遍所有资料。',
    '',
    `今天可以接着做：\n${taskBlock(profile)}`
  ].join('\n')
}

const motivationReply = (profile) => ([
  aiSnapshotLine(profile),
  '',
  '如果现在没动力，先别逼自己“热血起来”。我们把目标降到足够小：',
  '1. 只承诺 10 分钟，不承诺完成全部。',
  '2. 开始前写一句：我这 10 分钟只要完成什么。',
  '3. 做完马上给自己一个可见反馈，比如勾掉任务、记录专注、看算力增长。',
  '',
  `你已经累计了 ${profile.totalFocusMinutes} 分钟专注，这说明系统是跑得起来的。下一步不是重来，是续上。`
]).join('\n')

const projectReply = (profile) => ([
  '如果是做 FocusPort 项目，我建议按“能演示、能解释、能提交”三条线推进：',
  '1. 能演示：登录、任务、专注、算力、商城/场景、AI 聊天至少跑通一遍。',
  '2. 能解释：准备好前后端分离、数据存储、账号隔离、算力激励这几个核心点。',
  '3. 能提交：README、summary、报告、PPT、代码目录结构保持清楚。',
  '',
  `你当前还有 ${profile.pendingCount} 个待办。先挑一个和提交最相关的任务做，不要同时修太多功能。`
]).join('\n')

const generalReply = (profile, message) => {
  const recentContext = profile.recentChat ? `\n\n我还参考了最近对话：\n${profile.recentChat}` : ''
  return [
    aiSnapshotLine(profile),
    '',
    `你刚才问的是：“${cleanAiText(message)}”。`,
    '我建议先把它变成一个可执行动作：',
    '1. 写清最终结果是什么。',
    '2. 列出现在缺的一个条件。',
    '3. 用 25 分钟只解决这一个条件。',
    '',
    `可以从这里开始：\n${profile.pendingTasks[0] || '新建一个具体任务，例如“整理报告目录”或“完成登录演示”。'}`,
    recentContext
  ].join('\n')
}

const generateLocalAiReply = (username, message) => {
  ensureUser(username)
  const lowered = String(message || '').toLowerCase()
  const profile = buildAiProfile(username)

  if (includesAny(message, ['你是谁', '哪个AI', '哪个ai', '什么AI', '什么ai']) || lowered.includes('who are you')) {
    return '我是 FocusPort 的本地 AI 副官，负责把你的任务、专注数据、算力记录和最近对话整合起来，给出学习计划、复盘建议和执行清单。当前本地版本不依赖外部大模型密钥，但已经会根据你的账号状态做个性化建议。'
  }
  if (includesAny(message, ['计划', '安排', '节奏', '今晚', '今天', '明天', '日程', '规划']) || lowered.includes('plan')) {
    return planReply(profile, message)
  }
  if (includesAny(message, ['分心', '专注', '拖延', '效率', '学不进去', '坐不住']) || lowered.includes('focus')) {
    return focusReply(profile)
  }
  if (includesAny(message, ['薄弱', '弱点', '提分', '分析', '复盘', '状态', '问题在哪'])) {
    return weaknessReply(profile)
  }
  if (includesAny(message, ['考试', '英语', '真题', '错题', '阅读', '听力', '写作', '词汇'])) {
    return examReply(profile, message)
  }
  if (includesAny(message, ['动力', '坚持', '焦虑', '压力', '累', '不想学', '没动力', '崩'])) {
    return motivationReply(profile)
  }
  if (includesAny(message, ['项目', '代码', '部署', 'render', 'github', '后端', '前端', 'README', '答辩', '提交'])) {
    return projectReply(profile)
  }
  return generalReply(profile, message)
}

const generateRoomCode = (length = 6) => {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  let code = ''
  for (let i = 0; i < length; i += 1) {
    code += alphabet[Math.floor(Math.random() * alphabet.length)]
  }
  return code
}

const normalizeArcadeGame = (game = '') => String(game || '').replace(/_online$/i, '')

const arcadeRoomPayload = (room = {}) => ({
  success: true,
  room_code: room.room_code,
  game: room.game,
  game_type: room.game_type || normalizeArcadeGame(room.game),
  status: room.status,
  player_host: room.player_host,
  player_guest: room.player_guest || null,
  host_color: 1,
  guest_color: 2,
  first_player: room.player_host,
  moves: room.moves || [],
  current_turn: Number(room.current_turn || 1),
  winner: Number(room.winner || 0),
  is_draw: Boolean(room.is_draw),
  last_move: room.last_move || null,
  created_at: room.created_at
})

const encodeWsTextFrame = (payload) => {
  const data = Buffer.from(JSON.stringify(payload), 'utf8')
  const headerLength = data.length < 126 ? 2 : data.length < 65536 ? 4 : 10
  const frame = Buffer.alloc(headerLength + data.length)
  frame[0] = 0x81
  if (data.length < 126) {
    frame[1] = data.length
  } else if (data.length < 65536) {
    frame[1] = 126
    frame.writeUInt16BE(data.length, 2)
  } else {
    frame[1] = 127
    frame.writeBigUInt64BE(BigInt(data.length), 2)
  }
  data.copy(frame, headerLength)
  return frame
}

const decodeWsTextFrame = (buffer) => {
  if (buffer.length < 2) return null
  const opcode = buffer[0] & 0x0f
  if (opcode === 0x8) return { type: 'close' }
  if (opcode !== 0x1) return null

  const masked = Boolean(buffer[1] & 0x80)
  let length = buffer[1] & 0x7f
  let offset = 2
  if (length === 126) {
    if (buffer.length < 4) return null
    length = buffer.readUInt16BE(2)
    offset = 4
  } else if (length === 127) {
    if (buffer.length < 10) return null
    length = Number(buffer.readBigUInt64BE(2))
    offset = 10
  }

  let mask
  if (masked) {
    if (buffer.length < offset + 4) return null
    mask = buffer.subarray(offset, offset + 4)
    offset += 4
  }
  if (buffer.length < offset + length) return null

  const payload = Buffer.from(buffer.subarray(offset, offset + length))
  if (masked && mask) {
    for (let i = 0; i < payload.length; i += 1) {
      payload[i] ^= mask[i % 4]
    }
  }
  try {
    return JSON.parse(payload.toString('utf8'))
  } catch {
    return null
  }
}

const sendWsJson = (socket, payload) => {
  if (!socket.destroyed) socket.write(encodeWsTextFrame(payload))
}

const arcadeRoomSockets = (roomCode) => {
  if (!arcadeWsConnections.has(roomCode)) arcadeWsConnections.set(roomCode, new Set())
  return arcadeWsConnections.get(roomCode)
}

const broadcastArcadeRoom = (roomCode, payload, exceptSocket = null) => {
  for (const socket of Array.from(arcadeRoomSockets(roomCode))) {
    if (socket === exceptSocket || socket.destroyed) continue
    sendWsJson(socket, payload)
  }
}

const arcadeSyncPayload = (room = {}) => ({
  type: 'sync',
  player_host: room.player_host,
  player_guest: room.player_guest || null,
  host_color: 1,
  guest_color: 2,
  first_player: room.player_host,
  status: room.status,
  moves: room.moves || [],
  current_turn: Number(room.current_turn || 1),
  winner: Number(room.winner || 0),
  is_draw: Boolean(room.is_draw),
  last_move: room.last_move || null
})

const arcadeExpectedPlayer = (room = {}) => {
  return Number(room.current_turn || 1) === 1 ? room.player_host : room.player_guest
}

const arcadeExpectedColor = (room = {}) => Number(room.current_turn || 1) === 2 ? 2 : 1

const arcadeWinnerUsername = (room = {}) => {
  const winner = Number(room.winner || 0)
  if (!winner) return ''
  if (winner === 1) return room.player_host || ''
  if (winner === 2) return room.player_guest || ''
  return ''
}

const awardArcadeWinnerOnce = (room = {}) => {
  if (room.winner_rewarded) return
  const winnerUsername = arcadeWinnerUsername(room)
  if (!winnerUsername) return
  ensureUser(winnerUsername)
  state.growth[winnerUsername].coins = Number(state.growth[winnerUsername].coins || 0) + ARCADE_WINNER_COMPUTE_REWARD
  recordComputeLedger(winnerUsername, ARCADE_WINNER_COMPUTE_REWARD, `arcade_win:${room.game_type || normalizeArcadeGame(room.game)}`, '娱乐大厅联机获胜奖励')
  room.winner_rewarded = true
}

const isCellOccupied = (room = {}, row, col) => (
  Array.isArray(room.moves) && room.moves.some((move) => Number(move.row) === row && Number(move.col) === col)
)

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || '/', `http://${HOST}:${PORT}`)
  const path = url.pathname

  try {
    if (req.method === 'OPTIONS') {
      res.writeHead(204, {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS,HEAD',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
        'Access-Control-Max-Age': '86400',
        'Cache-Control': 'no-store'
      })
      return res.end()
    }

    if (req.method === 'GET' && path === '/') {
      return send(res, 200, { ok: true, service: 'FocusPort local dev API' })
    }

    if ((req.method === 'GET' || req.method === 'HEAD') && path.startsWith('/static/')) {
      return await sendStaticFile(req, res, path)
    }

    if (req.method === 'POST' && path === '/api/admin/upload') {
      const uploaded = await readMultipartFile(req)
      const filename = sanitizeAdminUploadFilename(uploaded.filename)
      if (!uploaded.data.length) return send(res, 400, { detail: '上传文件不能为空' })
      await mkdir(STATIC_DIR, { recursive: true })
      await writeFile(new URL(filename, STATIC_DIR), uploaded.data)
      return send(res, 200, { success: true, message: '上传成功', filename, url: `/static/${filename}` })
    }

    if (req.method === 'POST' && path === '/api/register') {
      const body = await readBody(req)
      const username = String(body.username || '').trim()
      const password = String(body.password || '')
      if (!username || !password) return send(res, 400, { success: false, message: '请填写用户名和密码。' })
      if (state.users[username]) return send(res, 200, { success: false, message: '该指挥官档案已存在，请直接登录。' })
      ensureUser(username, password)
      await saveState()
      return send(res, 200, { success: true, message: 'registered' })
    }

    if (req.method === 'POST' && path === '/api/login') {
      const body = await readBody(req)
      const username = String(body.username || '').trim()
      const password = String(body.password || '')
      const user = state.users[username]
      if (!user || user.password !== password) return send(res, 200, { success: false, message: '身份核验失败，请检查序列号或密钥。' })
      ensureUser(username, password)
      await saveState()
      return send(res, 200, { success: true, username })
    }

    if (req.method === 'GET' && path === '/api/exams') {
      return send(res, 200, {
        success: true,
        exams: mockExams.map(({ answer_key_json, ...exam }) => exam)
      })
    }

    if (req.method === 'POST' && path === '/api/submit_exam') {
      const body = await readBody(req)
      const username = String(body.username || '').trim() || 'guest'
      const exam = mockExams.find((item) => item.exam_code === body.exam_code)
      if (!exam) return send(res, 404, { detail: '试卷不存在' })

      ensureUser(username)
      const graded = gradeExam(exam, body.answers || {})
      const expGained = Math.max(5, Math.round(graded.objective_score / 10))
      state.growth[username].exp = Number(state.growth[username].exp || 0) + expGained
      recordComputeLedger(username, 0, 'exam_submit', `提交试卷 ${exam.title}`)
      await saveState()
      return send(res, 200, {
        success: true,
        score: graded.objective_score,
        objective_score: graded.objective_score,
        total_questions: graded.total_questions,
        attempted_score: graded.total_questions,
        mistakes: graded.mistakes,
        exp_gained: expGained,
        has_subjective: false,
        submission_id: Date.now()
      })
    }

    const examGradingStatusMatch = path.match(/^\/api\/exam\/grading_status\/([^/]+)$/)
    if (req.method === 'GET' && examGradingStatusMatch) {
      return send(res, 200, { status: 'completed', subjective_score: 0, feedback: '暂无主观题需要批改。' })
    }

    if (req.method === 'POST' && path === '/api/exam/ai_analysis') {
      const body = await readBody(req)
      return send(res, 200, {
        success: true,
        analysis: `这题的正确答案是 ${body.correct_answer || '标准答案'}。建议先抓住题干语境，再比较选项差异。`
      })
    }

    const growthMatch = path.match(/^\/api\/growth\/([^/]+)$/)
    if (req.method === 'GET' && growthMatch) {
      const username = decodeURIComponent(growthMatch[1])
      ensureUser(username)
      await saveState()
      return send(res, 200, { growth: state.growth[username] })
    }

    if (req.method === 'POST' && path === '/api/growth/check-streak') {
      const body = await readBody(req)
      const username = String(body.username || '').trim()
      ensureUser(username)
      await saveState()
      return send(res, 200, { success: true, growth: state.growth[username] })
    }

    const avatarMatch = path.match(/^\/api\/user\/([^/]+)\/avatar$/)
    if (req.method === 'GET' && avatarMatch) {
      const username = decodeURIComponent(avatarMatch[1])
      return send(res, 200, { avatar: '', nickname: username })
    }

    const statsMatch = path.match(/^\/api\/stats\/([^/]+)$/)
    if (req.method === 'GET' && statsMatch) {
      const username = decodeURIComponent(statsMatch[1])
      const period = url.searchParams.get('period') || 'week'
      const days = periodDayCount(period)
      ensureUser(username)
      const dailyStats = dailyStatsFor(username, days)
      const totalTasks = (state.todos[username] || []).filter((task) => taskCompletedWithinDays(task, days)).length
      let totalFocusMinutes = dailyStats.reduce((sum, day) => sum + Number(day.focus_minutes || 0), 0)
      const legacyFocusMinutes = Math.max(0, Number(state.growth[username].total_focus_minutes || 0))
      if (totalFocusMinutes === 0 && legacyFocusMinutes > 0 && dailyStats.length) {
        dailyStats[dailyStats.length - 1].focus_minutes = Math.round(legacyFocusMinutes)
        totalFocusMinutes = legacyFocusMinutes
      }
      return send(res, 200, {
        success: true,
        daily_stats: dailyStats,
        summary: {
          totalFocusHours: Math.round((totalFocusMinutes / 60) * 10) / 10,
          totalTasks,
          totalExp: state.growth[username].exp || 0,
          avgDiscipline: state.growth[username].discipline_score || 50,
          streakDays: state.growth[username].streak_days || 0
        }
      })
    }

    const todoListMatch = path.match(/^\/api\/todo\/([^/]+)$/)
    if (req.method === 'GET' && todoListMatch) {
      const username = decodeURIComponent(todoListMatch[1])
      ensureUser(username)
      return send(res, 200, { tasks: state.todos[username].map(normalizeTask) })
    }

    if (req.method === 'POST' && path === '/api/todo/add') {
      const body = await readBody(req)
      const username = String(body.username || '').trim()
      ensureUser(username)
      const task = {
        id: state.nextTaskId++,
        content: String(body.content || '').trim(),
        is_completed: false,
        status: body.status || 'todo',
        scheduled_date: body.scheduled_date || '',
        scheduled_time: body.scheduled_time || '',
        category: body.category || 'FocusPort',
        accent: body.accent || '#4880FF',
        created_at: new Date().toISOString()
      }
      state.todos[username].unshift(task)
      await saveState()
      return send(res, 200, { success: true, task_id: task.id, task: normalizeTask(task) })
    }

    if (req.method === 'POST' && path === '/api/todo/toggle') {
      const body = await readBody(req)
      const username = String(body.username || '').trim()
      const taskId = Number(body.task_id)
      ensureUser(username)
      const task = state.todos[username].find((item) => Number(item.id) === taskId)
      if (!task) return send(res, 404, { detail: 'Task not found' })
      task.is_completed = !task.is_completed
      task.status = task.is_completed ? 'done' : 'todo'
      task.completed_at = task.is_completed ? new Date().toISOString() : ''
      await saveState()
      return send(res, 200, { success: true, task: normalizeTask(task) })
    }

    if (req.method === 'POST' && path === '/api/todo/delete') {
      const body = await readBody(req)
      const username = String(body.username || '').trim()
      const taskId = Number(body.task_id)
      ensureUser(username)
      state.todos[username] = state.todos[username].filter((item) => Number(item.id) !== taskId)
      await saveState()
      return send(res, 200, { success: true })
    }

    if (req.method === 'POST' && path === '/api/ai/chat') {
      const body = await readBody(req)
      const username = String(body.username || '').trim()
      const message = String(body.message || '').trim()
      const conversationId = String(body.conversation_id || '').trim()
      if (!username) return send(res, 400, { detail: '缺少用户名' })
      if (!message) return send(res, 400, { detail: '消息不能为空' })
      const result = await withStateWrite(async () => {
        ensureUser(username)
        state.aiChats[username].push({
          id: state.nextAiChatId++,
          role: 'user',
          content: message,
          conversation_id: conversationId,
          created_at: new Date().toISOString()
        })
        const reply = generateLocalAiReply(username, message)
        state.aiChats[username].push({
          id: state.nextAiChatId++,
          role: 'assistant',
          content: reply,
          conversation_id: conversationId,
          created_at: new Date().toISOString()
        })
        return { status: 200, payload: { success: true, reply } }
      })
      return send(res, result.status, result.payload)
    }

    const aiHistoryMatch = path.match(/^\/api\/ai\/history\/([^/]+)$/)
    if (req.method === 'GET' && aiHistoryMatch) {
      const username = decodeURIComponent(aiHistoryMatch[1])
      const conversationId = String(url.searchParams.get('conversation_id') || '').trim()
      const messages = aiHistoryFor(username, conversationId)
      return send(res, 200, { success: true, messages, history: messages })
    }

    if (req.method === 'DELETE' && aiHistoryMatch) {
      const username = decodeURIComponent(aiHistoryMatch[1])
      ensureUser(username)
      state.aiChats[username] = []
      await saveState()
      return send(res, 200, { success: true })
    }

    const aiSuggestionsMatch = path.match(/^\/api\/ai\/suggestions\/([^/]+)$/)
    if (req.method === 'GET' && aiSuggestionsMatch) {
      return send(res, 200, {
        success: true,
        suggestions: [
          '帮我安排今晚 90 分钟学习节奏',
          '根据最近状态给我一份提分建议',
          '我容易分心，给我一个 25 分钟执行清单'
        ]
      })
    }

    if (req.method === 'POST' && path === '/api/arcade/play') {
      const body = await readBody(req)
      const username = String(body.username || '').trim()
      const game = String(body.game || '').trim()
      if (!username) return send(res, 400, { detail: '缺少用户名' })
      if (!game) return send(res, 400, { detail: '缺少游戏类型' })
      const result = await withStateWrite(async () => {
        ensureUser(username)
        let code = generateRoomCode()
        while (state.arcadeRooms[code]) code = generateRoomCode()
        const gameType = normalizeArcadeGame(game)
        const isOnlineRoom = /_online$/i.test(game)
        if (isOnlineRoom) {
          const currentCoins = Number(state.growth[username]?.coins || 0)
          if (currentCoins < ARCADE_ROOM_CREATE_COST) return { status: 400, payload: { detail: `CU 不足，需要 ${ARCADE_ROOM_CREATE_COST} CU` } }
          if (username === ADMIN_TEST_USERNAME) {
            state.growth[username].coins = ADMIN_TEST_COMPUTE
            recordComputeLedger(username, 0, `arcade_room_create:${gameType}`, '管理员测试账号创建房间免扣算力')
          } else {
            state.growth[username].coins = currentCoins - ARCADE_ROOM_CREATE_COST
            recordComputeLedger(username, -ARCADE_ROOM_CREATE_COST, `arcade_room_create:${gameType}`, '创建娱乐大厅联机房间')
          }
        }
        const room = {
          room_code: code,
          game,
          game_type: gameType,
          status: game.endsWith('_online') ? 'waiting' : 'solo',
          player_host: username,
          player_guest: null,
          moves: [],
          current_turn: 1,
          winner: 0,
          is_draw: false,
          last_move: null,
          winner_rewarded: false,
          created_at: new Date().toISOString()
        }
        state.arcadeRooms[code] = room
        return { status: 200, payload: arcadeRoomPayload(room) }
      })
      return send(res, result.status, result.payload)
    }

    if (req.method === 'POST' && path === '/api/arcade/join') {
      const body = await readBody(req)
      const username = String(body.username || '').trim()
      const roomCode = String(body.room_code || '').trim().toUpperCase()
      const result = await withStateWrite(async () => {
        ensureUser(username)
        const room = state.arcadeRooms[roomCode]
        if (!room) return { status: 404, payload: { detail: '房间不存在' } }
        if (room.status === 'playing' && room.player_guest && room.player_guest !== username) {
          return { status: 400, payload: { detail: '房间已满' } }
        }
        if (room.player_host === username) {
          return { status: 400, payload: { detail: '不能加入自己创建的房间' } }
        }
        room.player_guest = username
        room.status = 'playing'
        broadcastArcadeRoom(roomCode, arcadeSyncPayload(room))
        return { status: 200, payload: arcadeRoomPayload(room) }
      })
      return send(res, result.status, result.payload)
    }

    const arcadeRoomMatch = path.match(/^\/api\/arcade\/room\/([^/]+)$/)
    if (req.method === 'GET' && arcadeRoomMatch) {
      const roomCode = decodeURIComponent(arcadeRoomMatch[1]).trim().toUpperCase()
      const room = state.arcadeRooms[roomCode]
      if (!room) return send(res, 404, { detail: '房间不存在' })
      return send(res, 200, arcadeRoomPayload(room))
    }

    const friendsMatch = path.match(/^\/api\/friends\/([^/]+)$/)
    if (req.method === 'GET' && friendsMatch) {
      const username = decodeURIComponent(friendsMatch[1])
      ensureUser(username)
      return send(res, 200, { success: true, friends: friendshipsFor(username) })
    }

    if (req.method === 'POST' && path === '/api/friends/request') {
      const body = await readBody(req)
      const userUsername = String(body.user_username || '').trim()
      const friendUsername = String(body.friend_username || '').trim()
      const result = await withStateWrite(async () => {
        if (!userUsername || !friendUsername) return { status: 400, payload: { detail: '用户名不能为空' } }
        ensureUser(userUsername)
        if (userUsername === friendUsername) return { status: 400, payload: { detail: '不能添加自己为好友' } }
        if (!state.users[friendUsername]) return { status: 404, payload: { detail: '目标用户不存在' } }
        if (findFriendship(userUsername, friendUsername)) return { status: 400, payload: { detail: '好友关系已存在' } }
        state.friends.push({
          id: state.nextFriendshipId++,
          user_username: userUsername,
          friend_username: friendUsername,
          status: 'pending',
          created_at: new Date().toISOString()
        })
        return { status: 200, payload: { success: true } }
      })
      return send(res, result.status, result.payload)
    }

    if (req.method === 'POST' && path === '/api/friends/respond') {
      const body = await readBody(req)
      const friendshipId = Number(body.friendship_id)
      const status = body.status === 'accepted' ? 'accepted' : 'rejected'
      const username = String(body.username || '').trim()
      const result = await withStateWrite(async () => {
        if (!username) return { status: 400, payload: { detail: '用户名不能为空' } }
        const friendship = state.friends.find((entry) => Number(entry.id) === friendshipId)
        if (!friendship) return { status: 404, payload: { detail: '好友请求不存在' } }
        if (friendship.status !== 'pending') return { status: 400, payload: { detail: '好友请求已处理' } }
        if (friendship.friend_username !== username) return { status: 403, payload: { detail: '只有请求接收方可以处理好友请求' } }
        friendship.status = status
        return { status: 200, payload: { success: true } }
      })
      return send(res, result.status, result.payload)
    }

    if (req.method === 'DELETE' && path === '/api/friends') {
      const body = await readBody(req)
      const userUsername = String(body.user_username || '').trim()
      const friendUsername = String(body.friend_username || '').trim()
      const result = await withStateWrite(async () => {
        const before = state.friends.length
        state.friends = state.friends.filter((entry) => !(
          (entry.user_username === userUsername && entry.friend_username === friendUsername) ||
          (entry.user_username === friendUsername && entry.friend_username === userUsername)
        ))
        return { status: 200, payload: { success: true, deleted: before - state.friends.length } }
      })
      return send(res, result.status, result.payload)
    }

    const unreadMatch = path.match(/^\/api\/messages\/([^/]+)\/unread$/)
    if (req.method === 'GET' && unreadMatch) {
      const username = decodeURIComponent(unreadMatch[1])
      const unread = messagesFor(username).filter((message) => !message.is_read).length
      return send(res, 200, { success: true, unread })
    }

    const messagesMatch = path.match(/^\/api\/messages\/([^/]+)$/)
    if (req.method === 'GET' && messagesMatch) {
      const username = decodeURIComponent(messagesMatch[1])
      const category = String(url.searchParams.get('category') || '').trim()
      return send(res, 200, { success: true, messages: messagesFor(username, category) })
    }

    if (req.method === 'POST' && path === '/api/messages') {
      const body = await readBody(req)
      const sender = String(body.sender || '').trim()
      const receiver = String(body.receiver || '').trim()
      const title = String(body.title || '').trim()
      const content = String(body.content || '').trim()
      const category = String(body.category || 'friend').trim() || 'friend'
      const result = await withStateWrite(async () => {
        if (!sender || !receiver || !title || !content) return { status: 400, payload: { detail: '消息信息不完整' } }
        ensureUser(sender)
        if (!state.users[receiver]) return { status: 404, payload: { detail: '收件人不存在' } }
        const message = {
          id: state.nextMessageId++,
          sender,
          receiver,
          title,
          content,
          category,
          is_read: false,
          created_at: new Date().toISOString()
        }
        state.messages[receiver].unshift(message)
        if (sender !== receiver) {
          state.messages[sender].unshift({ ...message, is_read: true })
        }
        return { status: 200, payload: { success: true, message: normalizeMessage(message) } }
      })
      return send(res, result.status, result.payload)
    }

    const messageReadMatch = path.match(/^\/api\/messages\/(\d+)\/read$/)
    if (req.method === 'POST' && messageReadMatch) {
      const messageId = Number(messageReadMatch[1])
      const result = await withStateWrite(async () => {
        let found = false
        Object.values(state.messages).forEach((list) => {
          list.forEach((message) => {
            if (Number(message.id) === messageId) {
              message.is_read = true
              found = true
            }
          })
        })
        return found
          ? { status: 200, payload: { success: true } }
          : { status: 404, payload: { detail: '消息不存在' } }
      })
      return send(res, result.status, result.payload)
    }

    const messageReadAllMatch = path.match(/^\/api\/messages\/read-all\/([^/]+)$/)
    if (req.method === 'POST' && messageReadAllMatch) {
      const username = decodeURIComponent(messageReadAllMatch[1])
      const result = await withStateWrite(async () => {
        ensureUser(username)
        state.messages[username].forEach((message) => { message.is_read = true })
        return { status: 200, payload: { success: true } }
      })
      return send(res, result.status, result.payload)
    }

    const messageDeleteMatch = path.match(/^\/api\/messages\/(\d+)$/)
    if (req.method === 'DELETE' && messageDeleteMatch) {
      const messageId = Number(messageDeleteMatch[1])
      const result = await withStateWrite(async () => {
        let deleted = 0
        Object.keys(state.messages).forEach((username) => {
          const before = state.messages[username].length
          state.messages[username] = state.messages[username].filter((message) => Number(message.id) !== messageId)
          deleted += before - state.messages[username].length
        })
        return { status: 200, payload: { success: true, deleted } }
      })
      return send(res, result.status, result.payload)
    }

    const shopBalanceMatch = path.match(/^\/api\/unified-shop\/balance\/([^/]+)$/)
    if (req.method === 'GET' && shopBalanceMatch) {
      const username = decodeURIComponent(shopBalanceMatch[1])
      ensureUser(username)
      const growth = state.growth[username]
      return send(res, 200, { success: true, coins: growth.coins, diamonds: growth.diamonds, sunshine: growth.diamonds })
    }

    const computeLedgerMatch = path.match(/^\/api\/compute-ledger\/([^/]+)$/)
    if (req.method === 'GET' && computeLedgerMatch) {
      const username = decodeURIComponent(computeLedgerMatch[1])
      const limit = Math.max(1, Math.min(200, Number(url.searchParams.get('limit') || 80)))
      ensureUser(username)
      const history = [...(state.computeLedger[username] || [])].reverse().slice(0, limit)
      return send(res, 200, { success: true, history })
    }

    if (req.method === 'GET' && path === '/api/unified-shop/items') {
      const username = String(url.searchParams.get('username') || '').trim()
      const dimension = normalizeDimension(url.searchParams.get('dimension'))
      const category = String(url.searchParams.get('category') || '').trim()
      const items = physicalShopCatalog
        .filter((item) => normalizeDimension(item.dimension) === dimension)
        .filter((item) => !category || item.category === category)
        .map((item) => enrichShopItem(item, username))
      return send(res, 200, { success: true, items })
    }

    const shopItemMatch = path.match(/^\/api\/unified-shop\/items\/(\d+)$/)
    if (req.method === 'GET' && shopItemMatch) {
      const username = String(url.searchParams.get('username') || '').trim()
      const item = catalogById.get(Number(shopItemMatch[1]))
      if (!item) return send(res, 404, { detail: '商品不存在' })
      return send(res, 200, { success: true, item: enrichShopItem(item, username) })
    }

    if (req.method === 'POST' && path === '/api/unified-shop/buy') {
      const body = await readBody(req)
      const username = String(body.username || '').trim()
      const itemId = Number(body.item_id)
      const quantity = Math.max(1, Number(body.quantity || 1))
      const result = await withStateWrite(async () => {
        ensureUser(username)
        const item = catalogById.get(itemId)
        if (!item) return { status: 404, payload: { detail: '商品不存在' } }
        const totalCoins = Number(item.price_coins || 0) * quantity
        const totalDiamonds = Number(item.price_sunshine || 0) * quantity
        const growth = state.growth[username]
        if (growth.coins < totalCoins) return { status: 400, payload: { detail: '金币不足' } }
        if (growth.diamonds < totalDiamonds) return { status: 400, payload: { detail: '钻石不足' } }
        if (username === ADMIN_TEST_USERNAME) growth.coins = ADMIN_TEST_COMPUTE
        else growth.coins -= totalCoins
        growth.diamonds -= totalDiamonds
        if (totalCoins > 0) recordComputeLedger(username, username === ADMIN_TEST_USERNAME ? 0 : -totalCoins, `buy:${itemId}`, username === ADMIN_TEST_USERNAME ? `管理员测试账号购买${item.name_cn || item.name || '商城物品'}免扣算力` : `购买${item.name_cn || item.name || '商城物品'}`)
        for (let index = 0; index < quantity; index += 1) {
          state.inventory[username].push({
            id: state.nextInventoryId++,
            username,
            item_id: itemId,
            status: 'owned',
            created_at: new Date().toISOString()
          })
        }
        return { status: 200, payload: { success: true, message: `已购买 ${item.name_cn || item.name}，现在可以直接放置。` } }
      })
      return send(res, result.status, result.payload)
    }

    const inventoryMatch = path.match(/^\/api\/unified-shop\/inventory\/([^/]+)$/)
    if (req.method === 'GET' && inventoryMatch) {
      const username = decodeURIComponent(inventoryMatch[1])
      ensureUser(username)
      const dimension = url.searchParams.get('dimension')
      const category = url.searchParams.get('category')
      const items = inventoryFor(username)
        .map((unit) => {
          const item = catalogById.get(Number(unit.item_id))
          if (!item) return null
          return { ...enrichShopItem(item, username), status: unit.status, inventory_id: unit.id }
        })
        .filter(Boolean)
        .filter((item) => !dimension || normalizeDimension(item.dimension) === normalizeDimension(dimension))
        .filter((item) => !category || item.category === category)
        .sort((left, right) => Number(right.inventory_id) - Number(left.inventory_id))
      return send(res, 200, { success: true, items })
    }

    if (req.method === 'POST' && path === '/api/unified-shop/place') {
      const body = await readBody(req)
      const username = String(body.username || '').trim()
      const itemId = Number(body.item_id)
      const result = await withStateWrite(async () => {
        ensureUser(username)
        const item = catalogById.get(itemId)
        if (!item) return { status: 404, payload: { detail: '商品不存在' } }
        const inventoryUnit = state.inventory[username].find((unit) => Number(unit.item_id) === itemId && unit.status === 'owned')
        if (!inventoryUnit) return { status: 400, payload: { detail: '请先购买该单元' } }
        const slotId = String(body.slot_id || '')
        if (slotId && state.placed[username].some((placed) => placed.map_id === (body.map_id || 'city') && placed.slot_id === slotId)) {
          return { status: 400, payload: { detail: '该槽位已被占用' } }
        }
        inventoryUnit.status = 'placed'
        const placed = {
          id: state.nextPlacedId++,
          username,
          item_id: itemId,
          inventory_id: inventoryUnit.id,
          position_x: Number(body.position_x || 0),
          position_y: Number(body.position_y || 1.7),
          position_z: Number(body.position_z || 0),
          rotation_y: Number(body.rotation_y || 0),
          scale: Number(body.scale || 1),
          map_id: body.map_id || 'city',
          slot_id: slotId,
          dimension: normalizeDimension(body.dimension),
          grid_x: body.grid_x ?? null,
          grid_y: body.grid_y ?? null
        }
        state.placed[username].push(placed)
        return { status: 200, payload: { success: true, placed_item: placedPayload(placed, username) } }
      })
      return send(res, result.status, result.payload)
    }

    const placedMatch = path.match(/^\/api\/unified-shop\/placed\/([^/]+)$/)
    if (req.method === 'GET' && placedMatch) {
      const username = decodeURIComponent(placedMatch[1])
      const dimension = url.searchParams.get('dimension')
      ensureUser(username)
      const items = placedFor(username)
        .filter((placed) => !dimension || normalizeDimension(placed.dimension) === normalizeDimension(dimension))
        .map((placed) => placedPayload(placed, username))
      return send(res, 200, { success: true, items })
    }

    const removePlacedMatch = path.match(/^\/api\/unified-shop\/placed\/(\d+)$/)
    if (req.method === 'DELETE' && removePlacedMatch) {
      const body = await readBody(req)
      const username = String(body.username || '').trim()
      const placedId = Number(removePlacedMatch[1])
      const result = await withStateWrite(async () => {
        ensureUser(username)
        const placedIndex = state.placed[username].findIndex((placed) => Number(placed.id) === placedId)
        if (placedIndex < 0) return { status: 404, payload: { detail: '摆件不存在' } }
        const [removed] = state.placed[username].splice(placedIndex, 1)
        const inventoryUnit = state.inventory[username].find((unit) => Number(unit.id) === Number(removed.inventory_id)) ||
          state.inventory[username].find((unit) => Number(unit.item_id) === Number(removed.item_id) && unit.status === 'placed')
        if (inventoryUnit) {
          inventoryUnit.status = 'owned'
        } else {
          state.inventory[username].push({
            id: state.nextInventoryId++,
            username,
            item_id: removed.item_id,
            status: 'owned',
            created_at: new Date().toISOString()
          })
        }
        return { status: 200, payload: { success: true } }
      })
      return send(res, result.status, result.payload)
    }

    if (req.method === 'POST' && path === '/api/focus/complete-v2') {
      const body = await readBody(req)
      const username = String(body.username || '').trim()
      ensureUser(username)
      const duration = Math.max(0, Number(body.duration || 0))
      const todayKey = toDateKey()
      const alreadyAwarded = state.growth[username].daily_pomodoro_compute_reward_date === todayKey
      state.growth[username].focus_energy += duration
      state.growth[username].total_focus_minutes += duration
      const focusCoins = Math.max(1, Math.round(duration / 5))
      state.growth[username].coins += focusCoins
      recordComputeLedger(username, focusCoins, 'focus_complete', '专注完成收益')
      state.focusSessions[username].push({
        duration_minutes: duration,
        subject: String(body.subject || 'Focus Session'),
        status: 'completed',
        created_at: new Date().toISOString()
      })
      if (!alreadyAwarded) {
        state.growth[username].coins += DAILY_POMODORO_COMPUTE_REWARD
        recordComputeLedger(username, DAILY_POMODORO_COMPUTE_REWARD, 'daily_pomodoro_compute', '每日番茄钟算力奖励')
        state.growth[username].daily_pomodoro_compute_reward_date = todayKey
      }
      await saveState()
      return send(res, 200, {
        success: true,
        growth: state.growth[username],
        daily_pomodoro_compute_reward: {
          awarded: !alreadyAwarded,
          amount: alreadyAwarded ? 0 : DAILY_POMODORO_COMPUTE_REWARD,
          date: todayKey
        }
      })
    }

    return send(res, 404, { detail: `Local dev API does not implement ${req.method} ${path}` })
  } catch (error) {
    console.error(error)
    return send(res, 500, { detail: 'Local dev API error' })
  }
})

server.on('upgrade', (req, socket) => {
  const url = new URL(req.url || '/', `http://${HOST}:${PORT}`)
  const match = url.pathname.match(/^\/ws\/arcade\/([^/]+)$/)
  if (!match) {
    socket.destroy()
    return
  }

  const roomCode = decodeURIComponent(match[1]).trim().toUpperCase()
  const room = state.arcadeRooms[roomCode]
  const key = req.headers['sec-websocket-key']
  if (!room || !key) {
    socket.destroy()
    return
  }

  const acceptKey = createHash('sha1')
    .update(`${key}258EAFA5-E914-47DA-95CA-C5AB0DC85B11`)
    .digest('base64')

  socket.write([
    'HTTP/1.1 101 Switching Protocols',
    'Upgrade: websocket',
    'Connection: Upgrade',
    `Sec-WebSocket-Accept: ${acceptKey}`,
    '',
    ''
  ].join('\r\n'))

  const sockets = arcadeRoomSockets(roomCode)
  sockets.add(socket)
  sendWsJson(socket, arcadeSyncPayload(room))

  socket.on('data', async (buffer) => {
    const msg = decodeWsTextFrame(buffer)
    if (!msg) return
    if (msg.type === 'close') {
      socket.end()
      return
    }

    if (msg.type === 'move') {
      room.moves = Array.isArray(room.moves) ? room.moves : []
      const row = Number(msg.row)
      const col = Number(msg.col)
      const username = String(msg.username || '')
      const expectedPlayer = arcadeExpectedPlayer(room)
      if (!expectedPlayer || username !== expectedPlayer) {
        sendWsJson(socket, { type: 'error', detail: '还没轮到你落子。' })
        sendWsJson(socket, arcadeSyncPayload(room))
        return
      }
      if (!Number.isInteger(row) || !Number.isInteger(col) || row < 0 || col < 0 || isCellOccupied(room, row, col)) {
        sendWsJson(socket, { type: 'error', detail: '无效落子。' })
        sendWsJson(socket, arcadeSyncPayload(room))
        return
      }
      const move = {
        row,
        col,
        color: arcadeExpectedColor(room),
        username
      }
      room.moves.push(move)
      room.last_move = { row, col, color: move.color, username }
      room.current_turn = move.color === 1 ? 2 : 1
      room.status = room.player_guest ? 'playing' : room.status
      await saveState()
      broadcastArcadeRoom(roomCode, arcadeSyncPayload(room))
      return
    }

    if (msg.type === 'pass') {
      const username = String(msg.username || '')
      const expectedPlayer = arcadeExpectedPlayer(room)
      if (!expectedPlayer || username !== expectedPlayer) {
        sendWsJson(socket, { type: 'error', detail: '还没轮到你。' })
        sendWsJson(socket, arcadeSyncPayload(room))
        return
      }
      room.current_turn = arcadeExpectedColor(room) === 1 ? 2 : 1
      await saveState()
      broadcastArcadeRoom(roomCode, arcadeSyncPayload(room))
      return
    }

    if (msg.type === 'game_over') {
      room.status = 'finished'
      room.winner = Number(msg.winner || msg.winner_color || 0)
      room.is_draw = !room.winner
      if (room.winner) awardArcadeWinnerOnce(room)
      await saveState()
      broadcastArcadeRoom(roomCode, arcadeSyncPayload(room))
    }
  })

  socket.on('close', () => sockets.delete(socket))
  socket.on('error', () => sockets.delete(socket))
})

server.listen(PORT, HOST, () => {
  console.log(`FocusPort local dev API listening on http://${HOST}:${PORT}`)
})
