<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { createArcadeWebSocket } from '../api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const SIZE = 8
const board = ref(initBoard())
const currentTurn = ref(1) // 1=Black, 2=White
const gameOver = ref(false)
const winner = ref(0)
const isPvE = ref(true)
const isOnline = ref(false)
const aiThinking = ref(false)
const onlineMyColor = ref(0)
const roomCode = ref('')
let ws = null

const username = computed(() => userStore.username || 'Player')

function initBoard() {
  const b = Array.from({ length: SIZE }, () => Array(SIZE).fill(0))
  b[3][3] = 2; b[3][4] = 1; b[4][3] = 1; b[4][4] = 2
  return b
}

const scores = computed(() => {
  let black = 0, white = 0
  for (const row of board.value) for (const c of row) {
    if (c === 1) black++
    else if (c === 2) white++
  }
  return { black, white }
})

const validMoves = computed(() => {
  const moves = []
  for (let r = 0; r < SIZE; r++)
    for (let c = 0; c < SIZE; c++)
      if (isValidMove(r, c, currentTurn.value)) moves.push([r, c])
  return moves
})

const isMyTurn = computed(() => {
  if (isPvE.value) return currentTurn.value === 1
  if (isOnline.value) return currentTurn.value === onlineMyColor.value
  return true
})

const statusText = computed(() => {
  if (gameOver.value) {
    if (scores.value.black === scores.value.white) return '平局！'
    if (isOnline.value) {
      const myScore = onlineMyColor.value === 1 ? scores.value.black : scores.value.white
      const oppScore = onlineMyColor.value === 1 ? scores.value.white : scores.value.black
      return myScore > oppScore ? '你赢了！' : '你输了！'
    }
    return scores.value.black > scores.value.white ? '黑方获胜！' : '白方获胜！'
  }
  if (isOnline.value) return isMyTurn.value ? '轮到你落子' : '等待对手...'
  if (aiThinking.value) return 'AI 思考中...'
  const turn = currentTurn.value === 1 ? '黑方' : '白方'
  return `${turn}落子 (${scores.value.black} : ${scores.value.white})`
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
    if (msg.moves && msg.moves.length > 0) {
      // Rebuild board from scratch
      board.value = initBoard()
      for (const m of msg.moves) {
        makeMoveOnline(m.row, m.col, m.color)
      }
      currentTurn.value = msg.moves.length % 2 === 0 ? 1 : 2
    }
  } else if (msg.type === 'move') {
    if (msg.username === username.value) return // skip own moves
    makeMoveOnline(msg.row, msg.col, msg.color)
    currentTurn.value = msg.color === 1 ? 2 : 1
    // Check game over after remote move
    checkGameEnd()
  } else if (msg.type === 'game_over') {
    gameOver.value = true
    winner.value = msg.winner
  }
}

function makeMoveOnline(row, col, color) {
  const opp = color === 1 ? 2 : 1
  const dirs = [[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]]
  const flipped = []
  for (const [dr, dc] of dirs) {
    const temp = []
    let r = row + dr, c = col + dc
    while (r >= 0 && r < SIZE && c >= 0 && c < SIZE && board.value[r][c] === opp) {
      temp.push([r, c]); r += dr; c += dc
    }
    if (temp.length > 0 && r >= 0 && r < SIZE && c >= 0 && c < SIZE && board.value[r][c] === color) {
      flipped.push(...temp)
    }
  }
  board.value[row][col] = color
  for (const [r, c] of flipped) board.value[r][c] = color
}

function isValidMove(row, col, color) {
  if (board.value[row][col] !== 0) return false
  const opp = color === 1 ? 2 : 1
  const dirs = [[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]]
  for (const [dr, dc] of dirs) {
    let r = row + dr, c = col + dc, found = false
    while (r >= 0 && r < SIZE && c >= 0 && c < SIZE && board.value[r][c] === opp) {
      r += dr; c += dc; found = true
    }
    if (found && r >= 0 && r < SIZE && c >= 0 && c < SIZE && board.value[r][c] === color) return true
  }
  return false
}

function makeMove(row, col, color) {
  const opp = color === 1 ? 2 : 1
  const dirs = [[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]]
  const flipped = []
  for (const [dr, dc] of dirs) {
    const temp = []
    let r = row + dr, c = col + dc
    while (r >= 0 && r < SIZE && c >= 0 && c < SIZE && board.value[r][c] === opp) {
      temp.push([r, c]); r += dr; c += dc
    }
    if (temp.length > 0 && r >= 0 && r < SIZE && c >= 0 && c < SIZE && board.value[r][c] === color) {
      flipped.push(...temp)
    }
  }
  board.value[row][col] = color
  for (const [r, c] of flipped) board.value[r][c] = color
}

function placePiece(row, col) {
  if (gameOver.value || aiThinking.value) return
  if (isOnline.value && !isMyTurn.value) return
  if (isPvE.value && currentTurn.value === 2) return
  if (!isValidMove(row, col, currentTurn.value)) return

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
    makeMoveOnline(row, col, color)
    currentTurn.value = color === 1 ? 2 : 1
    checkGameEnd()
    return
  }

  makeMove(row, col, currentTurn.value)
  nextTurn()
}

function checkGameEnd() {
  const opp = currentTurn.value === 1 ? 2 : 1
  let oppHas = false, curHas = false
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      if (isValidMove(r, c, opp)) oppHas = true
      if (isValidMove(r, c, currentTurn.value)) curHas = true
    }
  }
  if (!oppHas && !curHas) {
    gameOver.value = true
    if (isOnline.value && ws && ws.readyState === WebSocket.OPEN) {
      const myScore = onlineMyColor.value === 1 ? scores.value.black : scores.value.white
      const oppScore = onlineMyColor.value === 1 ? scores.value.white : scores.value.black
      ws.send(JSON.stringify({
        type: 'game_over',
        winner_color: myScore > oppScore ? onlineMyColor.value : (onlineMyColor.value === 1 ? 2 : 1),
        winner_name: myScore > oppScore ? username.value : 'opponent'
      }))
    }
  }
}

function nextTurn() {
  const opp = currentTurn.value === 1 ? 2 : 1
  let oppHasMove = false
  for (let r = 0; r < SIZE && !oppHasMove; r++)
    for (let c = 0; c < SIZE && !oppHasMove; c++)
      if (isValidMove(r, c, opp)) oppHasMove = true

  if (oppHasMove) {
    currentTurn.value = opp
    if (isPvE.value && opp === 2) aiTurn()
    return
  }

  let curHasMove = false
  for (let r = 0; r < SIZE && !curHasMove; r++)
    for (let c = 0; c < SIZE && !curHasMove; c++)
      if (isValidMove(r, c, currentTurn.value)) curHasMove = true

  if (curHasMove) {
    if (isPvE.value && currentTurn.value === 2) aiTurn()
    return
  }

  gameOver.value = true
}

function aiTurn() {
  aiThinking.value = true
  setTimeout(() => {
    const move = getAiMove()
    if (move) {
      makeMove(move[0], move[1], 2)
    }
    aiThinking.value = false
    nextTurn()
  }, 400)
}

function getAiMove() {
  const weights = [
    [120,-20,20,5,5,20,-20,120],
    [-20,-40,-5,-5,-5,-5,-40,-20],
    [20,-5,15,3,3,15,-5,20],
    [5,-5,3,3,3,3,-5,5],
    [5,-5,3,3,3,3,-5,5],
    [20,-5,15,3,3,15,-5,20],
    [-20,-40,-5,-5,-5,-5,-40,-20],
    [120,-20,20,5,5,20,-20,120]
  ]

  let bestScore = -Infinity
  let bestMove = null
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      if (!isValidMove(r, c, 2)) continue
      const savedBoard = board.value.map(row => [...row])
      makeMove(r, c, 2)
      let score = weights[r][c]
      score += (scores.value.white - scores.value.black) * 2
      board.value = savedBoard
      if (score > bestScore) { bestScore = score; bestMove = [r, c] }
    }
  }
  return bestMove
}

function resetGame() {
  board.value = initBoard()
  currentTurn.value = 1
  gameOver.value = false
  winner.value = 0
}

function goBack() {
  router.push('/playground')
}

function isValid(r, c) {
  return validMoves.value.some(([vr, vc]) => vr === r && vc === c)
}
</script>

<template>
  <div class="game-page space-theme">
    <div class="stars-bg"></div>
    <div class="game-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h2>黑白棋</h2>
      <div class="mode-badge">{{ isOnline ? '联机' : '人机' }}</div>
    </div>
    <div v-if="isOnline && roomCode" class="room-badge">房间: {{ roomCode }}</div>
    <div class="status-bar">{{ statusText }}</div>
    <div class="score-bar">
      <div class="score-item" :class="{ active: currentTurn === 1 }"><span class="stone black-stone-sm"></span> {{ scores.black }}</div>
      <div class="score-sep">:</div>
      <div class="score-item" :class="{ active: currentTurn === 2 }">{{ scores.white }} <span class="stone white-stone-sm"></span></div>
    </div>
    <div class="reversi-board">
      <template v-for="(row, r) in board" :key="r">
        <div v-for="(cell, c) in row" :key="`${r}-${c}`"
             class="reversi-cell"
             :class="{ 'valid': isValid(r, c) && !gameOver && !(isOnline && !isMyTurn) }"
             @click="placePiece(r, c)">
          <span v-if="cell === 1" class="piece black-p"></span>
          <span v-else-if="cell === 2" class="piece white-p"></span>
          <span v-else-if="isValid(r, c) && !gameOver && !(isOnline && !isMyTurn)" class="hint-dot"></span>
        </div>
      </template>
    </div>
    <div v-if="gameOver" class="game-over-overlay">
      <div class="game-over-card">
        <h3>{{ statusText }}</h3>
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
.status-bar { position: relative; z-index: 1; text-align: center; padding: 6px; color: #7dd3fc; font-size: 14px; margin-bottom: 6px; }
.score-bar { position: relative; z-index: 1; display: flex; align-items: center; gap: 16px; margin-bottom: 12px; font-size: 24px; font-weight: 700; }
.score-item { display: flex; align-items: center; gap: 8px; transition: opacity 0.2s; opacity: 0.6; }
.score-item.active { opacity: 1; }
.score-sep { color: rgba(255,255,255,0.4); }
.stone { display: inline-block; width: 20px; height: 20px; border-radius: 50%; }
.black-stone-sm { background: radial-gradient(circle at 35% 35%, #555, #111); }
.white-stone-sm { background: radial-gradient(circle at 35% 35%, #fff, #ccc); }
.reversi-board {
  position: relative; z-index: 1;
  display: grid; grid-template-columns: repeat(8, 1fr); gap: 2px;
  padding: 12px; background: #065f46; border: 2px solid rgba(255,255,255,0.1); border-radius: 16px;
}
.reversi-cell {
  width: 48px; height: 48px; display: grid; place-items: center;
  background: #047857; cursor: pointer; transition: background 0.15s;
}
.reversi-cell.valid:hover { background: #10b981; }
.piece { width: 80%; height: 80%; border-radius: 50%; }
.black-p { background: radial-gradient(circle at 35% 35%, #555, #111); box-shadow: 1px 1px 3px rgba(0,0,0,0.5); }
.white-p { background: radial-gradient(circle at 35% 35%, #fff, #ccc); box-shadow: 1px 1px 3px rgba(0,0,0,0.3); }
.hint-dot { width: 10px; height: 10px; border-radius: 50%; background: rgba(255,255,255,0.2); }
.game-over-overlay { position: fixed; inset: 0; z-index: 10; display: grid; place-items: center; background: rgba(2,6,23,0.7); }
.game-over-card { background: #0f172a; border: 1px solid rgba(255,255,255,0.15); border-radius: 24px; padding: 32px; text-align: center; min-width: 280px; }
.game-over-card h3 { margin: 0 0 20px; font-size: 24px; }
.game-over-actions { display: flex; gap: 12px; justify-content: center; }
.action-btn { padding: 10px 20px; border-radius: 12px; border: none; font-weight: 700; cursor: pointer; font-size: 14px; }
.action-btn.primary { background: linear-gradient(135deg, #38bdf8, #60a5fa); color: #08111e; }
.action-btn.secondary { background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.15); }
.bottom-actions { position: relative; z-index: 1; margin-top: 16px; }
</style>
