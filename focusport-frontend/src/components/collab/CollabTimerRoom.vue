<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import SpaceButton from '../base/SpaceButton.vue'
import SpaceProgressBar from '../base/SpaceProgressBar.vue'
import SpacePanel from '../base/SpacePanel.vue'
import BackButton from '../base/BackButton.vue'
import { WORLD_NAMES, composeWorldLabel } from '../../constants/worldNames'

const route = useRoute()
const router = useRouter()
const roomId = computed(() => parseInt(route.params.id))

// 用户信息
const currentUsername = ref(localStorage.getItem('username') || 'guest')
const userDiamonds = ref(0)

// 房间数据
const room = ref(null)
const seats = ref([])
const growingUsers = ref([])
const isLoading = ref(true)

// 当前用户状态
const mySeat = ref(null)
const isGrowing = ref(false)
const growProgress = ref(0)
const growTimer = ref(null)
const startTime = ref(null)
const selectedDuration = ref(25)
const completedDuration = ref(0)

// 任务
const myTasks = ref([])
const selectedTaskId = ref(null)
const showTaskSelector = ref(false)

// WebSocket
const ws = ref(null)
const isConnected = ref(false)

// 表情
const emojis = ref([])
const availableEmojis = ['💎', '💧', '🌱', '🌸', '💪', '👍', '❤️', '🎉', '🚀', '⭐']

// 时长选项
const durationOptions = [25, 45, 60]

// Toast 通知
const toastMessage = ref('')
const toastVisible = ref(false)
const toastReward = ref(0)

// WebSocket 重连
const wsActive = ref(true)
const reconnectAttempts = ref(0)

// 主题色
const themeAccents = {
  space: { accent: 'rgba(0,255,255,0.34)', glow: 'rgba(0,255,255,0.3)' },
  nebula: { accent: 'rgba(168,85,247,0.34)', glow: 'rgba(168,85,247,0.3)' },
  mars: { accent: 'rgba(249,115,22,0.34)', glow: 'rgba(249,115,22,0.3)' },
  lunar: { accent: 'rgba(226,232,240,0.34)', glow: 'rgba(226,232,240,0.3)' }
}

// Computed
const selectedTaskTitle = computed(() => {
  if (!selectedTaskId.value) return null
  const task = myTasks.value.find(t => t.id === selectedTaskId.value)
  return task?.content || task?.title || null
})

const gridLayout = computed(() => {
  const seatCount = room.value?.max_seats || 4
  if (seatCount <= 4) return { columns: 2, maxWidth: '500px' }
  if (seatCount <= 6) return { columns: 3, maxWidth: '700px' }
  return { columns: 4, maxWidth: '900px' }
})

const themeAccent = computed(() => {
  const theme = room.value?.theme || 'space'
  return themeAccents[theme] || themeAccents.space
})

// 加载房间数据
const loadRoom = async () => {
  try {
    const res = await axios.get(`/api/greenhouse/${roomId.value}`)
    room.value = res.data.greenhouse
    seats.value = res.data.seats
    growingUsers.value = res.data.growing_users
    isLoading.value = false
  } catch (err) {
    console.error('加载房间失败:', err)
    alert('房间不存在或已关闭')
    router.push('/collab')
  }
}

// 加载用户阳光
const loadSunshine = async () => {
  try {
    const res = await axios.get(`/api/greenhouse/sunshine/${currentUsername.value}`)
    userDiamonds.value = res.data.sunshine || 0
  } catch (err) {
    console.error('加载阳光失败:', err)
  }
}

// 加载任务列表
const loadTasks = async () => {
  try {
    const res = await axios.get(`/api/todo/${currentUsername.value}`)
    myTasks.value = (res.data.tasks || []).filter(t => !t.is_completed)
  } catch (err) {
    console.error('加载任务失败:', err)
  }
}

// 连接 WebSocket
const connectWebSocket = () => {
  if (!wsActive.value) return
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/greenhouse/${roomId.value}`

  ws.value = new WebSocket(wsUrl)

  ws.value.onopen = () => {
    isConnected.value = true
    reconnectAttempts.value = 0
  }

  ws.value.onmessage = (event) => {
    const data = JSON.parse(event.data)
    handleWebSocketMessage(data)
  }

  ws.value.onclose = () => {
    isConnected.value = false
    if (!wsActive.value) return
    reconnectAttempts.value++
    if (reconnectAttempts.value < 10) {
      setTimeout(connectWebSocket, 5000)
    }
  }
}

// 处理 WebSocket 消息
const handleWebSocketMessage = (data) => {
  switch (data.type) {
    case 'user_joined':
      seats.value = data.seats
      break
    case 'user_left':
      seats.value = data.seats
      break
    case 'grow_started':
      growingUsers.value = data.growing_users
      if (data.username === currentUsername.value) {
        isGrowing.value = true
        startTime.value = Date.now()
      }
      break
    case 'grow_ended':
      growingUsers.value = data.growing_users
      if (data.username === currentUsername.value) {
        isGrowing.value = false
        if (data.status === 'completed') {
          userDiamonds.value += data.diamonds_earned || 0
        }
      }
      break
    case 'emoji':
      showEmoji(data.emoji, data.username)
      break
    case 'sync':
      seats.value = data.seats
      growingUsers.value = data.growing_users
      break
  }
}

// 显示表情动画
const showEmoji = (emoji, username) => {
  const id = Date.now()
  emojis.value.push({ id, emoji, username, x: Math.random() * 80 + 10, y: 0 })
  setTimeout(() => {
    emojis.value = emojis.value.filter(e => e.id !== id)
  }, 3000)
}

// 入座
const takeSeat = async (seatIndex) => {
  try {
    const res = await axios.post('/api/greenhouse/join', {
      room_id: roomId.value,
      username: currentUsername.value,
      seat_index: seatIndex,
      password: ''
    })
    if (res.data.success) {
      mySeat.value = seatIndex
      seats.value = res.data.seats
    }
  } catch (err) {
    alert(err.response?.data?.error || '入座失败')
  }
}

// 离开座位
const leaveSeat = async () => {
  if (isGrowing.value) {
    if (!confirm('正在专注中，离开会丢失进度，确定离开吗？')) return
    await endGrow('failed')
  }

  try {
    await axios.post('/api/greenhouse/leave', {
      room_id: roomId.value,
      username: currentUsername.value
    })
    mySeat.value = null
    loadRoom()
  } catch (err) {
    console.error('离开失败:', err)
  }
}

// 开始专注
const startGrow = async () => {
  try {
    const res = await axios.post('/api/greenhouse/start', {
      room_id: roomId.value,
      username: currentUsername.value,
      duration: selectedDuration.value,
      task_id: selectedTaskId.value
    })
    if (res.data.success) {
      isGrowing.value = true
      startTime.value = Date.now()
      startLocalTimer()
    }
  } catch (err) {
    alert(err.response?.data?.error || '开始失败')
  }
}

// 本地计时器
const startLocalTimer = () => {
  const totalSeconds = selectedDuration.value * 60
  growProgress.value = totalSeconds

  growTimer.value = setInterval(() => {
    growProgress.value--
    if (growProgress.value <= 0) {
    endGrow('completed')
  }
  }, 1000)
}

// 结束专注
const endGrow = async (status) => {
  if (growTimer.value) {
    clearInterval(growTimer.value)
    growTimer.value = null
  }

  try {
    const res = await axios.post('/api/greenhouse/end', {
      room_id: roomId.value,
      username: currentUsername.value,
      status: status
    })
    isGrowing.value = false
    if (status === 'completed' && res.data.diamonds_earned) {
      userDiamonds.value += res.data.diamonds_earned
      toastReward.value = res.data.diamonds_earned
      toastMessage.value = '专注完成！'
      toastVisible.value = true
      setTimeout(() => { toastVisible.value = false }, 4000)
    }
  } catch (err) {
    console.error('结束失败:', err)
  }
}

// 放弃专注
const giveUpGrow = async () => {
  if (!confirm('确定要放弃吗？进度将不会保存！')) return
  await endGrow('failed')
}

// 发送表情
const sendEmoji = async (emoji) => {
  try {
    await axios.post('/api/greenhouse/emoji', {
      room_id: roomId.value,
      username: currentUsername.value,
      emoji: emoji
    })
    showEmoji(emoji, currentUsername.value)
  } catch (err) {
    console.error('发送表情失败:', err)
  }
}

// 格式化时间
const formatTime = (seconds) => {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m < 10 ? '0' + m : m}:${s < 10 ? '0' + s : s}`
}

// 获取座位状态
const getSeatUser = (index) => {
  return seats.value.find(s => s.seat_index === index)
}

// 获取专注用户信息
const getGrowingInfo = (username) => {
  return growingUsers.value.find(g => g.username === username)
}

// 退出房间
const exitRoom = async () => {
  await leaveSeat()
  router.push('/collab')
}

// 连接状态指示器颜色
const connectionColor = computed(() => {
  return isConnected.value ? '#10b981' : '#ef4444'
})

onMounted(() => {
  loadRoom()
  loadSunshine()
  loadTasks()
  connectWebSocket()
})

onUnmounted(() => {
  wsActive.value = false
  if (ws.value) ws.value.close()
  if (growTimer.value) clearInterval(growTimer.value)
})
</script>

<template>
  <div class="collab-room-page space-theme">
    <!-- 背景星星效果 -->
    <div class="stars-bg"></div>

    <!-- Toast 通知 -->
    <div v-if="toastVisible" class="toast-card">
      <h4>{{ toastMessage }}</h4>
      <p>本轮专注已结算</p>
      <div class="toast-reward">+{{ toastReward }} {{ WORLD_NAMES.currency.zh }}</div>
    </div>

    <!-- 加载中 -->
    <div v-if="isLoading" class="loading-state">
      <div class="space-spinner"></div>
      <p>Synchronizing Fleet Nexus berth...</p>
    </div>

    <!-- 房间内容 -->
    <div v-else class="room-container">
      <!-- 返回按钮（仅未入座时显示） -->
      <BackButton v-if="mySeat === null" to="/collab" label="返回码头" style="margin-bottom: 16px;" />

      <!-- 头部 -->
      <div class="space-header" :style="{ borderColor: themeAccent.accent }">
        <div class="header-left">
          <div class="connection-indicator" :style="{ background: connectionColor }"></div>
          <span v-if="!isConnected" class="connection-warning">LINK LOST · RETRY {{ reconnectAttempts }}</span>
          <div class="room-info">
            <h2>{{ room?.name || composeWorldLabel(WORLD_NAMES.fleetNexus) }}</h2>
            <span class="room-desc">{{ room?.description || 'Shared dock live. Coordinate, focus, and hold the ring.' }}</span>
          </div>
        </div>
        <div class="diamonds-display">
          <span class="diamonds-icon">CU</span>
          <span class="diamonds-value">{{ userDiamonds }}</span>
          <span class="diamonds-label">{{ WORLD_NAMES.currency.zh }} · {{ WORLD_NAMES.currency.en }}</span>
        </div>
      </div>

      <!-- 座位区域 - 自适应网格 -->
      <div class="seats-area">
        <div
          class="seats-grid"
          :style="{
            gridTemplateColumns: `repeat(${gridLayout.columns}, 1fr)`,
            maxWidth: gridLayout.maxWidth
          }"
        >
          <div
            v-for="i in (room?.max_seats || 4)"
            :key="i"
            class="seat"
            :class="{
              'my-seat': mySeat === i - 1,
              'occupied': getSeatUser(i - 1),
              'growing': getSeatUser(i - 1) && getGrowingInfo(getSeatUser(i - 1).username)
            }"
            :style="mySeat === i - 1 ? { borderColor: themeAccent.accent, boxShadow: `0 0 20px ${themeAccent.glow}` } : {}"
          >
            <!-- 空座位 -->
            <template v-if="!getSeatUser(i - 1)">
              <div class="empty-seat">
                <span class="seat-label">VACANT · 座位 {{ i }}</span>
                <SpaceButton
                  v-if="mySeat === null"
                  variant="primary"
                  size="sm"
                  @click="takeSeat(i - 1)"
                >
                  入座
                </SpaceButton>
              </div>
            </template>

            <!-- 有人的座位 -->
            <template v-else>
              <div class="occupied-seat">
                <span class="avatar">👨‍🚀</span>
                <span class="username">{{ getSeatUser(i - 1).username }}</span>

                <!-- 专注中 -->
                <template v-if="getGrowingInfo(getSeatUser(i - 1).username)">
                  <div class="timer-display">
                    {{ formatTime(getGrowingInfo(getSeatUser(i - 1).username).remaining_seconds || 0) }}
                  </div>
                  <SpaceProgressBar
                    :progress="getGrowingInfo(getSeatUser(i - 1).username).remaining_seconds || 0"
                    :max="getGrowingInfo(getSeatUser(i - 1).username).duration * 60 || 1500"
                    color="green"
                    :height="'16px'"
                    :show-text="false"
                  />
                  <span class="status growing">Dock Locked / Focus Running</span>
                </template>

                <!-- 我的座位 - 控制面板 -->
                <template v-if="mySeat === i - 1">
                  <!-- 未开始专注 -->
                  <div v-if="!isGrowing" class="control-panel">
                    <!-- 时长选择 -->
                    <select v-model="selectedDuration" class="space-select">
                      <option v-for="d in durationOptions" :key="d" :value="d">
                        {{ d }} 分钟
                      </option>
                    </select>

                    <!-- 任务关联 -->
                    <div v-if="selectedTaskTitle" class="linked-task-chip">
                      <span>关联:</span>
                      <strong>{{ selectedTaskTitle }}</strong>
                      <button type="button" class="linked-task-clear" @click="selectedTaskId = null">&times;</button>
                    </div>

                    <button type="button" class="task-link-btn" @click="showTaskSelector = !showTaskSelector">
                      {{ selectedTaskTitle ? '更换任务' : '+ 关联任务' }}
                    </button>

                    <!-- 任务列表面板 -->
                    <div v-if="showTaskSelector" class="task-selector-panel">
                      <div v-if="myTasks.length">
                        <button
                          v-for="task in myTasks"
                          :key="task.id"
                          type="button"
                          class="task-option"
                          :class="{ selected: selectedTaskId === task.id }"
                          @click="selectedTaskId = task.id; showTaskSelector = false"
                        >
                          {{ task.content || task.title }}
                        </button>
                      </div>
                      <div v-else class="task-option-empty">没有待办任务</div>
                    </div>

                    <SpaceButton variant="success" @click="startGrow" glow>
                      Deploy Pulse Core
                    </SpaceButton>
                  </div>

                  <!-- 专注中 -->
                  <div v-else class="growing-panel">
                    <div class="my-timer">{{ formatTime(growProgress) }}</div>
                    <div v-if="selectedTaskTitle" class="linked-task-chip" style="margin-bottom: 8px;">
                      <span>关联:</span>
                      <strong>{{ selectedTaskTitle }}</strong>
                    </div>
                    <SpaceProgressBar
                      :progress="growProgress"
                      :max="selectedDuration * 60"
                      color="blue"
                      :height="'20px'"
                    />
                    <SpaceButton variant="danger" size="sm" @click="giveUpGrow">
                      Abort Current Pulse
                    </SpaceButton>
                  </div>
                </template>
              </div>
            </template>
          </div>
        </div>

        <!-- 中心装饰 -->
        <div class="center-decoration">
          <span class="station-icon">🛸</span>
        </div>

        <!-- 表情飘屏 -->
        <div class="emoji-container">
          <div
            v-for="emoji in emojis"
            :key="emoji.id"
            class="floating-emoji"
            :style="{ left: emoji.x + '%', animationDelay: '0s' }"
          >
            {{ emoji.emoji }}
          </div>
        </div>
      </div>

      <!-- 底部操作栏 -->
      <div class="bottom-bar">
        <!-- 表情栏 -->
        <div class="emoji-bar">
          <SpaceButton
            v-for="emoji in availableEmojis"
            :key="emoji"
            variant="secondary"
            size="sm"
            @click="sendEmoji(emoji)"
          >
            {{ emoji }}
          </SpaceButton>
        </div>

        <!-- 退出按钮 -->
        <SpaceButton variant="danger" @click="exitRoom">
          Leave Fleet Nexus
        </SpaceButton>
      </div>
    </div>
  </div>
</template>

<style scoped>
.collab-room-page.space-theme {
  min-height: 100vh;
  padding: 28px 20px 36px;
  background: linear-gradient(180deg, #050914 0%, #08111f 48%, #0a192f 100%);
  display: flex;
  flex-direction: column;
  font-family: 'Segoe UI', sans-serif;
  color: #eefcff;
  position: relative;
  overflow: hidden;
}

/* 星星背景 */
.stars-bg {
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(2px 2px at 20px 30px, rgba(255, 255, 255, 0.92), transparent),
    radial-gradient(1px 1px at 90px 40px, rgba(255, 255, 255, 0.82), transparent),
    radial-gradient(2px 2px at 160px 120px, rgba(255, 255, 255, 0.55), transparent),
    radial-gradient(1px 1px at 260px 60px, rgba(255, 255, 255, 0.76), transparent);
  background-size: 360px 220px;
  opacity: 0.55;
  pointer-events: none;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: rgba(214, 247, 255, 0.68);
  z-index: 1;
}

.space-spinner {
  width: 44px;
  height: 44px;
  border: 3px solid rgba(0, 255, 255, 0.16);
  border-top-color: #00ffff;
  border-radius: 999px;
  animation: spin 1s linear infinite;
  margin: 0 auto 14px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.room-container {
  max-width: 700px;
  margin: 0 auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
}

/* 头部样式 */
.space-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  padding: 22px;
  background:
    linear-gradient(180deg, rgba(10, 26, 46, 0.96), rgba(6, 13, 30, 0.98)),
    rgba(4, 9, 20, 0.92);
  border: 1px solid rgba(0, 255, 255, 0.16);
  border-radius: 26px;
  box-shadow: 0 24px 56px rgba(2, 8, 18, 0.32);
  margin-bottom: 22px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.connection-indicator {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  box-shadow: 0 0 10px rgba(0, 255, 255, 0.55);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.connection-warning {
  color: #ff9aa7;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  white-space: nowrap;
}

.room-info h2 {
  color: #eefcff;
  margin: 0 0 4px;
  font-size: 1.3em;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-shadow: 0 0 16px rgba(0, 255, 255, 0.2);
}

.room-desc {
  color: rgba(214, 247, 255, 0.72);
  font-size: 0.85em;
}

.diamonds-display {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.045);
  padding: 10px 16px;
  border: 1px solid rgba(0, 255, 255, 0.14);
  border-radius: 18px;
}

.diamonds-icon {
  font-size: 1.3em;
  color: #fbbf24;
}
.diamonds-value {
  color: #fbbf24;
  font-weight: bold;
  font-size: 1.2em;
}
.diamonds-label {
  color: rgba(251, 191, 36, 0.8);
  font-size: 0.8em;
  text-transform: uppercase;
}

/* 座位区域 */
.seats-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  min-height: 400px;
}

.seats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18px;
  max-width: 500px;
  width: 100%;
}

.seat {
  background:
    linear-gradient(180deg, rgba(10, 26, 46, 0.96), rgba(6, 13, 30, 0.98)),
    rgba(4, 9, 20, 0.92);
  border: 1px solid rgba(0, 255, 255, 0.16);
  border-radius: 18px;
  padding: 22px;
  text-align: center;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
  min-height: 160px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.seat:hover {
  border-color: rgba(0, 255, 255, 0.3);
}

.seat.my-seat {
  border-color: rgba(0, 255, 255, 0.34);
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
}

.seat.growing {
  border-color: rgba(16, 185, 129, 0.34);
  box-shadow: 0 0 20px rgba(16, 185, 129, 0.3);
}

.empty-seat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.seat-icon {
  font-size: 2.5em;
  opacity: 0.5;
}

.seat-label {
  color: rgba(164, 245, 255, 0.68);
  font-size: 0.8em;
  text-transform: uppercase;
  letter-spacing: 0.14em;
}

.occupied-seat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.avatar {
  font-size: 2.2em;
}

.username {
  font-weight: 600;
  color: #eefcff;
  font-size: 0.95em;
}

.timer-display {
  font-size: 2.5em;
  font-weight: bold;
  color: #eefcff;
  font-family: 'Roboto Mono', 'Consolas', monospace;
  text-shadow: 0 0 16px rgba(0, 255, 255, 0.3);
  margin-top: 8px;
}

.status.growing {
  color: rgba(16, 185, 129, 0.9);
  font-size: 0.85em;
  text-transform: uppercase;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
}

.control-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
  width: 100%;
}

.space-select {
  width: 100%;
  box-sizing: border-box;
  padding: 12px 14px;
  background: rgba(7, 16, 34, 0.94);
  border: 1px solid rgba(0, 255, 255, 0.14);
  border-radius: 14px;
  color: #eefcff;
  font-size: 14px;
  cursor: pointer;
  outline: none;
}

.space-select:focus {
  border-color: rgba(0, 255, 255, 0.42);
  box-shadow: 0 0 0 1px rgba(0, 255, 255, 0.16), 0 0 18px rgba(0, 255, 255, 0.08);
}

.growing-panel {
  margin-top: 12px;
  width: 100%;
}

.my-timer {
  font-size: 3em;
  font-weight: bold;
  color: #eefcff;
  font-family: 'Roboto Mono', 'Consolas', monospace;
  text-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
  margin-bottom: 8px;
}

.center-decoration {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 0;
  pointer-events: none;
}

.station-icon {
  font-size: 4em;
  opacity: 0.15;
  animation: float 4s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.emoji-container {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  overflow: hidden;
  z-index: 10;
}

.floating-emoji {
  position: absolute;
  font-size: 2em;
  animation: floatUp 3s ease-out forwards;
}

@keyframes floatUp {
  0% {
    transform: translateY(0) scale(1);
    opacity: 1;
  }
  100% {
    transform: translateY(-300px) scale(1.5);
    opacity: 0;
  }
}

.bottom-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 22px;
  background:
    linear-gradient(180deg, rgba(10, 26, 46, 0.96), rgba(6, 13, 30, 0.98)),
    rgba(4, 9, 20, 0.92);
  border: 1px solid rgba(0, 255, 255, 0.16);
  border-radius: 26px;
  box-shadow: 0 24px 56px rgba(2, 8, 18, 0.32);
  margin-top: 22px;
}

.emoji-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* 任务选择器 */
.task-selector-panel {
  background: rgba(7, 16, 34, 0.94);
  border: 1px solid rgba(0, 255, 255, 0.14);
  border-radius: 14px;
  padding: 10px;
  max-height: 180px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 255, 255, 0.4) rgba(10, 25, 47, 0.6);
}

.task-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  cursor: pointer;
  transition: background 0.15s ease;
  text-align: left;
  border: none;
  background: transparent;
  color: #eefcff;
  width: 100%;
  font-size: 13px;
}

.task-option:hover {
  background: rgba(255, 255, 255, 0.06);
}

.task-option.selected {
  background: rgba(0, 255, 255, 0.1);
  border: 1px solid rgba(0, 255, 255, 0.24);
}

.task-option-empty {
  padding: 16px;
  text-align: center;
  color: rgba(214, 247, 255, 0.5);
  font-size: 13px;
}

.linked-task-chip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-radius: 12px;
  background: rgba(0, 255, 255, 0.06);
  border: 1px solid rgba(0, 255, 255, 0.14);
  font-size: 12px;
  color: rgba(214, 247, 255, 0.8);
}

.linked-task-chip strong {
  color: #9ef8ff;
}

.linked-task-clear {
  background: none;
  border: none;
  color: rgba(255, 154, 167, 0.8);
  cursor: pointer;
  font-size: 16px;
  padding: 2px 6px;
  border-radius: 6px;
}

.linked-task-clear:hover {
  color: #ff9aa7;
  background: rgba(255, 154, 167, 0.1);
}

.task-link-btn {
  width: 100%;
  padding: 10px;
  border-radius: 12px;
  border: 1px dashed rgba(0, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(164, 245, 255, 0.68);
  cursor: pointer;
  font-size: 13px;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.task-link-btn:hover {
  border-color: rgba(0, 255, 255, 0.36);
  background: rgba(0, 255, 255, 0.04);
}

/* Toast 通知 */
.toast-card {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  padding: 18px 24px;
  border-radius: 20px;
  background:
    linear-gradient(180deg, rgba(16, 46, 26, 0.96), rgba(8, 30, 16, 0.98)),
    rgba(4, 20, 10, 0.92);
  border: 1px solid rgba(16, 185, 129, 0.34);
  box-shadow: 0 20px 48px rgba(0, 0, 0, 0.4), 0 0 24px rgba(16, 185, 129, 0.2);
  backdrop-filter: blur(18px);
  color: #eefcff;
  text-align: center;
  animation: toastIn 0.3s ease-out;
}

.toast-card h4 {
  margin: 0 0 6px;
  font-size: 18px;
  color: #6ee7b7;
}

.toast-card p {
  margin: 0;
  font-size: 14px;
  color: rgba(214, 247, 255, 0.72);
}

.toast-reward {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 6px 14px;
  border-radius: 999px;
  background: rgba(251, 191, 36, 0.12);
  border: 1px solid rgba(251, 191, 36, 0.3);
  color: #fbbf24;
  font-weight: 700;
  font-size: 15px;
}

@keyframes toastIn {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-12px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

@media (max-width: 768px) {
  .space-header {
    flex-direction: column;
    align-items: stretch;
  }

  .diamonds-display {
    justify-content: center;
  }

  .bottom-bar {
    flex-direction: column;
    gap: 12px;
  }
}
</style>
