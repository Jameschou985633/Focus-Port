<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { getBestMove } from '../utils/gomokuAI'
import { gomokuApi, createGomokuWebSocket, createArcadeWebSocket } from '../api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const SIZE = 15
const board = ref(Array.from({ length: SIZE }, () => Array(SIZE).fill(0)))
const currentTurn = ref(1) // 1=black, 2=white
const gameOver = ref(false)
const winner = ref(0)
const isDraw = ref(false)
const lastMove = ref(null)
const winLine = ref([])

// Player info
const playerBlack = ref('')
const playerWhite = ref('')
const playerColor = ref(1) // 1=black(player), 2=white(player) in PvE
const isPvE = ref(false)
const isOnline = ref(false)
const isAiThinking = ref(false)
const difficulty = ref('hard')

// Online WebSocket
let ws = null
let aiTimeoutId = null
const onlineRoomCode = ref('')
const onlineMyColor = ref(0)

// First-hand choice for PvE
const firstChoice = ref('player') // 'player', 'ai', 'random'

const username = computed(() => userStore.username || 'Player')

// Computed display helpers
const aiColor = computed(() => playerColor.value === 1 ? 2 : 1)

const isMyTurn = computed(() => {
  if (isPvE.value) return currentTurn.value === playerColor.value
  if (isOnline.value) return currentTurn.value === onlineMyColor.value
  return false
})

const isAiTurn = computed(() => {
  return isPvE.value && currentTurn.value === aiColor.value && !gameOver.value
})

const leftName = computed(() => {
  if (isPvE.value) return username.value
  return onlineMyColor.value === 1 ? username.value : (playerBlack.value || '对手')
})

const rightName = computed(() => {
  if (isPvE.value) return 'AI'
  return onlineMyColor.value === 2 ? username.value : (playerWhite.value || '对手')
})

const leftStone = computed(() => {
  if (isPvE.value) return playerColor.value === 1 ? '⬤' : '○'
  return onlineMyColor.value === 1 ? '⬤' : '○'
})

const rightStone = computed(() => {
  if (isPvE.value) return playerColor.value === 1 ? '○' : '⬤'
  return onlineMyColor.value === 1 ? '○' : '⬤'
})

const leftColorIdx = computed(() => {
  if (isPvE.value) return playerColor.value
  return onlineMyColor.value
})

const rightColorIdx = computed(() => {
  if (isPvE.value) return aiColor.value
  return onlineMyColor.value === 1 ? 2 : 1
})

const statusText = computed(() => {
  if (gameOver.value) {
    if (isDraw.value) return '平局！'
    if (winner.value === 0) return ''
    const winnerName = winner.value === leftColorIdx.value ? leftName.value : rightName.value
    return `${winnerName} 获胜！`
  }
  if (isAiThinking.value) return 'AI 思考中...'
  if (isPvE.value) return isMyTurn.value ? '轮到你落子' : 'AI 回合'
  return isMyTurn.value ? '轮到你落子' : '等待对手...'
})

// Initialize
onMounted(() => {
  if (route.params.roomCode) {
    // New arcade online mode (via /playground/gomoku/online/:roomCode)
    isOnline.value = true
    onlineRoomCode.value = route.params.roomCode
    onlineMyColor.value = 1
    initArcadeOnline(route.params.roomCode)
  } else if (route.params.id) {
    isOnline.value = true
    initOnlineGame(route.params.id)
  } else {
    // Default: PvE
    isPvE.value = true
    const first = route.query.first || 'player'
    firstChoice.value = first
    difficulty.value = route.query.difficulty || 'hard'
    initFirstChoice(first)
    initPlayerNames()
    if (aiColor.value === 1) {
      aiTimeoutId = setTimeout(() => aiMove(), 300)
    }
  }

  // Endgame export listener
  window.addEventListener('keydown', onKeyDown)
})

onUnmounted(() => {
  if (aiTimeoutId) clearTimeout(aiTimeoutId)
  if (ws) ws.close()
  window.removeEventListener('keydown', onKeyDown)
})

function initFirstChoice(first) {
  if (first === 'player') {
    playerColor.value = 1 // Player is black (goes first)
  } else if (first === 'ai') {
    playerColor.value = 2 // Player is white (AI goes first)
  } else {
    // Random
    playerColor.value = Math.random() < 0.5 ? 1 : 2
  }
  currentTurn.value = 1 // Black always goes first in gomoku
}

function initPlayerNames() {
  if (playerColor.value === 1) {
    playerBlack.value = username.value
    playerWhite.value = 'AI'
  } else {
    playerBlack.value = 'AI'
    playerWhite.value = username.value
  }
}

async function initOnlineGame(roomId) {
  try {
    const res = await gomokuApi.get(roomId)
    const data = res.data
    onlineRoomCode.value = data.room_code || roomId

    // Determine my color
    if (data.player_black === username.value) {
      onlineMyColor.value = 1
      playerBlack.value = username.value
      playerWhite.value = data.player_white || '等待中...'
    } else {
      onlineMyColor.value = 2
      playerBlack.value = data.player_black || '等待中...'
      playerWhite.value = username.value
    }

    // Restore board state
    if (data.moves) {
      for (const move of data.moves) {
        board.value[move.row][move.col] = move.color
      }
      currentTurn.value = data.moves.length % 2 === 0 ? 1 : 2
    }

    // Connect WebSocket
    ws = createGomokuWebSocket(roomId)
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        handleOnlineMessage(msg)
      } catch (err) {
        console.error('WebSocket parse error:', err)
      }
    }
  } catch (err) {
    console.error('Failed to load game:', err)
  }
}

function initArcadeOnline(roomCodeStr) {
  ws = createArcadeWebSocket(roomCodeStr)
  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data)
      handleArcadeMessage(msg)
    } catch (err) {
      console.error('Arcade WS parse error:', err)
    }
  }
}

function handleArcadeMessage(msg) {
  if (msg.type === 'sync') {
    if (msg.player_host === username.value) {
      onlineMyColor.value = 1
      playerBlack.value = username.value
      playerWhite.value = msg.player_guest || '等待中...'
    } else {
      onlineMyColor.value = 2
      playerBlack.value = msg.player_host || '等待中...'
      playerWhite.value = username.value
    }
    if (msg.moves) {
      for (const m of msg.moves) {
        board.value[m.row][m.col] = m.color
      }
      currentTurn.value = msg.moves.length % 2 === 0 ? 1 : 2
    }
  } else if (msg.type === 'move') {
    if (msg.username === username.value) return // skip own moves (already applied locally)
    board.value[msg.row][msg.col] = msg.color
    lastMove.value = { row: msg.row, col: msg.col }
    currentTurn.value = msg.color === 1 ? 2 : 1
    checkGameState(msg.row, msg.col, msg.color)
  } else if (msg.type === 'game_over') {
    gameOver.value = true
    winner.value = msg.winner
  }
}

function handleOnlineMessage(msg) {
  if (msg.type === 'move') {
    board.value[msg.row][msg.col] = msg.color
    lastMove.value = { row: msg.row, col: msg.col }
    currentTurn.value = msg.color === 1 ? 2 : 1
    checkGameState(msg.row, msg.col, msg.color)
  } else if (msg.type === 'game_over') {
    gameOver.value = true
    winner.value = msg.winner
  } else if (msg.type === 'player_joined') {
    if (msg.player_black) playerBlack.value = msg.player_black
    if (msg.player_white) playerWhite.value = msg.player_white
  }
}

// Game logic
function placeStone(row, col) {
  if (board.value[row][col] !== 0 || gameOver.value) return
  if (isPvE.value && !isMyTurn.value) return
  if (isOnline.value && !isMyTurn.value) return

  const color = isOnline.value ? onlineMyColor.value : currentTurn.value

  if (isOnline.value) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    const payload = {
      type: 'move',
      row,
      col,
      color: onlineMyColor.value,
      username: username.value
    }
    if (route.params.id) {
      payload.game_id = route.params.id
    }
    ws.send(JSON.stringify(payload))
    // Apply locally for arcade mode (roomCode route)
    if (route.params.roomCode) {
      board.value[row][col] = color
      lastMove.value = { row, col }
      currentTurn.value = color === 1 ? 2 : 1
      checkGameState(row, col, color)
      if (gameOver.value) {
        ws.send(JSON.stringify({
          type: 'game_over',
          winner_color: color,
          winner_name: username.value
        }))
      }
    }
    return
  }

  board.value[row][col] = color
  lastMove.value = { row, col }
  currentTurn.value = color === 1 ? 2 : 1

  checkGameState(row, col, color)

  // Trigger AI
  if (isPvE.value && !gameOver.value && isAiTurn.value) {
    aiMove()
  }
}

function checkGameState(row, col, color) {
  if (checkWin(row, col, color)) {
    gameOver.value = true
    winner.value = color
    return
  }
  // Check draw
  let hasEmpty = false
  for (let r = 0; r < SIZE && !hasEmpty; r++)
    for (let c = 0; c < SIZE && !hasEmpty; c++)
      if (board.value[r][c] === 0) hasEmpty = true
  if (!hasEmpty) {
    gameOver.value = true
    isDraw.value = true
  }
}

function checkWin(row, col, color) {
  const dirs = [[1, 0], [0, 1], [1, 1], [1, -1]]
  for (const [dr, dc] of dirs) {
    let count = 1
    let cells = [[row, col]]
    for (let d = -1; d <= 1; d += 2) {
      let r = row + dr * d, c = col + dc * d
      while (r >= 0 && r < SIZE && c >= 0 && c < SIZE && board.value[r][c] === color) {
        count++; cells.push([r, c]); r += dr * d; c += dc * d
      }
    }
    if (count >= 5) {
      winLine.value = cells
      return true
    }
  }
  return false
}

function aiMove() {
  if (gameOver.value) return
  isAiThinking.value = true

  aiTimeoutId = setTimeout(() => {
    if (gameOver.value) { isAiThinking.value = false; return }
    const [row, col] = getBestMove(board.value, aiColor.value, difficulty.value)
    board.value[row][col] = aiColor.value
    lastMove.value = { row, col }
    currentTurn.value = playerColor.value
    isAiThinking.value = false

    checkGameState(row, col, aiColor.value)
  }, 200)
}

function resetGame() {
  if (aiTimeoutId) clearTimeout(aiTimeoutId)
  board.value = Array.from({ length: SIZE }, () => Array(SIZE).fill(0))
  currentTurn.value = 1
  gameOver.value = false
  winner.value = 0
  isDraw.value = false
  lastMove.value = null
  winLine.value = []

  if (isPvE.value) {
    // Re-randomize if random mode
    if (firstChoice.value === 'random') {
      initFirstChoice('random')
      initPlayerNames()
    }
    if (aiColor.value === 1) {
      aiTimeoutId = setTimeout(() => aiMove(), 300)
    }
  }
}

function goBack() {
  router.push('/playground')
}

// Endgame export (press E)
function onKeyDown(e) {
  if (e.key === 'e' || e.key === 'E') {
    if (gameOver.value || lastMove.value) {
      const data = {
        board: board.value.map(row => [...row]),
        currentTurn: currentTurn.value,
        lastMove: lastMove.value,
        playerColor: playerColor.value,
        aiColor: aiColor.value,
        winner: winner.value
      }
      console.log('=== 棋局导出 ===')
      console.log(JSON.stringify(data))
      console.table(
        board.value.map((row, r) =>
          row.reduce((acc, v, c) => ({ ...acc, [c]: v }), { _: r })
        )
      )
      navigator.clipboard?.writeText(JSON.stringify(data))
    }
  }
}

// Star points for display
const starPoints = [[3,3],[3,7],[3,11],[7,3],[7,7],[7,11],[11,3],[11,7],[11,11]]
function isStarPoint(r, c) {
  return starPoints.some(([sr, sc]) => sr === r && sc === c)
}
</script>

<template>
  <div class="gomoku-room space-theme">
    <div class="stars-bg"></div>

    <div class="game-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h2>五子棋</h2>
      <div class="mode-badge">{{ isPvE ? '人机' : '联机' }}</div>
    </div>

    <div class="player-bar">
      <div class="player-card" :class="{ active: currentTurn === leftColorIdx && !gameOver }">
        <span class="stone-icon" :class="leftColorIdx === 1 ? 'black' : 'white'">{{ leftStone }}</span>
        <span class="player-name">{{ leftName }}</span>
      </div>
      <div class="vs-text">VS</div>
      <div class="player-card" :class="{ active: currentTurn === rightColorIdx && !gameOver }">
        <span class="stone-icon" :class="rightColorIdx === 1 ? 'black' : 'white'">{{ rightStone }}</span>
        <span class="player-name">{{ rightName }}</span>
      </div>
    </div>

    <div class="status-bar">{{ statusText }}</div>

    <div class="board-container">
      <div class="board">
        <template v-for="(row, r) in board" :key="r">
          <div v-for="(cell, c) in row" :key="`${r}-${c}`"
               class="cell"
               :class="{
                 'has-stone': cell !== 0,
                 'last-move': lastMove?.row === r && lastMove?.col === c,
                 'win-cell': winLine.some(([wr, wc]) => wr === r && wc === c),
                 'star-point': isStarPoint(r, c)
               }"
               @click="placeStone(r, c)">
            <span v-if="cell === 1" class="stone black-stone"></span>
            <span v-else-if="cell === 2" class="stone white-stone"></span>
            <span v-else-if="isStarPoint(r, c)" class="star-dot"></span>
          </div>
        </template>
      </div>
    </div>

    <div v-if="gameOver" class="game-over-overlay">
      <div class="game-over-card">
        <h3>{{ isDraw ? '平局' : (winner === leftColorIdx ? leftName : rightName) + ' 获胜！' }}</h3>
        <div class="game-over-actions">
          <button class="action-btn primary" @click="resetGame">再来一局</button>
          <button class="action-btn secondary" @click="goBack">返回</button>
        </div>
      </div>
    </div>

    <div v-if="!gameOver" class="bottom-actions">
      <button class="action-btn secondary" @click="resetGame">重新开始</button>
    </div>
  </div>
</template>

<style scoped>
.gomoku-room.space-theme {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0f1a 0%, #0f172a 50%, #0a0f1a 100%);
  padding: 12px 16px 24px;
  color: white;
  font-family: 'Segoe UI', sans-serif;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stars-bg {
  position: fixed;
  inset: 0;
  background-image:
    radial-gradient(2px 2px at 20px 30px, #fff, transparent),
    radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.8), transparent),
    radial-gradient(1px 1px at 90px 40px, #fff, transparent),
    radial-gradient(1px 1px at 130px 80px, rgba(255,255,255,0.6), transparent);
  background-size: 200px 120px;
  opacity: 0.35;
  pointer-events: none;
}

.game-header {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
  max-width: 680px;
  margin-bottom: 12px;
}

.back-btn {
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  color: white;
  padding: 8px 14px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 14px;
}

.game-header h2 {
  flex: 1;
  margin: 0;
  font-size: 22px;
}

.mode-badge {
  padding: 6px 14px;
  border-radius: 999px;
  background: rgba(56, 189, 248, 0.2);
  color: #7dd3fc;
  font-size: 13px;
}

.player-bar {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  max-width: 680px;
  margin-bottom: 8px;
}

.player-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255,255,255,0.08);
  transition: all 0.2s;
}

.player-card.active {
  border-color: #38bdf8;
  background: rgba(56, 189, 248, 0.1);
}

.stone-icon {
  font-size: 20px;
}

.stone-icon.black { color: #333; text-shadow: 0 0 4px rgba(255,255,255,0.5); }
.stone-icon.white { color: #eee; }

.player-name {
  font-weight: 600;
  font-size: 15px;
}

.vs-text {
  color: rgba(255,255,255,0.4);
  font-size: 14px;
  font-weight: 700;
}

.status-bar {
  position: relative;
  z-index: 1;
  text-align: center;
  padding: 6px;
  color: #7dd3fc;
  font-size: 14px;
  margin-bottom: 8px;
}

.board-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 680px;
}

.board {
  display: grid;
  grid-template-columns: repeat(15, 1fr);
  gap: 0;
  padding: 8px 4px 16px;
  background: rgba(15, 23, 42, 0.78);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 18px;
  backdrop-filter: blur(18px);
  aspect-ratio: 1;
}

.cell {
  position: relative;
  display: grid;
  place-items: center;
  cursor: pointer;
  border: 1px solid rgba(255,255,255,0.06);
  aspect-ratio: 1;
}

.cell:hover:not(.has-stone) {
  background: rgba(56, 189, 248, 0.08);
}

.stone {
  width: 82%;
  height: 82%;
  border-radius: 50%;
  display: block;
}

.black-stone {
  background: radial-gradient(circle at 35% 35%, #555, #111);
  box-shadow: 1px 1px 3px rgba(0,0,0,0.6);
}

.white-stone {
  background: radial-gradient(circle at 35% 35%, #fff, #ccc);
  box-shadow: 1px 1px 3px rgba(0,0,0,0.3);
}

.star-dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: rgba(255,255,255,0.3);
}

.cell.last-move .stone {
  box-shadow: 0 0 8px 2px rgba(251, 191, 36, 0.7);
}

.cell.win-cell {
  background: rgba(34, 197, 94, 0.2);
}

.game-over-overlay {
  position: fixed;
  inset: 0;
  z-index: 10;
  display: grid;
  place-items: center;
  background: rgba(2, 6, 23, 0.7);
}

.game-over-card {
  background: #0f172a;
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 24px;
  padding: 32px;
  text-align: center;
  min-width: 280px;
}

.game-over-card h3 {
  margin: 0 0 20px;
  font-size: 24px;
}

.game-over-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
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

.bottom-actions {
  position: relative;
  z-index: 1;
  margin-top: 12px;
}
</style>
