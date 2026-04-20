<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { createArcadeWebSocket } from '../api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const SIZE = 3
const board = ref(Array.from({ length: SIZE }, () => Array(SIZE).fill(0)))
const currentTurn = ref(1) // 1=X, 2=O
const gameOver = ref(false)
const winner = ref(0)
const isDraw = ref(false)
const isPvE = ref(true)
const isOnline = ref(false)
const aiThinking = ref(false)
const onlineMyColor = ref(0)
const roomCode = ref('')
let ws = null

const username = computed(() => userStore.username || 'Player')

const isMyTurn = computed(() => {
  if (isPvE.value) return currentTurn.value === 1
  if (isOnline.value) return currentTurn.value === onlineMyColor.value
  return true
})

const statusText = computed(() => {
  if (gameOver.value) {
    if (isDraw.value) return '平局！'
    if (isOnline.value) {
      if (winner.value === onlineMyColor.value) return '你赢了！'
      return '你输了！'
    }
    return winner.value === 1 ? 'X 获胜！' : 'O 获胜！'
  }
  if (isOnline.value) return isMyTurn.value ? '轮到你落子' : '等待对手...'
  if (aiThinking.value) return 'AI 思考中...'
  return currentTurn.value === 1 ? 'X 落子' : 'O 落子'
})

onMounted(() => {
  const rc = route.params.roomCode
  if (rc) {
    isOnline.value = true
    roomCode.value = rc
    onlineMyColor.value = 1 // host is X (goes first)
    connectWebSocket(rc)
  }
})

onUnmounted(() => {
  if (ws) ws.close()
})

function connectWebSocket(rc) {
  ws = createArcadeWebSocket(rc)
  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data)
      handleWsMessage(msg)
    } catch (err) {
      console.error('WS parse error:', err)
    }
  }
}

function handleWsMessage(msg) {
  if (msg.type === 'sync') {
    // Restore state from sync
    if (msg.player_host === username.value) {
      onlineMyColor.value = 1
    } else {
      onlineMyColor.value = 2
    }
    if (msg.moves) {
      for (const m of msg.moves) {
        board.value[m.row][m.col] = m.color
      }
      const totalMoves = msg.moves.length
      currentTurn.value = totalMoves % 2 === 0 ? 1 : 2
    }
  } else if (msg.type === 'move') {
    if (msg.username === username.value) return // skip own moves (already applied locally)
    board.value[msg.row][msg.col] = msg.color
    currentTurn.value = msg.color === 1 ? 2 : 1
    if (checkWin(msg.row, msg.col, msg.color)) {
      gameOver.value = true
      winner.value = msg.color
    } else if (board.value.flat().every(v => v !== 0)) {
      gameOver.value = true
      isDraw.value = true
    }
  } else if (msg.type === 'game_over') {
    gameOver.value = true
    winner.value = msg.winner
  }
}

function placeStone(r, c) {
  if (board.value[r][c] !== 0 || gameOver.value) return
  if (isOnline.value && !isMyTurn.value) return
  if (isPvE.value && currentTurn.value === 2) return

  const color = isOnline.value ? onlineMyColor.value : currentTurn.value

  if (isOnline.value) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    ws.send(JSON.stringify({
      type: 'move',
      row: r,
      col: c,
      color: onlineMyColor.value,
      username: username.value
    }))
    // Apply locally immediately
    board.value[r][c] = color
    currentTurn.value = color === 1 ? 2 : 1
    if (checkWin(r, c, color)) {
      gameOver.value = true
      winner.value = color
      // Notify server
      ws.send(JSON.stringify({
        type: 'game_over',
        winner_color: color,
        winner_name: username.value
      }))
    } else if (board.value.flat().every(v => v !== 0)) {
      gameOver.value = true
      isDraw.value = true
    }
    return
  }

  board.value[r][c] = color
  if (checkWin(r, c, color)) {
    gameOver.value = true
    winner.value = color
    return
  }
  if (board.value.flat().every(v => v !== 0)) {
    gameOver.value = true
    isDraw.value = true
    return
  }
  currentTurn.value = color === 1 ? 2 : 1

  if (isPvE.value && currentTurn.value === 2 && !gameOver.value) {
    aiThinking.value = true
    setTimeout(() => {
      const [ar, ac] = getAiMove()
      board.value[ar][ac] = 2
      if (checkWin(ar, ac, 2)) {
        gameOver.value = true
        winner.value = 2
      } else if (board.value.flat().every(v => v !== 0)) {
        gameOver.value = true
        isDraw.value = true
      }
      currentTurn.value = 1
      aiThinking.value = false
    }, 300)
  }
}

function checkWin(row, col, color) {
  const lines = [
    ...Array.from({ length: SIZE }, (_, r) => Array.from({ length: SIZE }, (_, c) => [r, c])),
    ...Array.from({ length: SIZE }, (_, c) => Array.from({ length: SIZE }, (_, r) => [r, c])),
    Array.from({ length: SIZE }, (_, i) => [i, i]),
    Array.from({ length: SIZE }, (_, i) => [i, SIZE - 1 - i])
  ]
  return lines.some(line => line.every(([r, c]) => board.value[r][c] === color))
}

function getAiMove() {
  let bestScore = -Infinity
  let bestMove = null
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      if (board.value[r][c] !== 0) continue
      board.value[r][c] = 2
      const score = minimax(0, false, -Infinity, Infinity)
      board.value[r][c] = 0
      if (score > bestScore) { bestScore = score; bestMove = [r, c] }
    }
  }
  return bestMove || [0, 0]
}

function minimax(depth, isMax, alpha, beta) {
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      if (board.value[r][c] && checkWin(r, c, board.value[r][c])) {
        return board.value[r][c] === 2 ? (10 - depth) : (depth - 10)
      }
    }
  }
  if (board.value.flat().every(v => v !== 0)) return 0
  if (isMax) {
    let best = -Infinity
    for (let r = 0; r < SIZE; r++) {
      for (let c = 0; c < SIZE; c++) {
        if (board.value[r][c] !== 0) continue
        board.value[r][c] = 2
        best = Math.max(best, minimax(depth + 1, false, alpha, beta))
        board.value[r][c] = 0
        alpha = Math.max(alpha, best)
        if (beta <= alpha) return best
      }
    }
    return best
  } else {
    let best = Infinity
    for (let r = 0; r < SIZE; r++) {
      for (let c = 0; c < SIZE; c++) {
        if (board.value[r][c] !== 0) continue
        board.value[r][c] = 1
        best = Math.min(best, minimax(depth + 1, true, alpha, beta))
        board.value[r][c] = 0
        beta = Math.min(beta, best)
        if (beta <= alpha) return best
      }
    }
    return best
  }
}

function resetGame() {
  board.value = Array.from({ length: SIZE }, () => Array(SIZE).fill(0))
  currentTurn.value = 1
  gameOver.value = false
  winner.value = 0
  isDraw.value = false
}

function goBack() {
  router.push('/playground')
}
</script>

<template>
  <div class="game-page space-theme">
    <div class="stars-bg"></div>
    <div class="game-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h2>井字棋</h2>
      <div class="mode-badge">{{ isOnline ? '联机' : '人机' }}</div>
    </div>
    <div v-if="isOnline && roomCode" class="room-badge">房间: {{ roomCode }}</div>
    <div class="status-bar">{{ statusText }}</div>
    <div class="ttt-board">
      <div v-for="(row, r) in board" :key="r" class="ttt-row">
        <div v-for="(cell, c) in row" :key="`${r}-${c}`"
             class="ttt-cell"
             :class="{ 'disabled': isOnline && !isMyTurn }"
             @click="placeStone(r, c)">
          <span v-if="cell === 1" class="x-mark">X</span>
          <span v-else-if="cell === 2" class="o-mark">O</span>
        </div>
      </div>
    </div>
    <div v-if="gameOver" class="game-over-overlay">
      <div class="game-over-card">
        <h3>{{ isDraw ? '平局' : (isOnline ? (winner === onlineMyColor ? '你赢了！' : '你输了！') : (winner === 1 ? 'X 获胜！' : 'O 获胜！')) }}</h3>
        <div class="game-over-actions">
          <button class="action-btn primary" @click="resetGame">再来一局</button>
          <button class="action-btn secondary" @click="goBack">返回</button>
        </div>
      </div>
    </div>
    <div v-if="!gameOver && !isOnline" class="bottom-actions">
      <button class="action-btn secondary" @click="resetGame">重新开始</button>
    </div>
  </div>
</template>

<style scoped>
.game-page.space-theme {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0f1a 0%, #0f172a 50%, #0a0f1a 100%);
  padding: 12px 16px 24px;
  color: white;
  font-family: 'Segoe UI', sans-serif;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.stars-bg {
  position: fixed; inset: 0;
  background-image: radial-gradient(2px 2px at 20px 30px, #fff, transparent), radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.8), transparent), radial-gradient(1px 1px at 90px 40px, #fff, transparent), radial-gradient(1px 1px at 130px 80px, rgba(255,255,255,0.6), transparent);
  background-size: 200px 120px; opacity: 0.35; pointer-events: none;
}
.game-header { position: relative; z-index: 1; display: flex; align-items: center; gap: 16px; width: 100%; max-width: 400px; margin-bottom: 12px; }
.back-btn { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); color: white; padding: 8px 14px; border-radius: 12px; cursor: pointer; font-size: 14px; }
.game-header h2 { flex: 1; margin: 0; font-size: 22px; }
.mode-badge { padding: 6px 14px; border-radius: 999px; background: rgba(56,189,248,0.2); color: #7dd3fc; font-size: 13px; }
.room-badge { position: relative; z-index: 1; text-align: center; color: rgba(255,255,255,0.5); font-size: 12px; font-family: 'Courier New', monospace; margin-bottom: 4px; }
.status-bar { position: relative; z-index: 1; text-align: center; padding: 6px; color: #7dd3fc; font-size: 14px; margin-bottom: 12px; }
.ttt-board { position: relative; z-index: 1; display: flex; flex-direction: column; gap: 6px; padding: 20px; background: rgba(15,23,42,0.78); border: 1px solid rgba(255,255,255,0.1); border-radius: 18px; backdrop-filter: blur(18px); }
.ttt-row { display: flex; gap: 6px; }
.ttt-cell { width: 90px; height: 90px; display: grid; place-items: center; background: rgba(255,255,255,0.05); border-radius: 14px; cursor: pointer; font-size: 40px; font-weight: 700; transition: background 0.15s; }
.ttt-cell:hover { background: rgba(56,189,248,0.1); }
.ttt-cell.disabled { opacity: 0.5; cursor: not-allowed; }
.x-mark { color: #38bdf8; }
.o-mark { color: #f59e0b; }
.game-over-overlay { position: fixed; inset: 0; z-index: 10; display: grid; place-items: center; background: rgba(2,6,23,0.7); }
.game-over-card { background: #0f172a; border: 1px solid rgba(255,255,255,0.15); border-radius: 24px; padding: 32px; text-align: center; min-width: 280px; }
.game-over-card h3 { margin: 0 0 20px; font-size: 24px; }
.game-over-actions { display: flex; gap: 12px; justify-content: center; }
.action-btn { padding: 10px 20px; border-radius: 12px; border: none; font-weight: 700; cursor: pointer; font-size: 14px; }
.action-btn.primary { background: linear-gradient(135deg, #38bdf8, #60a5fa); color: #08111e; }
.action-btn.secondary { background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.15); }
.bottom-actions { position: relative; z-index: 1; margin-top: 16px; }
</style>
