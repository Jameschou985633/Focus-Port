<script setup>
import { computed, nextTick, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const rankLabels = {
  3: '3',
  4: '4',
  5: '5',
  6: '6',
  7: '7',
  8: '8',
  9: '9',
  10: '10',
  11: 'J',
  12: 'Q',
  13: 'K',
  14: 'A',
  15: '2',
  16: '小王',
  17: '大王'
}

const suits = [
  { id: 'S', label: '♠', color: 'black' },
  { id: 'H', label: '♥', color: 'red' },
  { id: 'C', label: '♣', color: 'black' },
  { id: 'D', label: '♦', color: 'red' }
]

const players = ref([
  { id: 'ai-left', name: '左家', role: '农民', hand: [] },
  { id: 'user', name: '你', role: '农民', hand: [] },
  { id: 'ai-right', name: '右家', role: '农民', hand: [] }
])
const landlordCards = ref([])
const selectedIds = ref(new Set())
const currentTurn = ref(1)
const landlordIndex = ref(null)
const phase = ref('bidding')
const message = ref('')
const lastPlay = ref(null)
const passCount = ref(0)
const winner = ref(null)
const history = ref([])
const busy = ref(false)

const user = computed(() => players.value[1])
const selectedCards = computed(() =>
  user.value.hand.filter(card => selectedIds.value.has(card.id)).sort(compareCards)
)
const selectedPattern = computed(() => describePattern(analyzeCards(selectedCards.value)))
const canPlaySelected = computed(() => {
  if (phase.value !== 'playing' || currentTurn.value !== 1 || selectedCards.value.length === 0) return false
  const pattern = analyzeCards(selectedCards.value)
  return Boolean(pattern && canBeat(pattern, lastPlay.value?.pattern || null))
})
const canPass = computed(() =>
  phase.value === 'playing' &&
  currentTurn.value === 1 &&
  Boolean(lastPlay.value && lastPlay.value.playerIndex !== 1)
)
const lastPlayText = computed(() => {
  if (!lastPlay.value) return '当前无人出牌'
  const names = players.value[lastPlay.value.playerIndex]?.name || '玩家'
  return `${names}：${describeCards(lastPlay.value.cards)}`
})

function makeDeck() {
  let serial = 0
  const deck = []
  for (let value = 3; value <= 15; value += 1) {
    for (const suit of suits) {
      deck.push({
        id: `${suit.id}-${value}-${serial++}`,
        value,
        rank: rankLabels[value],
        suit: suit.label,
        suitColor: suit.color
      })
    }
  }
  deck.push({ id: `J-16-${serial++}`, value: 16, rank: '小王', suit: '', suitColor: 'joker' })
  deck.push({ id: `J-17-${serial++}`, value: 17, rank: '大王', suit: '', suitColor: 'joker' })
  return shuffle(deck)
}

function shuffle(cards) {
  const copy = [...cards]
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

function compareCards(a, b) {
  if (b.value !== a.value) return b.value - a.value
  return a.id.localeCompare(b.id)
}

function sortHand(hand) {
  hand.sort(compareCards)
}

function deal() {
  const deck = makeDeck()
  players.value.forEach(player => {
    player.role = '农民'
    player.hand = []
  })
  for (let i = 0; i < 51; i += 1) {
    players.value[i % 3].hand.push(deck[i])
  }
  players.value.forEach(player => sortHand(player.hand))
  landlordCards.value = deck.slice(51).sort(compareCards)
  selectedIds.value = new Set()
  currentTurn.value = 1
  landlordIndex.value = null
  phase.value = 'bidding'
  message.value = '请选择是否抢地主'
  lastPlay.value = null
  passCount.value = 0
  winner.value = null
  history.value = []
  busy.value = false
}

function chooseLandlord(index) {
  landlordIndex.value = index
  players.value.forEach((player, playerIndex) => {
    player.role = playerIndex === index ? '地主' : '农民'
  })
  players.value[index].hand.push(...landlordCards.value)
  sortHand(players.value[index].hand)
  phase.value = 'playing'
  currentTurn.value = index
  message.value = `${players.value[index].name} 成为地主，先出牌`
  if (index !== 1) {
    void scheduleAiTurn()
  }
}

function userBid(grab) {
  if (phase.value !== 'bidding') return
  if (grab) {
    chooseLandlord(1)
    return
  }
  const aiIndex = pickAiLandlord()
  chooseLandlord(aiIndex)
}

function pickAiLandlord() {
  const leftScore = handScore(players.value[0].hand)
  const rightScore = handScore(players.value[2].hand)
  return leftScore >= rightScore ? 0 : 2
}

function handScore(hand) {
  return hand.reduce((sum, card) => sum + card.value, 0)
}

function toggleCard(card) {
  if (phase.value !== 'playing' || currentTurn.value !== 1) return
  const next = new Set(selectedIds.value)
  if (next.has(card.id)) {
    next.delete(card.id)
  } else {
    next.add(card.id)
  }
  selectedIds.value = next
}

function countByValue(cards) {
  const map = new Map()
  for (const card of cards) {
    map.set(card.value, (map.get(card.value) || 0) + 1)
  }
  return [...map.entries()].sort((a, b) => a[0] - b[0])
}

function isConsecutive(values) {
  for (let i = 1; i < values.length; i += 1) {
    if (values[i] !== values[i - 1] + 1) return false
  }
  return true
}

function analyzeCards(cards) {
  const sorted = [...cards].sort((a, b) => a.value - b.value)
  const length = sorted.length
  if (!length) return null
  const groups = countByValue(sorted)
  const values = groups.map(([value]) => value)
  const counts = groups.map(([, count]) => count)

  if (length === 2 && values.includes(16) && values.includes(17)) {
    return { type: 'joker_bomb', main: 17, length }
  }
  if (length === 4 && counts.length === 1) {
    return { type: 'bomb', main: values[0], length }
  }
  if (length === 1) {
    return { type: 'single', main: values[0], length }
  }
  if (length === 2 && counts[0] === 2) {
    return { type: 'pair', main: values[0], length }
  }
  if (length === 3 && counts[0] === 3) {
    return { type: 'triple', main: values[0], length }
  }
  if (length === 4 && counts.includes(3)) {
    return { type: 'triple_single', main: groups.find(([, count]) => count === 3)[0], length }
  }
  if (length === 5 && counts.includes(3) && counts.includes(2)) {
    return { type: 'triple_pair', main: groups.find(([, count]) => count === 3)[0], length }
  }
  if (length >= 5 && counts.every(count => count === 1) && values.every(value => value <= 14) && isConsecutive(values)) {
    return { type: 'straight', main: values.at(-1), length }
  }
  if (length >= 6 && length % 2 === 0 && counts.every(count => count === 2) && values.every(value => value <= 14) && isConsecutive(values)) {
    return { type: 'pair_sequence', main: values.at(-1), length }
  }
  return null
}

function describePattern(pattern) {
  if (!pattern) return '请选择有效牌型'
  const names = {
    single: '单张',
    pair: '对子',
    triple: '三张',
    triple_single: '三带一',
    triple_pair: '三带对',
    straight: '顺子',
    pair_sequence: '连对',
    bomb: '炸弹',
    joker_bomb: '王炸'
  }
  return names[pattern.type] || '有效牌型'
}

function canBeat(pattern, target) {
  if (!pattern) return false
  if (!target) return true
  if (pattern.type === 'joker_bomb') return target.type !== 'joker_bomb'
  if (target.type === 'joker_bomb') return false
  if (pattern.type === 'bomb' && target.type !== 'bomb') return true
  if (pattern.type !== target.type || pattern.length !== target.length) return false
  return pattern.main > target.main
}

function playSelected() {
  if (!canPlaySelected.value) {
    message.value = '这手牌暂时不能出'
    return
  }
  playCards(1, selectedCards.value)
  selectedIds.value = new Set()
  void scheduleAiTurn()
}

function playCards(playerIndex, cards) {
  const pattern = analyzeCards(cards)
  const ids = new Set(cards.map(card => card.id))
  players.value[playerIndex].hand = players.value[playerIndex].hand.filter(card => !ids.has(card.id))
  lastPlay.value = { playerIndex, cards: [...cards].sort(compareCards), pattern }
  passCount.value = 0
  history.value.unshift({
    id: `${Date.now()}-${playerIndex}`,
    player: players.value[playerIndex].name,
    text: `${describePattern(pattern)}：${describeCards(cards)}`
  })
  if (history.value.length > 6) history.value.pop()

  if (players.value[playerIndex].hand.length === 0) {
    phase.value = 'ended'
    winner.value = players.value[playerIndex]
    message.value = `${winner.value.name} 获胜`
    return
  }
  currentTurn.value = nextPlayer(playerIndex)
  message.value = `轮到 ${players.value[currentTurn.value].name}`
}

function passTurn() {
  if (!canPass.value) return
  selectedIds.value = new Set()
  history.value.unshift({ id: `${Date.now()}-pass-user`, player: '你', text: '不要' })
  passCount.value += 1
  if (passCount.value >= 2) {
    resetRoundAfterPasses(1)
  } else {
    currentTurn.value = nextPlayer(1)
    message.value = `轮到 ${players.value[currentTurn.value].name}`
  }
  void scheduleAiTurn()
}

function resetRoundAfterPasses(lastIndex) {
  const leadIndex = lastPlay.value?.playerIndex ?? lastIndex
  lastPlay.value = null
  passCount.value = 0
  currentTurn.value = leadIndex
  message.value = `${players.value[leadIndex].name} 重新领出`
}

function nextPlayer(index) {
  return (index + 1) % 3
}

async function scheduleAiTurn() {
  await nextTick()
  if (busy.value || phase.value !== 'playing' || currentTurn.value === 1) return
  busy.value = true
  window.setTimeout(() => {
    runAiTurns()
    busy.value = false
  }, 520)
}

function runAiTurns() {
  if (phase.value !== 'playing' || currentTurn.value === 1) return
  const aiIndex = currentTurn.value
  const aiCards = findAiPlay(players.value[aiIndex].hand, lastPlay.value)
  if (aiCards.length) {
    playCards(aiIndex, aiCards)
  } else {
    history.value.unshift({ id: `${Date.now()}-pass-${aiIndex}`, player: players.value[aiIndex].name, text: '不要' })
    passCount.value += 1
    if (passCount.value >= 2) {
      resetRoundAfterPasses(aiIndex)
    } else {
      currentTurn.value = nextPlayer(aiIndex)
      message.value = `轮到 ${players.value[currentTurn.value].name}`
    }
  }
  if (phase.value === 'playing' && currentTurn.value !== 1) {
    void scheduleAiTurn()
  }
}

function findAiPlay(hand, targetPlay) {
  const target = targetPlay?.pattern || null
  const candidates = buildCandidates(hand)
    .filter(cards => canBeat(analyzeCards(cards), target))
    .sort((a, b) => {
      const pa = analyzeCards(a)
      const pb = analyzeCards(b)
      const bombPenaltyA = pa.type.includes('bomb') ? 100 : 0
      const bombPenaltyB = pb.type.includes('bomb') ? 100 : 0
      return bombPenaltyA - bombPenaltyB || a.length - b.length || pa.main - pb.main
    })
  return candidates[0] || []
}

function buildCandidates(hand) {
  const groups = countByValue(hand).map(([value, count]) => ({
    value,
    cards: hand.filter(card => card.value === value).slice(0, count)
  }))
  const candidates = []

  for (const group of groups) {
    candidates.push([group.cards[0]])
    if (group.cards.length >= 2) candidates.push(group.cards.slice(0, 2))
    if (group.cards.length >= 3) candidates.push(group.cards.slice(0, 3))
    if (group.cards.length === 4) candidates.push(group.cards.slice(0, 4))
  }

  for (const triple of groups.filter(group => group.cards.length >= 3)) {
    const single = groups.find(group => group.value !== triple.value)?.cards[0]
    if (single) candidates.push([...triple.cards.slice(0, 3), single])
    const pair = groups.find(group => group.value !== triple.value && group.cards.length >= 2)
    if (pair) candidates.push([...triple.cards.slice(0, 3), ...pair.cards.slice(0, 2)])
  }

  candidates.push(...buildStraightCandidates(groups, 1, 5))
  candidates.push(...buildStraightCandidates(groups, 2, 3))

  const smallJoker = hand.find(card => card.value === 16)
  const bigJoker = hand.find(card => card.value === 17)
  if (smallJoker && bigJoker) candidates.push([smallJoker, bigJoker])

  return candidates
}

function buildStraightCandidates(groups, neededCount, minGroups) {
  const usable = groups.filter(group => group.value <= 14 && group.cards.length >= neededCount)
  const result = []
  for (let start = 0; start < usable.length; start += 1) {
    const run = [usable[start]]
    for (let i = start + 1; i < usable.length; i += 1) {
      if (usable[i].value === run.at(-1).value + 1) {
        run.push(usable[i])
        if (run.length >= minGroups) {
          result.push(run.flatMap(group => group.cards.slice(0, neededCount)))
        }
      } else {
        break
      }
    }
  }
  return result
}

function describeCards(cards) {
  return [...cards]
    .sort(compareCards)
    .map(card => card.value >= 16 ? card.rank : `${card.suit}${card.rank}`)
    .join(' ')
}

function restart() {
  deal()
}

function goBack() {
  router.push('/playground')
}

deal()
</script>

<template>
  <main class="ddz-page">
    <section class="ddz-table">
      <header class="topbar">
        <button class="ghost-btn" type="button" @click="goBack">返回</button>
        <div>
          <h1>斗地主</h1>
          <p>本地三人对局</p>
        </div>
        <button class="ghost-btn" type="button" @click="restart">重开</button>
      </header>

      <div class="table-layout">
        <aside class="opponent left-player" :class="{ active: currentTurn === 0 && phase === 'playing' }">
          <span class="role">{{ players[0].role }}</span>
          <strong>{{ players[0].name }}</strong>
          <span>{{ players[0].hand.length }} 张</span>
        </aside>

        <aside class="opponent right-player" :class="{ active: currentTurn === 2 && phase === 'playing' }">
          <span class="role">{{ players[2].role }}</span>
          <strong>{{ players[2].name }}</strong>
          <span>{{ players[2].hand.length }} 张</span>
        </aside>

        <section class="center-board">
          <div class="landlord-cards">
            <span v-for="card in landlordCards" :key="card.id" class="mini-card" :class="card.suitColor">
              {{ card.value >= 16 ? card.rank : `${card.suit}${card.rank}` }}
            </span>
          </div>

          <div class="status-panel">
            <span class="status">{{ message }}</span>
            <strong>{{ lastPlayText }}</strong>
          </div>

          <div class="last-cards">
            <div
              v-for="card in lastPlay?.cards || []"
              :key="card.id"
              class="played-card"
              :class="card.suitColor"
            >
              <span>{{ card.rank }}</span>
              <small>{{ card.suit }}</small>
            </div>
          </div>
        </section>
      </div>

      <section class="history">
        <div v-for="item in history" :key="item.id">
          <span>{{ item.player }}</span>
          <p>{{ item.text }}</p>
        </div>
      </section>

      <section class="controls" v-if="phase === 'bidding'">
        <button class="primary-btn" type="button" @click="userBid(true)">抢地主</button>
        <button class="secondary-btn" type="button" @click="userBid(false)">不抢</button>
      </section>

      <section class="controls" v-else-if="phase === 'playing'">
        <span class="pattern-text">{{ selectedPattern }}</span>
        <button class="secondary-btn" type="button" :disabled="!canPass" @click="passTurn">不要</button>
        <button class="primary-btn" type="button" :disabled="!canPlaySelected" @click="playSelected">出牌</button>
      </section>

      <section class="controls" v-else>
        <span class="pattern-text">{{ winner?.name }} 获胜</span>
        <button class="primary-btn" type="button" @click="restart">再来一局</button>
      </section>

      <section class="hand-zone" :class="{ active: currentTurn === 1 && phase === 'playing' }">
        <button
          v-for="card in user.hand"
          :key="card.id"
          type="button"
          class="card"
          :class="[card.suitColor, { selected: selectedIds.has(card.id) }]"
          @click="toggleCard(card)"
        >
          <span class="rank">{{ card.rank }}</span>
          <span class="suit">{{ card.suit }}</span>
        </button>
      </section>
    </section>
  </main>
</template>

<style scoped>
.ddz-page {
  min-height: 100dvh;
  overflow: hidden;
  padding: 18px;
  color: #f8fafc;
  background: #07111f;
  font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
}

.ddz-table {
  position: relative;
  display: grid;
  grid-template-rows: auto 1fr auto auto auto;
  gap: 12px;
  width: min(1180px, 100%);
  height: calc(100dvh - 36px);
  margin: 0 auto;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 20px;
  background:
    linear-gradient(rgba(6, 18, 33, 0.5), rgba(6, 18, 33, 0.76)),
    url('/ddz/table_bg_1.jpg') center / cover;
  box-shadow: 0 22px 70px rgba(0, 0, 0, 0.34);
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 18px 0;
}

.topbar h1 {
  margin: 0;
  font-size: 26px;
  text-align: center;
}

.topbar p {
  margin: 2px 0 0;
  color: rgba(248, 250, 252, 0.66);
  text-align: center;
  font-size: 13px;
}

.ghost-btn,
.primary-btn,
.secondary-btn {
  min-width: 84px;
  min-height: 38px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  color: #fff;
  font-weight: 700;
  cursor: pointer;
}

.ghost-btn {
  background: rgba(15, 23, 42, 0.72);
}

.primary-btn {
  background: linear-gradient(135deg, #f97316, #facc15);
  color: #1f1304;
}

.secondary-btn {
  background: rgba(15, 23, 42, 0.78);
}

.primary-btn:disabled,
.secondary-btn:disabled {
  cursor: not-allowed;
  opacity: 0.42;
}

.table-layout {
  position: relative;
  min-height: 0;
}

.opponent {
  position: absolute;
  top: 32px;
  display: grid;
  gap: 5px;
  width: 126px;
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 12px;
  background: rgba(5, 12, 24, 0.72);
}

.opponent.active {
  border-color: #facc15;
  box-shadow: 0 0 0 2px rgba(250, 204, 21, 0.2);
}

.left-player {
  left: 24px;
}

.right-player {
  right: 24px;
}

.role {
  width: fit-content;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(250, 204, 21, 0.16);
  color: #fde68a;
  font-size: 12px;
}

.center-board {
  display: grid;
  justify-items: center;
  align-content: start;
  gap: 14px;
  width: min(620px, calc(100% - 320px));
  min-height: 260px;
  margin: 0 auto;
  padding-top: 26px;
}

.landlord-cards {
  display: flex;
  gap: 8px;
  min-height: 34px;
}

.mini-card {
  display: inline-grid;
  place-items: center;
  min-width: 48px;
  height: 32px;
  padding: 0 8px;
  border-radius: 7px;
  background: #fff8ec;
  color: #111827;
  font-weight: 800;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
}

.status-panel {
  display: grid;
  gap: 6px;
  min-width: min(520px, 100%);
  padding: 14px 18px;
  border-radius: 12px;
  background: rgba(2, 6, 23, 0.6);
  text-align: center;
}

.status {
  color: #bae6fd;
  font-size: 14px;
}

.last-cards {
  display: flex;
  justify-content: center;
  min-height: 82px;
}

.played-card {
  display: grid;
  place-items: center;
  width: 48px;
  height: 68px;
  margin-left: -10px;
  border-radius: 8px;
  background: #fff9ef;
  color: #111827;
  font-weight: 900;
  box-shadow: 0 10px 22px rgba(0, 0, 0, 0.2);
}

.played-card:first-child {
  margin-left: 0;
}

.played-card small {
  font-size: 18px;
}

.history {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  min-height: 58px;
  max-height: 76px;
  padding: 0 18px;
  overflow-y: auto;
}

.history div {
  min-width: 0;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(2, 6, 23, 0.52);
}

.history span {
  display: block;
  color: #bfdbfe;
  font-size: 12px;
}

.history p {
  margin: 2px 0 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 44px;
  padding: 0 18px;
}

.pattern-text {
  min-width: 138px;
  color: #fde68a;
  font-weight: 800;
  text-align: right;
}

.hand-zone {
  display: flex;
  align-items: end;
  justify-content: center;
  min-height: 152px;
  padding: 0 20px 18px;
  overflow-x: auto;
}

.hand-zone.active {
  box-shadow: inset 0 -3px 0 rgba(250, 204, 21, 0.72);
}

.card {
  flex: 0 0 72px;
  width: 72px;
  height: 106px;
  margin-left: -26px;
  padding: 8px;
  border: 1px solid rgba(17, 24, 39, 0.16);
  border-radius: 10px;
  background:
    linear-gradient(160deg, rgba(255, 255, 255, 0.98), rgba(255, 247, 237, 0.96)),
    url('/ddz/card.png') center / 260px auto;
  color: #111827;
  cursor: pointer;
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.28);
  transition: transform 0.16s ease, box-shadow 0.16s ease;
}

.card:first-child {
  margin-left: 0;
}

.card.selected {
  transform: translateY(-22px);
  box-shadow: 0 18px 30px rgba(250, 204, 21, 0.28);
}

.rank,
.suit {
  display: block;
  text-align: left;
  line-height: 1;
}

.rank {
  font-size: 22px;
  font-weight: 900;
}

.suit {
  margin-top: 6px;
  font-size: 28px;
}

.red {
  color: #dc2626;
}

.black {
  color: #111827;
}

.joker {
  color: #7c2d12;
}

@media (max-width: 760px) {
  .ddz-page {
    padding: 10px;
  }

  .ddz-table {
    height: calc(100dvh - 20px);
    border-radius: 14px;
  }

  .topbar h1 {
    font-size: 20px;
  }

  .opponent {
    top: 18px;
    width: 94px;
    padding: 10px;
  }

  .left-player {
    left: 12px;
  }

  .right-player {
    right: 12px;
  }

  .center-board {
    width: calc(100% - 220px);
    min-height: 238px;
  }

  .history {
    grid-template-columns: 1fr;
  }

  .card {
    flex-basis: 58px;
    width: 58px;
    height: 90px;
    margin-left: -24px;
  }

  .rank {
    font-size: 18px;
  }

  .suit {
    font-size: 22px;
  }
}
</style>
