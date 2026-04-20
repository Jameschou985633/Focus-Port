<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { createArcadeWebSocket } from '../api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const ROWS = 6
const COLS = 7
const board = ref(Array.from({ length: ROWS }, () => Array(COLS).fill(0)))
const currentTurn = ref(1) // 1=Red, 2=Yellow
const gameOver = ref(false)
const winner = ref(0)
const isDraw = ref(false)
const isPvE = ref(true)
const isOnline = ref(false)
const aiThinking = ref(false)
const winCells = ref([])
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
      return winner.value === onlineMyColor.value ? '你赢了！' : '你输了！'
    }
    return winner.value === 1 ? '红方获胜！' : '黄方获胜！'
  }
  if (isOnline.value) return isMyTurn.value ? '轮到你落子' : '等待对手...'
  if (aiThinking.value) return 'AI 思考中...'
  return currentTurn.value === 1 ? '红方落子' : '黄方落子'
})

onMounted(() => {
  const rc = route.params.roomCode
  if (rc) {
    isOnline.value = true
    roomCode.value = rc
    onlineMyColor.value = 1
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
    onlineMyColor.value = msg.player_host === username.value ? 1 : 2
    if (msg.moves) {
      for (const m of msg.moves) {
        board.value[m.row][m.col] = m.color
      }
      currentTurn.value = msg.moves.length % 2 === 0 ? 1 : 2
    }
  } else if (msg.type === 'move') {
    if (msg.username === username.value) return // skip own moves
    board.value[msg.row][msg.col] = msg.color
    const w = checkWinAt(msg.row, msg.col, msg.color)
    if (w) {
      gameOver.value = true
      winner.value = msg.color
      winCells.value = w
    } else if (board.value[0].every((_, c) => board.value[0][c] !== 0)) {
      gameOver.value = true
      isDraw.value = true
    }
    currentTurn.value = msg.color === 1 ? 2 : 1
  } else if (msg.type === 'game_over') {
    gameOver.value = true
    winner.value = msg.winner
  }
}

function dropPiece(col) {
  if (gameOver.value || aiThinking.value) return
  if (isOnline.value && !isMyTurn.value) return
  if (isPvE.value && currentTurn.value === 2) return

  const row = getDropRow(col)
  if (row === -1) return

  const color = isOnline.value ? onlineMyColor.value : currentTurn.value

  if (isOnline.value) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    ws.send(JSON.stringify({
      type: 'move',
      row,
      col,
      color,
      username: username.value
    }))
    board.value[row][col] = color
    currentTurn.value = color === 1 ? 2 : 1
    const w = checkWinAt(row, col, color)
    if (w) {
      gameOver.value = true
      winner.value = color
      winCells.value = w
      ws.send(JSON.stringify({
        type: 'game_over',
        winner_color: color,
        winner_name: username.value
      }))
    } else if (board.value[0].every((_, c) => board.value[0][c] !== 0)) {
      gameOver.value = true
      isDraw.value = true
    }
    return
  }

  board.value[row][col] = color
  const w = checkWinAt(row, col, color)
  if (w) {
    gameOver.value = true
    winner.value = color
    winCells.value = w
    return
  }
  if (board.value[0].every((_, c) => board.value[0][c] !== 0)) {
    gameOver.value = true
    isDraw.value = true
    return
  }
  currentTurn.value = color === 1 ? 2 : 1

  if (isPvE.value && currentTurn.value === 2 && !gameOver.value) {
    aiThinking.value = true
    setTimeout(() => {
      const aiCol = getAiMove()
      const aiRow = getDropRow(aiCol)
      if (aiRow === -1) { aiThinking.value = false; return }
      board.value[aiRow][aiCol] = 2
      const aw = checkWinAt(aiRow, aiCol, 2)
      if (aw) {
        gameOver.value = true
        winner.value = 2
        winCells.value = aw
      } else if (board.value[0].every((_, c) => board.value[0][c] !== 0)) {
        gameOver.value = true
        isDraw.value = true
      }
      currentTurn.value = 1
      aiThinking.value = false
    }, 400)
  }
}

function getDropRow(col) {
  for (let r = ROWS - 1; r >= 0; r--) {
    if (board.value[r][col] === 0) return r
  }
  return -1
}

function checkWinAt(row, col, color) {
  const dirs = [[0,1],[1,0],[1,1],[1,-1]]
  for (const [dr, dc] of dirs) {
    let cells = [[row, col]]
    for (let d = -1; d <= 1; d += 2) {
      let r = row + dr * d, c = col + dc * d
      while (r >= 0 && r < ROWS && c >= 0 && c < COLS && board.value[r][c] === color) {
        cells.push([r, c]); r += dr * d; c += dc * d
      }
    }
    if (cells.length >= 4) return cells
  }
  return null
}

function getAiMove() {
  let bestScore = -Infinity
  let bestCol = 3
  for (let c = 0; c < COLS; c++) {
    const r = getDropRow(c)
    if (r === -1) continue
    let score = scorePosition(r, c, 2) - scorePosition(r, c, 1) * 0.9
    score += (3 - Math.abs(c - 3)) * 3
    if (score > bestScore) { bestScore = score; bestCol = c }
  }
  return bestCol
}

function scorePosition(row, col, color) {
  let score = 0
  const dirs = [[0,1],[1,0],[1,1],[1,-1]]
  board.value[row][col] = color
  for (const [dr, dc] of dirs) {
    let count = 1
    for (let d = -1; d <= 1; d += 2) {
      let r = row + dr * d, c = col + dc * d
      while (r >= 0 && r < ROWS && c >= 0 && c < COLS && board.value[r][c] === color) {
        count++; r += dr * d; c += dc * d
      }
    }
    if (count >= 4) score += 100000
    else if (count === 3) score += 1000
    else if (count === 2) score += 100
  }
  board.value[row][col] = 0
  return score
}

function resetGame() {
  board.value = Array.from({ length: ROWS }, () => Array(COLS).fill(0))
  currentTurn.value = 1
  gameOver.value = false
  winner.value = 0
  isDraw.value = false
  winCells.value = []
}

function goBack() {
  router.push('/playground')
}

function isWinCell(r, c) {
  return winCells.value.some(([wr, wc]) => wr === r && wc === c)
}
</script>

<template>
  <div class="game-page space-theme">
    <div class="stars-bg"></div>
    <div class="game-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h2>四子棋</h2>
      <div class="mode-badge">{{ isOnline ? '联机' : '人机' }}</div>
    </div>
    <div v-if="isOnline && roomCode" class="room-badge">房间: {{ roomCode }}</div>
    <div class="status-bar">{{ statusText }}</div>
    <div class="cf-board">
      <template v-for="(row, r) in board" :key="r">
        <div v-for="(cell, c) in row" :key="`${r}-${c}`"
             class="cf-cell"
             :class="{ 'win-cell': isWinCell(r, c), 'disabled': isOnline && !isMyTurn }"
             @click="dropPiece(c)">
          <span v-if="cell === 1" class="piece red"></span>
          <span v-else-if="cell === 2" class="piece yellow"></span>
        </div>
      </template>
    </div>
    <div v-if="gameOver" class="game-over-overlay">
      <div class="game-over-card">
        <h3>{{ isDraw ? '平局' : (isOnline ? (winner === onlineMyColor ? '你赢了！' : '你输了！') : (winner === 1 ? '红方获胜！' : '黄方获胜！')) }}</h3>
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
  min-height: 100vh; background: linear-gradient(135deg, #0a0f1a 0%, #0f172a 50%, #0a0f1a 100%);
  padding: 12px 16px 24px; color: white; font-family: 'Segoe UI', sans-serif;
  display: flex; flex-direction: column; align-items: center;
}
.stars-bg {
  position: fixed; inset: 0;
  background-image: radial-gradient(2px 2px at 20px 30px, #fff, transparent), radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.8), transparent), radial-gradient(1px 1px at 90px 40px, #fff, transparent), radial-gradient(1px 1px at 130px 80px, rgba(255,255,255,0.6), transparent);
  background-size: 200px 120px; opacity: 0.35; pointer-events: none;
}
.game-header { position: relative; z-index: 1; display: flex; align-items: center; gap: 16px; width: 100%; max-width: 500px; margin-bottom: 12px; }
.back-btn { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); color: white; padding: 8px 14px; border-radius: 12px; cursor: pointer; font-size: 14px; }
.game-header h2 { flex: 1; margin: 0; font-size: 22px; }
.mode-badge { padding: 6px 14px; border-radius: 999px; background: rgba(56,189,248,0.2); color: #7dd3fc; font-size: 13px; }
.room-badge { position: relative; z-index: 1; text-align: center; color: rgba(255,255,255,0.5); font-size: 12px; font-family: 'Courier New', monospace; margin-bottom: 4px; }
.status-bar { position: relative; z-index: 1; text-align: center; padding: 6px; color: #7dd3fc; font-size: 14px; margin-bottom: 12px; }
.cf-board {
  position: relative; z-index: 1;
  display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px;
  padding: 16px; background: rgba(15,23,42,0.78); border: 1px solid rgba(255,255,255,0.1);
  border-radius: 18px; backdrop-filter: blur(18px);
}
.cf-cell {
  width: 52px; height: 52px; display: grid; place-items: center;
  background: rgba(255,255,255,0.04); border-radius: 50%; cursor: pointer; transition: background 0.15s;
}
.cf-cell:hover { background: rgba(56,189,248,0.1); }
.cf-cell.disabled { opacity: 0.5; cursor: not-allowed; }
.piece { width: 80%; height: 80%; border-radius: 50%; }
.piece.red { background: radial-gradient(circle at 35% 35%, #f87171, #dc2626); box-shadow: 0 2px 4px rgba(0,0,0,0.4); }
.piece.yellow { background: radial-gradient(circle at 35% 35%, #fde047, #eab308); box-shadow: 0 2px 4px rgba(0,0,0,0.4); }
.cf-cell.win-cell { background: rgba(34,197,94,0.3); }
.game-over-overlay { position: fixed; inset: 0; z-index: 10; display: grid; place-items: center; background: rgba(2,6,23,0.7); }
.game-over-card { background: #0f172a; border: 1px solid rgba(255,255,255,0.15); border-radius: 24px; padding: 32px; text-align: center; min-width: 280px; }
.game-over-card h3 { margin: 0 0 20px; font-size: 24px; }
.game-over-actions { display: flex; gap: 12px; justify-content: center; }
.action-btn { padding: 10px 20px; border-radius: 12px; border: none; font-weight: 700; cursor: pointer; font-size: 14px; }
.action-btn.primary { background: linear-gradient(135deg, #38bdf8, #60a5fa); color: #08111e; }
.action-btn.secondary { background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.15); }
.bottom-actions { position: relative; z-index: 1; margin-top: 16px; }
</style>
