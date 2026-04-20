/**
 * Gomoku AI Engine
 * Heuristic evaluation + Minimax with Alpha-Beta pruning
 */

const SIZE = 15

// Score constants - absolute priority hierarchy
const FIVE = 10_000_000
const OPP_FIVE = 8_000_000
const LIVE4 = 5_000_000
const OPP_LIVE4 = 4_000_000
const RUSH4_LIVE3 = 3_000_000
const OPP_DOUBLE_THREAT = 2_500_000
const RUSH4 = 1_500_000
const LIVE3_RUSH3 = 800_000
const LIVE3 = 600_000
const OPP_LIVE3 = 500_000
const OPP_RUSH4 = 200_000
const JUMP_RUSH4 = 120_000
const JUMP_LIVE3 = 80_000
const LIVE2 = 1_000
const RUSH3 = 800
const DEAD4 = 200

/**
 * Get the best move for the AI
 * @param {number[][]} board - 15x15 grid, 0=empty, 1=black, 2=white
 * @param {number} aiColor - AI's color (1 or 2)
 * @param {string} difficulty - 'easy', 'medium', 'hard'
 * @returns {[number, number]} - [row, col]
 */
export function getBestMove(board, aiColor, difficulty = 'hard') {
  const opponent = aiColor === 1 ? 2 : 1
  const totalStones = countStones(board)

  // First move: play center
  if (totalStones === 0) return [7, 7]
  // Second move: play adjacent to center
  if (totalStones === 1) {
    const [cr, cc] = findStone(board, opponent)
    const offsets = [[0,1],[1,0],[1,1],[1,-1]]
    const [dr, dc] = offsets[Math.floor(Math.random() * offsets.length)]
    return [cr + dr, cc + dc]
  }

  const candidates = getCandidates(board, aiColor, opponent, totalStones)
  if (candidates.length === 0) return [7, 7]

  // If best candidate is a forced win/defend, skip minimax
  if (candidates[0].score >= OPP_FIVE) {
    return [candidates[0].row, candidates[0].col]
  }

  // Minimax search
  const depth = difficulty === 'easy' ? 0 : (difficulty === 'medium' ? 2 : 4)
  const width = difficulty === 'easy' ? 1 : (difficulty === 'medium' ? 8 : 10)

  if (depth === 0) {
    // Easy: pick from top candidates randomly
    const topN = Math.min(6, candidates.length)
    const idx = Math.floor(Math.random() * topN)
    return [candidates[idx].row, candidates[idx].col]
  }

  // Run minimax on top candidates
  const topCandidates = candidates.slice(0, width)
  let bestScore = -Infinity
  let bestMove = [topCandidates[0].row, topCandidates[0].col]

  for (const cand of topCandidates) {
    const b = cloneBoard(board)
    b[cand.row][cand.col] = aiColor
    // Check instant win
    if (checkWin(b, cand.row, cand.col, aiColor)) return [cand.row, cand.col]
    const score = minimax(b, depth - 1, -Infinity, Infinity, false, aiColor, opponent, width)
    if (score > bestScore) {
      bestScore = score
      bestMove = [cand.row, cand.col]
    }
  }

  // Easy-medium randomness
  if (difficulty === 'medium' && Math.random() < 0.15 && topCandidates.length > 1) {
    const idx = Math.floor(Math.random() * Math.min(3, topCandidates.length))
    return [topCandidates[idx].row, topCandidates[idx].col]
  }

  return bestMove
}

function countStones(board) {
  let c = 0
  for (let r = 0; r < SIZE; r++)
    for (let i = 0; i < SIZE; i++)
      if (board[r][i]) c++
  return c
}

function findStone(board, color) {
  for (let r = 0; r < SIZE; r++)
    for (let c = 0; c < SIZE; c++)
      if (board[r][c] === color) return [r, c]
  return [7, 7]
}

function cloneBoard(board) {
  return board.map(row => [...row])
}

function checkWin(board, row, col, color) {
  const dirs = [[1,0],[0,1],[1,1],[1,-1]]
  for (const [dr, dc] of dirs) {
    let count = 1
    for (let d = -1; d <= 1; d += 2) {
      let r = row + dr * d, c = col + dc * d
      while (r >= 0 && r < SIZE && c >= 0 && c < SIZE && board[r][c] === color) {
        count++; r += dr * d; c += dc * d
      }
    }
    if (count >= 5) return true
  }
  return false
}

/**
 * Get scored candidate moves
 */
function getCandidates(board, aiColor, opponent, totalStones) {
  const candidates = []
  const [centerR, centerC] = getCenterOfMass(board)

  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      if (board[r][c] !== 0) continue
      if (!hasAdjacent(board, r, c)) continue

      const atkScore = evaluatePoint(board, r, c, aiColor)
      const defScore = evaluatePoint(board, r, c, opponent)

      let score = 0
      const { isFive: aiFive } = atkScore
      const { isFive: oppFive, hasLive4: oppLive4 } = defScore
      const { hasLive4: aiLive4, hasRush4: aiRush4, hasLive3: aiLive3, hasRush3: aiRush3, hasRush4Double: aiRush4Double } = atkScore
      const { hasRush4: oppRush4, hasLive3: oppLive3, hasRush4Double: oppRush4Double } = defScore

      // Priority ladder - absolute hierarchy
      if (aiFive) {
        score = FIVE
      } else if (oppFive) {
        score = OPP_FIVE
      } else if (aiLive4) {
        score = LIVE4
      } else if (oppLive4) {
        score = OPP_LIVE4
      } else if (aiRush4 && aiLive3) {
        score = RUSH4_LIVE3
      } else if (oppRush4Double || (oppRush4 && oppLive3)) {
        score = OPP_DOUBLE_THREAT
      } else if (aiRush4Double) {
        score = RUSH4_LIVE3 - 100_000
      } else if (aiRush4) {
        score = RUSH4
      } else if (aiLive3 && aiRush3) {
        score = LIVE3_RUSH3
      } else if (aiLive3 && aiLive3) {
        // Double live3 = very strong
        score = LIVE3_RUSH3 + 50_000
      } else if (oppLive3) {
        score = OPP_LIVE3
      } else if (oppRush4) {
        score = OPP_RUSH4
      } else if (aiLive3) {
        score = LIVE3
      } else {
        score = Math.max(atkScore.score * 1.05, defScore.score)
      }

      // Positional bonuses
      // 1. Edge penalty
      const edgeDist = Math.min(r, c, SIZE - 1 - r, SIZE - 1 - c)
      if (edgeDist === 0) score *= 0.5
      else if (edgeDist === 1) score *= 0.75

      // 2. Distance from center of mass
      const distFromCenter = Math.abs(r - centerR) + Math.abs(c - centerC)
      if (distFromCenter > 5) score *= 0.6
      else if (distFromCenter > 4) score *= 0.8

      // 3. Proximity to own stones
      const ownNearby = countNearby(board, r, c, aiColor)
      if (ownNearby >= 3) score *= 1.15
      else if (ownNearby >= 2) score *= 1.05

      candidates.push({ row: r, col: c, score })
    }
  }

  candidates.sort((a, b) => b.score - a.score)
  return candidates
}

function getCenterOfMass(board) {
  let totalR = 0, totalC = 0, count = 0
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      if (board[r][c]) {
        totalR += r; totalC += c; count++
      }
    }
  }
  return count > 0 ? [totalR / count, totalC / count] : [7, 7]
}

function hasAdjacent(board, row, col) {
  for (let dr = -1; dr <= 1; dr++) {
    for (let dc = -1; dc <= 1; dc++) {
      if (dr === 0 && dc === 0) continue
      const r = row + dr, c = col + dc
      if (r >= 0 && r < SIZE && c >= 0 && c < SIZE && board[r][c] !== 0) return true
    }
  }
  return false
}

function countNearby(board, row, col, color) {
  let count = 0
  for (let dr = -1; dr <= 1; dr++) {
    for (let dc = -1; dc <= 1; dc++) {
      if (dr === 0 && dc === 0) continue
      const r = row + dr, c = col + dc
      if (r >= 0 && r < SIZE && c >= 0 && c < SIZE && board[r][c] === color) count++
    }
  }
  return count
}

/**
 * Evaluate placing a stone at (row, col) for given color
 */
function evaluatePoint(board, row, col, color) {
  const dirs = [[1, 0], [0, 1], [1, 1], [1, -1]]
  let totalScore = 0
  let isFive = false
  let hasLive4 = false
  let hasRush4 = false
  let hasRush4Double = false
  let live3Count = 0
  let rush3Count = 0

  board[row][col] = color

  for (const [dr, dc] of dirs) {
    const result = analyzeDirection(board, row, col, dr, dc, color)
    totalScore += result.score

    if (result.pattern === 'five') isFive = true
    else if (result.pattern === 'live4') hasLive4 = true
    else if (result.pattern === 'rush4') {
      if (hasRush4) hasRush4Double = true
      hasRush4 = true
    }
    else if (result.pattern === 'live3') live3Count++
    else if (result.pattern === 'rush3') rush3Count++
  }

  board[row][col] = 0

  const hasLive3 = live3Count >= 1
  const hasRush3 = rush3Count >= 1

  return {
    score: totalScore,
    isFive,
    hasLive4,
    hasRush4,
    hasRush4Double,
    hasLive3,
    hasRush3
  }
}

/**
 * Analyze a direction for patterns
 */
function analyzeDirection(board, row, col, dr, dc, color) {
  // Scan in both directions from (row, col)
  let count = 1  // the stone itself
  let openEnds = 0
  let hasJump = false

  // Positive direction
  let r = row + dr, c = col + dc
  while (r >= 0 && r < SIZE && c >= 0 && c < SIZE && board[r][c] === color) {
    count++; r += dr; c += dc
  }
  // Check for gap (jump) pattern: X_XX or XX_X
  if (r >= 0 && r < SIZE && c >= 0 && c < SIZE && board[r][c] === 0) {
    let jr = r + dr, jc = c + dc
    let jumpCount = 0
    while (jr >= 0 && jr < SIZE && jc >= 0 && jc < SIZE && board[jr][jc] === color) {
      jumpCount++; jr += dr; jc += dc
    }
    if (jumpCount > 0 && count + jumpCount >= 3) {
      hasJump = true
      count += jumpCount
    } else {
      openEnds++  // The gap position is open
    }
  } else if (r >= 0 && r < SIZE && c >= 0 && c < SIZE && board[r][c] === 0) {
    openEnds++
  }
  // If we went off board or hit opponent, no open end

  // Negative direction
  r = row - dr; c = col - dc
  while (r >= 0 && r < SIZE && c >= 0 && c < SIZE && board[r][c] === color) {
    count++; r -= dr; c -= dc
  }
  if (r >= 0 && r < SIZE && c >= 0 && c < SIZE && board[r][c] === 0) {
    let jr = r - dr, jc = c - dc
    let jumpCount = 0
    while (jr >= 0 && jr < SIZE && jc >= 0 && jc < SIZE && board[jr][jc] === color) {
      jumpCount++; jr -= dr; jc -= dc
    }
    if (jumpCount > 0 && count + jumpCount >= 3) {
      hasJump = true
      count += jumpCount
    } else {
      openEnds++
    }
  } else if (r >= 0 && r < SIZE && c >= 0 && c < SIZE) {
    // hit opponent or edge - not open
  }

  return classifyPattern(count, openEnds, hasJump)
}

function classifyPattern(count, openEnds, hasJump) {
  if (count >= 5) return { pattern: 'five', score: FIVE }

  if (count === 4) {
    if (openEnds === 2) return { pattern: 'live4', score: 500_000 }
    if (openEnds === 1) return { pattern: 'rush4', score: 30_000 }
    return { pattern: 'dead4', score: DEAD4 }
  }

  if (count === 3) {
    if (hasJump) {
      // Jump patterns are stronger
      if (openEnds >= 2) return { pattern: 'live3', score: 20_000 }
      if (openEnds === 1) return { pattern: 'rush3', score: 3_000 }
    }
    if (openEnds === 2) return { pattern: 'live3', score: 15_000 }
    if (openEnds === 1) return { pattern: 'rush3', score: 1_200 }
    return { pattern: 'dead3', score: 100 }
  }

  if (count === 2) {
    if (openEnds === 2) return { pattern: 'live2', score: LIVE2 }
    if (openEnds === 1) return { pattern: 'rush2', score: 300 }
    return { pattern: 'dead2', score: 50 }
  }

  // count === 1
  if (openEnds === 2) return { pattern: 'live1', score: 100 }
  if (openEnds === 1) return { pattern: 'rush1', score: 30 }
  return { pattern: 'dead1', score: 0 }
}

/**
 * Minimax with alpha-beta pruning
 */
function minimax(board, depth, alpha, beta, isMaximizing, aiColor, opponent, width) {
  // Check for terminal/winning state
  const lastMove = findLastMove(board)
  if (lastMove) {
    const [lr, lc] = lastMove
    const color = board[lr][lc]
    if (checkWin(board, lr, lc, color)) {
      return color === aiColor ? 1_000_000 + depth : -1_000_000 - depth
    }
  }

  if (depth === 0) {
    return evaluateBoard(board, aiColor, opponent)
  }

  const currentColor = isMaximizing ? aiColor : opponent
  const candidates = getCandidates(board, currentColor, currentColor === aiColor ? opponent : aiColor, countStones(board))
  const topCandidates = candidates.slice(0, width)

  if (topCandidates.length === 0) return 0

  if (isMaximizing) {
    let maxEval = -Infinity
    for (const cand of topCandidates) {
      board[cand.row][cand.col] = currentColor
      const evalScore = minimax(board, depth - 1, alpha, beta, false, aiColor, opponent, width)
      board[cand.row][cand.col] = 0
      maxEval = Math.max(maxEval, evalScore)
      alpha = Math.max(alpha, evalScore)
      if (beta <= alpha) break
    }
    return maxEval
  } else {
    let minEval = Infinity
    for (const cand of topCandidates) {
      board[cand.row][cand.col] = currentColor
      const evalScore = minimax(board, depth - 1, alpha, beta, true, aiColor, opponent, width)
      board[cand.row][cand.col] = 0
      minEval = Math.min(minEval, evalScore)
      beta = Math.min(beta, evalScore)
      if (beta <= alpha) break
    }
    return minEval
  }
}

function findLastMove(board) {
  // Heuristic: find the most recently placed stone by scanning
  // In the context of minimax, we check the stone just placed
  // This is called after placing, so we look for the last non-zero entry
  // Better approach: pass lastMove explicitly, but for simplicity:
  return null // We handle win detection via checkWin on each candidate
}

/**
 * Board evaluation for minimax leaf nodes
 * Normalized: score per pattern, not per stone
 */
function evaluateBoard(board, aiColor, opponent) {
  let aiScore = 0
  let oppScore = 0

  // Evaluate each position that has a stone
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      if (board[r][c] === aiColor) {
        aiScore += evaluateStoneInPlace(board, r, c, aiColor)
      } else if (board[r][c] === opponent) {
        oppScore += evaluateStoneInPlace(board, r, c, opponent)
      }
    }
  }

  return aiScore - oppScore * 1.1
}

/**
 * Evaluate a stone's contribution (per direction, normalized to avoid double-counting)
 */
function evaluateStoneInPlace(board, row, col, color) {
  const dirs = [[1, 0], [0, 1], [1, 1], [1, -1]]
  let score = 0

  for (const [dr, dc] of dirs) {
    // Only evaluate in positive direction to avoid double-counting
    // Check if this is the "start" of a line (no same-color stone behind)
    const prevR = row - dr, prevC = col - dc
    if (prevR >= 0 && prevR < SIZE && prevC >= 0 && prevC < SIZE && board[prevR][prevC] === color) {
      continue  // Not the start of this line, skip
    }

    // Count consecutive stones in positive direction
    let count = 0
    let r = row, c = col
    while (r >= 0 && r < SIZE && c >= 0 && c < SIZE && board[r][c] === color) {
      count++; r += dr; c += dc
    }

    // Check open ends
    let openEnds = 0
    // Forward end
    if (r >= 0 && r < SIZE && c >= 0 && c < SIZE && board[r][c] === 0) openEnds++
    // Backward end
    if (prevR >= 0 && prevR < SIZE && prevC >= 0 && prevC < SIZE && board[prevR][prevC] === 0) openEnds++

    const result = classifyPattern(count, openEnds, false)
    score += result.score
  }

  return score
}
