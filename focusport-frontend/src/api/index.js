import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

console.log('API Base URL:', API_BASE || '(same-origin)')

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export const authApi = {
  login: (username, password) => api.post('/api/login', { username, password }),
  register: (username, password) => api.post('/api/register', { username, password })
}

export const growthApi = {
  get: (username) => api.get(`/api/growth/${username}`),
  addExp: (username, expAmount, source) => api.post('/api/growth/add-exp', { username, exp_amount: expAmount, source }),
  checkStreak: (username) => api.post('/api/growth/check-streak', { username }),
  updateStats: (data) => api.post('/api/growth/update-stats', data),
  updateDiscipline: (username, phoneMinutes) => api.post('/api/growth/update-discipline', { username, phone_minutes: phoneMinutes })
}

export const focusApi = {
  start: (username, subject, duration, treeType) => api.post('/api/focus/start', { username, subject, duration, tree_type: treeType }),
  end: (sessionId, username, status) => api.post('/api/focus/end', { session_id: sessionId, username, status }),
  complete: (username, duration, subject, sessionLog = '', taskDifficulty = 'L1') =>
    api.post('/api/focus/complete-v2', {
      username,
      duration,
      subject,
      session_log: sessionLog,
      task_difficulty: taskDifficulty
    }),
  stats: (username) => api.get(`/api/focus/stats/${username}`)
}

export const taskApi = {
  add: (username, content, meta = {}) => api.post('/api/todo/add', {
    username,
    content,
    scheduled_date: meta.scheduledDate || meta.scheduled_date || '',
    scheduled_time: meta.scheduledTime || meta.scheduled_time || '',
    status: meta.status || 'todo',
    category: meta.category || '',
    accent: meta.accent || '#4880FF'
  }),
  list: (username) => api.get(`/api/todo/${username}`),
  toggle: (taskId, username) => api.post('/api/todo/toggle', { task_id: taskId, username }),
  delete: (taskId, username) => api.post('/api/todo/delete', { task_id: taskId, username }),
  score: (taskId, username, proofUrl) => api.post(`/api/tasks/${taskId}/score`, { username, proof_url: proofUrl })
}

export const itemApi = {
  inventory: (username) => api.get(`/api/items/inventory/${username}`),
  use: (username, itemId) => api.post('/api/items/use', { username, item_id: itemId }),
  definitions: () => api.get('/api/items/definitions'),
  synthesize: (username, recipeId) => api.post('/api/items/synthesize', { username, recipe_id: recipeId }),
  recipes: () => api.get('/api/items/recipes'),
  market: () => api.get('/api/items/market'),
  list: (data) => api.post('/api/items/list', data),
  buy: (data) => api.post('/api/items/buy', data)
}

export const phoneApi = {
  report: (username, usageMinutes, category, notes) =>
    api.post('/api/phone-usage/report', { username, usage_minutes: usageMinutes, category, notes }),
  stats: (username, days) => api.get(`/api/phone-usage/stats/${username}`, { params: { days } }),
  analyzeScreenshot: (file, username) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('username', username)
    return api.post('/api/phone-usage/analyze-screenshot', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }
}

export const aiApi = {
  chat: (username, message, conversationId) =>
    api.post('/api/ai/chat', { username, message, conversation_id: conversationId }),
  history: (username, conversationId) =>
    api.get(`/api/ai/history/${username}`, { params: { conversation_id: conversationId } }),
  suggestions: (username) => api.get(`/api/ai/suggestions/${username}`),
  clearHistory: (username) => api.delete(`/api/ai/history/${username}`)
}

export const planApi = {
  create: (data) => api.post('/api/plans/create', data),
  list: (username, status = '') => api.get(`/api/plans/${username}`, { params: { status } }),
  detail: (planId) => api.get(`/api/plans/detail/${planId}`),
  update: (planId, data) => api.put(`/api/plans/${planId}`, data),
  delete: (planId, username) => api.delete(`/api/plans/${planId}`, { data: { username } }),
  updateStage: (planId, stageId, data) => api.put(`/api/plans/${planId}/stages/${stageId}`, data),
  completeTask: (taskId, username, actualMinutes = 0) => api.post(`/api/tasks/${taskId}/complete`, { username, actual_minutes: actualMinutes }),
  aiGenerate: (data) => api.post('/api/plans/ai/generate-stages', data),
  aiChat: (data) => api.post('/api/plans/ai/chat', data),
  daily: (username) => api.get(`/api/plans/daily/${username}`)
}

export const statsApi = {
  get: (username, period) => api.get(`/api/stats/${username}`, { params: { period } }),
  focusDistribution: (username) => api.get(`/api/stats/${username}/focus-distribution`),
  growthCurve: (username, days) => api.get(`/api/stats/${username}/growth-curve`, { params: { days } })
}

export const leaderboardApi = {
  get: (type, category, period) => api.get('/api/leaderboard', { params: { type, category, period } })
}

export const friendApi = {
  request: (userUsername, friendUsername) =>
    api.post('/api/friends/request', { user_username: userUsername, friend_username: friendUsername }),
  respond: (friendshipId, status) => api.post('/api/friends/respond', { friendship_id: friendshipId, status }),
  list: (username) => api.get(`/api/friends/${username}`),
  delete: (userUsername, friendUsername) =>
    api.delete('/api/friends', { data: { user_username: userUsername, friend_username: friendUsername } })
}

export const achievementApi = {
  all: () => api.get('/api/achievements'),
  user: (username) => api.get(`/api/achievements/${username}`),
  check: (username, achievementCode) => api.post('/api/achievements/check', { username, achievement_code: achievementCode })
}

export const islandApi = {
  decorations: () => api.get('/api/island/decorations'),
  buyDecoration: (username, decorationId) =>
    api.post('/api/island/decorations/buy', { username, decoration_id: decorationId }),
  placeDecoration: (username, decorationId, position) =>
    api.put('/api/island/decorations/place', { username, decoration_id: decorationId, position }),
  skins: () => api.get('/api/island/skins'),
  userSkins: (username) => api.get(`/api/island/skins/${username}`),
  buySkin: (username, skinId) => api.post('/api/island/skins/buy', { username, skin_id: skinId }),
  activateSkin: (username, skinId) => api.put('/api/island/skins/activate', { username, skin_id: skinId })
}

export const focusEnergyApi = {
  get: (username) => api.get(`/api/focus-energy/${username}`),
  add: (username, duration) => api.post('/api/focus-energy/add', { username, duration })
}

export const shopApi = {
  items: () => api.get('/api/shop/items'),
  buy: (username, itemId) => api.post('/api/shop/buy', { username, item_id: itemId }),
  diamonds: (username) => api.get(`/api/shop/diamonds/${username}`),
  studyroomItems: () => api.get('/api/studyroom/items'),
  buyStudyroom: (username, itemId) => api.post('/api/studyroom/buy', { username, item_id: itemId })
}

export const inventoryApi = {
  get: (username) => api.get(`/api/inventory/${username}`),
  place: (username, itemId, posX, posZ, rotation = 0) =>
    api.post('/api/island/place', { username, item_id: itemId, position_x: posX, position_z: posZ, rotation })
}

export const infrastructureApi = {
  get: (username) => api.get(`/api/island/infrastructure/${username}`)
}

export const eventApi = {
  list: (activeOnly) => api.get('/api/events', { params: { active_only: activeOnly } }),
  join: (eventId) => api.post(`/api/events/${eventId}/join`),
  updateProgress: (eventId, username, progress) =>
    api.put(`/api/events/${eventId}/progress`, { username, progress })
}

export const checkinApi = {
  checkin: (username) => api.post('/api/checkin', { username }),
  status: (username) => api.get(`/api/checkin/${username}`)
}

export const postApi = {
  create: (username, content, imageUrl) =>
    api.post('/api/posts/create', { username, content, image_url: imageUrl }),
  list: (username) => api.get('/api/posts', { params: { username } }),
  like: (postId, username) => api.post('/api/posts/like', { post_id: postId, username }),
  comment: (postId, username, content) => api.post('/api/posts/comment', { post_id: postId, username, content })
}

export const greenhouseApi = {
  create: (data) => api.post('/api/greenhouse/create', data),
  list: (isPublic = true) => api.get('/api/greenhouse/list', { params: { is_public: isPublic } }),
  get: (roomId) => api.get(`/api/greenhouse/${roomId}`),
  join: (roomId, username, password = '') => api.post(`/api/greenhouse/${roomId}/join`, { username, password }),
  selectSeat: (roomId, username, seatNumber, taskId = null) =>
    api.post(`/api/greenhouse/${roomId}/select-seat`, {
      room_id: roomId,
      username,
      seat_number: seatNumber,
      task_id: taskId
    }),
  endSession: (sessionId, username) =>
    api.post('/api/greenhouse/session/end', { session_id: sessionId, username }),
  getSunshine: (username) => api.get(`/api/sunshine/${username}`),
  getSunshineHistory: (username, limit = 50) =>
    api.get(`/api/sunshine/history/${username}`, { params: { limit } })
}

export const unifiedShopApi = {
  items: (params = {}) => api.get('/api/unified-shop/items', { params }),
  itemDetail: (itemId) => api.get(`/api/unified-shop/items/${itemId}`),
  buy: (username, itemId, quantity = 1) =>
    api.post('/api/unified-shop/buy', { username, item_id: itemId, quantity }),
  inventory: (username, category = null, dimension = null) =>
    api.get(`/api/unified-shop/inventory/${username}`, { params: { category, dimension } }),
  place: (
    username,
    itemId,
    slotId = null,
    posX = 0,
    posY = 0,
    posZ = 0,
    rotationY = 0,
    scale = 1.0,
    mapId = 'city',
    dimension = '3D',
    gridX = null,
    gridY = null
  ) =>
    api.post('/api/unified-shop/place', {
      username,
      item_id: itemId,
      slot_id: slotId,
      position_x: posX,
      position_y: posY,
      position_z: posZ,
      rotation_y: rotationY,
      scale,
      map_id: mapId,
      dimension,
      grid_x: gridX,
      grid_y: gridY
    }),
  removePlaced: (placedId, username) =>
    api.delete(`/api/unified-shop/placed/${placedId}`, { data: { username } }),
  placed: (username, params = {}) => api.get(`/api/unified-shop/placed/${username}`, { params }),
  getFavorites: (username) => api.get(`/api/unified-shop/favorites/${username}`),
  addFavorite: (username, itemId) =>
    api.post('/api/unified-shop/favorites', { username, item_id: itemId }),
  removeFavorite: (username, itemId) =>
    api.delete('/api/unified-shop/favorites', { data: { username, item_id: itemId } }),
  balance: (username) => api.get(`/api/unified-shop/balance/${username}`)
}

export const createGreenhouseWebSocket = (roomId) => {
  const apiBase = import.meta.env.VITE_API_BASE_URL
  let wsBase
  if (apiBase) {
    wsBase = apiBase.replace(/^https:/, 'wss').replace(/^http:/, 'ws')
  } else {
    wsBase = import.meta.env.PROD
      ? 'wss://focusport-backend.onrender.com'
      : 'ws://127.0.0.1:8000'
  }
  return new WebSocket(`${wsBase}/ws/greenhouse/${roomId}`)
}

export const createGomokuWebSocket = (gameId) => {
  const apiBase = import.meta.env.VITE_API_BASE_URL
  let wsBase
  if (apiBase) {
    wsBase = apiBase.replace(/^https:/, 'wss').replace(/^http:/, 'ws')
  } else {
    wsBase = import.meta.env.PROD
      ? 'wss://focusport-backend.onrender.com'
      : 'ws://127.0.0.1:8000'
  }
  return new WebSocket(`${wsBase}/ws/gomoku/${gameId}`)
}

export const createArcadeWebSocket = (roomCode) => {
  const apiBase = import.meta.env.VITE_API_BASE_URL
  let wsBase
  if (apiBase) {
    wsBase = apiBase.replace(/^https:/, 'wss').replace(/^http:/, 'ws')
  } else {
    wsBase = import.meta.env.PROD
      ? 'wss://focusport-backend.onrender.com'
      : 'ws://127.0.0.1:8000'
  }
  return new WebSocket(`${wsBase}/ws/arcade/${roomCode}`)
}

export const gomokuApi = {
  list: () => api.get('/api/gomoku/list'),
  get: (gameId) => api.get(`/api/gomoku/${gameId}`),
  create: (username) => api.post('/api/gomoku/create', { username }),
  join: (roomCode, username) => api.post('/api/gomoku/join', { room_code: roomCode, username }),
  move: (gameId, username, row, col) => api.post('/api/gomoku/move', { game_id: gameId, username, row, col }),
  surrender: (gameId, username) => api.post('/api/gomoku/surrender', { game_id: gameId, username })
}

export const arcadeApi = {
  play: (username, game) => api.post('/api/arcade/play', { username, game }),
  join: (roomCode, username) => api.post('/api/arcade/join', { room_code: roomCode, username }),
  room: (roomCode) => api.get(`/api/arcade/room/${roomCode}`)
}

export const messageApi = {
  list: (username, category = '') => api.get(`/api/messages/${username}`, { params: { category } }),
  unread: (username) => api.get(`/api/messages/${username}/unread`),
  send: (sender, receiver, title, content, category = 'friend') =>
    api.post('/api/messages', { sender, receiver, title, content, category }),
  markRead: (msgId) => api.post(`/api/messages/${msgId}/read`),
  markAllRead: (username) => api.post(`/api/messages/read-all/${username}`),
  delete: (msgId) => api.delete(`/api/messages/${msgId}`)
}

export const circleApi = {
  posts: (username, filterType, page, pageSize = 20) =>
    api.get('/api/circle/posts', { params: { username, filter_type: filterType, page, page_size: pageSize } }),
  create: (username, content, imageUrls, visibility) =>
    api.post('/api/circle/posts', { username, content, image_urls: imageUrls, visibility }),
  delete: (postId, username) =>
    api.delete(`/api/circle/posts/${postId}`, { params: { username } }),
  like: (postId, username) =>
    api.post(`/api/circle/posts/${postId}/like`, { post_id: postId, username }),
  comments: (postId) =>
    api.get(`/api/circle/posts/${postId}/comments`),
  addComment: (postId, username, content) =>
    api.post(`/api/circle/posts/${postId}/comments`, { post_id: postId, username, content }),
  uploadImage: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/api/circle/upload-image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }
}

export const pkApi = {
  active: (username) => api.get(`/api/pk/active/${username}`),
  create: (creator, opponent, type, duration, targetValue) =>
    api.post('/api/pk/create', { creator, opponent, type, duration, target_value: targetValue }),
  accept: (pkId, username) => api.post('/api/pk/accept', { pk_id: pkId, username }),
  decline: (pkId, username) => api.post('/api/pk/decline', { pk_id: pkId, username })
}

export const examApi = {
  list: () => api.get('/api/exams'),
  submit: (examCode, username, answers, timeUsed) =>
    api.post('/api/submit_exam', { exam_code: examCode, username, answers, time_used: timeUsed }),
  gradingStatus: (submissionId) => api.get(`/api/exam/grading_status/${submissionId}`),
  aiAnalysis: (question, userAnswer, correctAnswer, context) =>
    api.post('/api/exam/ai_analysis', { question, user_answer: userAnswer, correct_answer: correctAnswer, context })
}

export default api

