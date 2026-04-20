<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { arcadeApi, unifiedShopApi } from '../api'

const router = useRouter()
const userStore = useUserStore()

const selectedGame = ref(null)
const onlineStep = ref('') // '', 'choose', 'create', 'join', 'waiting'
const roomCode = ref('')
const joinCode = ref('')
const joinError = ref('')
const createError = ref('')
const userCoins = ref(0)

const games = [
  { id: 'gomoku', name: '五子棋', icon: '⚫', desc: '经典五子连珠' },
  { id: 'tictactoe', name: '井字棋', icon: '✖️', desc: '3x3 经典对弈' },
  { id: 'connect4', name: '四子棋', icon: '🔴', desc: '纵向落子，四子连线' },
  { id: 'reversi', name: '黑白棋', icon: '⬛', desc: '翻转对手棋子占领棋盘' }
]

const onlineRoutes = {
  gomoku: 'gomoku',
  tictactoe: 'tictactoe',
  connect4: 'connect-four',
  reversi: 'reversi'
}

function selectGame(game) {
  selectedGame.value = game
}

function closeGameModal() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  selectedGame.value = null
  onlineStep.value = ''
  roomCode.value = ''
  joinCode.value = ''
  joinError.value = ''
  createError.value = ''
}

function showOnlineOptions() {
  onlineStep.value = 'choose'
}

async function loadBalance() {
  try {
    const res = await unifiedShopApi.balance(userStore.username)
    userCoins.value = res.data.coins || 0
  } catch (e) { /* ignore */ }
}

async function startPvE() {
  const g = selectedGame.value
  closeGameModal()

  try {
    await arcadeApi.play(userStore.username, g.id)
  } catch (e) {
    console.warn('Arcade play API error:', e)
  }

  const routes = {
    gomoku: '/playground/gomoku-solo?mode=pve',
    tictactoe: '/playground/tictactoe',
    connect4: '/playground/connect-four',
    reversi: '/playground/reversi'
  }
  router.push(routes[g.id])
}

async function createRoom() {
  const g = selectedGame.value
  createError.value = ''
  await loadBalance()

  if (userCoins.value < 50) {
    createError.value = `CU 不足！需要 50 CU，当前 ${userCoins.value} CU`
    return
  }

  try {
    const res = await arcadeApi.play(userStore.username, `${g.id}_online`)
    if (res.data?.room_code) {
      roomCode.value = res.data.room_code
      onlineStep.value = 'waiting'
      // Start polling for opponent
      pollForOpponent()
    }
  } catch (e) {
    const detail = e.response?.data?.detail
    if (detail?.includes('金币不足') || detail?.includes('CU')) {
      createError.value = 'CU 不足！需要 50 CU'
    } else {
      createError.value = detail || '创建房间失败'
    }
  }
}

let pollTimer = null
function pollForOpponent() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    if (!roomCode.value) return
    try {
      const res = await arcadeApi.room(roomCode.value)
      if (res.data?.status === 'playing' && res.data?.player_guest) {
        clearInterval(pollTimer)
        pollTimer = null
        const g = selectedGame.value
        router.push(`/playground/${onlineRoutes[g.id]}/online/${roomCode.value}`)
      }
    } catch (e) { /* keep polling */ }
  }, 2000)
}

async function joinRoom() {
  joinError.value = ''
  const code = joinCode.value.trim().toUpperCase()
  if (!code) {
    joinError.value = '请输入房间码'
    return
  }

  try {
    const joinRes = await arcadeApi.join(code, userStore.username)
    if (joinRes.data?.success) {
      const gameType = joinRes.data.game_type
      closeGameModal()
      router.push(`/playground/${onlineRoutes[gameType]}/online/${code}`)
    }
  } catch (e) {
    const detail = e.response?.data?.detail
    joinError.value = detail || '加入失败'
  }
}

function copyCode() {
  if (roomCode.value) {
    navigator.clipboard?.writeText(roomCode.value)
  }
}

function goBack() {
  if (pollTimer) clearInterval(pollTimer)
  router.push('/')
}

onUnmounted(() => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
})
</script>

<template>
  <div class="playground space-theme">
    <div class="stars-bg"></div>

    <div class="page-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h1>游乐场</h1>
    </div>

    <div class="game-grid">
      <div v-for="game in games" :key="game.id" class="game-card" @click="selectGame(game)">
        <div class="game-icon">{{ game.icon }}</div>
        <div class="game-info">
          <h3>{{ game.name }}</h3>
          <p>{{ game.desc }}</p>
        </div>
        <span class="game-arrow">→</span>
      </div>
    </div>

    <!-- Mode selection modal -->
    <div v-if="selectedGame && onlineStep === ''" class="modal-overlay" @click.self="closeGameModal">
      <div class="modal-card">
        <div class="modal-header">
          <h3>{{ selectedGame.name }}</h3>
          <button class="close-btn" @click="closeGameModal">×</button>
        </div>
        <div class="modal-body">
          <p class="modal-desc">选择游戏模式</p>
          <div class="mode-buttons">
            <button class="mode-btn" @click="startPvE">
              <span class="mode-icon">🤖</span>
              <span>人机对战</span>
            </button>
            <button class="mode-btn" @click="showOnlineOptions">
              <span class="mode-icon">👥</span>
              <span>两人联机</span>
              <span class="cu-badge">50 CU</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Online options: create or join -->
    <div v-if="selectedGame && onlineStep === 'choose'" class="modal-overlay" @click.self="closeGameModal">
      <div class="modal-card">
        <div class="modal-header">
          <button class="back-btn-sm" @click="onlineStep = ''">←</button>
          <h3>{{ selectedGame.name }} · 联机</h3>
          <button class="close-btn" @click="closeGameModal">×</button>
        </div>
        <div class="modal-body">
          <div class="mode-buttons vertical">
            <button class="mode-btn wide" @click="createRoom">
              <span class="mode-icon">🏠</span>
              <span>创建房间</span>
              <span class="cu-cost">花费 50 CU</span>
            </button>
            <button class="mode-btn wide" @click="onlineStep = 'join'">
              <span class="mode-icon">🚪</span>
              <span>加入房间</span>
              <span class="cu-cost">输入房间码</span>
            </button>
          </div>
          <p v-if="createError" class="error-text">{{ createError }}</p>
        </div>
      </div>
    </div>

    <!-- Waiting for opponent -->
    <div v-if="selectedGame && onlineStep === 'waiting'" class="modal-overlay">
      <div class="modal-card">
        <div class="modal-header">
          <h3>{{ selectedGame.name }} · 等待对手</h3>
          <button class="close-btn" @click="closeGameModal">×</button>
        </div>
        <div class="modal-body waiting-body">
          <div class="room-code-display">
            <p class="waiting-label">房间码</p>
            <div class="code-row">
              <span class="code-text">{{ roomCode }}</span>
              <button class="copy-btn" @click="copyCode">复制</button>
            </div>
          </div>
          <div class="waiting-spinner">
            <div class="spinner"></div>
            <p>等待对手加入...</p>
          </div>
          <button class="action-btn secondary" @click="closeGameModal">取消</button>
        </div>
      </div>
    </div>

    <!-- Join room -->
    <div v-if="selectedGame && onlineStep === 'join'" class="modal-overlay" @click.self="closeGameModal">
      <div class="modal-card">
        <div class="modal-header">
          <button class="back-btn-sm" @click="onlineStep = 'choose'">←</button>
          <h3>加入房间</h3>
          <button class="close-btn" @click="closeGameModal">×</button>
        </div>
        <div class="modal-body">
          <div class="join-form">
            <input
              v-model="joinCode"
              class="join-input"
              placeholder="输入房间码 (如 GOM-A1B2C3D4)"
              @keyup.enter="joinRoom"
              maxlength="20"
            />
            <button class="action-btn primary" @click="joinRoom">加入</button>
          </div>
          <p v-if="joinError" class="error-text">{{ joinError }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.playground.space-theme {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0f1a 0%, #0f172a 50%, #0a0f1a 100%);
  padding: 20px;
  color: white;
  font-family: 'Segoe UI', sans-serif;
  position: relative;
}

.stars-bg {
  position: fixed; inset: 0;
  background-image:
    radial-gradient(2px 2px at 20px 30px, #fff, transparent),
    radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.8), transparent),
    radial-gradient(1px 1px at 90px 40px, #fff, transparent),
    radial-gradient(1px 1px at 130px 80px, rgba(255,255,255,0.6), transparent);
  background-size: 200px 120px;
  opacity: 0.35;
  pointer-events: none;
}

.page-header {
  position: relative; z-index: 1;
  display: flex; align-items: center; gap: 16px;
  max-width: 600px; margin: 0 auto 24px;
}

.back-btn {
  background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12);
  color: white; padding: 8px 14px; border-radius: 12px; cursor: pointer; font-size: 14px;
}

.page-header h1 { margin: 0; font-size: 30px; }

.game-grid {
  position: relative; z-index: 1;
  max-width: 600px; margin: 0 auto;
  display: grid; gap: 12px;
}

.game-card {
  display: flex; align-items: center; gap: 16px;
  padding: 18px 20px;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(18px);
  cursor: pointer;
  transition: all 0.2s;
}

.game-card:hover {
  border-color: #38bdf8;
  background: rgba(56, 189, 248, 0.08);
  transform: translateY(-2px);
}

.game-icon {
  font-size: 32px;
  width: 56px; height: 56px;
  display: grid; place-items: center;
  border-radius: 16px;
  background: rgba(255,255,255,0.06);
}

.game-info { flex: 1; }
.game-info h3 { margin: 0 0 4px; font-size: 18px; }
.game-info p { margin: 0; color: rgba(255,255,255,0.6); font-size: 14px; }
.game-arrow { color: #7dd3fc; font-size: 18px; }

.modal-overlay {
  position: fixed; inset: 0; z-index: 20;
  display: grid; place-items: center; padding: 20px;
  background: rgba(2, 6, 23, 0.66);
}

.modal-card {
  width: min(420px, 100%);
  border-radius: 24px;
  background: #0f172a;
  border: 1px solid rgba(255,255,255,0.12);
  overflow: hidden;
}

.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 20px; gap: 12px;
}

.modal-header h3 { margin: 0; flex: 1; text-align: center; }

.close-btn {
  border: none; background: transparent; color: white;
  font-size: 28px; cursor: pointer; flex-shrink: 0;
}

.back-btn-sm {
  background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12);
  color: white; padding: 4px 10px; border-radius: 8px; cursor: pointer; font-size: 16px;
  flex-shrink: 0;
}

.modal-body { padding: 0 20px 20px; }
.modal-desc { margin: 0 0 16px; color: rgba(255,255,255,0.7); }

.mode-buttons {
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
}

.mode-buttons.vertical {
  grid-template-columns: 1fr;
}

.mode-btn {
  padding: 18px 16px;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.06);
  color: white;
  cursor: pointer;
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  font-weight: 600; font-size: 15px;
  transition: all 0.2s;
  position: relative;
}

.mode-btn:hover {
  border-color: #38bdf8;
  background: rgba(56, 189, 248, 0.1);
}

.mode-btn.wide {
  flex-direction: row; justify-content: center; gap: 10px;
}

.mode-icon { font-size: 28px; }
.mode-btn.wide .mode-icon { font-size: 22px; }

.cu-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
  position: absolute;
  top: 8px;
  right: 8px;
}

.cu-cost {
  font-size: 12px;
  color: rgba(255,255,255,0.5);
  font-weight: 400;
}

.error-text {
  color: #f87171;
  text-align: center;
  margin: 12px 0 0;
  font-size: 14px;
}

/* Waiting */
.waiting-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.room-code-display {
  text-align: center;
  width: 100%;
}

.waiting-label {
  margin: 0 0 8px;
  color: rgba(255,255,255,0.6);
  font-size: 14px;
}

.code-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.code-text {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 3px;
  font-family: 'Courier New', monospace;
  color: #7dd3fc;
}

.copy-btn {
  padding: 6px 14px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.15);
  background: rgba(255,255,255,0.08);
  color: white;
  cursor: pointer;
  font-size: 13px;
}

.copy-btn:hover {
  background: rgba(255,255,255,0.15);
}

.waiting-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: rgba(255,255,255,0.6);
  font-size: 14px;
}

.spinner {
  width: 32px; height: 32px;
  border: 3px solid rgba(255,255,255,0.1);
  border-top-color: #38bdf8;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Join */
.join-form {
  display: flex;
  gap: 10px;
}

.join-input {
  flex: 1;
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.15);
  background: rgba(255,255,255,0.06);
  color: white;
  font-size: 16px;
  font-family: 'Courier New', monospace;
  letter-spacing: 2px;
  outline: none;
  text-transform: uppercase;
}

.join-input:focus {
  border-color: #38bdf8;
}

.join-input::placeholder {
  font-family: 'Segoe UI', sans-serif;
  letter-spacing: normal;
  font-size: 13px;
  text-transform: none;
}

.action-btn {
  padding: 10px 20px;
  border-radius: 12px;
  border: none;
  font-weight: 700;
  cursor: pointer;
  font-size: 14px;
}

.action-btn.primary {
  background: linear-gradient(135deg, #38bdf8, #60a5fa);
  color: #08111e;
}

.action-btn.secondary {
  background: rgba(255,255,255,0.1);
  color: white;
  border: 1px solid rgba(255,255,255,0.15);
}
</style>
