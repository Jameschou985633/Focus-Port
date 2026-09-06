<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import SpaceButton from '../base/SpaceButton.vue'
import SpaceProgressBar from '../base/SpaceProgressBar.vue'
import SpacePanel from '../base/SpacePanel.vue'
import BackButton from '../base/BackButton.vue'
import { WORLD_NAMES } from '../../constants/worldNames'
import { useUserStore } from '../../stores/user'
import { createGreenhouseWebSocket, friendApi, greenhouseApi } from '../../api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const roomId = computed(() => parseInt(route.params.id))

// 用户信息
const currentUsername = computed(() => userStore.username || 'guest')
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
const friends = ref([])
const showInvitePanel = ref(false)
const inviteSending = ref(false)
const inviteHint = ref('')

// WebSocket
const ws = ref(null)
const isConnected = ref(false)
const sharedClock = ref(Date.now())
const sharedClockTimer = ref(null)

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
const reconnectTimer = ref(null)

const focusExitSlogans = [
  '再坚持一下，真正的进步往往发生在想放弃之后。',
  '先别急着退出，把这一轮做完，给自己一个确定的胜利。',
  '专注不是靠情绪，是靠一次次把手放回任务上。',
  '你已经开始了，这本身就比停在原地更强。',
  '现在多坚持一分钟，等会儿就少一点遗憾。'
]

const confirmFocusExit = (message) => {
  const slogan = focusExitSlogans[Math.floor(Math.random() * focusExitSlogans.length)]
  return confirm(`${slogan}\n\n${message}`)
}

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

const occupiedSeats = computed(() => seats.value.filter((seat) => seat?.is_occupied && seat.username))
const memberCountLabel = computed(() => `${occupiedSeats.value.length}/${room.value?.max_seats || 0} 人已入座`)

const seatDisplayName = (seat) => seat?.nickname || seat?.username || '空座-无人'
const seatAvatar = (seat) => seat?.avatar || '👨‍🚀'
const isImageAvatar = (avatar) => /^(https?:\/\/|data:image\/)/i.test(String(avatar || ''))

const normalizeGrowingUsers = (users) => (
  (Array.isArray(users) ? users : [])
    .filter((item) => item?.username)
    .map((item) => ({
      ...item,
      duration: Number(item.duration || item.duration_minutes || 25),
      started_at: item.started_at || item.start_time || '',
      remaining_seconds: Number(item.remaining_seconds || 0)
    }))
)

// 加载房间数据
const loadRoom = async () => {
  try {
    await greenhouseApi.visit(roomId.value, currentUsername.value)
    const res = await greenhouseApi.get(roomId.value)
    room.value = res.data.room || res.data.greenhouse || res.data
    seats.value = res.data.seats || room.value?.seats || []
    growingUsers.value = normalizeGrowingUsers(res.data.growing_users)

    // 房主进入自己的协作舱时自动入座，人数统计与实际状态保持一致。
    if (room.value?.owner_username === currentUsername.value) {
      const currentSeat = seats.value.find((seat) => seat.is_occupied && seat.username === currentUsername.value)
      if (currentSeat) {
        mySeat.value = currentSeat.seat_index
      } else {
        const firstEmptySeat = seats.value.find((seat) => !seat.is_occupied)
        if (firstEmptySeat) {
          const seatRes = await greenhouseApi.takeSeat(roomId.value, currentUsername.value, firstEmptySeat.seat_index)
          if (seatRes.data.success) {
            mySeat.value = firstEmptySeat.seat_index
            seats.value = seatRes.data.seats || seats.value
          }
        }
      }
    } else {
      const currentSeat = seats.value.find((seat) => seat.is_occupied && seat.username === currentUsername.value)
      mySeat.value = currentSeat?.seat_index ?? null
    }
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
    const res = await greenhouseApi.getSunshine(currentUsername.value)
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

const loadFriends = async () => {
  try {
    const res = await friendApi.list(currentUsername.value)
    friends.value = (res.data.friends || []).filter((friend) => friend.status === 'accepted')
  } catch (err) {
    console.error('加载好友失败:', err)
  }
}

// 连接 WebSocket
const connectWebSocket = () => {
  if (!wsActive.value) return
  if (ws.value && [WebSocket.OPEN, WebSocket.CONNECTING].includes(ws.value.readyState)) return
  if (reconnectTimer.value) {
    clearTimeout(reconnectTimer.value)
    reconnectTimer.value = null
  }
  ws.value = createGreenhouseWebSocket(roomId.value)

  ws.value.onopen = () => {
    isConnected.value = true
    reconnectAttempts.value = 0
  }

  ws.value.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      handleWebSocketMessage(data)
    } catch (e) {
      console.error('WebSocket 消息解析失败:', e)
    }
  }

  ws.value.onclose = () => {
    isConnected.value = false
    if (!wsActive.value) return
    reconnectAttempts.value++
    const delay = Math.min(15000, 1500 * Math.max(1, reconnectAttempts.value))
    reconnectTimer.value = setTimeout(connectWebSocket, delay)
  }

  ws.value.onerror = () => {
    isConnected.value = false
  }
}

// 处理 WebSocket 消息
const handleWebSocketMessage = (data) => {
  switch (data.type) {
    case 'room_deleted':
      wsActive.value = false
      alert('该协作舱已被创建者删除。')
      router.push('/collab')
      break
    case 'user_joined':
      seats.value = data.seats
      break
    case 'user_left':
      seats.value = data.seats
      break
    case 'grow_started':
      growingUsers.value = normalizeGrowingUsers(data.growing_users)
      if (data.username === currentUsername.value) {
        isGrowing.value = true
        startTime.value = Date.now()
      }
      break
    case 'grow_ended':
      growingUsers.value = normalizeGrowingUsers(data.growing_users)
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
      growingUsers.value = normalizeGrowingUsers(data.growing_users)
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
    const res = await greenhouseApi.takeSeat(roomId.value, currentUsername.value, seatIndex)
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
    if (!confirmFocusExit('正在专注中，离开会丢失进度，确定离开吗？')) return false
    await endGrow('failed')
  }

  try {
    await greenhouseApi.leave(roomId.value, currentUsername.value)
    mySeat.value = null
    loadRoom()
    return true
  } catch (err) {
    console.error('离开失败:', err)
    return false
  }
}

// 开始专注
const startGrow = async () => {
  try {
    const res = await greenhouseApi.start(roomId.value, currentUsername.value, selectedDuration.value, selectedTaskId.value)
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
    const res = await greenhouseApi.end(roomId.value, currentUsername.value, status)
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
  if (!confirmFocusExit('确定要放弃吗？进度将不会保存！')) return
  await endGrow('failed')
}

// 发送表情
const sendEmoji = async (emoji) => {
  try {
    await greenhouseApi.emoji(roomId.value, currentUsername.value, emoji)
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
  return seats.value.find(s => s.seat_index === index && s.is_occupied && s.username)
}

// 获取专注用户信息
const getGrowingInfo = (username) => {
  return growingUsers.value.find(g => g.username === username)
}

const getGrowingSeconds = (username) => {
  if (username === currentUsername.value && isGrowing.value) return growProgress.value
  const info = getGrowingInfo(username)
  if (!info) return 0
  const startedAt = info.started_at || info.start_time
  if (!startedAt) return Number(info.remaining_seconds || 0)
  const startedTimestamp = new Date(String(startedAt).replace(' ', 'T')).getTime()
  if (!Number.isFinite(startedTimestamp)) return Number(info.remaining_seconds || 0)
  return Math.max(0, Number(info.duration || 0) * 60 - Math.floor((sharedClock.value - startedTimestamp) / 1000))
}

const isSeatGrowing = (username) => (
  Boolean(getGrowingInfo(username) || (username === currentUsername.value && isGrowing.value))
)

const getGrowingDuration = (username) => (
  getGrowingInfo(username)?.duration || (username === currentUsername.value ? selectedDuration.value : 25)
)

// 退出房间
const exitRoom = async () => {
  if (!isGrowing.value && !confirmFocusExit('确定要离开协作舱吗？')) return
  const hasLeft = await leaveSeat()
  if (!hasLeft) return
  router.push('/collab')
}

// 连接状态指示器颜色
const connectionColor = computed(() => {
  return isConnected.value ? '#10b981' : '#ef4444'
})

const reloadAccountState = async () => {
  mySeat.value = null
  isGrowing.value = false
  growProgress.value = 0
  selectedTaskId.value = null
  showInvitePanel.value = false
  inviteHint.value = ''
  if (growTimer.value) clearInterval(growTimer.value)
  await Promise.all([loadRoom(), loadSunshine(), loadTasks(), loadFriends()])
}

const sendInvite = async (friendUsername) => {
  inviteSending.value = true
  inviteHint.value = ''
  try {
    const res = await greenhouseApi.invite(roomId.value, currentUsername.value, friendUsername)
    if (res.data.success) {
      inviteHint.value = `已邀请 ${friendUsername}`
      setTimeout(() => { inviteHint.value = '' }, 3000)
    }
  } catch (err) {
    inviteHint.value = err.response?.data?.detail || '邀请失败'
  } finally {
    inviteSending.value = false
  }
}

onMounted(async () => {
  sharedClockTimer.value = setInterval(() => {
    sharedClock.value = Date.now()
  }, 1000)
  await loadRoom()
  await Promise.all([loadSunshine(), loadTasks(), loadFriends()])
  connectWebSocket()
})

watch(currentUsername, async () => {
  await reloadAccountState()
})

onUnmounted(() => {
  wsActive.value = false
  if (reconnectTimer.value) clearTimeout(reconnectTimer.value)
  if (ws.value) ws.value.close()
  if (growTimer.value) clearInterval(growTimer.value)
  if (sharedClockTimer.value) clearInterval(sharedClockTimer.value)
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
      <p>正在同步协作舱状态...</p>
    </div>

    <!-- 房间内容 -->
    <div v-else class="room-container">
      <!-- 返回按钮（仅未入座时显示） -->
      <BackButton v-if="mySeat === null" to="/collab" label="返回码头" style="margin-bottom: 16px;" />

      <!-- 头部 -->
      <div class="space-header" :style="{ borderColor: themeAccent.accent }">
        <div class="header-left">
          <div class="connection-indicator" :style="{ background: connectionColor }"></div>
          <span v-if="!isConnected" class="connection-warning">连接中断 · 第 {{ reconnectAttempts }} 次重试</span>
          <div class="room-info">
            <h2>{{ room?.name || WORLD_NAMES.fleetNexus.zh }}</h2>
            <span class="room-desc">{{ room?.description || '共享协作舱已开启。一起协调节奏，保持专注。' }}</span>
          </div>
        </div>
        <div class="diamonds-display">
          <span class="diamonds-icon">算</span>
          <span class="diamonds-value">{{ userDiamonds }}</span>
          <span class="diamonds-label">{{ WORLD_NAMES.currency.zh }}</span>
        </div>
      </div>

      <div class="members-strip">
        <div class="members-heading">
          <span class="members-kicker">当前舱内</span>
          <strong>{{ memberCountLabel }}</strong>
        </div>
        <div v-if="occupiedSeats.length" class="member-list">
          <div v-for="seat in occupiedSeats" :key="seat.id" class="member-chip">
            <span class="member-avatar">
              <img v-if="isImageAvatar(seatAvatar(seat))" :src="seatAvatar(seat)" :alt="seatDisplayName(seat)">
              <span v-else>{{ seatAvatar(seat) }}</span>
            </span>
            <span class="member-name">{{ seatDisplayName(seat) }}</span>
          </div>
        </div>
        <span v-else class="members-empty">还没有人入座，选择一个座位开始吧。</span>
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
                <span class="seat-label">空座-无人 · 座位 {{ i }}</span>
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
                <span class="avatar">
                  <img
                    v-if="isImageAvatar(seatAvatar(getSeatUser(i - 1)))"
                    :src="seatAvatar(getSeatUser(i - 1))"
                    :alt="seatDisplayName(getSeatUser(i - 1))"
                  >
                  <span v-else>{{ seatAvatar(getSeatUser(i - 1)) }}</span>
                </span>
                <span class="username">{{ seatDisplayName(getSeatUser(i - 1)) }}</span>

                <!-- 所有人共享同一种专注状态展示，只有本人显示控制按钮 -->
                <template v-if="isSeatGrowing(getSeatUser(i - 1).username)">
                  <div class="growing-panel shared-growing-panel">
                    <div class="my-timer">
                      {{ formatTime(getGrowingSeconds(getSeatUser(i - 1).username)) }}
                    </div>
                    <div
                      v-if="mySeat === i - 1 && selectedTaskTitle"
                      class="linked-task-chip"
                      style="margin-bottom: 8px;"
                    >
                      <span>关联:</span>
                      <strong>{{ selectedTaskTitle }}</strong>
                    </div>
                    <SpaceProgressBar
                      :progress="getGrowingSeconds(getSeatUser(i - 1).username)"
                      :max="getGrowingDuration(getSeatUser(i - 1).username) * 60"
                      color="blue"
                      :height="'20px'"
                    />
                    <span class="status growing">座位锁定 / 专注进行中</span>
                    <SpaceButton
                      v-if="mySeat === i - 1"
                      variant="danger"
                      size="sm"
                      @click="giveUpGrow"
                    >
                      放弃本轮专注
                    </SpaceButton>
                  </div>
                </template>

                <!-- 我的座位 - 控制面板 -->
                <template v-else-if="mySeat === i - 1">
                  <!-- 未开始专注 -->
                  <div class="control-panel">
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
                      启动专注
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

      <Teleport to="body">
        <Transition name="modal">
          <div v-if="showInvitePanel" class="invite-overlay" @click.self="showInvitePanel = false">
            <div class="invite-panel">
              <header class="invite-header">
                <h3>邀请好友进入协作舱</h3>
                <button class="close-btn" @click="showInvitePanel = false">×</button>
              </header>
              <p class="invite-desc">选择一位好友，系统会发出可直达本房间的邀请消息。</p>
              <div v-if="friends.length" class="invite-list">
                <button
                  v-for="friend in friends"
                  :key="friend.id"
                  class="invite-friend"
                  :disabled="inviteSending"
                  @click="sendInvite(friend.friend_username)"
                >
                  <span class="invite-name">{{ friend.friend_username }}</span>
                  <span class="invite-arrow">邀请</span>
                </button>
              </div>
              <div v-else class="invite-empty">你还没有已通过的好友，先去好友页加一个吧。</div>
              <div v-if="inviteHint" class="invite-hint">{{ inviteHint }}</div>
            </div>
          </div>
        </Transition>
      </Teleport>

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

        <SpaceButton variant="secondary" @click="showInvitePanel = true">
          邀请好友
        </SpaceButton>

        <!-- 退出按钮 -->
        <SpaceButton variant="danger" @click="exitRoom">
          离开协作舱
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

.members-strip {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
  padding: 14px 18px;
  margin-bottom: 18px;
  border: 1px solid rgba(0, 255, 255, 0.14);
  border-radius: 18px;
  background: rgba(7, 16, 34, 0.72);
}

.members-heading {
  display: grid;
  gap: 3px;
  min-width: 90px;
}

.members-kicker {
  color: rgba(164, 245, 255, 0.62);
  font-size: 11px;
  letter-spacing: 0.12em;
}

.members-heading strong {
  color: #eefcff;
  font-size: 13px;
}

.member-list {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.member-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 10px 6px 6px;
  border: 1px solid rgba(0, 255, 255, 0.14);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.045);
}

.member-avatar,
.avatar {
  display: grid;
  place-items: center;
  overflow: hidden;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(0, 117, 255, 0.8), rgba(132, 94, 247, 0.8));
}

.member-avatar {
  width: 28px;
  height: 28px;
  font-size: 16px;
}

.member-avatar img,
.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.member-name {
  color: #dffcff;
  font-size: 12px;
  font-weight: 600;
}

.members-empty {
  color: rgba(214, 247, 255, 0.58);
  font-size: 12px;
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
  width: 58px;
  height: 58px;
  font-size: 2em;
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

.invite-overlay {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.7);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 120;
  padding: 20px;
}

.invite-panel {
  width: min(560px, 100%);
  max-height: min(78vh, 760px);
  overflow: auto;
  border-radius: 24px;
  padding: 22px;
  background: linear-gradient(180deg, rgba(10, 26, 46, 0.98), rgba(6, 13, 30, 0.99));
  border: 1px solid rgba(0, 255, 255, 0.18);
  box-shadow: 0 28px 64px rgba(2, 8, 18, 0.5);
  color: #eefcff;
}

.invite-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.invite-header h3 {
  margin: 0;
  font-size: 18px;
}

.invite-desc,
.invite-empty,
.invite-hint {
  color: rgba(214, 247, 255, 0.74);
  font-size: 13px;
  line-height: 1.6;
}

.invite-list {
  display: grid;
  gap: 10px;
  margin-top: 14px;
}

.invite-friend {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(255, 255, 255, 0.04);
  color: #eefcff;
  cursor: pointer;
  transition: transform 0.15s ease, border-color 0.15s ease, background 0.15s ease;
}

.invite-friend:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(0, 255, 255, 0.3);
  background: rgba(0, 255, 255, 0.06);
}

.invite-friend:disabled {
  opacity: 0.6;
  cursor: wait;
}

.invite-name {
  font-weight: 600;
}

.invite-arrow {
  font-size: 12px;
  color: #9ef8ff;
}

.invite-hint {
  margin-top: 12px;
  color: #9ef8ff;
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
